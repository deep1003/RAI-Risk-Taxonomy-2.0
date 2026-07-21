#!/usr/bin/env python3
"""Create General and Agentic HOLD L2 paths while preserving semantic lineage."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/data/releases/v2.14.0"
OUTPUT = ROOT / "public/data/releases/v2.15.0"
REPORT = ROOT / "reports/data_quality/hold_l2_overlay_v2.15.0"

HOLD_PATHS = {
    "RAI1-G": {
        "l2_id": "RAI2-G-HLD",
        "l3_id": "RAI3-G-HLD-01",
        "l1_en": "General",
        "l1_ko": "일반 AI",
        "count": 626,
    },
    "RAI1-A": {
        "l2_id": "RAI2-A-HLD",
        "l3_id": "RAI3-A-HLD-01",
        "l1_en": "Agentic AI",
        "l1_ko": "에이전틱 AI",
        "count": 94,
    },
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def domain_id(l3_id: str) -> str:
    return f"RAI1-{l3_id.split('-')[1]}"


def hold_nodes():
    nodes = []
    for sequence, (l1_id, meta) in enumerate(HOLD_PATHS.items(), start=3):
        nodes.extend(
            [
                {
                    "node_id": meta["l2_id"],
                    "level": 2,
                    "parent_id": l1_id,
                    "sequence": sequence,
                    "label_en": "HOLD",
                    "label_ko": "분류 검토 보류",
                    "definition_en": "Review path for assigned L4 cards whose semantic L3 placement requires human taxonomy adjudication.",
                    "definition_ko": "의미 기반 L3 배치는 보존하지만 사람의 분류체계 판정이 필요한 L4 카드를 모은 검토 경로.",
                    "status": "active_review_path",
                    "introduced_in": "v2.15.0",
                    "canonical_l2_id": "RAI2-HLD",
                },
                {
                    "node_id": meta["l3_id"],
                    "level": 3,
                    "parent_id": meta["l2_id"],
                    "sequence": 1,
                    "label_en": "Taxonomy Decision Hold",
                    "label_ko": "분류체계 결정 보류",
                    "definition_en": "Assigned risks retained for human review because the current semantic L3 destination is provisional or insufficiently supported.",
                    "definition_ko": "현재 의미 기반 L3 목적지가 잠정적이거나 근거가 충분하지 않아 사람의 검토를 위해 보류한 리스크.",
                    "status": "active_review_path",
                    "introduced_in": "v2.15.0",
                    "l4_count": meta["count"],
                    "references": [],
                },
            ]
        )
    return nodes


def main() -> None:
    cards_payload = load(SOURCE / "cards.json")
    hierarchy = load(SOURCE / "hierarchy.json")
    source_cards = cards_payload["cards"]
    node_by_id = {node["node_id"]: node for node in hierarchy["nodes"]}

    cards = []
    moves = []
    for source in source_cards:
        card = copy.deepcopy(source)
        card["release_id"] = "v2.15.0"
        l1_id = domain_id(card["primary_l3_id"])
        if card["decision_required"] and l1_id in HOLD_PATHS:
            meta = HOLD_PATHS[l1_id]
            original_l3_id = card["primary_l3_id"]
            original_l3 = node_by_id[original_l3_id]
            original_l2 = node_by_id[original_l3["parent_id"]]
            card["hold_semantic_path"] = {
                "l2_id": original_l2["node_id"],
                "l3_id": original_l3_id,
                "l2_label_en": original_l2["label_en"],
                "l2_label_ko": original_l2["label_ko"],
                "l3_label_en": original_l3["label_en"],
                "l3_label_ko": original_l3["label_ko"],
            }
            card["hold_review_l2_id"] = meta["l2_id"]
            card["hold_review_l3_id"] = meta["l3_id"]
            card["primary_l3_id"] = meta["l3_id"]
            root_node = node_by_id["RAI0"]
            card["breadcrumb"] = [
                {"node_id": "RAI0", "label_en": root_node["label_en"], "label_ko": root_node["label_ko"]},
                {"node_id": l1_id, "label_en": meta["l1_en"], "label_ko": meta["l1_ko"]},
                {"node_id": meta["l2_id"], "label_en": "HOLD", "label_ko": "분류 검토 보류"},
                {"node_id": meta["l3_id"], "label_en": "Taxonomy Decision Hold", "label_ko": "분류체계 결정 보류"},
            ]
            moves.append(
                {
                    "l4_id": card["l4_id"],
                    "l1_id": l1_id,
                    "from_l2_id": original_l2["node_id"],
                    "from_l3_id": original_l3_id,
                    "to_l2_id": meta["l2_id"],
                    "to_l3_id": meta["l3_id"],
                }
            )
        cards.append(card)

    nodes = copy.deepcopy(hierarchy["nodes"])
    non_hold_counts = Counter(
        card["primary_l3_id"]
        for card in source_cards
        if not card["decision_required"]
    )
    for node in nodes:
        if node["level"] == 3:
            node["l4_count"] = non_hold_counts[node["node_id"]]
    nodes.extend(hold_nodes())

    canonical_l2 = copy.deepcopy(hierarchy["canonical_l2_categories"])
    canonical_l2.append(
        {
            "category_id": "RAI2-HLD",
            "label_en": "HOLD",
            "label_ko": "분류 검토 보류",
            "path_node_ids": ["RAI2-G-HLD", "RAI2-A-HLD"],
            "review_overlay": True,
        }
    )
    output_hierarchy = {
        **hierarchy,
        "release_id": "v2.15.0",
        "canonical_l2_categories": canonical_l2,
        "nodes": nodes,
    }
    output_cards = {"release_id": "v2.15.0", "cards": cards}

    counts = Counter(move["l1_id"] for move in moves)
    summary = {
        "release_id": "v2.15.0",
        "source_release": "v2.14.0",
        "method": "orthogonal HOLD review path with preserved semantic L3 lineage",
        "moved_to_hold_review_path": len(moves),
        "general_hold": counts["RAI1-G"],
        "agentic_hold": counts["RAI1-A"],
        "physical_changed": 0,
        "semantic_paths_preserved": True,
        "non_hold_validation_population": len(cards) - len(moves),
        "counts": {
            "l4": len(cards),
            "l1_nodes": 3,
            "canonical_l2_categories": 4,
            "l2_path_nodes": 8,
            "active_l3_nodes_including_review_paths": 52,
            "semantic_l3_nodes": 50,
            "hold_review_l3_nodes": 2,
        },
    }

    dump(OUTPUT / "cards.json", output_cards)
    dump(OUTPUT / "hierarchy.json", output_hierarchy)
    dump(REPORT / "hold_path_moves.json", moves)
    dump(REPORT / "summary.json", summary)

    manifest = {
        "release_id": "v2.15.0",
        "source_release": "v2.14.0",
        "status": "published",
        "counts": {
            "l4": len(cards),
            "classified": len(cards),
            "physical_locked": 182,
            "decision_required": len(moves),
            "l1_nodes": 3,
            "l2_categories": 4,
            "l2_path_nodes": 8,
            "l3_nodes": 52,
            "semantic_l3_nodes": 50,
            "hold_review_l3_nodes": 2,
        },
        "summary": summary,
        "files": [],
    }
    for path in (OUTPUT / "cards.json", OUTPUT / "hierarchy.json", REPORT / "summary.json", REPORT / "hold_path_moves.json"):
        manifest["files"].append({"path": str(path.relative_to(ROOT)), "sha256": sha256(path)})
    dump(OUTPUT / "manifest.json", manifest)

    assert len(cards) == 1711
    assert len(moves) == 720
    assert counts == Counter({"RAI1-G": 626, "RAI1-A": 94})
    assert all(card["primary_l3_id"].startswith("RAI3-P-") for card in cards if card["l4_id"] in {
        row["l4_id"] for row in source_cards if row["primary_l3_id"].startswith("RAI3-P-")
    })
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
