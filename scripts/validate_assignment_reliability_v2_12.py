#!/usr/bin/env python3
"""Re-run Technical Report assignment reliability checks for v2.12.0."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "public/data/releases/v2.12.0"
BASELINE = ROOT / "public/data/releases/v2.8.0"
CACHE = ROOT / "reports/validation/v2.8.0/reliability"
OUT = ROOT / "reports/validation/v2.12.0/reliability"
SEED = 20260721
PERMUTATIONS = 5_000
PERTURBATIONS = 200
SIGMAS = [0.0, 0.01, 0.025, 0.05, 0.075, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def text_fingerprint(values: list[str]) -> str:
    return hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest()


def card_text(cards: list[dict]) -> list[str]:
    return [
        " | ".join(filter(None, [
            card.get("label_en"), card.get("label_ko"),
            card.get("definition_en"), card.get("definition_ko"),
        ]))
        for card in cards
    ]


def node_text(nodes: list[dict]) -> list[str]:
    return [
        " | ".join(filter(None, [
            node.get("label_en"), node.get("label_ko"),
            node.get("definition_en"), node.get("definition_ko"),
        ]))
        for node in nodes
    ]


def unit(values: np.ndarray) -> np.ndarray:
    return values / np.maximum(np.linalg.norm(values, axis=1, keepdims=True), 1e-12)


def centroids(
    values: np.ndarray,
    labels: np.ndarray,
    k: int,
    fallback: np.ndarray | None = None,
) -> tuple[np.ndarray, list[int]]:
    result = np.empty((k, values.shape[1]), dtype=np.float32)
    empty = []
    for cluster in range(k):
        members = values[labels == cluster]
        if len(members):
            result[cluster] = members.mean(axis=0)
        elif fallback is not None:
            result[cluster] = fallback[cluster]
            empty.append(cluster)
        else:
            raise ValueError(f"Empty family {cluster}")
    return unit(result), empty


def em_assignment(
    values: np.ndarray,
    seed_centroids: np.ndarray,
    l3_ids: list[str],
    max_iterations: int = 100,
) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    mu = unit(seed_centroids.copy())
    previous = None
    trace = []
    for iteration in range(1, max_iterations + 1):
        scores = values @ mu.T
        labels = scores.argmax(axis=1).astype(np.int32)
        changes = len(values) if previous is None else int(np.sum(labels != previous))
        trace.append({
            "iteration": iteration,
            "objective": float(scores[np.arange(len(values)), labels].mean()),
            "reassigned": changes,
        })
        if previous is not None and changes == 0:
            return labels, mu, trace
        previous = labels.copy()
        mu, empty = centroids(values, labels, len(mu), fallback=seed_centroids)
        trace[-1]["empty_families"] = [l3_ids[index] for index in empty]
    raise RuntimeError("EM did not converge")


def geometry(
    values: np.ndarray,
    labels: np.ndarray,
    mu: np.ndarray,
) -> tuple[dict, np.ndarray, np.ndarray, np.ndarray]:
    scores = values @ mu.T
    order = np.argsort(-scores, axis=1)
    ranks = np.array([
        int(np.where(order[row] == labels[row])[0][0]) + 1
        for row in range(len(values))
    ])
    assigned = scores[np.arange(len(values)), labels]
    alternatives = np.max(
        np.where(np.eye(len(mu), dtype=bool)[labels], -np.inf, scores), axis=1
    )
    margins = assigned - alternatives
    result = {
        "mean_within_family_cohesion": float(assigned.mean()),
        "median_assignment_margin": float(np.median(margins)),
        "negative_margin_share": float(np.mean(margins < 0)),
        "top_k_containment": {f"top_{k}": float(np.mean(ranks <= k)) for k in (1, 2, 3, 5, 10)},
    }
    return result, scores, ranks, margins


def permutation_test(
    values: np.ndarray,
    labels: np.ndarray,
    observed: float,
    seed: int,
) -> dict:
    rng = np.random.default_rng(seed)
    sizes = np.bincount(labels)
    sizes = sizes[sizes > 0]
    boundaries = np.cumsum(sizes)[:-1]
    null = np.empty(PERMUTATIONS, dtype=np.float32)
    for iteration in range(PERMUTATIONS):
        shuffled = values[rng.permutation(len(values))]
        sums = np.add.reduceat(shuffled, np.r_[0, boundaries], axis=0)
        null[iteration] = np.linalg.norm(sums, axis=1).sum() / len(values)
    exceedances = int(np.sum(null >= observed))
    return {
        "permutations": PERMUTATIONS,
        "observed_cohesion": observed,
        "null_mean": float(null.mean()),
        "null_sd": float(null.std(ddof=1)),
        "null_p95": float(np.quantile(null, 0.95)),
        "exceedances": exceedances,
        "p_value_plus_one": float((exceedances + 1) / (PERMUTATIONS + 1)),
    }


def perturbation_test(
    values: np.ndarray,
    mu: np.ndarray,
    seed: int,
) -> list[dict]:
    rng = np.random.default_rng(seed)
    base_scores = values @ mu.T
    baseline = base_scores.argmax(axis=1)
    covariance = mu @ mu.T
    covariance = (covariance + covariance.T) / 2
    covariance += np.eye(len(mu), dtype=np.float32) * 1e-7
    chol = np.linalg.cholesky(covariance).astype(np.float32)
    results = []
    for sigma in SIGMAS:
        agreements = np.empty(PERTURBATIONS, dtype=np.float32)
        if sigma == 0:
            agreements.fill(1.0)
        else:
            for repeat in range(PERTURBATIONS):
                z = rng.standard_normal((len(values), len(mu)), dtype=np.float32)
                noisy_scores = base_scores + sigma * (z @ chol.T)
                agreements[repeat] = np.mean(noisy_scores.argmax(axis=1) == baseline)
        results.append({
            "sigma": sigma,
            "mean_agreement": float(agreements.mean()),
            "ci95_low": float(np.quantile(agreements, 0.025)),
            "ci95_high": float(np.quantile(agreements, 0.975)),
        })
    return results


def subset_metrics(
    mask: np.ndarray,
    assigned: np.ndarray,
    ranks: np.ndarray,
    margins: np.ndarray,
) -> dict:
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
    baseline_l3 = sorted((node for node in baseline_hierarchy if node["level"] == 3), key=lambda node: node["node_id"])
    l3_ids = [node["node_id"] for node in l3_nodes]
    index = {node_id: idx for idx, node_id in enumerate(l3_ids)}

    current_card_text = card_text(cards)
    baseline_card_text = card_text(baseline_cards)
    current_node_text = node_text(l3_nodes)
    baseline_node_text = node_text(baseline_l3)
    fingerprints = {
        "current_cards": text_fingerprint(current_card_text),
        "cache_source_cards": text_fingerprint(baseline_card_text),
        "current_l3": text_fingerprint(current_node_text),
        "cache_source_l3": text_fingerprint(baseline_node_text),
    }
    if fingerprints["current_cards"] != fingerprints["cache_source_cards"]:
        raise ValueError("Card text changed; regenerate BGE-M3 embeddings")
    if fingerprints["current_l3"] != fingerprints["cache_source_l3"]:
        raise ValueError("L3 text changed; regenerate BGE-M3 seed embeddings")

    x = np.load(CACHE / "card_embeddings_bge_m3.npy").astype(np.float32)
    seed_mu = np.load(CACHE / "l3_seed_embeddings_bge_m3.npy").astype(np.float32)
    if len(x) != len(cards) or len(seed_mu) != len(l3_nodes):
        raise ValueError("Embedding cache shape does not match v2.12.0")
    if len(cards) != len({card["l4_id"] for card in cards}) or len(cards) != 1711:
        raise ValueError("Expected 1,711 unique L4 cards")

    labels = np.array([index[card["primary_l3_id"]] for card in cards], dtype=np.int32)
    published_mu, empty = centroids(x, labels, len(l3_ids), fallback=seed_mu)
    if empty:
        raise ValueError(f"Published empty families: {empty}")
    published, scores, ranks, margins = geometry(x, labels, published_mu)
    assigned = scores[np.arange(len(x)), labels]

    em_labels, em_mu, em_trace = em_assignment(x, seed_mu, l3_ids)
    objectives = [row["objective"] for row in em_trace]
    em_agreement = {
        "exact_assignment_agreement": float(np.mean(em_labels == labels)),
        "adjusted_rand_index": float(adjusted_rand_score(labels, em_labels)),
        "normalized_mutual_information": float(normalized_mutual_info_score(labels, em_labels)),
        "candidate_changes": int(np.sum(em_labels != labels)),
    }

    baseline_labels = np.array([index[card["primary_l3_id"]] for card in baseline_cards], dtype=np.int32)
    baseline_mu, baseline_empty = centroids(x, baseline_labels, len(l3_ids), fallback=seed_mu)
    if baseline_empty:
        raise ValueError(f"Baseline empty families: {baseline_empty}")
    baseline_geometry, _, _, _ = geometry(x, baseline_labels, baseline_mu)

    physical_mask = np.array([card["primary_l3_id"].startswith("RAI3-P-") for card in cards])
    hold_mask = np.array([bool(card.get("decision_required")) for card in cards])
    baseline_by_id = {card["l4_id"]: card for card in baseline_cards}
    changed_mask = np.array([
        card["primary_l3_id"] != baseline_by_id[card["l4_id"]]["primary_l3_id"]
        for card in cards
    ])
    subsets = {
        "physical_locked": subset_metrics(physical_mask, assigned, ranks, margins),
        "nonphysical": subset_metrics(~physical_mask, assigned, ranks, margins),
        "hold": subset_metrics(hold_mask, assigned, ranks, margins),
        "non_hold": subset_metrics(~hold_mask, assigned, ranks, margins),
        "v2_9_to_v2_12_changed": subset_metrics(changed_mask, assigned, ranks, margins),
    }

    per_l3 = []
    for cluster, node in enumerate(l3_nodes):
        mask = labels == cluster
        per_l3.append({
            "node_id": node["node_id"], "label_en": node["label_en"],
            "n": int(mask.sum()),
            "mean_assigned_similarity": float(assigned[mask].mean()),
            "median_assignment_margin": float(np.median(margins[mask])),
            "negative_margin_share": float(np.mean(margins[mask] < 0)),
            "top_1": float(np.mean(ranks[mask] <= 1)),
            "top_3": float(np.mean(ranks[mask] <= 3)),
        })

    permutation = permutation_test(x, labels, published["mean_within_family_cohesion"], SEED)
    perturbation = perturbation_test(x, published_mu, SEED + 1)
    baseline_perturbation = perturbation_test(x, baseline_mu, SEED + 2)
    monotonic = all(b + 1e-7 >= a for a, b in zip(objectives, objectives[1:]))

    summary = {
        "release_id": "v2.12.0",
        "as_of": "2026-07-21",
        "encoder": "BAAI/bge-m3 dense",
        "embedding_dimension": int(x.shape[1]),
        "seed": SEED,
        "population": {
            "cards": len(cards), "unique_l4_ids": len({card["l4_id"] for card in cards}),
            "l3_families": len(l3_ids), "physical_locked": int(physical_mask.sum()),
            "decision_required": int(hold_mask.sum()), "changed_since_v2_8": int(changed_mask.sum()),
        },
        "embedding_cache_validation": fingerprints,
        "em": {
            "iterations_to_fixed_point": len(em_trace), "trace": em_trace,
            "objective_monotonic_non_decreasing": monotonic, **em_agreement,
        },
        "published_assignment_geometry": published,
        "label_permutation_test": permutation,
        "embedding_perturbation": perturbation,
        "v2_8_comparator": {
            "published_assignment_geometry": baseline_geometry,
            "embedding_perturbation": baseline_perturbation,
        },
        "subsets": subsets,
        "per_l3": per_l3,
        "interpretation_rule": {
            "strong": "top-1 >= 0.90, top-2 >= 0.95, permutation p < 0.001, and >=97% perturbation agreement through sigma=0.05",
            "caution": "Failure of a geometric threshold indicates review need; it does not by itself prove semantic misclassification.",
        },
    }
    write(OUT / "reliability_summary.json", summary)
    write(OUT / "per_l3_metrics.json", per_l3)
    write(OUT / "em_trace.json", em_trace)

    plt.rcParams.update({
        "font.family": "sans-serif", "font.size": 8, "axes.linewidth": 0.7,
        "axes.spines.top": False, "axes.spines.right": False,
    })
    blue, orange, grey = "#0072B2", "#D55E00", "#6B6B6B"
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.15), constrained_layout=True)
    iterations = [row["iteration"] for row in em_trace]
    axes[0].plot(iterations, objectives, color=blue, marker="o", markersize=2.5)
    ax_changes = axes[0].twinx()
    ax_changes.bar(iterations, [row["reassigned"] for row in em_trace], color="#D9D9D9", alpha=0.55)
    axes[0].set(xlabel="EM iteration", ylabel="Mean cosine objective", title="a  EM convergence")
    ax_changes.set_ylabel("Cards reassigned", color=grey)

    ks = [1, 2, 3, 5]
    current_topk = [100 * published["top_k_containment"][f"top_{k}"] for k in ks]
    baseline_topk = [100 * baseline_geometry["top_k_containment"][f"top_{k}"] for k in ks]
    positions = np.arange(len(ks))
    axes[1].bar(positions - 0.18, baseline_topk, width=0.36, color="#D9D9D9", edgecolor=grey, label="v2.8.0")
    axes[1].bar(positions + 0.18, current_topk, width=0.36, color=blue, edgecolor=blue, label="v2.12.0")
    axes[1].set(xticks=positions, xticklabels=[str(k) for k in ks], xlabel="Top-k", ylabel="Containment (%)", ylim=(0, 100), title="b  Released assignment geometry")
    axes[1].legend(frameon=False, fontsize=7, loc="lower right")

    sigma = [row["sigma"] for row in perturbation]
    current_agreement = np.array([row["mean_agreement"] for row in perturbation]) * 100
    current_low = np.array([row["ci95_low"] for row in perturbation]) * 100
    current_high = np.array([row["ci95_high"] for row in perturbation]) * 100
    baseline_agreement = np.array([row["mean_agreement"] for row in baseline_perturbation]) * 100
    axes[2].plot(sigma, baseline_agreement, color=grey, linestyle="--", label="v2.8.0")
    axes[2].plot(sigma, current_agreement, color=orange, label="v2.12.0")
    axes[2].fill_between(sigma, current_low, current_high, color=orange, alpha=0.18)
    axes[2].axhline(97, color=grey, linestyle=":", linewidth=0.8)
    axes[2].set(xlabel="Gaussian perturbation sigma", ylabel="Agreement (%)", ylim=(0, 101), title="c  Perturbation stability")
    axes[2].legend(frameon=False, fontsize=7)
    fig.savefig(OUT / "reliability_validation.png", dpi=300, facecolor="white")
    fig.savefig(OUT / "reliability_validation.pdf", facecolor="white")
    plt.close(fig)

    print(json.dumps({
        "em": summary["em"],
        "published_assignment_geometry": published,
        "label_permutation_test": permutation,
        "subsets": subsets,
        "sigma_0_05": next(row for row in perturbation if row["sigma"] == 0.05),
    }, indent=2))


if __name__ == "__main__":
    main()
