#!/usr/bin/env python3
"""Run v2.17.2 full active-card sensitivity using cached BGE-M3 embeddings.

The test includes Physical AI cards. It evaluates two conditions:
1. HOLD included: all 1,660 active cards, with HOLD cards evaluated against
   their stored semantic review L3 when available.
2. HOLD excluded: active non-HOLD cards only.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.preprocessing import normalize


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/data/releases/v2.17.2"
BGE = ROOT / "reports/validation/v2.17.2/bge_m3_active"
OUT = ROOT / "reports/validation/v2.17.2/full_sensitivity_bge_m3"
SEED = 20260723


def load() -> tuple[list[dict], list[dict], np.ndarray, np.ndarray, list[str]]:
    cards_all = json.loads((SOURCE / "cards.json").read_text())["cards"]
    cards = [card for card in cards_all if card.get("status") == "active"]
    hierarchy = json.loads((SOURCE / "hierarchy.json").read_text())["nodes"]
    l3_nodes = [node for node in hierarchy if node.get("level") == 3 and "HLD" not in node["node_id"]]
    l3_ids = [node["node_id"] for node in l3_nodes]
    index = json.loads((BGE / "index.json").read_text())
    emb_all = np.load(BGE / "card_embeddings.npy")
    seed_embeddings = np.load(BGE / "l3_seed_embeddings.npy")
    position = {l4_id: i for i, l4_id in enumerate(index["l4_ids"])}
    missing = [card["l4_id"] for card in cards if card["l4_id"] not in position]
    if missing:
        raise ValueError(f"Missing BGE embeddings for {len(missing)} active cards")
    card_embeddings = emb_all[[position[card["l4_id"]] for card in cards]]
    if len(cards) != 1660:
        raise ValueError(f"Expected 1,660 active cards, got {len(cards)}")
    if len(l3_ids) != 50:
        raise ValueError(f"Expected 50 semantic L3 nodes, got {len(l3_ids)}")
    return cards, l3_nodes, card_embeddings, seed_embeddings, l3_ids


def semantic_l3(card: dict) -> str:
    primary = card.get("primary_l3_id") or ""
    if "HLD" in primary and card.get("hold_semantic_path"):
        return card["hold_semantic_path"]["l3_id"]
    if "HLD" in primary and card.get("previous_primary_l3_id"):
        return card["previous_primary_l3_id"]
    return primary


def centroids(embeddings: np.ndarray, assignment: np.ndarray, seeds: np.ndarray) -> np.ndarray:
    family_count = seeds.shape[0]
    output = np.zeros((family_count, embeddings.shape[1]), dtype="float32")
    for family in range(family_count):
        members = embeddings[assignment == family]
        output[family] = members.mean(axis=0) if len(members) else seeds[family]
    return normalize(output)


def reliability(embeddings: np.ndarray, seeds: np.ndarray, assignment: np.ndarray, condition: str) -> dict:
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

    rng = np.random.default_rng(SEED)
    perturb = {}
    for sigma in (0.01, 0.05):
        agreements = []
        for _ in range(200):
            perturbed = embeddings + rng.normal(0, sigma, embeddings.shape).astype("float32")
            perturbed = normalize(perturbed)
            agreements.append(float(((perturbed @ centers.T).argmax(axis=1) == top1).mean()))
        perturb[f"sigma_{sigma}"] = round(float(np.mean(agreements)) * 100, 1)

    return {
        "condition": condition,
        "cards": int(len(assignment)),
        "families": int(family_count),
        "top1_containment": round(float((pos < 1).mean()) * 100, 1),
        "top2_containment": round(float((pos < 2).mean()) * 100, 1),
        "top3_containment": round(float((pos < 3).mean()) * 100, 1),
        "top5_containment": round(float((pos < 5).mean()) * 100, 1),
        "median_margin": round(float(np.median(margins)), 4),
        "negative_margin_share": round(float((margins < 0).mean()) * 100, 1),
        "mean_within_family_cosine": round(float(observed), 4),
        "null_mean": round(float(null.mean()), 4),
        "permutation_p": round(float((1 + (null >= observed).sum()) / (len(null) + 1)), 4),
        "em_iterations": int(iteration + 1),
        "em_final_objective": round(objective, 3),
        "em_agreement": round(float((z == assignment).mean()) * 100, 1),
        "ari": round(float(adjusted_rand_score(assignment, z)), 3),
        "nmi": round(float(normalized_mutual_info_score(assignment, z)), 3),
        "perturb_agreement_sigma_0.01": perturb["sigma_0.01"],
        "perturb_agreement_sigma_0.05": perturb["sigma_0.05"],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cards, l3_nodes, embeddings, seeds, l3_ids = load()
    l3_index = {l3_id: i for i, l3_id in enumerate(l3_ids)}
    assignment = np.array([l3_index[semantic_l3(card)] for card in cards], dtype=int)
    is_hold = np.array([bool(card.get("decision_required")) for card in cards])
    is_physical = np.array([(semantic_l3(card) or "").startswith("RAI3-P-") for card in cards])
    included = reliability(embeddings, seeds, assignment, "hold_included_physical_included")
    non_hold = ~is_hold
    excluded = reliability(embeddings[non_hold], seeds, assignment[non_hold], "hold_excluded_physical_included")
    results = {
        "release": "v2.17.2",
        "model": "BAAI/bge-m3 cached local embeddings",
        "seed": SEED,
        "scope": "active cards only; Physical AI included; retired merged records excluded from reliability metrics",
        "registered_ids": 1711,
        "active_cards": int(len(cards)),
        "active_physical_cards": int(is_physical.sum()),
        "active_hold_cards": int(is_hold.sum()),
        "active_non_hold_cards": int(non_hold.sum()),
        "hold_included": included,
        "hold_excluded": excluded,
    }
    (OUT / "full_sensitivity_bge_m3_v2172.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    np.save(OUT / "assignment.npy", assignment)
    (OUT / "index.json").write_text(json.dumps({"l4_ids": [card["l4_id"] for card in cards], "l3_ids": l3_ids}, indent=2))
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
