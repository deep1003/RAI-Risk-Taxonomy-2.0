#!/usr/bin/env python3
"""Validate Stage 2 experimental placements against the immutable baseline."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "releases" / "v1.0.0"
STAGE2 = ROOT / "data" / "experiments" / "stage2-v1"
VALIDATION = ROOT / "reports" / "validation" / "stage2-v1"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    baseline = read(BASE / "placements.json")
    stage2 = read(STAGE2 / "stage2_placements.json")
    config = read(STAGE2 / "stage2_config.json")
    summary = read(STAGE2 / "stage2_summary.json")
    baseline_by_l4 = {row["l4_id"]: row for row in baseline}
    stage2_by_l4 = {row["l4_id"]: row for row in stage2}
    checks = []

    def add(check_id: str, description: str, passed: bool, actual=None, expected=None) -> None:
        checks.append(
            {
                "check_id": check_id,
                "description": description,
                "status": "PASS" if passed else "FAIL",
                "expected": expected,
                "actual": actual,
            }
        )

    add("S2-001", "Exactly one Stage 2 row per baseline L4", len(stage2) == 1726 and set(stage2_by_l4) == set(baseline_by_l4), len(stage2), 1726)
    add("S2-002", "Stage 2 L4 IDs remain unique", len(stage2_by_l4) == 1726, len(stage2_by_l4), 1726)
    status_counts = Counter(row["stage2_status"] for row in stage2)
    add("S2-003", "Physical 182 placements remain locked", status_counts["locked_physical"] == 182, status_counts["locked_physical"], 182)
    physical_failures = [
        row["l4_id"]
        for row in stage2
        if baseline_by_l4[row["l4_id"]]["assignment_status"] == "locked_physical"
        and (
            row["stage2_status"] != "locked_physical"
            or row["stage2_l3_id"] != baseline_by_l4[row["l4_id"]]["primary_l3_id"]
        )
    ]
    add("S2-004", "Every Physical card preserves its exact L3", not physical_failures, len(physical_failures), 0)
    stage1_proposals = [row for row in baseline if row["assignment_status"] == "algorithm_proposed"]
    stage1_failures = [
        row["l4_id"]
        for row in stage1_proposals
        if stage2_by_l4[row["l4_id"]]["stage2_l3_id"] != row["primary_l3_id"]
        or stage2_by_l4[row["l4_id"]]["stage2_status"] != "stage1_algorithm_proposed"
    ]
    add("S2-005", "All 37 Stage 1 consensus proposals remain unchanged", not stage1_failures, len(stage1_failures), 0)
    add("S2-006", "Stage 2 leaves exactly 173 cards unresolved", status_counts["needs_taxonomy_decision"] == 173, status_counts["needs_taxonomy_decision"], 173)
    add("S2-007", "Stage 2 unresolved rate is approximately 10%", abs(summary["actual_unclassified_rate"] - 0.10) <= 0.001, summary["actual_unclassified_rate"], 0.10)
    add("S2-008", "No Stage 2 row claims human approval", all(row["human_approved"] is False for row in stage2), sum(row["human_approved"] is True for row in stage2), 0)
    add("S2-009", "Legacy global hierarchy remains excluded", all(row["legacy_hierarchy_used_as_feature"] is False for row in stage2), sum(row["legacy_hierarchy_used_as_feature"] is not False for row in stage2), 0)
    null_failures = [row["l4_id"] for row in stage2 if (row["stage2_status"] == "needs_taxonomy_decision") != (row["stage2_l3_id"] is None)]
    add("S2-010", "Only unresolved cards have null Stage 2 L3", not null_failures, len(null_failures), 0)
    hard_reasons = set(config["hard_hold_reasons"])
    hard_failures = [
        row["l4_id"]
        for row in stage2
        if row["stage1_abstention_reason"] in hard_reasons
        and row["stage2_status"] != "needs_taxonomy_decision"
    ]
    add("S2-011", "Every hard-hold reason remains unresolved", not hard_failures, len(hard_failures), 0)
    add("S2-012", "Largest L3 share stays below 20% of assigned cards", summary["largest_l3_share_of_all_assigned"] < 0.20, summary["largest_l3_share_of_all_assigned"], "<0.20")
    add("S2-013", "Stage 2 configuration remains explicitly uncalibrated", config["confidence_calibrated"] is False, config["confidence_calibrated"], False)

    failed = [row for row in checks if row["status"] == "FAIL"]
    result = {
        "stage2_id": "stage2-v1",
        "status": "PASS_WITH_WARNINGS" if not failed else "FAIL",
        "passed_checks": len(checks) - len(failed),
        "failed_checks": len(failed),
        "warning_count": 3,
        "warnings": summary["warnings"],
        "checks": checks,
        "artifact_hashes": {
            "stage2_config.json": sha256(STAGE2 / "stage2_config.json"),
            "stage2_placements.json": sha256(STAGE2 / "stage2_placements.json"),
            "stage2_summary.json": sha256(STAGE2 / "stage2_summary.json"),
            "stage2_hold_queue.json": sha256(STAGE2 / "stage2_hold_queue.json"),
        },
    }
    VALIDATION.mkdir(parents=True, exist_ok=True)
    (VALIDATION / "validation_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
