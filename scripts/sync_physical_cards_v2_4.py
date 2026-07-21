#!/usr/bin/env python3
"""Sync the protected Physical AI cards from the authoritative local source."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RELEASE = ROOT / "public/data/releases/v2.3.0"
OUT = ROOT / "public/data/releases/v2.4.0"
PHYSICAL = ROOT.parent / "Physical-AI-Risk-Taxonomy" / "data"
LOCK_PATH = ROOT / "data/releases/v1.0.0/physical_lock.json"
AUDIT_PATH = ROOT / "reports/data_quality/physical_card_sync_v2.4.json"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_bilingual(value: str) -> tuple[str, str]:
    """Split `Korean (English)` at the final balanced parenthesized segment."""
    value = value.strip()
    if not value.endswith(")"):
        raise ValueError(f"Bilingual value has no terminal English segment: {value}")
    depth = 0
    start = None
    for index in range(len(value) - 1, -1, -1):
        if value[index] == ")":
            depth += 1
        elif value[index] == "(":
            depth -= 1
            if depth == 0:
                start = index
                break
    if start is None:
        raise ValueError(f"Unbalanced bilingual value: {value}")
    korean = value[:start].strip()
    english = value[start + 1 : -1].strip()
    if not korean or not english or not re.search(r"[A-Za-z]", english):
        raise ValueError(f"Invalid bilingual split: {value}")
    return korean, english


def parse_three_h_one_r(raw: str) -> list[dict]:
    source_axes = {"H1": "Harmless", "H2": "Helpful", "H3": "Honest", "RC": "Role"}
    canonical_axes = {**source_axes, "RC": "Role Consistency"}
    values = []
    for token in (part.strip() for part in raw.split("|") if part.strip()):
        match = re.fullmatch(r"(H1|H2|H3|RC)\s+([^\[]+)\[([PS])\]", token)
        if not match:
            raise ValueError(f"Invalid 3H1R token: {token}")
        axis_code, axis_name, priority_code = match.groups()
        if axis_name.strip() != source_axes[axis_code]:
            raise ValueError(f"3H1R axis mismatch: {token}")
        values.append({
            "axis_code": axis_code,
            "axis_name": canonical_axes[axis_code],
            "priority_code": priority_code,
            "priority": "Primary" if priority_code == "P" else "Secondary",
        })
    return values


def main() -> None:
    physical_cards = read(PHYSICAL / "l4_cards.json")
    physical_refs = read(PHYSICAL / "l4_references.json")
    locks = read(LOCK_PATH)
    source_cards = read(SOURCE_RELEASE / "cards.json")["cards"]
    hierarchy = read(SOURCE_RELEASE / "hierarchy.json")

    physical_by_id = {card["card_id"]: card for card in physical_cards}
    lock_by_id = {row["physical_card_id"]: row for row in locks}
    if len(physical_by_id) != 182 or len(lock_by_id) != 182 or set(physical_by_id) != set(lock_by_id):
        raise ValueError("Physical source and lock must have the same 182 unique IDs")
    refs_by_id = defaultdict(list)
    for ref in physical_refs:
        refs_by_id[ref["card_id"]].append(ref)
    if set(refs_by_id) != set(physical_by_id):
        raise ValueError("Every Physical card must have at least one reference row")

    source_by_l4 = {card["l4_id"]: card for card in source_cards}
    synced_l4_ids = {row["l4_id"] for row in locks}
    if len(synced_l4_ids) != 182 or not synced_l4_ids <= set(source_by_l4):
        raise ValueError("Physical lock does not cover 182 release cards")

    changes = []
    for physical_id, lock in lock_by_id.items():
        source = physical_by_id[physical_id]
        card = source_by_l4[lock["l4_id"]]
        if card["assignment_status"] != "locked_physical" or card["primary_l3_id"] != lock["new_l3_id"]:
            raise ValueError(f"Protected mapping changed for {physical_id}")
        label_ko, label_en = split_bilingual(source["label"])
        definition_ko, definition_en = split_bilingual(source["definition"])
        severity = float(source["severity"])
        probability = float(source["probability"])
        references = []
        for ref in sorted(refs_by_id[physical_id], key=lambda row: row["reference_index"]):
            references.append({
                "title": ref["reference_title"],
                "url": ref["reference_url"],
                "type": ref["reference_class"],
                "source_system": "physical_182",
                "reference_index": ref["reference_index"],
                "justification": ref["justification"],
                "is_linked": bool(ref["is_linked"]),
            })
        before = {key: card.get(key) for key in (
            "label_en", "label_ko", "definition_en", "definition_ko", "severity_1to5",
            "probability_0to1", "impact_score", "impact_percentile", "three_h_one_r_raw", "references"
        )}
        card.update({
            "label_en": label_en,
            "label_ko": label_ko,
            "definition_en": definition_en,
            "definition_ko": definition_ko,
            "severity_1to5": severity,
            "probability_0to1": probability,
            "impact_score": round(severity * probability, 6),
            "impact_percentile": None,
            "metrics_source": "physical_ai_taxonomy_local_sync_v2.4",
            "three_h_one_r_raw": source["three_h_one_r"],
            "three_h_one_r": parse_three_h_one_r(source["three_h_one_r"]),
            "references": references,
            "release_id": "v2.4.0",
            "physical_source_card_id": physical_id,
            "physical_source_l3_id": source["l3_id"],
            "physical_source_sync": "v2.4.0",
        })
        changes.append({
            "physical_card_id": physical_id,
            "l4_id": card["l4_id"],
            "changed_fields": [key for key, value in before.items() if value != card.get(key)],
        })

    output = []
    for card in source_cards:
        updated = source_by_l4[card["l4_id"]]
        updated["release_id"] = "v2.4.0"
        output.append(updated)
    if len(output) != 1711 or sum(card["assignment_status"] == "locked_physical" for card in output) != 182:
        raise ValueError("Release grain or Physical lock changed")

    hierarchy["release_id"] = "v2.4.0"
    cards_path, hierarchy_path = OUT / "cards.json", OUT / "hierarchy.json"
    write(cards_path, {"release_id": "v2.4.0", "cards": output})
    write(hierarchy_path, hierarchy)
    audit = {
        "release_id": "v2.4.0",
        "authoritative_source": "https://deep1003.github.io/Physical-AI-Risk-Taxonomy/",
        "local_source_files": {
            "l4_cards.json": sha256(PHYSICAL / "l4_cards.json"),
            "l4_references.json": sha256(PHYSICAL / "l4_references.json"),
        },
        "quality_checks": {
            "unique_physical_ids": len(physical_by_id),
            "lock_join_coverage": len(changes),
            "reference_rows": len(physical_refs),
            "cards_with_references": len(refs_by_id),
            "unlinked_reference_rows": sum(not row["is_linked"] for row in physical_refs),
            "missing_justification_rows": sum(not str(row.get("justification", "")).strip() for row in physical_refs),
            "severity_range": [min(float(x["severity"]) for x in physical_cards), max(float(x["severity"]) for x in physical_cards)],
            "probability_range": [min(float(x["probability"]) for x in physical_cards), max(float(x["probability"]) for x in physical_cards)],
        },
        "format_policy": {
            "bilingual_fields": "Terminal parenthesized English text split into *_ko and *_en.",
            "impact_score": "severity_1to5 multiplied by probability_0to1",
            "impact_percentile": "null because the authoritative Physical source does not provide a comparable percentile",
            "references": "Physical reference rows replace mixed legacy references; justification is preserved per reference.",
        },
        "changed_field_frequency": Counter(field for row in changes for field in row["changed_fields"]),
        "changes": changes,
    }
    write(AUDIT_PATH, audit)
    manifest = {
        "release_id": "v2.4.0",
        "source_release": "v2.3.0",
        "release_status": "physical_cards_synced_from_authoritative_local_source",
        "counts": {
            "l4": len(output),
            "classified": len(output),
            "physical_locked": 182,
            "physical_total": 182,
            "physical_cards_synced": len(changes),
            "physical_reference_rows": len(physical_refs),
            "decision_required": sum(card["decision_required"] for card in output),
            "l3_nodes": sum(node["level"] == 3 for node in hierarchy["nodes"]),
        },
        "artifacts": [
            {"path": "cards.json", "sha256": sha256(cards_path)},
            {"path": "hierarchy.json", "sha256": sha256(hierarchy_path)},
            {"path": str(AUDIT_PATH.relative_to(ROOT)), "sha256": sha256(AUDIT_PATH)},
        ],
    }
    write(OUT / "manifest.json", manifest)
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
