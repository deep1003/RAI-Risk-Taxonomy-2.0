#!/usr/bin/env python3
"""Retire four sparse Agentic L3 families and force-migrate their 39 L4 cards.

The v2.13.0 bundle is immutable. This script creates v2.14.0, preserves the
retired L3 definitions and references in an archive, records every L4 path
migration, protects all Physical cards, and marks every migrated card HOLD.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "v2.13.0"
RELEASE_ID = "v2.14.0"
SOURCE = ROOT / "public/data/releases" / SOURCE_ID
OUT = ROOT / "public/data/releases" / RELEASE_ID
REPORT = ROOT / "reports/data_quality/agentic_l3_retirement_v2.14.0"
CARD_EMBEDDINGS = ROOT / "reports/validation/v2.8.0/reliability/card_embeddings_bge_m3.npy"
L3_EMBEDDINGS = ROOT / "reports/validation/v2.8.0/reliability/l3_seed_embeddings_bge_m3.npy"

RETIRED_L3 = {
    "RAI3-A-SYS-07": "Goal & Planning",
    "RAI3-A-SYS-08": "Tool Calling",
    "RAI3-A-SYS-09": "Memory",
    "RAI3-A-SYS-10": "Oversight & Control",
}

# Explicit, mechanism-first forced destinations. The destination is operational,
# not human-approved truth; all 39 migrations remain HOLD.
MIGRATIONS = {
    "RAI4-0001": ("RAI3-G-SYS-08", "proxy objective violates intended goal"),
    "RAI4-0002": ("RAI3-A-SYS-01", "consequential action continues beyond supervised authority"),
    "RAI4-0003": ("RAI3-G-SYS-09", "shutdown, pause, and correction cannot be meaningfully exercised"),
    "RAI4-0004": ("RAI3-G-SYS-07", "agent explores despite insufficient certainty and stopping policy"),
    "RAI4-0011": ("RAI3-G-SYS-03", "poisoned context supplies false information to later reasoning"),
    "RAI4-0014": ("RAI3-A-SYS-03", "compromised external component propagates through an agent dependency"),
    "RAI4-0018": ("RAI3-A-SYS-01", "external interfaces expand consequential action authority"),
    "RAI4-0027": ("RAI3-A-SYS-01", "financial or property action exceeds safe delegated authority"),
    "RAI4-0028": ("RAI3-G-SYS-08", "indirect instructions redirect the agent from the intended objective"),
    "RAI4-0029": ("RAI3-A-SYS-03", "one tool output propagates compromise into subsequent tool calls"),
    "RAI4-0030": ("RAI3-G-INT-06", "cross-application action exposes sensitive data"),
    "RAI4-0033": ("RAI3-G-SYS-07", "agent proceeds with unjustified confidence about action side effects"),
    "RAI4-0037": ("RAI3-A-SYS-01", "real tools enable consequential action beyond safe necessity"),
    "RAI4-0045": ("RAI3-A-SYS-01", "operating-system authority enables harmful irreversible action"),
    "RAI4-0117": ("RAI3-G-SYS-09", "affected humans lose a meaningful veto or review channel"),
    "RAI4-0479": ("RAI3-A-SYS-01", "integrated tool authority is used in an unsafe or unauthorized way"),
    "RAI4-0480": ("RAI3-G-SYS-08", "multi-step execution drifts from the user objective"),
    "RAI4-0481": ("RAI3-A-SYS-01", "scope of autonomous authority expands without approval"),
    "RAI4-0484": ("RAI3-G-SYS-03", "stale or false stored information degrades later decisions"),
    "RAI4-0581": ("RAI3-G-SYS-08", "self-expanded goals diverge from the assigned objective"),
    "RAI4-0602": ("RAI3-A-SYS-01", "unsupervised execution combines broad delegated authority"),
    "RAI4-1122": ("RAI3-G-SYS-08", "learned goals drift away from human-endorsed objectives"),
    "RAI4-1130": ("RAI3-G-SYS-08", "consequentialist metric differs from user and social intent"),
    "RAI4-1161": ("RAI3-G-SYS-02", "planning is exercised beyond supported operating scope"),
    "RAI4-1234": ("RAI3-G-SYS-08", "proxy reward optimization diverges from intended performance"),
    "RAI4-1235": ("RAI3-G-SYS-08", "deployment objective diverges from the training objective"),
    "RAI4-1236": ("RAI3-G-SYS-08", "reward-signal interference subverts the intended objective"),
    "RAI4-1239": ("RAI3-G-SYS-08", "situational knowledge enables instrumental pursuit of misaligned goals"),
    "RAI4-1323": ("RAI3-G-SYS-08", "long-term goals and power-seeking differ from supplied goals"),
    "RAI4-1382": ("RAI3-G-SYS-09", "correction and reconsideration cannot be effectively exercised"),
    "RAI4-1424": ("RAI3-G-SYS-08", "AI goals and values diverge from human goals"),
    "RAI4-1431": ("RAI3-G-SYS-08", "harmful objective pursuit persists against human interests"),
    "RAI4-1669": ("RAI3-A-SYS-01", "unsafe API invocation turns delegated authority into external action"),
    "RAI4-1670": ("RAI3-G-SYS-03", "persistent poisoned records provide false information to later decisions"),
    "RAI4-1674": ("RAI3-G-SYS-09", "shutdown and correction cannot be meaningfully exercised"),
    "RAI4-1693": ("RAI3-G-SYS-08", "world-model exploitation optimizes reward against intended task success"),
    "RAI4-1694": ("RAI3-G-SYS-03", "incorrect world-model rollouts are treated as factual planning state"),
    "RAI4-1699": ("RAI3-G-SYS-08", "imperfect objective is gamed against designer intent"),
    "RAI4-1701": ("RAI3-G-SYS-07", "exploratory action proceeds without adequate uncertainty and stopping policy"),
}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def breadcrumb(node_id: str, nodes: dict[str, dict]) -> list[dict]:
    result = []
    while node_id:
        node = nodes[node_id]
        result.append({"node_id": node_id, "label_en": node["label_en"], "label_ko": node["label_ko"]})
        node_id = node.get("parent_id")
    return list(reversed(result))


def main() -> None:
    cards_payload = read(SOURCE / "cards.json")
    hierarchy = read(SOURCE / "hierarchy.json")
    cards = deepcopy(cards_payload["cards"])
    source_nodes = deepcopy(hierarchy["nodes"])
    source_node_by_id = {node["node_id"]: node for node in source_nodes}
    source_cards = {card["l4_id"]: card for card in cards_payload["cards"]}

    retired_cards = [card for card in cards if card["primary_l3_id"] in RETIRED_L3]
    if len(retired_cards) != 39 or {card["l4_id"] for card in retired_cards} != set(MIGRATIONS):
        raise ValueError("The retirement mapping must cover exactly the 39 cards in the four L3 families")

    active_nodes = [node for node in source_nodes if node["node_id"] not in RETIRED_L3]
    active_node_by_id = {node["node_id"]: node for node in active_nodes}
    for destination, _ in MIGRATIONS.values():
        if destination not in active_node_by_id or destination.startswith("RAI3-P-"):
            raise ValueError(f"Invalid forced destination: {destination}")

    ordered_l3_before = sorted(
        (node for node in source_nodes if node["level"] == 3), key=lambda node: node["node_id"]
    )
    l3_index_before = {node["node_id"]: index for index, node in enumerate(ordered_l3_before)}
    card_index = {card["l4_id"]: index for index, card in enumerate(cards)}
    card_embeddings = np.load(CARD_EMBEDDINGS).astype(np.float32)
    l3_embeddings = np.load(L3_EMBEDDINGS).astype(np.float32)
    if card_embeddings.shape[0] != len(cards) or l3_embeddings.shape[0] != len(ordered_l3_before):
        raise ValueError("Embedding cache is not aligned with v2.13.0")
    candidate_ids = [
        node["node_id"] for node in ordered_l3_before
        if node["node_id"] not in RETIRED_L3 and not node["node_id"].startswith("RAI3-P-")
    ]
    candidate_seed_indices = [l3_index_before[node_id] for node_id in candidate_ids]

    migrations = []
    newly_held = 0
    for card in retired_cards:
        l4_id = card["l4_id"]
        source_l3 = card["primary_l3_id"]
        destination, rationale = MIGRATIONS[l4_id]
        scores = card_embeddings[card_index[l4_id]] @ l3_embeddings[candidate_seed_indices].T
        rank_order = np.argsort(-scores)
        destination_position = candidate_ids.index(destination)
        destination_rank = int(np.where(rank_order == destination_position)[0][0]) + 1
        top_position = int(rank_order[0])
        was_hold = bool(card.get("decision_required"))
        newly_held += int(not was_hold)

        card["previous_primary_l3_id"] = source_l3
        card["primary_l3_id"] = destination
        card["breadcrumb"] = breadcrumb(destination, active_node_by_id)
        card["assignment_status"] = "forced_reassigned_from_retired_l3"
        card["review_status"] = "forced_retirement_migration_hold"
        card["decision_required"] = True
        card["decision_reason"] = "RETIRED_SPARSE_AGENTIC_L3_FORCED_MIGRATION"
        card["human_approved"] = False
        card["mapping_review_method"] = "mechanism_first_retired_l3_forced_migration_v2.14"
        card["retired_l3_migration"] = {
            "from_l3_id": source_l3,
            "to_l3_id": destination,
            "rationale": rationale,
            "destination_seed_cosine": float(scores[destination_position]),
            "destination_seed_rank_among_26": destination_rank,
            "top_seed_l3_id": candidate_ids[top_position],
            "top_seed_cosine": float(scores[top_position]),
        }
        migrations.append({
            "l4_id": l4_id,
            "label_en": card["label_en"],
            "from_l3_id": source_l3,
            "from_l3_label": RETIRED_L3[source_l3],
            "to_l3_id": destination,
            "to_l3_label": active_node_by_id[destination]["label_en"],
            "rationale": rationale,
            "was_hold": was_hold,
            "decision_required": True,
            "destination_seed_cosine": float(scores[destination_position]),
            "destination_seed_rank_among_26": destination_rank,
            "top_seed_l3_id": candidate_ids[top_position],
            "top_seed_cosine": float(scores[top_position]),
        })

    for card in cards:
        card["release_id"] = RELEASE_ID
    counts = Counter(card["primary_l3_id"] for card in cards)
    for node in active_nodes:
        if node["level"] == 3:
            node["l4_count"] = counts[node["node_id"]]
    if any(counts[node_id] for node_id in RETIRED_L3):
        raise AssertionError("A retired L3 still has assigned cards")
    if any(node["level"] == 3 and node.get("l4_count", 0) == 0 for node in active_nodes):
        raise AssertionError("The active hierarchy contains an empty L3")

    archive = []
    for node_id, label in RETIRED_L3.items():
        node = deepcopy(source_node_by_id[node_id])
        node.update({
            "status": "retired",
            "retired_in": RELEASE_ID,
            "retirement_reason": "sparse experimental Agentic family; operational granularity withdrawn",
            "l4_count_at_retirement": sum(card["primary_l3_id"] == node_id for card in cards_payload["cards"]),
            "id_reuse_prohibited": True,
        })
        archive.append(node)

    cards_payload["release_id"] = RELEASE_ID
    cards_payload["cards"] = cards
    hierarchy["release_id"] = RELEASE_ID
    hierarchy["nodes"] = active_nodes
    hierarchy["retired_l3_archive"] = archive
    write(OUT / "cards.json", cards_payload)
    write(OUT / "hierarchy.json", hierarchy)
    write(REPORT / "retired_l3_nodes.json", archive)
    write(REPORT / "l4_migrations.json", migrations)
    with (REPORT / "l4_migrations.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(migrations[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(migrations)

    physical_before = {
        card["l4_id"]: {**card, "release_id": SOURCE_ID}
        for card in cards if card.get("assignment_status") == "locked_physical"
    }
    for l4_id, after in physical_before.items():
        if after != source_cards[l4_id]:
            raise AssertionError(f"Protected Physical card changed: {l4_id}")

    destination_counts = Counter(row["to_l3_id"] for row in migrations)
    domain_id = {"G": "RAI1-G", "A": "RAI1-A", "P": "RAI1-P"}
    domain_counts = Counter(domain_id[card["primary_l3_id"].split("-")[1]] for card in cards)
    summary = {
        "release_id": RELEASE_ID,
        "source_release": SOURCE_ID,
        "retired_l3_ids": list(RETIRED_L3),
        "retired_l3_count": 4,
        "migrated_l4_count": len(migrations),
        "newly_held_count": newly_held,
        "all_migrations_hold": all(row["decision_required"] for row in migrations),
        "physical_lock_preserved": len(physical_before) == 182,
        "candidate_destination_scope": "26 active non-Physical L3 families",
        "method": "mechanism-first explicit forced migration with BGE-M3 seed-rank diagnostics",
        "destination_counts": dict(sorted(destination_counts.items())),
        "domain_counts": dict(sorted(domain_counts.items())),
        "counts": {
            "l4": len(cards),
            "l3_active": sum(node["level"] == 3 for node in active_nodes),
            "l3_retired_archived": len(archive),
            "physical_locked": len(physical_before),
            "decision_required": sum(bool(card.get("decision_required")) for card in cards),
        },
    }
    write(REPORT / "summary.json", summary)

    manifest = {
        "release_id": RELEASE_ID,
        "source_release": SOURCE_ID,
        "status": "published",
        "counts": {
            "l4": len(cards),
            "classified": len(cards),
            "physical_locked": len(physical_before),
            "decision_required": summary["counts"]["decision_required"],
            "l1_nodes": 3,
            "l2_categories": 3,
            "l2_path_nodes": 6,
            "l3_nodes": summary["counts"]["l3_active"],
            "retired_l3_archived": len(archive),
        },
        "summary": summary,
        "files": [
            {"path": "cards.json", "sha256": sha256(OUT / "cards.json")},
            {"path": "hierarchy.json", "sha256": sha256(OUT / "hierarchy.json")},
            {"path": "reports/data_quality/agentic_l3_retirement_v2.14.0/summary.json", "sha256": sha256(REPORT / "summary.json")},
            {"path": "reports/data_quality/agentic_l3_retirement_v2.14.0/retired_l3_nodes.json", "sha256": sha256(REPORT / "retired_l3_nodes.json")},
            {"path": "reports/data_quality/agentic_l3_retirement_v2.14.0/l4_migrations.json", "sha256": sha256(REPORT / "l4_migrations.json")},
        ],
    }
    write(OUT / "manifest.json", manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
