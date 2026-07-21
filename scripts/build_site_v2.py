#!/usr/bin/env python3
"""Build the public RAI Risk Taxonomy 2.0 site bundle."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "public/data/releases/v1.0.0"
POLICY = ROOT / "data/experiments/stage3-review-hold-v1/placements.json"
OUT = ROOT / "public/data/releases/v2.0.0"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    base_cards = load(BASE / "cards.json")["cards"]
    hierarchy = load(BASE / "hierarchy.json")
    policy = load(POLICY)
    policy_by_id = {row["l4_id"]: row for row in policy}
    assert len(base_cards) == len(policy_by_id) == 1726

    status_map = {
        "locked_physical": "locked_physical",
        "stage1_algorithm_proposed": "stage1_consensus",
        "algorithm_proposed_stage2": "stage2_proposed",
        "forced_match_stage3": "stage3_forced",
        "needs_taxonomy_decision": "needs_taxonomy_decision",
    }
    cards = []
    for base in base_cards:
        placement = policy_by_id[base["l4_id"]]
        card = dict(base)
        card.update(
            {
                "release_id": "v2.0.0",
                "primary_l3_id": placement["policy_l3_id"],
                "assignment_status": status_map[placement["policy_status"]],
                "review_status": "taxonomy_decision_hold" if placement["policy_l3_id"] is None else "human_review_required",
                "operational_bucket_id": placement["operational_bucket_id"],
                "stage2_hold_reason": placement["stage2_hold_reason"],
                "forced_candidate_l3_id": placement["stage3_l3_id"] if placement["policy_l3_id"] is None else None,
                "stage2_suitability_score": placement["stage2_suitability_score"],
                "human_approved": placement["human_approved"],
            }
        )
        cards.append(card)

    hierarchy["release_id"] = "v2.0.0"
    hierarchy_path = OUT / "hierarchy.json"
    cards_path = OUT / "cards.json"
    write(hierarchy_path, hierarchy)
    write(cards_path, {"release_id": "v2.0.0", "cards": cards})

    counts = {status: sum(card["assignment_status"] == status for card in cards) for status in status_map.values()}
    manifest = {
        "release_id": "v2.0.0",
        "release_status": "technical_report_2.0_policy_view",
        "provisional": True,
        "created_at": "2026-07-21T00:00:00+09:00",
        "policy_view_id": "stage3-review-hold-v1",
        "counts": {
            "l4": len(cards),
            "classified": sum(card["primary_l3_id"] is not None for card in cards),
            "physical_locked": counts["locked_physical"],
            "stage1_consensus": counts["stage1_consensus"],
            "stage2_proposed": counts["stage2_proposed"],
            "stage3_forced": counts["stage3_forced"],
            "needs_taxonomy_decision": counts["needs_taxonomy_decision"],
            "l3_nodes": sum(node["level"] == 3 for node in hierarchy["nodes"]),
        },
        "human_approval": {
            "algorithmic_placements_approved": False,
            "hold_is_taxonomy_node": False,
        },
        "artifacts": [
            {"path": "hierarchy.json", "sha256": sha256(hierarchy_path)},
            {"path": "cards.json", "sha256": sha256(cards_path)},
            {"path": "reports/pdf/rai_risk_taxonomy_technical_report_2_0_en.pdf"},
        ],
    }
    write(OUT / "manifest.json", manifest)
    print(json.dumps(manifest["counts"], indent=2))


if __name__ == "__main__":
    main()
