#!/usr/bin/env python3
"""Force-match the 173 Stage 2 holds while preserving all prior placements."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STAGE2_ID = "stage2-v1"
STAGE3_ID = "stage3-v1"
HARD_HOLD_REASONS = {
    "PHYSICAL_OUTSIDE_LOCK",
    "FRONTIER_EXPERT_REJECTED",
    "FRONTIER_EXPERT_DISAGREEMENT",
    "MULTI_MECHANISM",
    "LOW_ABSOLUTE_FIT",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def csv_value(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return value


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        if columns:
            writer.writeheader()
            for row in rows:
                writer.writerow({key: csv_value(row.get(key)) for key in columns})


def main() -> None:
    release_dir = ROOT / "data" / "releases" / "v1.0.0"
    stage2_dir = ROOT / "data" / "experiments" / STAGE2_ID
    output_dir = ROOT / "data" / "experiments" / STAGE3_ID
    validation_dir = ROOT / "reports" / "validation" / STAGE3_ID

    stage2_rows = read_json(stage2_dir / "stage2_placements.json")
    scores = read_json(release_dir / "algorithm_scores.json")
    nodes = read_json(release_dir / "taxonomy_nodes.json")
    score_by_l4 = {row["l4_id"]: row for row in scores}
    l3_ids = {row["node_id"] for row in nodes if row["level"] == 3}

    stage3_rows = []
    forced_rows = []
    for stage2 in stage2_rows:
        row = dict(stage2)
        if stage2["stage2_status"] == "needs_taxonomy_decision":
            score = score_by_l4[stage2["l4_id"]]
            stage3_l3_id = score["top1_l3_id"]
            if stage3_l3_id not in l3_ids:
                raise ValueError(f"Unknown forced L3: {stage3_l3_id}")
            hold_reason = stage2["stage2_hold_reason"]
            forced_hold_class = "hard_hold" if hold_reason in HARD_HOLD_REASONS else "quota_hold"
            row.update(
                {
                    "stage3_id": STAGE3_ID,
                    "stage3_status": "forced_match_stage3",
                    "stage3_l3_id": stage3_l3_id,
                    "stage3_method": "forced_hierarchy_blind_top1",
                    "forced_match": True,
                    "forced_from_stage2_hold_reason": hold_reason,
                    "forced_hold_class": forced_hold_class,
                    "stage3_review_priority": "critical" if forced_hold_class == "hard_hold" else "high",
                    "requires_human_review": True,
                    "human_approved": False,
                    "confidence_calibrated": False,
                }
            )
            forced_rows.append(row)
        else:
            row.update(
                {
                    "stage3_id": STAGE3_ID,
                    "stage3_status": stage2["stage2_status"],
                    "stage3_l3_id": stage2["stage2_l3_id"],
                    "stage3_method": "stage2_placement_preserved",
                    "forced_match": False,
                    "forced_from_stage2_hold_reason": None,
                    "forced_hold_class": None,
                    "stage3_review_priority": "normal" if stage2["requires_human_review"] else "locked_gold",
                    "confidence_calibrated": False,
                }
            )
        stage3_rows.append(row)

    stage3_status_counts = Counter(row["stage3_status"] for row in stage3_rows)
    forced_reason_counts = Counter(row["forced_from_stage2_hold_reason"] for row in forced_rows)
    forced_l3_counts = Counter(row["stage3_l3_id"] for row in forced_rows)
    assigned_l3_counts = Counter(row["stage3_l3_id"] for row in stage3_rows)
    distribution = [
        {
            "l3_id": l3_id,
            "stage3_card_count": count,
            "share_of_all_cards": round(count / 1726, 6),
            "forced_stage3_count": forced_l3_counts[l3_id],
        }
        for l3_id, count in sorted(assigned_l3_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    summary = {
        "stage3_id": STAGE3_ID,
        "input_stage2_id": STAGE2_ID,
        "base_release_id": "v1.0.0",
        "classification_authority": "forced_algorithmic_mapping_not_human_approved",
        "total_cards": len(stage3_rows),
        "classified_count": sum(row["stage3_l3_id"] is not None for row in stage3_rows),
        "classified_rate": round(sum(row["stage3_l3_id"] is not None for row in stage3_rows) / 1726, 6),
        "unclassified_count": sum(row["stage3_l3_id"] is None for row in stage3_rows),
        "stage3_status_counts": dict(stage3_status_counts),
        "forced_match_count": len(forced_rows),
        "forced_hard_hold_count": sum(row["forced_hold_class"] == "hard_hold" for row in forced_rows),
        "forced_quota_hold_count": sum(row["forced_hold_class"] == "quota_hold" for row in forced_rows),
        "forced_reason_counts": dict(forced_reason_counts),
        "forced_l3_counts": dict(forced_l3_counts),
        "largest_l3_id": distribution[0]["l3_id"],
        "largest_l3_count": distribution[0]["stage3_card_count"],
        "largest_l3_share": distribution[0]["share_of_all_cards"],
        "physical_locks_changed": 0,
        "stage1_consensus_changed": 0,
        "stage2_assignments_changed": 0,
        "human_approved_count": 0,
        "legacy_hierarchy_used_as_feature": False,
        "warnings": [
            "Stage 3 is a 100% forced mapping, not a validated taxonomy ground truth.",
            "All 173 former holds require human review; 55 originated from hard-hold reasons.",
            "Forced mappings preserve the original hold reason and must remain visibly distinguishable in any UI or export.",
            "Coverage completeness must not be interpreted as evidence that the 50 L3 taxonomy is sufficient.",
        ],
    }
    config = {
        "stage3_id": STAGE3_ID,
        "input_stage2_id": STAGE2_ID,
        "selection_rule": "Preserve every non-null Stage 2 placement. For each of the 173 Stage 2 holds, assign the existing hierarchy-blind BGE/rule top1_l3_id regardless of hard-hold or quota-hold reason.",
        "forced_status": "forced_match_stage3",
        "preserve_original_hold_reason": True,
        "confidence_calibrated": False,
        "human_approved": False,
        "legacy_hierarchy_used_as_feature": False,
    }

    write_json(output_dir / "stage3_config.json", config)
    write_json(output_dir / "stage3_placements.json", stage3_rows)
    write_csv(output_dir / "stage3_placements.csv", stage3_rows)
    write_json(output_dir / "stage3_forced_matches.json", forced_rows)
    write_csv(output_dir / "stage3_forced_matches.csv", forced_rows)
    write_json(output_dir / "stage3_summary.json", summary)
    write_csv(output_dir / "stage3_l3_distribution.csv", distribution)
    write_json(validation_dir / "stage3_summary.json", summary)
    write_json(validation_dir / "stage3_forced_matches.json", forced_rows)
    write_csv(validation_dir / "stage3_l3_distribution.csv", distribution)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
