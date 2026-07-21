#!/usr/bin/env python3
"""Create a Stage 3 policy view that separates the 55 hard holds."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/experiments/stage3-v1/stage3_placements.json"
OUT = ROOT / "data/experiments/stage3-review-hold-v1"
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
        is_review_hold = (
            row["stage3_status"] == "forced_match_stage3"
            and row["forced_from_stage2_hold_reason"] in HARD_REASONS
        )
        row.update(
            {
                "policy_view_id": "stage3-review-hold-v1",
                "policy_status": "needs_taxonomy_decision" if is_review_hold else row["stage3_status"],
                "policy_l3_id": None if is_review_hold else row["stage3_l3_id"],
                "operational_bucket_id": "RAI-HOLD" if is_review_hold else None,
                "operational_bucket_name": "Taxonomy Decision Hold" if is_review_hold else None,
                "excluded_from_taxonomy_distribution": is_review_hold,
            }
        )
        rows.append(row)

    holds = [row for row in rows if row["operational_bucket_id"] == "RAI-HOLD"]
    classified = [row for row in rows if row["policy_l3_id"] is not None]
    summary = {
        "policy_view_id": "stage3-review-hold-v1",
        "source_experiment": "stage3-v1",
        "total_l4": len(rows),
        "classified_count": len(classified),
        "classified_share": len(classified) / len(rows),
        "review_hold_count": len(holds),
        "review_hold_share": len(holds) / len(rows),
        "review_hold_bucket": {
            "id": "RAI-HOLD",
            "name": "Taxonomy Decision Hold",
            "taxonomy_level": None,
            "is_l3": False,
        },
        "hold_reason_counts": dict(Counter(row["forced_from_stage2_hold_reason"] for row in holds)),
        "remaining_stage3_forced_count": sum(
            row["policy_status"] == "forced_match_stage3" for row in rows
        ),
        "human_approved_hold_count": sum(row["human_approved"] for row in holds),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "placements.json", rows)
    write_json(OUT / "review_hold.json", holds)
    write_json(OUT / "summary.json", summary)
    with (OUT / "review_hold.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fields = [
            "l4_id", "label_en", "stage2_hold_reason", "stage2_suitability_score",
            "top1_semantic_score", "stage3_l3_id", "operational_bucket_id",
            "policy_status", "stage3_review_priority",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(holds)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
