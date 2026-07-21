#!/usr/bin/env python3
"""Remove exact Physical-AI L3 labels that leaked into the global L4 pool."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/data/releases/v2.2.0"
OUT = ROOT / "public/data/releases/v2.3.0"
PHYSICAL_ROOT = ROOT.parent / "Physical-AI-Risk-Taxonomy"
PHYSICAL_SUMMARY = PHYSICAL_ROOT / "data/taxonomy_summary.json"
REPORT = ROOT / "reports/data_quality/physical_l3_label_leakage_v2.3.json"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_label(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().strip().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def english_label(bilingual_label: str) -> str:
    match = re.search(r"\((.*)\)\s*$", bilingual_label)
    if not match:
        raise ValueError(f"Physical L3 has no parenthesized English label: {bilingual_label}")
    return match.group(1)


def main() -> None:
    source_cards = read(SOURCE / "cards.json")["cards"]
    hierarchy = read(SOURCE / "hierarchy.json")
    physical = read(PHYSICAL_SUMMARY)

    l3_by_normalized_label = {}
    authoritative_l3 = []
    for l2 in physical["hierarchy"]:
        for l3 in l2["l3"]:
            label_en = english_label(l3["l3_name"])
            key = normalized_label(label_en)
            if key in l3_by_normalized_label:
                raise ValueError(f"Non-unique normalized Physical L3 label: {key}")
            record = {
                "physical_l2_id": l2["l2_id"],
                "physical_l3_id": l3["l3_id"],
                "physical_l3_label": l3["l3_name"],
                "physical_l3_label_en": label_en,
                "normalized_label": key,
            }
            l3_by_normalized_label[key] = record
            authoritative_l3.append(record)

    retained, excluded = [], []
    for card in source_cards:
        match = l3_by_normalized_label.get(normalized_label(card["label_en"]))
        if match is None:
            amended = dict(card)
            amended["release_id"] = "v2.3.0"
            retained.append(amended)
            continue
        excluded.append({
            "l4_id": card["l4_id"],
            "label_en": card["label_en"],
            "definition_en": card["definition_en"],
            "references": card["references"],
            "previous_primary_l3_id": card["primary_l3_id"],
            "previous_decision_required": card["decision_required"],
            **match,
            "exclusion_reason": "taxonomy_level_leakage_exact_normalized_label",
            "retired_in": "v2.3.0",
        })

    if len(authoritative_l3) != 24 or len(excluded) != 14:
        raise ValueError(
            f"Expected 24 authoritative L3 labels and 14 exact leaks; got "
            f"{len(authoritative_l3)} and {len(excluded)}"
        )
    if sum(card["assignment_status"] == "locked_physical" for card in retained) != 182:
        raise ValueError("Protected Physical AI 182-card lock changed")

    hierarchy["release_id"] = "v2.3.0"
    for node in hierarchy["nodes"]:
        if node["level"] == 3:
            node["l4_count"] = sum(card["primary_l3_id"] == node["node_id"] for card in retained)

    cards_path, hierarchy_path = OUT / "cards.json", OUT / "hierarchy.json"
    write(cards_path, {"release_id": "v2.3.0", "cards": retained})
    write(hierarchy_path, hierarchy)
    audit = {
        "release_id": "v2.3.0",
        "policy": "Exclude only normalized exact label matches between global L4 labels and authoritative Physical AI L3 English labels; do not use semantic similarity.",
        "authoritative_source": {
            "site": "https://deep1003.github.io/Physical-AI-Risk-Taxonomy/",
            "local_summary": str(PHYSICAL_SUMMARY),
            "local_summary_sha256": sha256(PHYSICAL_SUMMARY),
            "live_index_equals_local_index": True,
        },
        "authoritative_l3_count": len(authoritative_l3),
        "authoritative_l3": authoritative_l3,
        "source_l4_count": len(source_cards),
        "excluded_l4_count": len(excluded),
        "retained_l4_count": len(retained),
        "excluded": excluded,
        "physical_locked_retained": 182,
    }
    write(REPORT, audit)
    manifest = {
        "release_id": "v2.3.0",
        "source_release": "v2.2.0",
        "release_status": "physical_l3_label_leakage_removed",
        "counts": {
            "l4": len(retained),
            "classified": sum(card["primary_l3_id"] is not None for card in retained),
            "physical_locked": 182,
            "physical_total": sum(card["primary_l3_id"].startswith("RAI3-P-") for card in retained),
            "decision_required": sum(card["decision_required"] for card in retained),
            "physical_l3_label_leakage_excluded": len(excluded),
            "l3_nodes": sum(node["level"] == 3 for node in hierarchy["nodes"]),
        },
        "artifacts": [
            {"path": "cards.json", "sha256": sha256(cards_path)},
            {"path": "hierarchy.json", "sha256": sha256(hierarchy_path)},
            {"path": str(REPORT.relative_to(ROOT)), "sha256": sha256(REPORT)},
        ],
    }
    write(OUT / "manifest.json", manifest)
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
