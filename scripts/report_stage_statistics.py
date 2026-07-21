#!/usr/bin/env python3
"""Create auditable Stage 2 hold and Stage 3 distribution statistics."""

from __future__ import annotations

import csv
import json
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "statistics"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def quantiles(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    pick = lambda q: ordered[round((len(ordered) - 1) * q)]
    return {
        "min": min(ordered),
        "p10": pick(0.10),
        "p25": pick(0.25),
        "median": statistics.median(ordered),
        "mean": statistics.mean(ordered),
        "p75": pick(0.75),
        "p90": pick(0.90),
        "max": max(ordered),
    }


def main() -> None:
    holds = load_json(ROOT / "data/experiments/stage2-v1/stage2_hold_queue.json")
    stage3 = load_json(ROOT / "data/experiments/stage3-v1/stage3_placements.json")
    nodes = load_json(ROOT / "data/releases/v1.0.0/taxonomy_nodes.json")
    node_by_id = {row["node_id"]: row for row in nodes}
    forced = [row for row in stage3 if row["forced_match"]]

    def ancestor(node_id: str, level: int) -> dict:
        node = node_by_id[node_id]
        while node["level"] != level:
            node = node_by_id[node["parent_id"]]
        return node

    hold_summary = {
        "stage2_id": "stage2-v1",
        "denominator_all_l4": len(stage3),
        "unclassified_count": len(holds),
        "unclassified_share": len(holds) / len(stage3),
        "hold_reason_counts": dict(Counter(row["stage2_hold_reason"] for row in holds)),
        "hold_class_counts": {
            "hard_hold": sum(row["stage2_hold_reason"] != "BOTTOM_10_PERCENT_SUITABILITY_RESERVE" for row in holds),
            "quota_hold": sum(row["stage2_hold_reason"] == "BOTTOM_10_PERCENT_SUITABILITY_RESERVE" for row in holds),
        },
        "rule_support": dict(Counter(str(row["rule_supported"]).lower() for row in holds)),
        "gap_sentinel_present": sum(bool(row["gap_sentinels"]) for row in holds),
        "anchor_top1_votes": dict(sorted(Counter(row["anchor_top1_votes"] for row in holds).items())),
        "score_profile": {
            field: quantiles([row[field] for row in holds])
            for field in ("stage2_suitability_score", "top1_semantic_score", "semantic_margin", "composite_margin")
        },
    }

    def distribution(rows: list[dict], level: int) -> list[dict]:
        counts = Counter(ancestor(row["stage3_l3_id"], level)["node_id"] for row in rows)
        return [
            {
                "node_id": node_id,
                "label_en": node_by_id[node_id]["label_en"],
                "count": count,
                "share": count / len(rows),
            }
            for node_id, count in counts.most_common()
        ]

    l3_counts = Counter(row["stage3_l3_id"] for row in stage3)
    forced_l3_counts = Counter(row["stage3_l3_id"] for row in forced)
    stage3_summary = {
        "stage3_id": "stage3-v1",
        "total_l4": len(stage3),
        "classified_count": sum(row["stage3_l3_id"] is not None for row in stage3),
        "classified_share": 1.0,
        "unclassified_count": 0,
        "status_counts": dict(Counter(row["stage3_status"] for row in stage3)),
        "stage2_fit_tier_counts": dict(Counter(row["stage2_fit_tier"] for row in stage3)),
        "forced_count": len(forced),
        "forced_share": len(forced) / len(stage3),
        "forced_review_priority_counts": dict(Counter(row["stage3_review_priority"] for row in forced)),
        "l1_distribution": distribution(stage3, 1),
        "l2_distribution": distribution(stage3, 2),
        "l3_nonempty_count": len(l3_counts),
        "l3_median_card_count": statistics.median(l3_counts.values()),
        "l3_top5_share": sum(v for _, v in l3_counts.most_common(5)) / len(stage3),
        "l3_hhi": sum((v / len(stage3)) ** 2 for v in l3_counts.values()),
        "forced_l1_distribution": distribution(forced, 1),
        "forced_l2_distribution": distribution(forced, 2),
        "forced_l3_nonempty_count": len(forced_l3_counts),
        "forced_l3_top5_share": sum(v for _, v in forced_l3_counts.most_common(5)) / len(forced),
        "forced_l3_hhi": sum((v / len(forced)) ** 2 for v in forced_l3_counts.values()),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT / "stage2_unclassified_statistics.json", hold_summary)
    write_json(OUT / "stage3_statistics.json", stage3_summary)
    with (OUT / "stage3_l3_statistics.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["l3_id", "l3_name", "final_count", "final_share", "forced_count", "forced_share"])
        writer.writeheader()
        for l3_id, final_count in l3_counts.most_common():
            forced_count = forced_l3_counts[l3_id]
            writer.writerow({
                "l3_id": l3_id,
                "l3_name": node_by_id[l3_id]["label_en"],
                "final_count": final_count,
                "final_share": round(final_count / len(stage3), 6),
                "forced_count": forced_count,
                "forced_share": round(forced_count / len(forced), 6),
            })

    print(json.dumps({"stage2_unclassified": hold_summary, "stage3": stage3_summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
