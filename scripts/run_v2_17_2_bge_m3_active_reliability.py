#!/usr/bin/env python3
"""Run BGE-M3 constrained-EM reliability on the v2.17.2 release candidate.

The v2.17.2-rc card file preserves retired IDs for provenance. Reliability is
computed on active cards only. The semantic L3 hierarchy is inherited from
v2.17.1 because the release candidate changes L4 labels and definitions, not
the L1-L3 taxonomy.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.preprocessing import normalize


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RELEASE = "v2.17.2-rc"
HIERARCHY_RELEASE = "v2.17.1"
OUT = ROOT / "reports/validation/v2.17.2/bge_m3_active"
MODEL = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "/Users/deep1003/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181"
)
SEED = 20260722
np.random.seed(SEED)


def load_inputs() -> tuple[list[dict], list[dict]]:
    cards_all = json.loads((ROOT / f"public/data/releases/{SOURCE_RELEASE}/cards.json").read_text())["cards"]
    cards = [card for card in cards_all if card.get("status") == "active"]
    hierarchy = json.loads((ROOT / f"public/data/releases/{HIERARCHY_RELEASE}/hierarchy.json").read_text())
    semantic_l3 = [
        node for node in hierarchy["nodes"]
        if node.get("level") == 3 and "HLD" not in node["node_id"]
    ]
    if len(semantic_l3) != 50:
        raise ValueError(f"Expected 50 semantic L3 nodes, got {len(semantic_l3)}")
    return cards, semantic_l3


def card_text(card: dict) -> str:
    return (
        f"{card.get('label_en', '')}. {card.get('definition_en', '')} / "
        f"{card.get('label_ko', '')}. {card.get('definition_ko', '')}"
    )


def seed_text(node: dict) -> str:
    return (
        f"{node.get('label_en', '')}. {node.get('definition_en', '')} / "
        f"{node.get('label_ko', '')}. {node.get('definition_ko', '')}"
    )


def current_l3(card: dict) -> str:
    primary = card.get("primary_l3_id") or ""
    if "HLD" in primary and card.get("hold_semantic_path"):
        return card["hold_semantic_path"]["l3_id"]
    return primary


def encode(texts: list[str], path: Path) -> np.ndarray:
    if path.exists():
        return np.load(path)
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL)
    try:
        model.max_seq_length = 256
    except Exception:
        pass
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=24,
        show_progress_bar=False,
    ).astype("float32")
    np.save(path, vectors)
    return vectors


def centroids(embeddings: np.ndarray, assignment: np.ndarray, seeds: np.ndarray) -> np.ndarray:
    family_count = seeds.shape[0]
    output = np.zeros((family_count, embeddings.shape[1]), dtype="float32")
    for family in range(family_count):
        members = embeddings[assignment == family]
        output[family] = members.mean(axis=0) if len(members) else seeds[family]
    return normalize(output)


def reliability(
    embeddings: np.ndarray,
    seeds: np.ndarray,
    assignment: np.ndarray,
    label: str,
) -> dict:
    family_count = seeds.shape[0]
    centers = centroids(embeddings, assignment, seeds)
    sims = embeddings @ centers.T
    order = np.argsort(-sims, axis=1)
    pos = (order == assignment[:, None]).argmax(axis=1)
    top1 = sims.argmax(axis=1)
    sorted_sims = np.sort(sims, axis=1)
    margins = sims[np.arange(len(assignment)), assignment] - np.where(
        top1 == assignment, sorted_sims[:, -2], sorted_sims[:, -1]
    )
    result = {
        "condition": label,
        "cards": int(len(assignment)),
        "families": int(family_count),
        "top1_containment": round(float((pos < 1).mean()) * 100, 1),
        "top2_containment": round(float((pos < 2).mean()) * 100, 1),
        "top3_containment": round(float((pos < 3).mean()) * 100, 1),
        "top5_containment": round(float((pos < 5).mean()) * 100, 1),
        "median_margin": round(float(np.median(margins)), 4),
        "negative_margin_share": round(float((margins < 0).mean()) * 100, 1),
    }

    def cohesion(assign: np.ndarray) -> float:
        total = 0.0
        count = 0
        for family in range(family_count):
            members = embeddings[assign == family]
            if len(members) >= 2:
                center = members.mean(axis=0)
                center = center / np.linalg.norm(center)
                total += float((members @ center).sum())
                count += len(members)
        return total / count if count else 0.0

    observed = cohesion(assignment)
    rng = np.random.default_rng(SEED)
    null = np.array([cohesion(rng.permutation(assignment)) for _ in range(5000)])
    result["mean_within_family_cosine"] = round(float(observed), 4)
    result["null_mean"] = round(float(null.mean()), 4)
    result["permutation_p"] = round(float((1 + (null >= observed).sum()) / (len(null) + 1)), 4)

    z = (embeddings @ seeds.T).argmax(axis=1)
    objective = 0.0
    for iteration in range(60):
        em_centers = centroids(embeddings, z, seeds)
        z_next = (embeddings @ em_centers.T).argmax(axis=1)
        objective = float((embeddings @ em_centers.T).max(axis=1).mean())
        if np.array_equal(z, z_next):
            z = z_next
            break
        z = z_next
    result["em_iterations"] = int(iteration + 1)
    result["em_final_objective"] = round(objective, 3)
    result["em_agreement"] = round(float((z == assignment).mean()) * 100, 1)
    result["ari"] = round(float(adjusted_rand_score(assignment, z)), 3)
    result["nmi"] = round(float(normalized_mutual_info_score(assignment, z)), 3)

    rng = np.random.default_rng(SEED)
    for sigma in (0.01, 0.05):
        agreements = []
        for _ in range(200):
            perturbed = embeddings + rng.normal(0, sigma, embeddings.shape).astype("float32")
            perturbed = normalize(perturbed)
            agreements.append(float(((perturbed @ centers.T).argmax(axis=1) == top1).mean()))
        result[f"perturb_agreement_sigma_{sigma}"] = round(float(np.mean(agreements)) * 100, 1)
    return result


def constrained_em_audit(
    cards: list[dict],
    semantic_l3: list[dict],
    family_ids: list[str],
    embeddings: np.ndarray,
    seeds: np.ndarray,
    current: np.ndarray,
) -> tuple[np.ndarray, list[dict]]:
    family_idx = {family_id: i for i, family_id in enumerate(family_ids)}
    physical_families = {family_id for family_id in family_ids if family_id.startswith("RAI3-P")}
    agentic_families = {family_id for family_id in family_ids if family_id.startswith("RAI3-A")}
    is_physical_card = np.array([(card.get("primary_l3_id") or "").startswith("RAI3-P") for card in cards])
    en_texts = [f"{card.get('label_en', '')}. {card.get('definition_en', '')}" for card in cards]
    en_seeds = [f"{node.get('label_en', '')}. {node.get('definition_en', '')}" for node in semantic_l3]
    vectorizer = TfidfVectorizer(lowercase=True, stop_words="english", max_features=20000)
    tfidf = vectorizer.fit_transform(en_texts + en_seeds)
    keyword = (normalize(tfidf[: len(cards)]) @ normalize(tfidf[len(cards):]).T).toarray()
    definition = embeddings @ seeds.T
    agentic_terms = re.compile(
        r"\b(agent|agentic|autonomous|tool[- ]?call|tool use|execution|planning|memory|multi-agent|orchestrat|self-improv|replicat|oversight)\b",
        re.I,
    )
    agentic_ok = np.array([bool(agentic_terms.search(text)) for text in en_texts])
    assignment = current.copy()
    moves: list[dict] = []
    for iteration in range(10):
        centers = centroids(embeddings, assignment, seeds)
        score = 0.60 * (embeddings @ centers.T) + 0.30 * definition + 0.10 * keyword
        changed = 0
        for i, card in enumerate(cards):
            if is_physical_card[i]:
                continue
            source_score = score[i, assignment[i]]
            for candidate in np.argsort(-score[i]):
                candidate_id = family_ids[candidate]
                if candidate_id in physical_families:
                    continue
                if candidate_id in agentic_families and not agentic_ok[i]:
                    continue
                if candidate == assignment[i]:
                    break
                if (
                    score[i, candidate] - source_score >= 0.020
                    and keyword[i, candidate] >= 0.015
                    and definition[i, candidate] >= definition[i, assignment[i]]
                ):
                    moves.append(
                        {
                            "l4_id": card["l4_id"],
                            "label_en": card.get("label_en", ""),
                            "iter": iteration,
                            "from": family_ids[assignment[i]],
                            "to": candidate_id,
                            "score_from": round(float(source_score), 6),
                            "score_to": round(float(score[i, candidate]), 6),
                            "improvement": round(float(score[i, candidate] - source_score), 6),
                            "keyword_cos": round(float(keyword[i, candidate]), 6),
                            "definition_cos_to": round(float(definition[i, candidate]), 6),
                            "definition_cos_from": round(float(definition[i, assignment[i]]), 6),
                        }
                    )
                    assignment[i] = candidate
                    changed += 1
                break
        print(f"iter {iteration} moves {changed}", flush=True)
        if changed == 0:
            break
    return assignment, moves


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cards, semantic_l3 = load_inputs()
    family_ids = [node["node_id"] for node in semantic_l3]
    family_idx = {family_id: i for i, family_id in enumerate(family_ids)}
    current = np.array([family_idx[current_l3(card)] for card in cards], dtype=int)
    is_hold = np.array([bool(card.get("decision_required")) for card in cards])
    card_embeddings = encode([card_text(card) for card in cards], OUT / "card_embeddings.npy")
    seed_embeddings = encode([seed_text(node) for node in semantic_l3], OUT / "l3_seed_embeddings.npy")
    audited, moves = constrained_em_audit(cards, semantic_l3, family_ids, card_embeddings, seed_embeddings, current)
    np.save(OUT / "final_assignment.npy", audited)
    (OUT / "reassignment_proposals.json").write_text(json.dumps(moves, ensure_ascii=False, indent=2))
    (OUT / "index.json").write_text(
        json.dumps({"fam_ids": family_ids, "l4_ids": [card["l4_id"] for card in cards]}, indent=2)
    )
    all_mask = np.ones(len(cards), dtype=bool)
    non_hold_mask = ~is_hold
    results = {
        "model": MODEL,
        "seed": SEED,
        "release": SOURCE_RELEASE,
        "hierarchy_release": HIERARCHY_RELEASE,
        "active_cards": len(cards),
        "hold_active_cards": int(is_hold.sum()),
        "guarded_move_events": len(moves),
        "guarded_unique_move_cards": len({move["l4_id"] for move in moves}),
        "baseline_pre_audit": {
            "all": reliability(card_embeddings[all_mask], seed_embeddings, current[all_mask], "all_pre"),
            "non_hold": reliability(card_embeddings[non_hold_mask], seed_embeddings, current[non_hold_mask], "nonhold_pre"),
        },
        "post_audit": {
            "all": reliability(card_embeddings[all_mask], seed_embeddings, audited[all_mask], "all_post"),
            "non_hold": reliability(card_embeddings[non_hold_mask], seed_embeddings, audited[non_hold_mask], "nonhold_post"),
        },
    }
    (OUT / "reliability_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
