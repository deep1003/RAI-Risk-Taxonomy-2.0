#!/usr/bin/env python3
"""Create the Stage 3 forced policy view with decision-required markers."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/experiments/stage3-v1/stage3_placements.json"
OUT = ROOT / "data/experiments/stage3-forced-policy-v2"
HARD_REASONS = {
    "PHYSICAL_OUTSIDE_LOCK",
    "FRONTIER_EXPERT_REJECTED",
    "FRONTIER_EXPERT_DISAGREEMENT",
    "MULTI_MECHANISM",
    "LOW_ABSOLUTE_FIT",
}


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = []
    for original in source:
        row = dict(original)
        decision_required = (
            row["stage3_status"] == "forced_match_stage3"
            and row["forced_from_stage2_hold_reason"] in HARD_REASONS
        )
        row.update(
            {
                "policy_view_id": "stage3-forced-policy-v2",
                "policy_status": row["stage3_status"],
                "policy_l3_id": row["stage3_l3_id"],
                "decision_required": decision_required,
                "decision_reason": row["forced_from_stage2_hold_reason"] if decision_required else None,
                "operational_bucket_id": None,
                "operational_bucket_name": None,
                "excluded_from_taxonomy_distribution": False,
            }
        )
        rows.append(row)

    marked = [row for row in rows if row["decision_required"]]
    classified = [row for row in rows if row["policy_l3_id"] is not None]
    summary = {
        "policy_view_id": "stage3-forced-policy-v2",
        "source_experiment": "stage3-v1",
        "total_l4": len(rows),
        "classified_count": len(classified),
        "classified_share": len(classified) / len(rows),
        "decision_required_count": len(marked),
        "decision_required_share": len(marked) / len(rows),
        "decision_reason_counts": dict(Counter(row["decision_reason"] for row in marked)),
        "remaining_stage3_forced_count": sum(
            row["policy_status"] == "forced_match_stage3" for row in rows
        ),
        "human_approved_decision_required_count": sum(row["human_approved"] for row in marked),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "placements.json", rows)
    write_json(OUT / "decision_required.json", marked)
    write_json(OUT / "summary.json", summary)
    with (OUT / "decision_required.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = [
            "l4_id", "label_en", "stage2_hold_reason", "stage2_suitability_score",
            "top1_semantic_score", "stage3_l3_id", "decision_required",
            "decision_reason", "policy_status", "stage3_review_priority",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(marked)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
