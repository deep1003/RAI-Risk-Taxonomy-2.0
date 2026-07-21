#!/usr/bin/env python3
"""Apply only exact two-reviewer consensus amendments to release v2.1.0."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/data/releases/v2.1.0"
OUT = ROOT / "public/data/releases/v2.2.0"
REVIEWS = ROOT / "reports/expert_review/v2.1"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    cards = read(SOURCE / "cards.json")["cards"]
    hierarchy = read(SOURCE / "hierarchy.json")
    reviews = [read(REVIEWS / "reviewer_a.json"), read(REVIEWS / "reviewer_b.json")]
    proposals = [{row["l4_id"]: row for row in review["proposals"]} for review in reviews]
    union_ids = set(proposals[0]) | set(proposals[1])
    consensus = {}
    disagreements = []
    for l4_id in sorted(union_ids):
        left, right = proposals[0].get(l4_id), proposals[1].get(l4_id)
        if (
            left and right
            and left["proposed_label"] == right["proposed_label"]
            and left.get("proposed_l3_id") == right.get("proposed_l3_id")
            and left["confidence"] == right["confidence"] == "high"
        ):
            consensus[l4_id] = left
        else:
            disagreements.append({
                "l4_id": l4_id,
                "reviewer_a": left,
                "reviewer_b": right,
                "action": "retain_current_card_and_mark_hold",
            })

    output = []
    for original in cards:
        card = dict(original)
        card["release_id"] = "v2.2.0"
        if card["l4_id"] in consensus:
            proposal = consensus[card["l4_id"]]
            card.update({
                "original_label_en": card["label_en"],
                "label_en": proposal["proposed_label"],
                "primary_l3_id": proposal["proposed_l3_id"] or card["primary_l3_id"],
                "decision_required": False,
                "decision_reason": None,
                "review_status": "two_reviewer_consensus",
                "expert_consensus_approved": True,
                "expert_reviewers": [reviews[0]["reviewer"], reviews[1]["reviewer"]],
                "expert_review_rationale": proposal["rationale"],
            })
        elif card["l4_id"] in union_ids:
            card.update({
                "decision_required": True,
                "decision_reason": card.get("decision_reason") or "EXPERT_REVIEW_NO_CONSENSUS",
                "review_status": "expert_review_no_consensus",
                "expert_consensus_approved": False,
            })
        output.append(card)

    hierarchy["release_id"] = "v2.2.0"
    cards_path, hierarchy_path = OUT / "cards.json", OUT / "hierarchy.json"
    write(cards_path, {"release_id": "v2.2.0", "cards": output})
    write(hierarchy_path, hierarchy)
    report = {
        "reviewed_count_per_reviewer": [review["reviewed_count"] for review in reviews],
        "reviewer_proposal_counts": [len(review["proposals"]) for review in reviews],
        "consensus_count": len(consensus),
        "consensus_amendments": [
            {
                "l4_id": l4_id,
                "old_label": next(card["label_en"] for card in cards if card["l4_id"] == l4_id),
                "new_label": row["proposed_label"],
                "l3_id": row["proposed_l3_id"],
            }
            for l4_id, row in sorted(consensus.items())
        ],
        "no_consensus_count": len(disagreements),
        "no_consensus": disagreements,
        "physical_cards_changed": sum(
            card["assignment_status"] == "locked_physical" and card["l4_id"] in consensus
            for card in cards
        ),
    }
    write(REVIEWS / "consensus_result.json", report)
    manifest = {
        "release_id": "v2.2.0",
        "source_release": "v2.1.0",
        "release_status": "two_reviewer_consensus_amended",
        "counts": {
            "l4": len(output),
            "classified": sum(card["primary_l3_id"] is not None for card in output),
            "physical_locked": sum(card["assignment_status"] == "locked_physical" for card in output),
            "decision_required": sum(card["decision_required"] for card in output),
            "expert_consensus_amendments": len(consensus),
            "expert_no_consensus": len(disagreements),
            "l3_nodes": sum(node["level"] == 3 for node in hierarchy["nodes"]),
        },
        "artifacts": [
            {"path": "cards.json", "sha256": sha256(cards_path)},
            {"path": "hierarchy.json", "sha256": sha256(hierarchy_path)},
            {"path": "reports/expert_review/v2.1/consensus_result.json"},
        ],
    }
    write(OUT / "manifest.json", manifest)
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
