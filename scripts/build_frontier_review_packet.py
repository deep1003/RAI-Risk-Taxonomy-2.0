#!/usr/bin/env python3
"""Create a hierarchy-blind packet for independent expert confirmation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import build_release as build  # noqa: E402
from rai_taxonomy.codebook import RELEASE_ID  # noqa: E402


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    release_dir = ROOT / "data" / "releases" / RELEASE_ID
    output_dir = ROOT / "reports" / "validation" / RELEASE_ID / "frontier_expert_reviews"
    global_cards = sorted(
        load(ROOT / "data" / "source_snapshots" / RELEASE_ID / "global_ai_risk_l4_overlay_nodes.json"),
        key=lambda row: row["id"],
    )
    placements = {row["l4_id"]: row for row in load(release_dir / "placements.json")}
    nodes = {row["node_id"]: row for row in load(release_dir / "taxonomy_nodes.json")}
    packet = []
    for number, card in enumerate(global_cards, start=1):
        l4_id = f"RAI4-{number:04d}"
        placement = placements[l4_id]
        if placement["assignment_status"] != "algorithm_proposed":
            continue
        proposed_l3 = nodes[placement["primary_l3_id"]]
        packet.append(
            {
                "l4_id": l4_id,
                "label": card.get("l4_label"),
                "mechanism_definition": build.mechanism_only_definition(card.get("definition")),
                "evidence_title": card.get("evidence_title") or card.get("ref_title"),
                "proposed_l3_id": proposed_l3["node_id"],
                "proposed_l3_label": proposed_l3["label_en"],
                "proposed_l3_definition": proposed_l3["definition_en"],
                "instruction": "Approve only if the direct L4 mechanism is fully included in this exact L3 definition; otherwise reject.",
            }
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    output = {
        "release_id": RELEASE_ID,
        "hierarchy_blind": True,
        "legacy_hierarchy_in_packet": False,
        "review_scope": "all initial strict BGE-M3 plus rule proposals",
        "card_count": len(packet),
        "cards": packet,
    }
    (output_dir / "review_packet.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"cards": len(packet), "path": str(output_dir / "review_packet.json")}))


if __name__ == "__main__":
    main()

