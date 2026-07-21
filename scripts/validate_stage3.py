#!/usr/bin/env python3
"""Validate the 100% Stage 3 forced-matching experiment."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGE2 = ROOT / "data" / "experiments" / "stage2-v1"
STAGE3 = ROOT / "data" / "experiments" / "stage3-v1"
BASE = ROOT / "data" / "releases" / "v1.0.0"
VALIDATION = ROOT / "reports" / "validation" / "stage3-v1"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    stage2 = read(STAGE2 / "stage2_placements.json")
    stage3 = read(STAGE3 / "stage3_placements.json")
    scores = read(BASE / "algorithm_scores.json")
    summary = read(STAGE3 / "stage3_summary.json")
    score_by_l4 = {row["l4_id"]: row for row in scores}
    stage2_by_l4 = {row["l4_id"]: row for row in stage2}
    stage3_by_l4 = {row["l4_id"]: row for row in stage3}
    checks = []

    def add(check_id: str, description: str, passed: bool, actual=None, expected=None) -> None:
        checks.append({"check_id": check_id, "description": description, "status": "PASS" if passed else "FAIL", "expected": expected, "actual": actual})

    add("S3-001", "Exactly one Stage 3 row per Stage 2 L4", len(stage3) == 1726 and set(stage3_by_l4) == set(stage2_by_l4), len(stage3), 1726)
    add("S3-002", "Every Stage 3 card has a non-null L3", all(row["stage3_l3_id"] for row in stage3), sum(not row["stage3_l3_id"] for row in stage3), 0)
    add("S3-003", "Stage 3 classified rate is exactly 100%", summary["classified_rate"] == 1.0, summary["classified_rate"], 1.0)
    forced = [row for row in stage3 if row["stage3_status"] == "forced_match_stage3"]
    add("S3-004", "Exactly the 173 Stage 2 holds are forced", len(forced) == 173, len(forced), 173)
    forced_source_failures = [row["l4_id"] for row in forced if stage2_by_l4[row["l4_id"]]["stage2_status"] != "needs_taxonomy_decision"]
    add("S3-005", "Every forced card was unresolved in Stage 2", not forced_source_failures, len(forced_source_failures), 0)
    missing_forced = [row["l4_id"] for row in stage2 if row["stage2_status"] == "needs_taxonomy_decision" and stage3_by_l4[row["l4_id"]]["stage3_status"] != "forced_match_stage3"]
    add("S3-006", "Every Stage 2 hold is forced in Stage 3", not missing_forced, len(missing_forced), 0)
    preserved_failures = [
        row["l4_id"] for row in stage2
        if row["stage2_l3_id"] is not None
        and stage3_by_l4[row["l4_id"]]["stage3_l3_id"] != row["stage2_l3_id"]
    ]
    add("S3-007", "All 1,553 Stage 2 placements remain unchanged", not preserved_failures, len(preserved_failures), 0)
    top1_failures = [row["l4_id"] for row in forced if row["stage3_l3_id"] != score_by_l4[row["l4_id"]]["top1_l3_id"]]
    add("S3-008", "Every forced match uses its recorded hierarchy-blind top1 L3", not top1_failures, len(top1_failures), 0)
    reason_failures = [row["l4_id"] for row in forced if row["forced_from_stage2_hold_reason"] != stage2_by_l4[row["l4_id"]]["stage2_hold_reason"]]
    add("S3-009", "Every forced match preserves its Stage 2 hold reason", not reason_failures, len(reason_failures), 0)
    physical_failures = [row["l4_id"] for row in stage3 if row["stage2_status"] == "locked_physical" and (row["stage3_status"] != "locked_physical" or row["forced_match"])]
    add("S3-010", "Physical 182 remain locked and unforced", not physical_failures, len(physical_failures), 0)
    add("S3-011", "No Stage 3 row claims human approval", not any(row["human_approved"] for row in stage3), sum(row["human_approved"] for row in stage3), 0)
    add("S3-012", "Legacy hierarchy remains excluded", not any(row["legacy_hierarchy_used_as_feature"] for row in stage3), sum(row["legacy_hierarchy_used_as_feature"] for row in stage3), 0)
    add("S3-013", "All forced matches remain explicitly uncalibrated", all(row["confidence_calibrated"] is False for row in forced), sum(row["confidence_calibrated"] is not False for row in forced), 0)
    add("S3-014", "Largest final L3 share stays below 20%", summary["largest_l3_share"] < 0.20, summary["largest_l3_share"], "<0.20")

    failed = [row for row in checks if row["status"] == "FAIL"]
    result = {
        "stage3_id": "stage3-v1",
        "status": "PASS_WITH_WARNINGS" if not failed else "FAIL",
        "passed_checks": len(checks) - len(failed),
        "failed_checks": len(failed),
        "warning_count": len(summary["warnings"]),
        "warnings": summary["warnings"],
        "checks": checks,
        "artifact_hashes": {
            "stage3_config.json": sha256(STAGE3 / "stage3_config.json"),
            "stage3_placements.json": sha256(STAGE3 / "stage3_placements.json"),
            "stage3_forced_matches.json": sha256(STAGE3 / "stage3_forced_matches.json"),
            "stage3_summary.json": sha256(STAGE3 / "stage3_summary.json"),
        },
    }
    VALIDATION.mkdir(parents=True, exist_ok=True)
    (VALIDATION / "validation_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
