#!/usr/bin/env python3
"""Validate the 991-card non-HOLD semantic partition in release v2.15.0."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

import validate_assignment_reliability_v2_8 as reliability


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "public/data/releases/v2.15.0"
BASELINE_SUMMARY = ROOT / "reports/validation/v2.14.0/reliability/reliability_summary.json"
BASELINE_EMBEDDINGS = ROOT / "reports/validation/v2.14.0/reliability/card_embeddings_bge_m3.npy"
OUT = ROOT / "reports/validation/v2.15.0/non_hold_reliability"
SEED = 20260721
reliability.SEED = SEED


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def node_text(nodes: list[dict]) -> list[str]:
    return [
        " | ".join(filter(None, [
            node.get("label_en"), node.get("label_ko"),
            node.get("definition_en"), node.get("definition_ko"),
        ]))
        for node in nodes
    ]


def geometry(x: np.ndarray, labels: np.ndarray, mu: np.ndarray):
    scores = x @ mu.T
    order = np.argsort(-scores, axis=1)
    ranks = np.array([
        int(np.where(order[row] == labels[row])[0][0]) + 1
        for row in range(len(labels))
    ], dtype=np.int32)
    assigned = scores[np.arange(len(labels)), labels]
    competing = scores.copy()
    competing[np.arange(len(labels)), labels] = -np.inf
    margins = assigned - competing.max(axis=1)
    return ranks, assigned, margins


def main() -> None:
    np.random.seed(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    cards = load(RELEASE / "cards.json")["cards"]
    non_hold_mask = np.array([not card["decision_required"] for card in cards])
    non_hold_cards = [card for card in cards if not card["decision_required"]]
    all_embeddings = np.load(BASELINE_EMBEDDINGS)
    if len(all_embeddings) != len(cards):
        raise ValueError("The v2.14 embedding cache does not align with the v2.15 card registry")
    x = all_embeddings[non_hold_mask]
    np.save(OUT / "non_hold_card_embeddings_bge_m3.npy", x)

    hierarchy = load(RELEASE / "hierarchy.json")["nodes"]
    semantic_l3 = sorted(
        (node for node in hierarchy if node["level"] == 3 and node["status"] == "active"),
        key=lambda node: node["node_id"],
    )
    l3_ids = [node["node_id"] for node in semantic_l3]
    l3_index = {node_id: index for index, node_id in enumerate(l3_ids)}
    labels = np.array([l3_index[card["primary_l3_id"]] for card in non_hold_cards], dtype=np.int32)
    seed_mu = reliability.encode(node_text(semantic_l3), OUT / "semantic_l3_seed_embeddings_bge_m3.npy")
    published_mu = reliability.centroids(x, labels, len(l3_ids))
    ranks, assigned, margins = geometry(x, labels, published_mu)
    cohesion = float(assigned.mean())
    sizes = np.bincount(labels, minlength=len(l3_ids))
    permutation = reliability.permutation_test(x, sizes, cohesion)
    perturbation = reliability.perturbation_test(x, published_mu)
    em_labels, em_trace = reliability.em_assignment(x, seed_mu)
    objectives = [row["objective"] for row in em_trace]

    per_l3 = []
    for index, node in enumerate(semantic_l3):
        mask = labels == index
        per_l3.append({
            "node_id": node["node_id"],
            "label_en": node["label_en"],
            "n": int(mask.sum()),
            "mean_assigned_similarity": float(assigned[mask].mean()),
            "median_assignment_margin": float(np.median(margins[mask])),
            "negative_margin_share": float(np.mean(margins[mask] < 0)),
            "top_1": float(np.mean(ranks[mask] <= 1)),
            "top_3": float(np.mean(ranks[mask] <= 3)),
        })

    baseline = load(BASELINE_SUMMARY)
    summary = {
        "release_id": "v2.15.0",
        "scope": "all and only non-HOLD cards",
        "encoder": "BAAI/bge-m3 dense",
        "model_revision": reliability.MODEL.name,
        "seed": SEED,
        "population": {
            "all_cards": len(cards),
            "excluded_hold_cards": len(cards) - len(non_hold_cards),
            "assessed_non_hold_cards": len(non_hold_cards),
            "semantic_l3_families": len(l3_ids),
            "empty_semantic_l3_families": int(np.sum(sizes == 0)),
        },
        "published_assignment_geometry": {
            "mean_within_family_cohesion": cohesion,
            "median_assignment_margin": float(np.median(margins)),
            "negative_margin_share": float(np.mean(margins < 0)),
            "top_k_containment": {f"top_{k}": float(np.mean(ranks <= k)) for k in (1, 2, 3, 5, 10)},
        },
        "em": {
            "iterations_to_fixed_point": len(em_trace),
            "objective_start": objectives[0],
            "objective_end": objectives[-1],
            "objective_monotonic_non_decreasing": all(b + 1e-7 >= a for a, b in zip(objectives, objectives[1:])),
            "exact_assignment_agreement": float(np.mean(em_labels == labels)),
            "adjusted_rand_index": float(adjusted_rand_score(labels, em_labels)),
            "normalized_mutual_information": float(normalized_mutual_info_score(labels, em_labels)),
            "candidate_changes": int(np.sum(em_labels != labels)),
            "trace": em_trace,
        },
        "label_permutation_test": permutation,
        "embedding_perturbation": perturbation,
        "comparison_all_v2_14": baseline["published_assignment_geometry"],
        "per_l3": per_l3,
        "interpretation": (
            "Removing HOLD cards measures the released semantic partition on the adjudication-ready subset. "
            "It is a diagnostic and not independent accuracy or human approval."
        ),
    }
    write(OUT / "reliability_summary.json", summary)
    write(OUT / "per_l3_metrics.json", per_l3)

    plt.rcParams.update({
        "font.family": "Arial", "font.size": 8, "axes.titlesize": 9,
        "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
        "axes.spines.top": False, "axes.spines.right": False,
    })
    blue, grey, orange = "#0072B2", "#B8B8B8", "#D55E00"
    fig, axes = plt.subplots(1, 3, figsize=(10.6, 3.35))
    topks = [1, 2, 3, 5]
    all_top = [baseline["published_assignment_geometry"]["top_k_containment"][f"top_{k}"] * 100 for k in topks]
    current_top = [summary["published_assignment_geometry"]["top_k_containment"][f"top_{k}"] * 100 for k in topks]
    pos = np.arange(len(topks))
    axes[0].bar(pos - 0.18, all_top, 0.36, color=grey, label="All v2.14")
    axes[0].bar(pos + 0.18, current_top, 0.36, color=blue, label="Non-HOLD v2.15")
    axes[0].set(xticks=pos, xticklabels=topks, ylim=(0, 100), xlabel="Top-k", ylabel="Containment (%)", title="a  Released geometry")
    axes[0].legend(frameon=False, fontsize=7)

    sigma = [row["sigma"] for row in perturbation]
    axes[1].plot(sigma, [row["mean_agreement"] * 100 for row in perturbation], color=orange)
    axes[1].set(ylim=(0, 101), xlabel="Gaussian perturbation sigma", ylabel="Agreement (%)", title="b  Non-HOLD stability")

    weakest = sorted(per_l3, key=lambda row: row["top_1"])[:10]
    names = [row["label_en"] for row in reversed(weakest)]
    values = [row["top_1"] * 100 for row in reversed(weakest)]
    axes[2].barh(names, values, color=blue)
    axes[2].set(xlim=(0, 100), xlabel="Top-1 containment (%)", title="c  Weakest non-HOLD families")
    fig.tight_layout(w_pad=2.0)
    fig.savefig(OUT / "non_hold_reliability.pdf", bbox_inches="tight")
    fig.savefig(OUT / "non_hold_reliability.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
