#!/usr/bin/env python3
"""Normalize six L1-specific L2 path nodes into three canonical L2 categories."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/data/releases/v2.5.0"
OUT = ROOT / "public/data/releases/v2.6.0"
AUDIT = ROOT / "reports/data_quality/l2_category_consolidation_v2.6.json"

CATEGORIES = [
    {
        "category_id": "RAI2-INT",
        "label_en": "Interaction Safety",
        "label_ko": "상호작용 안전성",
        "path_node_ids": ["RAI2-G-INT", "RAI2-P-INT"],
    },
    {
        "category_id": "RAI2-SYS",
        "label_en": "System Safety",
        "label_ko": "시스템 안전성",
        "path_node_ids": ["RAI2-G-SYS", "RAI2-A-SYS", "RAI2-P-SYS"],
    },
    {
        "category_id": "RAI2-SOC",
        "label_en": "Societal Safety",
        "label_ko": "사회적 안전성",
        "path_node_ids": ["RAI2-P-SOC"],
    },
]


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
    category_by_path = {
        node_id: category
        for category in CATEGORIES
        for node_id in category["path_node_ids"]
    }
    l2_nodes = [node for node in hierarchy["nodes"] if node["level"] == 2]
    if len(l2_nodes) != 6 or {node["node_id"] for node in l2_nodes} != set(category_by_path):
        raise ValueError("Expected the six known L1-specific L2 path nodes")

    node_changes = []
    for node in l2_nodes:
        category = category_by_path[node["node_id"]]
        before = {"label_en": node["label_en"], "label_ko": node["label_ko"]}
        node.update({
            "label_en": category["label_en"],
            "label_ko": category["label_ko"],
            "canonical_l2_id": category["category_id"],
        })
        node_changes.append({"node_id": node["node_id"], "before": before, "after": {
            "label_en": node["label_en"], "label_ko": node["label_ko"],
            "canonical_l2_id": node["canonical_l2_id"],
        }})

    l2_label_by_id = {node["node_id"]: node for node in l2_nodes}
    for card in cards:
        card["release_id"] = "v2.6.0"
        for crumb in card.get("breadcrumb", []):
            if crumb["node_id"] in l2_label_by_id:
                node = l2_label_by_id[crumb["node_id"]]
                crumb["label_en"] = node["label_en"]
                crumb["label_ko"] = node["label_ko"]

    hierarchy["release_id"] = "v2.6.0"
    hierarchy["canonical_l2_categories"] = CATEGORIES
    cards_path, hierarchy_path = OUT / "cards.json", OUT / "hierarchy.json"
    write(cards_path, {"release_id": "v2.6.0", "cards": cards})
    write(hierarchy_path, hierarchy)
    audit = {
        "release_id": "v2.6.0",
        "policy": "L2 count means three unique canonical categories; six L1-specific path nodes remain only to preserve the L0-L1-L2-L3 tree and existing L3 parent paths.",
        "canonical_l2_category_count": 3,
        "l1_specific_l2_path_node_count": 6,
        "categories": CATEGORIES,
        "node_changes": node_changes,
        "l3_paths_changed": 0,
        "l4_assignments_changed": 0,
    }
    write(AUDIT, audit)
    manifest = {
        "release_id": "v2.6.0",
        "source_release": "v2.5.0",
        "release_status": "three_canonical_l2_categories",
        "counts": {
            "l4": len(cards),
            "classified": len(cards),
            "physical_locked": 182,
            "physical_total": 182,
            "decision_required": sum(card["decision_required"] for card in cards),
            "l1_nodes": sum(node["level"] == 1 for node in hierarchy["nodes"]),
            "l2_categories": 3,
            "l2_path_nodes": 6,
            "l3_nodes": sum(node["level"] == 3 for node in hierarchy["nodes"]),
        },
        "artifacts": [
            {"path": "cards.json", "sha256": sha256(cards_path)},
            {"path": "hierarchy.json", "sha256": sha256(hierarchy_path)},
            {"path": str(AUDIT.relative_to(ROOT)), "sha256": sha256(AUDIT)},
        ],
    }
    write(OUT / "manifest.json", manifest)
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
