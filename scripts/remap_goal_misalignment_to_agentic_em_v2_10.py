#!/usr/bin/env python3
"""Constrained EM remapping from Goal Misalignment to four Agentic L3 nodes."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "v2.9.0"
RELEASE_ID = "v2.10.0"
SOURCE = ROOT / "public/data/releases" / SOURCE_ID
OUT = ROOT / "public/data/releases" / RELEASE_ID
REPORT = ROOT / "reports/data_quality/goal_misalignment_agentic_em_v2.10.0"
EMBEDDINGS = ROOT / "reports/validation/v2.8.0/reliability/card_embeddings_bge_m3.npy"
SEEDS = ROOT / "reports/validation/v2.8.0/reliability/l3_seed_embeddings_bge_m3.npy"

SOURCE_L3 = "RAI3-G-SYS-08"
CANDIDATES = [SOURCE_L3, "RAI3-A-SYS-07", "RAI3-A-SYS-08", "RAI3-A-SYS-09", "RAI3-A-SYS-10"]
PATTERNS = {
    "RAI3-A-SYS-07": [
        r"(?:agent|assistant|autonomous (?:agent|system)).{0,120}(?:multi[- ]step plan|plans?|planning|subgoals?|actively pursues|goal pursuit)",
        r"(?:multi[- ]step plan|instrumental subgoals?|consequentialist reasoning).{0,120}(?:agent|assistant|autonomous)",
        r"goal misgeneralization.{0,120}agent", r"agent task drift",
    ],
    "RAI3-A-SYS-08": [
        r"(?:agent|agentic|autonomous).{0,80}tool[- ]?(?:use|call|calling|execution|invocation)",
        r"tool[- ]?(?:use|call|calling|execution|invocation).{0,80}(?:agent|agentic|autonomous)",
        r"real[- ]tool", r"computer[- ]use agent", r"operating.system action", r"\bMCP (?:tool|server|service)",
    ],
    "RAI3-A-SYS-09": [
        r"(?:agent|agentic).{0,50}memory", r"memory.{0,50}(?:agent|agentic)",
        r"cross[- ]session memory", r"memory poison", r"persistent memory",
    ],
    "RAI3-A-SYS-10": [
        r"human veto", r"human override", r"absent supervisor", r"unsafe interrupt",
        r"autonomy escalation", r"unsupervised autonomous", r"shutdown resistance",
        r"corrigibility", r"cannot.{0,40}(?:interrupt|pause|shut.?down|roll.?back)",
        r"resist.{0,50}(?:correction|interrupt|shut.?down)",
    ],
}
CENTROID_WEIGHT, DEFINITION_WEIGHT, KEYWORD_WEIGHT = 0.60, 0.30, 0.10
MIN_MARGIN, MAX_ITERATIONS = 0.02, 50


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unit(vector: np.ndarray) -> np.ndarray:
    return vector / max(float(np.linalg.norm(vector)), 1e-12)


def keyword_hits(text: str, node_id: str) -> list[str]:
    return [pattern for pattern in PATTERNS[node_id] if re.search(pattern, text, re.I | re.S)]


def breadcrumb(node_id: str, nodes: dict[str, dict]) -> list[dict]:
    result = []
    while node_id:
        node = nodes[node_id]
        result.append({"node_id": node_id, "label_en": node["label_en"], "label_ko": node["label_ko"]})
        node_id = node.get("parent_id")
    return list(reversed(result))


def main() -> None:
    payload = read(SOURCE / "cards.json")
    hierarchy = read(SOURCE / "hierarchy.json")
    cards, hierarchy_nodes = payload["cards"], hierarchy["nodes"]
    nodes = {node["node_id"]: node for node in hierarchy_nodes}
    l3_nodes = sorted((node for node in hierarchy_nodes if node["level"] == 3), key=lambda node: node["node_id"])
    l3_index = {node["node_id"]: index for index, node in enumerate(l3_nodes)}
    x, seeds = np.load(EMBEDDINGS), np.load(SEEDS)
    if len(x) != len(cards) or len(seeds) != len(l3_nodes):
        raise ValueError("Embedding cache is not aligned with the release")

    movable = np.array([index for index, card in enumerate(cards) if card["primary_l3_id"] == SOURCE_L3])
    if len(movable) != 149:
        raise ValueError(f"Expected 149 Goal Misalignment cards, found {len(movable)}")
    movable_set = set(movable.tolist())
    fixed = {
        cluster: [index for index, card in enumerate(cards) if card["primary_l3_id"] == node_id and index not in movable_set]
        for cluster, node_id in enumerate(CANDIDATES)
    }
    assignments = np.zeros(len(movable), dtype=np.int32)
    trace, score_records = [], {}

    for iteration in range(1, MAX_ITERATIONS + 1):
        centroids = []
        for cluster, node_id in enumerate(CANDIDATES):
            members = fixed[cluster] + movable[assignments == cluster].tolist()
            centroids.append(unit(x[members].mean(axis=0)) if members else seeds[l3_index[node_id]])
        centroids = np.asarray(centroids, dtype=np.float32)
        next_assignments, changes, objective = assignments.copy(), 0, 0.0
        for row, card_index in enumerate(movable):
            card = cards[card_index]
            text = " ".join((card.get("label_en", ""), card.get("definition_en", "")))
            centroid_similarity = x[card_index] @ centroids.T
            definition_similarity = x[card_index] @ seeds[[l3_index[node_id] for node_id in CANDIDATES]].T
            hits = {SOURCE_L3: []}
            hits.update({node_id: keyword_hits(text, node_id) for node_id in CANDIDATES[1:]})
            signal = np.array([0.0] + [float(bool(hits[node_id])) for node_id in CANDIDATES[1:]], dtype=np.float32)
            scores = CENTROID_WEIGHT * centroid_similarity + DEFINITION_WEIGHT * definition_similarity + KEYWORD_WEIGHT * signal
            eligible = [0] + [cluster for cluster in range(1, len(CANDIDATES)) if hits[CANDIDATES[cluster]]]
            best = max(eligible, key=lambda cluster: (float(scores[cluster]), -cluster))
            if best and scores[best] < scores[0] + MIN_MARGIN:
                best = 0
            next_assignments[row] = best
            changes += int(best != assignments[row])
            objective += float(scores[best])
            score_records[card["l4_id"]] = {
                "scores": {node_id: float(scores[cluster]) for cluster, node_id in enumerate(CANDIDATES)},
                "keyword_hits": hits, "selected": CANDIDATES[best],
                "margin_over_goal_misalignment": float(scores[best] - scores[0]),
            }
        assignments = next_assignments
        trace.append({
            "iteration": iteration, "changes": changes, "objective": objective / len(movable),
            "counts": {CANDIDATES[cluster]: int(np.sum(assignments == cluster)) for cluster in range(len(CANDIDATES))},
        })
        if changes == 0:
            break
    else:
        raise RuntimeError("Constrained EM did not converge")

    audits = []
    for row, card_index in enumerate(movable):
        destination, card = CANDIDATES[int(assignments[row])], cards[card_index]
        if destination == SOURCE_L3:
            continue
        evidence = score_records[card["l4_id"]]
        card["primary_l3_id"] = destination
        card["breadcrumb"] = breadcrumb(destination, nodes)
        card["assignment_status"] = "algorithmically_remapped"
        card["review_status"] = "algorithmically_remapped_hold"
        card["decision_required"] = True
        card["decision_reason"] = "CONSTRAINED_EM_REMAP_REQUIRES_HUMAN_REVIEW"
        card["mapping_review_method"] = "goal_misalignment_to_agentic_constrained_em_v2.10"
        card["v2_10_em_scores"] = evidence["scores"]
        audits.append({
            "l4_id": card["l4_id"], "label_en": card["label_en"], "from_l3_id": SOURCE_L3,
            "to_l3_id": destination, "margin_over_goal_misalignment": evidence["margin_over_goal_misalignment"],
            "keyword_hits": evidence["keyword_hits"][destination], "decision_required": True,
        })

    for card in cards:
        card["release_id"] = RELEASE_ID
    counts = Counter(card["primary_l3_id"] for card in cards)
    for node in hierarchy_nodes:
        if node["level"] == 3:
            node["l4_count"] = counts[node["node_id"]]
    payload["release_id"], hierarchy["release_id"] = RELEASE_ID, RELEASE_ID
    write(OUT / "cards.json", payload)
    write(OUT / "hierarchy.json", hierarchy)
    write(REPORT / "remapping_audit.json", audits)
    write(REPORT / "em_trace.json", trace)
    write(REPORT / "card_scores.json", score_records)
    with (REPORT / "remapping_audit.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = ["l4_id", "label_en", "from_l3_id", "to_l3_id", "margin_over_goal_misalignment", "keyword_hits", "decision_required"]
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in audits:
            writer.writerow({**row, "keyword_hits": " | ".join(row["keyword_hits"])})

    summary = {
        "release_id": RELEASE_ID, "source_release": SOURCE_ID,
        "population": {"all_l4": len(cards), "goal_misalignment_evaluated": len(movable), "physical_unchanged": 182},
        "method": {
            "name": "keyword-gated constrained spherical EM", "candidate_l3": CANDIDATES,
            "weights": {"centroid_similarity": CENTROID_WEIGHT, "definition_similarity": DEFINITION_WEIGHT, "keyword_signal": KEYWORD_WEIGHT},
            "minimum_destination_margin": MIN_MARGIN,
        },
        "converged": trace[-1]["changes"] == 0, "iterations": len(trace), "trace": trace,
        "remapped_total": len(audits), "remapped_by_destination": dict(Counter(row["to_l3_id"] for row in audits)),
        "goal_misalignment_before": len(movable), "goal_misalignment_after": counts[SOURCE_L3],
        "all_remaps_retain_hold": all(row["decision_required"] for row in audits),
    }
    write(REPORT / "summary.json", summary)
    manifest = {
        "release_id": RELEASE_ID, "source_release": SOURCE_ID, "status": "generated_unpublished",
        "counts": {
            "l4": len(cards), "classified": len(cards), "physical_locked": 182,
            "decision_required": sum(bool(card.get("decision_required")) for card in cards),
            "l1_nodes": 3, "l2_categories": 3, "l2_path_nodes": 6, "l3_nodes": 54,
        },
        "summary": summary,
        "files": [
            {"path": "cards.json", "sha256": sha256(OUT / "cards.json")},
            {"path": "hierarchy.json", "sha256": sha256(OUT / "hierarchy.json")},
            {"path": "reports/data_quality/goal_misalignment_agentic_em_v2.10.0/summary.json", "sha256": sha256(REPORT / "summary.json")},
        ],
    }
    write(OUT / "manifest.json", manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
