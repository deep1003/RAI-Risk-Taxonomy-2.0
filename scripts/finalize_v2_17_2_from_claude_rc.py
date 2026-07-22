#!/usr/bin/env python3
"""Finalize v2.17.2 from Claude's v2.17.2-rc L4 edits and BGE-M3 audit.

All 1,711 L4 IDs are preserved. Retired IDs remain in cards.json with
merged_into provenance. BGE-M3 proposals are reflected conservatively: active
non-Physical cards are moved into the domain HOLD review path and their
semantic destination is stored in hold_semantic_path. Existing HOLD cards keep
their HOLD primary path and receive an updated semantic path.
"""

from __future__ import annotations

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "public/data/releases/v2.17.2-rc"
OUT = ROOT / "public/data/releases/v2.17.2"
HIER_SRC = ROOT / "public/data/releases/v2.17.1/hierarchy.json"
AUDIT = ROOT / "reports/validation/v2.17.2/bge_m3_active"


def load_json(path: Path):
    return json.loads(path.read_text())


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cards_payload = load_json(SRC / "cards.json")
    cards = deepcopy(cards_payload["cards"])
    hierarchy = load_json(HIER_SRC)
    manifest_rc = load_json(SRC / "manifest.json")
    reliability = load_json(AUDIT / "reliability_results.json")
    moves = load_json(AUDIT / "reassignment_proposals.json")
    nodes = {node["node_id"]: node for node in hierarchy["nodes"]}
    parent = {node["node_id"]: node.get("parent_id") for node in hierarchy["nodes"]}
    cards_by_id = {card["l4_id"]: card for card in cards}

    def l2_for_l3(l3_id: str) -> dict:
        l2_id = parent[l3_id]
        return nodes[l2_id]

    def semantic_path(l3_id: str) -> dict:
        l3 = nodes[l3_id]
        l2 = l2_for_l3(l3_id)
        return {
            "l2_id": l2["node_id"],
            "l3_id": l3["node_id"],
            "l2_label_en": l2.get("label_en", ""),
            "l2_label_ko": l2.get("label_ko", ""),
            "l3_label_en": l3.get("label_en", ""),
            "l3_label_ko": l3.get("label_ko", ""),
        }

    def hold_l3_for(target_l3_id: str) -> str:
        if target_l3_id.startswith("RAI3-A-"):
            return "RAI3-A-HLD-01"
        return "RAI3-G-HLD-01"

    applied = []
    for move in moves:
        card = cards_by_id[move["l4_id"]]
        if card.get("status") != "active":
            continue
        if (card.get("primary_l3_id") or "").startswith("RAI3-P-"):
            continue
        target = move["to"]
        old_primary = card.get("primary_l3_id")
        old_hold_path = deepcopy(card.get("hold_semantic_path"))
        card["release_id"] = "v2.17.2"
        card["decision_required"] = True
        card["decision_reason"] = "HOLD: BGE-M3 v2.17.2 guarded remap requires human taxonomy review."
        card["mapping_review_method"] = "bge_m3_v2_17_2_guarded_active_audit"
        card["bge_m3_v2_17_2_guarded_move"] = {
            "from_l3_id": move["from"],
            "to_l3_id": target,
            "score_from": move["score_from"],
            "score_to": move["score_to"],
            "improvement": move["improvement"],
            "keyword_cos": move["keyword_cos"],
            "definition_cos_to": move["definition_cos_to"],
            "definition_cos_from": move["definition_cos_from"],
        }
        card["hold_semantic_path"] = semantic_path(target)
        if "HLD" not in (old_primary or ""):
            card["previous_primary_l3_id"] = old_primary
            card["primary_l3_id"] = hold_l3_for(target)
            card["hold_review_l3_id"] = card["primary_l3_id"]
            card["hold_review_l2_id"] = parent[card["primary_l3_id"]]
        applied.append(
            {
                "l4_id": card["l4_id"],
                "label_en": card.get("label_en", ""),
                "old_primary_l3_id": old_primary,
                "old_hold_semantic_path": old_hold_path,
                "new_primary_l3_id": card.get("primary_l3_id"),
                "new_hold_semantic_path": card.get("hold_semantic_path"),
                "move": move,
            }
        )

    for card in cards:
        card["release_id"] = "v2.17.2"

    active_cards = [card for card in cards if card.get("status") == "active"]
    retired_cards = [card for card in cards if card.get("status") == "retired"]
    hold_active = [card for card in active_cards if card.get("decision_required")]
    physical_active = [card for card in active_cards if (card.get("primary_l3_id") or "").startswith("RAI3-P-")]
    by_path = Counter()
    for card in active_cards:
        primary = card.get("primary_l3_id") or ""
        if "HLD" in primary:
            by_path["HOLD-path"] += 1
        elif primary.startswith("RAI3-G-"):
            by_path["General"] += 1
        elif primary.startswith("RAI3-A-"):
            by_path["Agentic"] += 1
        elif primary.startswith("RAI3-P-"):
            by_path["Physical"] += 1

    manifest = deepcopy(manifest_rc)
    manifest["release_id"] = "v2.17.2"
    manifest["source_release"] = "v2.17.2-rc"
    manifest["status"] = "published_after_bge_m3_active_reliability"
    manifest["method"] = (
        "Claude L4 label deduplication and redefinition, followed by BGE-M3 "
        "active-card constrained-EM reliability audit. All 1,711 L4 IDs are preserved."
    )
    manifest["counts"] = {
        **manifest.get("counts", {}),
        "l4_total_ids_preserved": len(cards),
        "active": len(active_cards),
        "retired_with_provenance": len(retired_cards),
        "decision_required_active": len(hold_active),
        "physical_active": len(physical_active),
        "bge_m3_guarded_move_candidates": len(moves),
        "bge_m3_guarded_moves_reflected_as_hold": len(applied),
        "by_active_path": dict(by_path),
    }
    manifest["bge_m3_active_reliability"] = {
        "active_cards": reliability["active_cards"],
        "hold_active_cards": reliability["hold_active_cards"],
        "guarded_unique_move_cards": reliability["guarded_unique_move_cards"],
        "all_pre": reliability["baseline_pre_audit"]["all"],
        "all_post": reliability["post_audit"]["all"],
        "non_hold_pre": reliability["baseline_pre_audit"]["non_hold"],
        "non_hold_post": reliability["post_audit"]["non_hold"],
    }
    manifest["policy"] = (
        "All 1,711 IDs are retained. Retired records remain available with merged_into provenance. "
        "BGE-M3 proposals are not human-approved ground truth; reflected moves remain HOLD review items. "
        "Physical source cards and v2.17.1 minimal Physical transfers remain locked."
    )

    # Recount L4 counts in hierarchy for active cards only.
    hierarchy_out = deepcopy(hierarchy)
    for node in hierarchy_out["nodes"]:
        if node.get("level") == 3:
            node["l4_count"] = sum(card.get("primary_l3_id") == node["node_id"] for card in active_cards)

    write_json(OUT / "cards.json", {"release_id": "v2.17.2", "source_release": "v2.17.2-rc", "cards": cards})
    write_json(OUT / "hierarchy.json", hierarchy_out)
    write_json(OUT / "manifest.json", manifest)
    if (SRC / "revision_changelog.json").exists():
        changelog = load_json(SRC / "revision_changelog.json")
    else:
        changelog = []
    write_json(
        OUT / "revision_changelog.json",
        {
            "release_id": "v2.17.2",
            "source_release": "v2.17.2-rc",
            "bge_m3_guarded_moves_reflected_as_hold": applied,
            "upstream_changelog": changelog,
        },
    )
    write_json(AUDIT / "finalization_summary.json", manifest)
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
