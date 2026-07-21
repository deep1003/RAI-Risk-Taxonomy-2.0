#!/usr/bin/env python3
"""Conservatively remap Copyrights cards to better non-Physical L3 nodes."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "v2.10.0"
RELEASE_ID = "v2.11.0"
SOURCE = ROOT / "public/data/releases" / SOURCE_ID
OUT = ROOT / "public/data/releases" / RELEASE_ID
REPORT = ROOT / "reports/data_quality/copyrights_all_l3_em_v2.11.0"
EMBEDDINGS = ROOT / "reports/validation/v2.8.0/reliability/card_embeddings_bge_m3.npy"
SEEDS = ROOT / "reports/validation/v2.8.0/reliability/l3_seed_embeddings_bge_m3.npy"

SOURCE_L3 = "RAI3-G-INT-08"
CENTROID_WEIGHT, DEFINITION_WEIGHT, KEYWORD_WEIGHT = 0.60, 0.30, 0.10
MIN_MARGIN, MIN_KEYWORD_SIMILARITY, MAX_ITERATIONS = 0.02, 0.015, 50

# These guards prevent a shared generic word (for example, "decision") from
# being mistaken for evidence of the destination's defining risk mechanism.
DESTINATION_GUARDS = {
    "RAI3-G-SYS-03": re.compile(
        r"misinformation|disinformation|fake news|misleading information|"
        r"conflicting information|incorrect information|false information", re.I
    ),
    "RAI3-G-INT-09": re.compile(
        r"weapon|cyber[- ]?(?:attack|offen[cs]e)|malicious (?:attack|hack)|"
        r"exploit(?:ation| vulnerabilities)|biological|chemical|nuclear", re.I
    ),
    "RAI3-G-INT-04": re.compile(
        r"stereotyp|discriminat|demeaning|protected group|marginali[sz]ed|"
        r"hate(?:ful| speech)|unfairness", re.I
    ),
    "RAI3-G-SYS-09": re.compile(
        r"contest|challenge|appeal|redress|reconsider|review procedure|"
        r"seek an alternative", re.I
    ),
}
AGENTIC_SIGNAL = re.compile(
    r"\b(agent(?:ic|s)?|autonomous|multi[- ]step plan(?:ning)?|"
    r"tool[- ]?(?:call|use|execution|invocation)|cross[- ]session memory|"
    r"persistent memory|human[- ]in[- ]the[- ]loop|supervisor|interrupt|"
    r"roll.?back|shutdown|corrigib)\b", re.I
)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unit(vector: np.ndarray) -> np.ndarray:
    return vector / max(float(np.linalg.norm(vector)), 1e-12)


def breadcrumb(node_id: str, nodes: dict[str, dict]) -> list[dict]:
    result = []
    while node_id:
        node = nodes[node_id]
        result.append({"node_id": node_id, "label_en": node["label_en"], "label_ko": node["label_ko"]})
        node_id = node.get("parent_id")
    return list(reversed(result))


def destination_allowed(node_id: str, text: str, keyword_similarity: float) -> bool:
    if keyword_similarity < MIN_KEYWORD_SIMILARITY:
        return False
    if node_id.startswith("RAI3-A-") and not AGENTIC_SIGNAL.search(text):
        return False
    guard = DESTINATION_GUARDS.get(node_id)
    return guard.search(text) is not None if guard else True


def main() -> None:
    payload, hierarchy = read(SOURCE / "cards.json"), read(SOURCE / "hierarchy.json")
    cards, hierarchy_nodes = payload["cards"], hierarchy["nodes"]
    nodes = {node["node_id"]: node for node in hierarchy_nodes}
    l3_nodes = sorted((node for node in hierarchy_nodes if node["level"] == 3), key=lambda node: node["node_id"])
    l3_index = {node["node_id"]: index for index, node in enumerate(l3_nodes)}
    candidates = [SOURCE_L3] + [
        node["node_id"] for node in l3_nodes
        if node["node_id"] != SOURCE_L3 and not node["node_id"].startswith("RAI3-P-")
    ]
    x, seeds = np.load(EMBEDDINGS), np.load(SEEDS)
    if len(x) != len(cards) or len(seeds) != len(l3_nodes):
        raise ValueError("Embedding cache is not aligned with the release")

    movable = np.array([index for index, card in enumerate(cards) if card["primary_l3_id"] == SOURCE_L3])
    if len(movable) != 117:
        raise ValueError(f"Expected 117 Copyrights cards, found {len(movable)}")
    movable_set = set(movable.tolist())
    fixed = {
        cluster: [
            index for index, card in enumerate(cards)
            if card["primary_l3_id"] == node_id and index not in movable_set
        ]
        for cluster, node_id in enumerate(candidates)
    }

    card_texts = [" ".join((card.get("label_en", ""), card.get("definition_en", ""))) for card in cards]
    node_texts = [" ".join((nodes[node_id].get("label_en", ""), nodes[node_id].get("definition_en", ""))) for node_id in candidates]
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
    tfidf = vectorizer.fit_transform(node_texts + card_texts)
    keyword_similarity = (
        normalize(tfidf[len(candidates):])[movable] @ normalize(tfidf[:len(candidates)]).T
    ).toarray()

    assignments = np.zeros(len(movable), dtype=np.int32)
    trace, score_records = [], {}
    seed_indices = [l3_index[node_id] for node_id in candidates]
    for iteration in range(1, MAX_ITERATIONS + 1):
        centroids = []
        for cluster, node_id in enumerate(candidates):
            members = fixed[cluster] + movable[assignments == cluster].tolist()
            centroids.append(unit(x[members].mean(axis=0)) if members else seeds[l3_index[node_id]])
        centroids = np.asarray(centroids, dtype=np.float32)
        next_assignments, changes, objective = assignments.copy(), 0, 0.0
        for row, card_index in enumerate(movable):
            card, text = cards[card_index], card_texts[card_index]
            centroid_similarity = x[card_index] @ centroids.T
            definition_similarity = x[card_index] @ seeds[seed_indices].T
            scores = (
                CENTROID_WEIGHT * centroid_similarity
                + DEFINITION_WEIGHT * definition_similarity
                + KEYWORD_WEIGHT * keyword_similarity[row]
            )
            eligible = [0] + [
                cluster for cluster in range(1, len(candidates))
                if destination_allowed(candidates[cluster], text, float(keyword_similarity[row, cluster]))
            ]
            best = max(eligible, key=lambda cluster: (float(scores[cluster]), -cluster))
            if best and scores[best] < scores[0] + MIN_MARGIN:
                best = 0
            next_assignments[row] = best
            changes += int(best != assignments[row])
            objective += float(scores[best])
            score_records[card["l4_id"]] = {
                "scores": {node_id: float(scores[cluster]) for cluster, node_id in enumerate(candidates)},
                "keyword_similarity": {
                    node_id: float(keyword_similarity[row, cluster])
                    for cluster, node_id in enumerate(candidates)
                },
                "selected": candidates[best],
                "margin_over_copyrights": float(scores[best] - scores[0]),
            }
        assignments = next_assignments
        trace.append({
            "iteration": iteration,
            "changes": changes,
            "objective": objective / len(movable),
            "counts": {
                candidates[cluster]: int(np.sum(assignments == cluster))
                for cluster in range(len(candidates)) if np.sum(assignments == cluster)
            },
        })
        if changes == 0:
            break
    else:
        raise RuntimeError("Constrained EM did not converge")

    audits = []
    for row, card_index in enumerate(movable):
        destination, card = candidates[int(assignments[row])], cards[card_index]
        if destination == SOURCE_L3:
            continue
        evidence = score_records[card["l4_id"]]
        card["primary_l3_id"] = destination
        card["breadcrumb"] = breadcrumb(destination, nodes)
        card["assignment_status"] = "algorithmically_remapped"
        card["review_status"] = "algorithmically_remapped_hold"
        card["decision_required"] = True
        card["decision_reason"] = "CONSTRAINED_EM_REMAP_REQUIRES_HUMAN_REVIEW"
        card["mapping_review_method"] = "copyrights_all_nonphysical_l3_constrained_em_v2.11"
        card["v2_11_em_scores"] = evidence["scores"]
        audits.append({
            "l4_id": card["l4_id"], "label_en": card["label_en"],
            "from_l3_id": SOURCE_L3, "to_l3_id": destination,
            "margin_over_copyrights": evidence["margin_over_copyrights"],
            "keyword_similarity": evidence["keyword_similarity"][destination],
            "decision_required": True,
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
        fields = ["l4_id", "label_en", "from_l3_id", "to_l3_id", "margin_over_copyrights", "keyword_similarity", "decision_required"]
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(audits)

    summary = {
        "release_id": RELEASE_ID, "source_release": SOURCE_ID,
        "population": {"all_l4": len(cards), "copyrights_evaluated": len(movable), "physical_locked": 182},
        "method": {
            "name": "definition- and keyword-gated constrained spherical EM",
            "candidate_l3": candidates,
            "excluded_destination_scope": "All Physical L3 nodes are locked to the authoritative 182-card taxonomy.",
            "weights": {"centroid_similarity": CENTROID_WEIGHT, "definition_similarity": DEFINITION_WEIGHT, "keyword_similarity": KEYWORD_WEIGHT},
            "minimum_destination_margin": MIN_MARGIN,
            "minimum_keyword_similarity": MIN_KEYWORD_SIMILARITY,
            "agentic_uniqueness_gate": True,
            "destination_definition_guard": True,
        },
        "converged": trace[-1]["changes"] == 0, "iterations": len(trace), "trace": trace,
        "remapped_total": len(audits),
        "remapped_by_destination": dict(Counter(row["to_l3_id"] for row in audits)),
        "copyrights_before": len(movable), "copyrights_after": counts[SOURCE_L3],
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
            {"path": "reports/data_quality/copyrights_all_l3_em_v2.11.0/summary.json", "sha256": sha256(REPORT / "summary.json")},
        ],
    }
    write(OUT / "manifest.json", manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
