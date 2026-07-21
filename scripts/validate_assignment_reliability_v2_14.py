#!/usr/bin/env python3
"""Re-run Algorithm 2 reliability checks after the v2.14.0 L3 retirement."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

import validate_assignment_reliability_v2_8 as reliability


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "public/data/releases/v2.14.0"
BASELINE = ROOT / "public/data/releases/v2.12.0"
OUT = ROOT / "reports/validation/v2.14.0/reliability"
MIGRATIONS = ROOT / "reports/data_quality/agentic_l3_retirement_v2.14.0/l4_migrations.json"
SEED = 20260721
reliability.SEED = SEED


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def text_for_cards(cards: list[dict]) -> list[str]:
    return [
        " | ".join(filter(None, [
            card.get("label_en"), card.get("label_ko"),
            card.get("definition_en"), card.get("definition_ko"),
        ]))
        for card in cards
    ]


def text_for_nodes(nodes: list[dict]) -> list[str]:
    return [
        " | ".join(filter(None, [
            node.get("label_en"), node.get("label_ko"),
            node.get("definition_en"), node.get("definition_ko"),
        ]))
        for node in nodes
    ]


def geometry(x: np.ndarray, labels: np.ndarray, mu: np.ndarray) -> tuple:
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
    return scores, ranks, assigned, margins


def subset(mask: np.ndarray, ranks: np.ndarray, assigned: np.ndarray, margins: np.ndarray) -> dict:
    return {
        "n": int(mask.sum()),
        "mean_assigned_similarity": float(assigned[mask].mean()),
        "median_assignment_margin": float(np.median(margins[mask])),
        "negative_margin_share": float(np.mean(margins[mask] < 0)),
        "top_1": float(np.mean(ranks[mask] <= 1)),
        "top_2": float(np.mean(ranks[mask] <= 2)),
        "top_3": float(np.mean(ranks[mask] <= 3)),
        "top_5": float(np.mean(ranks[mask] <= 5)),
    }


def main() -> None:
    np.random.seed(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    cards = load(RELEASE / "cards.json")["cards"]
    hierarchy = load(RELEASE / "hierarchy.json")["nodes"]
    baseline_cards = load(BASELINE / "cards.json")["cards"]
    baseline_hierarchy = load(BASELINE / "hierarchy.json")["nodes"]
    l3_nodes = sorted((node for node in hierarchy if node["level"] == 3), key=lambda node: node["node_id"])
    l3_ids = [node["node_id"] for node in l3_nodes]
    l3_index = {node_id: index for index, node_id in enumerate(l3_ids)}
    labels = np.array([l3_index[card["primary_l3_id"]] for card in cards], dtype=np.int32)

    x = reliability.encode(text_for_cards(cards), OUT / "card_embeddings_bge_m3.npy")
    seed_mu = reliability.encode(text_for_nodes(l3_nodes), OUT / "l3_seed_embeddings_bge_m3.npy")
    published_mu = reliability.centroids(x, labels, len(l3_ids))
    scores, ranks, assigned, margins = geometry(x, labels, published_mu)
    cohesion = float(assigned.mean())
    sizes = np.bincount(labels, minlength=len(l3_ids))
    permutation = reliability.permutation_test(x, sizes, cohesion)
    perturbation = reliability.perturbation_test(x, published_mu)
    em_labels, em_trace = reliability.em_assignment(x, seed_mu)
    objectives = [row["objective"] for row in em_trace]

    migration_ids = {row["l4_id"] for row in load(MIGRATIONS)}
    migrated_mask = np.array([card["l4_id"] in migration_ids for card in cards])
    physical_mask = np.array([card.get("assignment_status") == "locked_physical" for card in cards])
    hold_mask = np.array([bool(card.get("decision_required")) for card in cards])
    domain = np.array([card["primary_l3_id"].split("-")[1] for card in cards])

    per_l3 = []
    for index, node in enumerate(l3_nodes):
        mask = labels == index
        row = subset(mask, ranks, assigned, margins)
        row.update({"node_id": node["node_id"], "label_en": node["label_en"]})
        per_l3.append(row)

    baseline = reliability.comparator_metrics(x, baseline_cards, baseline_hierarchy)
    summary = {
        "release_id": "v2.14.0",
        "baseline_release": "v2.12.0",
        "encoder": "BAAI/bge-m3 dense",
        "model_revision": reliability.MODEL.name,
        "seed": SEED,
        "population": {
            "cards": len(cards),
            "active_l3": len(l3_ids),
            "retired_l3": 4,
            "migrated_cards": int(migrated_mask.sum()),
            "physical_locked": int(physical_mask.sum()),
            "decision_required": int(hold_mask.sum()),
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
        "baseline_v2_12": baseline,
        "subsets": {
            "migrated_39": subset(migrated_mask, ranks, assigned, margins),
            "not_migrated": subset(~migrated_mask, ranks, assigned, margins),
            "physical_locked": subset(physical_mask, ranks, assigned, margins),
            "hold": subset(hold_mask, ranks, assigned, margins),
            "non_hold": subset(~hold_mask, ranks, assigned, margins),
            "general": subset(domain == "G", ranks, assigned, margins),
            "agentic": subset(domain == "A", ranks, assigned, margins),
        },
        "per_l3": per_l3,
        "interpretation": (
            "The v2.14.0 forced migration is an operational consolidation. All 39 migrated paths remain HOLD; "
            "geometric results prioritize review and do not constitute human approval."
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
    baseline_top = [baseline["top_k_containment"][f"top_{k}"] * 100 for k in topks]
    current_top = [summary["published_assignment_geometry"]["top_k_containment"][f"top_{k}"] * 100 for k in topks]
    pos = np.arange(len(topks))
    axes[0].bar(pos - 0.18, baseline_top, 0.36, color=grey, label="v2.12.0")
    axes[0].bar(pos + 0.18, current_top, 0.36, color=blue, label="v2.14.0")
    axes[0].set(xticks=pos, xticklabels=topks, ylim=(0, 100), xlabel="Top-k", ylabel="Containment (%)", title="a  Released geometry")
    axes[0].legend(frameon=False, fontsize=7)

    sigma = [row["sigma"] for row in perturbation]
    current_stability = [row["mean_agreement"] * 100 for row in perturbation]
    baseline_stability = [row["mean_agreement"] * 100 for row in baseline["embedding_perturbation"]]
    axes[1].plot(sigma, baseline_stability, color=grey, linestyle="--", label="v2.12.0")
    axes[1].plot(sigma, current_stability, color=orange, label="v2.14.0")
    axes[1].set(ylim=(0, 101), xlabel="Gaussian perturbation sigma", ylabel="Agreement (%)", title="b  Perturbation stability")
    axes[1].legend(frameon=False, fontsize=7)

    destinations = Counter(row["to_l3_label"] for row in load(MIGRATIONS))
    names, values = zip(*sorted(destinations.items(), key=lambda item: item[1]))
    axes[2].barh(names, values, color=blue)
    axes[2].set(xlabel="Migrated L4 cards", title="c  Forced destinations")
    for y, value in enumerate(values):
        axes[2].text(value + 0.2, y, str(value), va="center", fontsize=7)
    axes[2].set_xlim(0, max(values) * 1.18)
    fig.tight_layout(w_pad=2.0)
    fig.savefig(OUT / "reliability_validation.pdf", bbox_inches="tight")
    fig.savefig(OUT / "reliability_validation.png", dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
