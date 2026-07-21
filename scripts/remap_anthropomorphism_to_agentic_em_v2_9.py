#!/usr/bin/env python3
"""Constrained EM remapping from Anthropomorphism to four Agentic L3 nodes."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "v2.8.0"
RELEASE_ID = "v2.9.0"
SOURCE = ROOT / "public/data/releases" / SOURCE_ID
OUT = ROOT / "public/data/releases" / RELEASE_ID
REPORT = ROOT / "reports/data_quality/anthropomorphism_agentic_em_v2.9.0"
EMBEDDINGS = ROOT / "reports/validation/v2.8.0/reliability/card_embeddings_bge_m3.npy"
SEEDS = ROOT / "reports/validation/v2.8.0/reliability/l3_seed_embeddings_bge_m3.npy"

ANTHRO = "RAI3-G-INT-10"
CANDIDATES = [
    ANTHRO,
    "RAI3-A-SYS-07",
    "RAI3-A-SYS-08",
    "RAI3-A-SYS-09",
    "RAI3-A-SYS-10",
]

# A destination is eligible only when its direct mechanism occurs in the card.
# This prevents generic occurrences of words such as "tool", "memory", or
# "control" from overriding the semantic geometry.
MECHANISM_PATTERNS = {
    ANTHRO: [
        r"anthropomorph", r"human[- ]like", r"emotional (?:trust|depend)",
        r"parasocial", r"relational bond", r"social presence", r"personif",
    ],
    "RAI3-A-SYS-07": [
        r"reward hack", r"reward tamper", r"goal (?:drift|expansion|hijack|pursuit)",
        r"goals? and values? (?:that )?are different", r"objective gaming",
        r"proxy objective", r"plan(?:ning)? hijack", r"long[- ]horizon plan",
        r"unsafe exploration", r"instrumental subgoals?",
    ],
    "RAI3-A-SYS-08": [
        r"(?:agent|agentic|autonomous).{0,80}tool[- ]?(?:use|call|calling|execution|invocation)",
        r"tool[- ]?(?:use|call|calling|execution|invocation).{0,80}(?:agent|agentic|autonomous)",
        r"real[- ]tool", r"computer[- ]use agent", r"operating.system action",
        r"\bMCP (?:tool|server|service)",
    ],
    "RAI3-A-SYS-09": [
        r"(?:agent|agentic).{0,50}memory", r"memory.{0,50}(?:agent|agentic)",
        r"cross[- ]session memory", r"memory poison", r"persistent memory",
    ],
    "RAI3-A-SYS-10": [
        r"human veto", r"human override", r"absent supervisor", r"unsafe interrupt",
        r"autonomy escalation", r"unsupervised autonomous", r"shutdown resistance",
        r"corrigibility", r"cannot.{0,40}(?:interrupt|pause|shut.?down|roll.?back)",
    ],
}

CENTROID_WEIGHT = 0.60
DEFINITION_WEIGHT = 0.30
KEYWORD_WEIGHT = 0.10
MIN_MARGIN = 0.02
MAX_ITERATIONS = 50


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unit(vector: np.ndarray) -> np.ndarray:
    return vector / max(float(np.linalg.norm(vector)), 1e-12)


def hits(text: str, node_id: str) -> list[str]:
    return [pattern for pattern in MECHANISM_PATTERNS[node_id] if re.search(pattern, text, re.I | re.S)]


def breadcrumb(node_id: str, nodes: dict[str, dict]) -> list[dict]:
    path = []
    while node_id:
        node = nodes[node_id]
        path.append({"node_id": node_id, "label_en": node["label_en"], "label_ko": node["label_ko"]})
        node_id = node.get("parent_id")
    return list(reversed(path))


def main() -> None:
    cards_payload = read(SOURCE / "cards.json")
    hierarchy = read(SOURCE / "hierarchy.json")
    cards = cards_payload["cards"]
    nodes = {node["node_id"]: node for node in hierarchy["nodes"]}
    l3_nodes = sorted((node for node in hierarchy["nodes"] if node["level"] == 3), key=lambda node: node["node_id"])
    l3_index = {node["node_id"]: index for index, node in enumerate(l3_nodes)}

    x = np.load(EMBEDDINGS)
    seed_embeddings = np.load(SEEDS)
    if len(x) != len(cards) or len(seed_embeddings) != len(l3_nodes):
        raise ValueError("Embedding cache is not aligned with the v2.8.0 release")

    movable = np.array([index for index, card in enumerate(cards) if card["primary_l3_id"] == ANTHRO])
    if len(movable) != 245:
        raise ValueError(f"Expected 245 Anthropomorphism cards, found {len(movable)}")
    movable_set = set(movable.tolist())
    fixed = {
        cluster: [
            index for index, card in enumerate(cards)
            if card["primary_l3_id"] == node_id and index not in movable_set
        ]
        for cluster, node_id in enumerate(CANDIDATES)
    }
    assignments = np.zeros(len(movable), dtype=np.int32)
    trace = []
    score_records: dict[str, dict] = {}

    for iteration in range(1, MAX_ITERATIONS + 1):
        centroids = []
        for cluster, node_id in enumerate(CANDIDATES):
            members = fixed[cluster] + movable[assignments == cluster].tolist()
            if not members:
                centroids.append(seed_embeddings[l3_index[node_id]])
            else:
                centroids.append(unit(x[members].mean(axis=0)))
        centroids = np.asarray(centroids, dtype=np.float32)

        changes = 0
        objective = 0.0
        next_assignments = assignments.copy()
        for row, card_index in enumerate(movable):
            card = cards[card_index]
            text = " ".join((card.get("label_en", ""), card.get("definition_en", "")))
            centroid_similarity = x[card_index] @ centroids.T
            definition_similarity = x[card_index] @ seed_embeddings[[l3_index[node_id] for node_id in CANDIDATES]].T
            keyword_hits = {node_id: hits(text, node_id) for node_id in CANDIDATES}
            keyword_signal = np.array([bool(keyword_hits[node_id]) for node_id in CANDIDATES], dtype=np.float32)
            scores = (
                CENTROID_WEIGHT * centroid_similarity
                + DEFINITION_WEIGHT * definition_similarity
                + KEYWORD_WEIGHT * keyword_signal
            )
            eligible = [0] + [cluster for cluster in range(1, len(CANDIDATES)) if keyword_hits[CANDIDATES[cluster]]]
            best = max(eligible, key=lambda cluster: (float(scores[cluster]), -cluster))
            if best and scores[best] < scores[0] + MIN_MARGIN:
                best = 0
            next_assignments[row] = best
            objective += float(scores[best])
            score_records[card["l4_id"]] = {
                "scores": {node_id: float(scores[cluster]) for cluster, node_id in enumerate(CANDIDATES)},
                "keyword_hits": keyword_hits,
                "selected": CANDIDATES[best],
                "margin_over_anthropomorphism": float(scores[best] - scores[0]),
            }
            changes += int(best != assignments[row])

        assignments = next_assignments
        trace.append({
            "iteration": iteration,
            "changes": changes,
            "objective": objective / len(movable),
            "counts": {CANDIDATES[cluster]: int(np.sum(assignments == cluster)) for cluster in range(len(CANDIDATES))},
        })
        if changes == 0:
            break
    else:
        raise RuntimeError("Constrained EM did not converge")

    audits = []
    for row, card_index in enumerate(movable):
        destination = CANDIDATES[int(assignments[row])]
        card = cards[card_index]
        if destination == ANTHRO:
            continue
        evidence = score_records[card["l4_id"]]
        card["primary_l3_id"] = destination
        card["breadcrumb"] = breadcrumb(destination, nodes)
        card["release_id"] = RELEASE_ID
        card["assignment_status"] = "algorithmically_remapped"
        card["review_status"] = "algorithmically_remapped_hold"
        card["decision_required"] = True
        card["decision_reason"] = "CONSTRAINED_EM_REMAP_REQUIRES_HUMAN_REVIEW"
        card["mapping_review_method"] = "anthropomorphism_to_agentic_constrained_em_v2.9"
        card["v2_9_em_scores"] = evidence["scores"]
        audits.append({
            "l4_id": card["l4_id"],
            "label_en": card["label_en"],
            "from_l3_id": ANTHRO,
            "to_l3_id": destination,
            "margin_over_anthropomorphism": evidence["margin_over_anthropomorphism"],
            "keyword_hits": evidence["keyword_hits"][destination],
            "decision_required": True,
        })

    for card in cards:
        card["release_id"] = RELEASE_ID
    counts = Counter(card["primary_l3_id"] for card in cards)
    for node in hierarchy["nodes"]:
        if node["level"] == 3:
            node["l4_count"] = counts[node["node_id"]]
    hierarchy["release_id"] = RELEASE_ID
    cards_payload["release_id"] = RELEASE_ID

    write(OUT / "cards.json", cards_payload)
    write(OUT / "hierarchy.json", hierarchy)
    write(REPORT / "remapping_audit.json", audits)
    write(REPORT / "em_trace.json", trace)
    write(REPORT / "card_scores.json", score_records)
    with (REPORT / "remapping_audit.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "l4_id", "label_en", "from_l3_id", "to_l3_id",
            "margin_over_anthropomorphism", "keyword_hits", "decision_required",
        ], lineterminator="\n")
        writer.writeheader()
        for row in audits:
            writer.writerow({**row, "keyword_hits": " | ".join(row["keyword_hits"])})

    summary = {
        "release_id": RELEASE_ID,
        "source_release": SOURCE_ID,
        "population": {"all_l4": len(cards), "anthropomorphism_evaluated": len(movable), "physical_unchanged": 182},
        "method": {
            "name": "keyword-gated constrained spherical EM",
            "candidate_l3": CANDIDATES,
            "weights": {"centroid_similarity": CENTROID_WEIGHT, "definition_similarity": DEFINITION_WEIGHT, "keyword_signal": KEYWORD_WEIGHT},
            "minimum_destination_margin": MIN_MARGIN,
        },
        "converged": trace[-1]["changes"] == 0,
        "iterations": len(trace),
        "trace": trace,
        "remapped_total": len(audits),
        "remapped_by_destination": dict(Counter(row["to_l3_id"] for row in audits)),
        "anthropomorphism_before": len(movable),
        "anthropomorphism_after": counts[ANTHRO],
        "all_remaps_retain_hold": all(row["decision_required"] for row in audits),
    }
    write(REPORT / "summary.json", summary)

    manifest = {
        "release_id": RELEASE_ID,
        "source_release": SOURCE_ID,
        "status": "generated_unpublished",
        "counts": {
            "l4": len(cards), "classified": len(cards), "physical_locked": 182,
            "decision_required": sum(bool(card.get("decision_required")) for card in cards),
            "l1_nodes": 3, "l2_categories": 3, "l2_path_nodes": 6, "l3_nodes": 54,
        },
        "summary": summary,
        "files": [
            {"path": "cards.json", "sha256": sha256(OUT / "cards.json")},
            {"path": "hierarchy.json", "sha256": sha256(OUT / "hierarchy.json")},
            {"path": "reports/data_quality/anthropomorphism_agentic_em_v2.9.0/summary.json", "sha256": sha256(REPORT / "summary.json")},
        ],
    }
    write(OUT / "manifest.json", manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
