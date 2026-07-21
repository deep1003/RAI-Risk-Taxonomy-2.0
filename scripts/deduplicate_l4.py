#!/usr/bin/env python3
"""Build a conservative semantically deduplicated L4 release."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/data/releases/v2.0.0"
OUT = ROOT / "public/data/releases/v2.1.0"
AUDIT = ROOT / "reports/data_quality/l4_deduplication_v2.1"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalized(text: str | None) -> str:
    value = unicodedata.normalize("NFKC", text or "").casefold()
    return re.sub(r"[^a-z0-9가-힣]+", "", value)


def core_definition(card: dict) -> str:
    return (card.get("definition_en") or "").split("This L4 risk card treats")[0].strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def choose_canonical(indices: list[int], cards: list[dict]) -> int:
    physical = [index for index in indices if cards[index]["assignment_status"] == "locked_physical"]
    if physical:
        return min(physical, key=lambda index: cards[index]["l4_id"])
    return min(indices, key=lambda index: cards[index]["l4_id"])


def main() -> None:
    cards = read_json(SOURCE / "cards.json")["cards"]
    hierarchy = read_json(SOURCE / "hierarchy.json")
    dsu = DisjointSet(len(cards))
    candidates = []
    normalized_labels = [normalized(card["label_en"]) for card in cards]
    normalized_cores = [normalized(core_definition(card)) for card in cards]
    for left in range(len(cards)):
        for right in range(left + 1, len(cards)):
            same_core = bool(normalized_cores[left]) and normalized_cores[left] == normalized_cores[right]
            same_label = normalized_labels[left] == normalized_labels[right]
            eligible = same_core and same_label
            both_physical = all(
                cards[index]["assignment_status"] == "locked_physical" for index in (left, right)
            )
            if eligible:
                candidates.append({
                    "left_l4_id": cards[left]["l4_id"],
                    "right_l4_id": cards[right]["l4_id"],
                    "same_core_definition": same_core,
                    "same_normalized_label": same_label,
                    "semantic_similarity": None,
                    "both_physical_protected": both_physical,
                    "action": "protected_review" if both_physical else "merge",
                })
                if not both_physical:
                    dsu.union(left, right)

    clusters = defaultdict(list)
    for index in range(len(cards)):
        clusters[dsu.find(index)].append(index)

    retained = []
    crosswalk = []
    for indices in sorted(clusters.values(), key=lambda group: min(group)):
        canonical_index = choose_canonical(indices, cards)
        canonical = dict(cards[canonical_index])
        merged = [cards[index] for index in indices if index != canonical_index]
        reference_keys = set()
        references = []
        for source in [canonical, *merged]:
            for reference in source.get("references", []):
                key = (reference.get("url"), reference.get("title"), reference.get("source_system"))
                if key not in reference_keys:
                    reference_keys.add(key)
                    references.append(reference)
        canonical.update({
            "release_id": "v2.1.0",
            "references": references,
            "merged_source_l4_ids": [card["l4_id"] for card in merged],
            "decision_required": canonical.get("decision_required", False) or any(
                card.get("decision_required", False) for card in merged
            ),
        })
        retained.append(canonical)
        for source in merged:
            crosswalk.append({
                "retired_l4_id": source["l4_id"],
                "canonical_l4_id": canonical["l4_id"],
                "retired_label_en": source["label_en"],
                "canonical_label_en": canonical["label_en"],
                "physical_canonical": canonical["assignment_status"] == "locked_physical",
                "reason": "exact_normalized_label_and_core_definition_duplicate",
            })

    retained.sort(key=lambda card: card["l4_id"])
    physical_before = sum(card["assignment_status"] == "locked_physical" for card in cards)
    physical_after = sum(card["assignment_status"] == "locked_physical" for card in retained)
    if physical_before != 182 or physical_after != 182:
        raise ValueError(f"Physical preservation failed: {physical_before} -> {physical_after}")

    write_json(OUT / "cards.json", {"release_id": "v2.1.0", "cards": retained})
    hierarchy["release_id"] = "v2.1.0"
    write_json(OUT / "hierarchy.json", hierarchy)
    write_json(AUDIT / "candidate_pairs.json", candidates)
    write_json(AUDIT / "retired_to_canonical.json", crosswalk)
    summary = {
        "release_id": "v2.1.0",
        "source_release": "v2.0.0",
        "source_rows": len(cards),
        "canonical_rows": len(retained),
        "retired_duplicate_rows": len(crosswalk),
        "duplicate_reduction_percent": len(crosswalk) / len(cards) * 100,
        "candidate_pairs": len(candidates),
        "protected_physical_pairs": sum(row["both_physical_protected"] for row in candidates),
        "physical_before": physical_before,
        "physical_after": physical_after,
        "decision_required_after": sum(card.get("decision_required", False) for card in retained),
        "method": {
            "exact_normalized_label_and_core_definition": True,
            "semantic_similarity_merging": False,
            "physical_priority": "Physical cards are never automatically retired; a Physical card wins any mixed cluster.",
        },
    }
    write_json(AUDIT / "summary.json", summary)
    with (AUDIT / "retired_to_canonical.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(crosswalk[0]) if crosswalk else ["retired_l4_id"])
        writer.writeheader()
        writer.writerows(crosswalk)
    cards_path, hierarchy_path = OUT / "cards.json", OUT / "hierarchy.json"
    manifest = {
        "release_id": "v2.1.0",
        "release_status": "conservatively_exact_deduplicated",
        "source_release": "v2.0.0",
        "counts": {
            "l4": len(retained),
            "classified": len(retained),
            "retired_duplicates": len(crosswalk),
            "physical_locked": physical_after,
            "decision_required": summary["decision_required_after"],
            "l3_nodes": sum(node["level"] == 3 for node in hierarchy["nodes"]),
        },
        "artifacts": [
            {"path": "cards.json", "sha256": sha256(cards_path)},
            {"path": "hierarchy.json", "sha256": sha256(hierarchy_path)},
            {"path": "reports/data_quality/l4_deduplication_v2.1/retired_to_canonical.json"},
        ],
    }
    write_json(OUT / "manifest.json", manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
