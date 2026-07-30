#!/usr/bin/env python3
"""Synchronize the active RAI release with the authoritative Physical AI cards."""

from __future__ import annotations

import hashlib
import json
import re
import argparse
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PHYSICAL_ROOT = ROOT.parent / "Physical-AI-Risk-Taxonomy"
PHYSICAL_CARDS = PHYSICAL_ROOT / "data" / "l4_cards.json"
RELEASE = ROOT / "public" / "data" / "releases" / "v2.18.0-rc"
APPROVED_MOVES = {
    "PHYSBENCH-REF-0065": "P3.2",
    "PHYSBENCH-REF-0107": "S3.6",
}
ORIGINAL_RAI_L3 = {
    "PHYSBENCH-REF-0065": "RAI3-P-INT-07",
    "PHYSBENCH-REF-0107": "RAI3-P-INT-06",
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def split_bilingual(value: str) -> tuple[str, str]:
    match = re.fullmatch(r"(.*?) \((.*)\)", value.strip(), flags=re.DOTALL)
    if not match:
        raise ValueError(f"Expected Korean (English) text: {value!r}")
    return match.group(1).strip(), match.group(2).strip()


def node_path(node_id: str, nodes_by_id: dict[str, dict]) -> list[dict]:
    path = []
    current = nodes_by_id[node_id]
    while current:
        path.append(
            {
                "node_id": current["node_id"],
                "label_en": current["label_en"],
                "label_ko": current["label_ko"],
            }
        )
        parent_id = current.get("parent_id")
        current = nodes_by_id.get(parent_id) if parent_id else None
    return list(reversed(path))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finalize_manifest() -> None:
    manifest_path = RELEASE / "manifest.json"
    manifest = read_json(manifest_path)
    risk_space = RELEASE / "risk_space.json"
    network = RELEASE / "semantic_proximity_network.json"
    network_payload = read_json(network)
    manifest["generated_assets"] = {
        "risk_space": {
            "path": risk_space.name,
            "sha256": sha256(risk_space),
        },
        "semantic_proximity_network": {
            "path": network.name,
            "sha256": sha256(network),
            "nodes": len(network_payload["nodes"]),
            "edges": len(network_payload["edges"]),
            "clusters": network_payload["metadata"]["cluster_count"],
        },
    }
    write_json(manifest_path, manifest)
    print(
        json.dumps(
            manifest["generated_assets"],
            ensure_ascii=False,
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--finalize-manifest", action="store_true")
    args = parser.parse_args()
    if args.finalize_manifest:
        finalize_manifest()
        return

    physical = read_json(PHYSICAL_CARDS)
    cards_payload = read_json(RELEASE / "cards.json")
    hierarchy = read_json(RELEASE / "hierarchy.json")
    manifest = read_json(RELEASE / "manifest.json")
    changelog = read_json(RELEASE / "revision_changelog.json")

    physical_by_id = {card["card_id"]: card for card in physical}
    nodes_by_id = {node["node_id"]: node for node in hierarchy["nodes"]}
    legacy_l3_to_node = {}
    for node in hierarchy["nodes"]:
        if node.get("level") != 3 or node.get("status") != "active":
            continue
        for legacy_id in node.get("legacy_ids") or []:
            if re.fullmatch(r"[PIS]3\.\d+", legacy_id):
                legacy_l3_to_node[legacy_id] = node["node_id"]

    synced = 0
    moves = []
    seen_source_ids = set()
    for card in cards_payload["cards"]:
        source_id = card.get("physical_source_card_id")
        if not source_id:
            continue
        source = physical_by_id[source_id]
        seen_source_ids.add(source_id)
        label_ko, label_en = split_bilingual(source["label"])
        definition_ko, definition_en = split_bilingual(source["definition"])
        card.update(
            {
                "label_en": label_en,
                "label_ko": label_ko,
                "definition_en": definition_en,
                "definition_ko": definition_ko,
                "physical_source_l2_id": source["l2_id"],
                "physical_source_l3_id": source["l3_id"],
                "physical_master_sync": {
                    "source": (
                        "Physical-AI-Risk-Taxonomy/data/l4_cards.json"
                    ),
                    "date": "2026-07-31",
                    "method": "authoritative_source_id_crosswalk",
                },
            }
        )
        synced += 1

        if source_id not in APPROVED_MOVES:
            continue
        target_legacy_id = APPROVED_MOVES[source_id]
        target_node_id = legacy_l3_to_node[target_legacy_id]
        old_node_id = card["primary_l3_id"]
        audit_from_node_id = ORIGINAL_RAI_L3[source_id]
        card["previous_primary_l3_id"] = audit_from_node_id
        card["primary_l3_id"] = target_node_id
        card["breadcrumb"] = node_path(target_node_id, nodes_by_id)
        card["review_status"] = "human_approved_em_sensitivity_20260731"
        card["human_approved"] = True
        card["assignment_status"] = "physical_master_sync_20260731"
        card["physical_l3_reassignment_audit"] = {
            "from_l3_id": audit_from_node_id,
            "to_l3_id": target_node_id,
            "physical_target_l3_id": target_legacy_id,
            "release_rule": (
                "same target in at least 80 percent of 24 EM sensitivity "
                "conditions and no empty Physical AI L3 family"
            ),
        }
        moves.append(
            {
                "physical_source_card_id": source_id,
                "rai_l4_id": card["l4_id"],
                "from_l3_id": audit_from_node_id,
                "to_l3_id": target_node_id,
            }
        )

    if synced != 182 or seen_source_ids != set(physical_by_id):
        missing = sorted(set(physical_by_id) - seen_source_ids)
        raise RuntimeError(
            f"Physical crosswalk incomplete: synced={synced}, missing={missing}"
        )

    active_counts = Counter(
        card["primary_l3_id"]
        for card in cards_payload["cards"]
        if card.get("status") == "active"
    )
    for node in hierarchy["nodes"]:
        if node.get("level") == 3:
            node["l4_count"] = active_counts.get(node["node_id"], 0)

    domain_counts = Counter(
        card["primary_l3_id"].split("-")[1]
        for card in cards_payload["cards"]
        if card.get("status") == "active"
    )
    manifest["counts"]["by_primary_domain_code"] = dict(domain_counts)
    manifest["physical_master_sync"] = {
        "date": "2026-07-31",
        "source": "Physical-AI-Risk-Taxonomy/data/l4_cards.json",
        "source_sha256": sha256(PHYSICAL_CARDS),
        "cards_synced": synced,
        "wording_and_definition_records_synced": synced,
        "approved_l3_moves": moves,
        "validation": (
            "EM sensitivity across 24 model, language, and seed-weight "
            "conditions with 1,000 bootstrap repeats"
        ),
    }
    changelog["physical_master_sync"] = {
        "date": "2026-07-31",
        "cards_synced": synced,
        "approved_l3_moves": moves,
        "scope": (
            "Authoritative Physical AI wording, definitions, and approved "
            "L3 paths synchronized by physical_source_card_id."
        ),
    }

    write_json(RELEASE / "cards.json", cards_payload)
    write_json(RELEASE / "hierarchy.json", hierarchy)
    write_json(RELEASE / "manifest.json", manifest)
    write_json(RELEASE / "revision_changelog.json", changelog)
    print(
        json.dumps(
            {
                "cards_synced": synced,
                "moves": moves,
                "domain_counts": dict(domain_counts),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
