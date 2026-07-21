#!/usr/bin/env python3
"""Reproduce Technical Report reliability checks for v2.8.0 assignments."""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "public/data/releases/v2.8.0"
OUT = ROOT / "reports/validation/v2.8.0/reliability"
MODEL = Path("/Users/deep1003/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181")
SEED = 20260704
PERMUTATIONS = 5000
PERTURBATIONS = 200
SIGMAS = [0.0, 0.01, 0.025, 0.05, 0.075, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
NEW_L3 = {"RAI3-A-SYS-07", "RAI3-A-SYS-08", "RAI3-A-SYS-09", "RAI3-A-SYS-10"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def unit(x: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.maximum(norms, 1e-12)


def centroids(x: np.ndarray, labels: np.ndarray, k: int, fallback: np.ndarray | None = None) -> np.ndarray:
    result = np.empty((k, x.shape[1]), dtype=np.float32)
    for idx in range(k):
        members = x[labels == idx]
        if len(members):
            result[idx] = members.mean(axis=0)
        elif fallback is not None:
            result[idx] = fallback[idx]
        else:
            raise ValueError(f"empty family {idx}")
    return unit(result)


def encode(texts: list[str], cache: Path) -> np.ndarray:
    if cache.exists():
        return np.load(cache)
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    model = SentenceTransformer(str(MODEL), local_files_only=True)
    model.max_seq_length = 256
    values = model.encode(
        texts, batch_size=32, show_progress_bar=True,
        normalize_embeddings=True, convert_to_numpy=True,
    ).astype(np.float32)
    np.save(cache, values)
    return values


def em_assignment(x: np.ndarray, seed_centroids: np.ndarray, max_iter: int = 100) -> tuple[np.ndarray, list[dict]]:
    mu = seed_centroids.copy()
    prior = None
    trace = []
    for iteration in range(1, max_iter + 1):
        scores = x @ mu.T
        labels = scores.argmax(axis=1)
        objective = float(scores[np.arange(len(x)), labels].mean())
        changes = len(x) if prior is None else int(np.sum(labels != prior))
        trace.append({"iteration": iteration, "objective": objective, "reassigned": changes})
        if prior is not None and changes == 0:
            return labels, trace
        prior = labels.copy()
        mu = centroids(x, labels, len(mu), fallback=seed_centroids)
    raise RuntimeError("EM did not converge")


def permutation_test(x: np.ndarray, family_sizes: np.ndarray, observed: float) -> dict:
    rng = np.random.default_rng(SEED)
    boundaries = np.cumsum(family_sizes)[:-1]
    null = np.empty(PERMUTATIONS, dtype=np.float32)
    for iteration in range(PERMUTATIONS):
        shuffled = x[rng.permutation(len(x))]
        sums = np.add.reduceat(shuffled, np.r_[0, boundaries], axis=0)
        # Mean cosine to each normalized group sum equals sum of group-sum norms / N.
        null[iteration] = np.linalg.norm(sums, axis=1).sum() / len(x)
    exceed = int(np.sum(null >= observed))
    return {
        "permutations": PERMUTATIONS,
        "observed_cohesion": observed,
        "null_mean": float(null.mean()),
        "null_sd": float(null.std(ddof=1)),
        "null_p95": float(np.quantile(null, 0.95)),
        "p_value_plus_one": float((exceed + 1) / (PERMUTATIONS + 1)),
        "exceedances": exceed,
    }


def perturbation_test(x: np.ndarray, mu: np.ndarray) -> list[dict]:
    rng = np.random.default_rng(SEED + 1)
    base_scores = x @ mu.T
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
                z = rng.standard_normal((len(x), len(mu)), dtype=np.float32)
                noisy_scores = base_scores + sigma * (z @ chol.T)
                agreements[repeat] = np.mean(noisy_scores.argmax(axis=1) == baseline)
        results.append({
            "sigma": sigma,
            "mean_agreement": float(agreements.mean()),
            "ci95_low": float(np.quantile(agreements, 0.025)),
            "ci95_high": float(np.quantile(agreements, 0.975)),
        })
    return results


def comparator_metrics(x: np.ndarray, cards: list[dict], hierarchy: list[dict]) -> dict:
    nodes = sorted((n for n in hierarchy if n["level"] == 3), key=lambda n: n["node_id"])
    ids = [n["node_id"] for n in nodes]
    index = {node_id: idx for idx, node_id in enumerate(ids)}
    labels = np.array([index[c["primary_l3_id"]] for c in cards], dtype=np.int32)
    mu = centroids(x, labels, len(ids))
    scores = x @ mu.T
    order = np.argsort(-scores, axis=1)
    ranks = np.array([int(np.where(order[row] == labels[row])[0][0]) + 1 for row in range(len(cards))])
    cohesion = float(scores[np.arange(len(cards)), labels].mean())
    sizes = np.bincount(labels, minlength=len(ids))
    return {
        "l3_families": len(ids),
        "mean_within_family_cohesion": cohesion,
        "top_k_containment": {f"top_{k}": float(np.mean(ranks <= k)) for k in (1, 2, 3, 5, 10)},
        "label_permutation_test": permutation_test(x, sizes, cohesion),
        "embedding_perturbation": perturbation_test(x, mu),
    }


def main() -> None:
    random.seed(SEED)
    np.random.seed(SEED)
    OUT.mkdir(parents=True, exist_ok=True)
    cards = load(RELEASE / "cards.json")["cards"]
    hierarchy = load(RELEASE / "hierarchy.json")["nodes"]
    l3_nodes = sorted((n for n in hierarchy if n["level"] == 3), key=lambda n: n["node_id"])
    ids = [n["node_id"] for n in l3_nodes]
    index = {node_id: idx for idx, node_id in enumerate(ids)}
    labels = np.array([index[c["primary_l3_id"]] for c in cards], dtype=np.int32)
    card_text = [
        " | ".join(filter(None, [c.get("label_en"), c.get("label_ko"), c.get("definition_en"), c.get("definition_ko")]))
        for c in cards
    ]
    node_text = [
        " | ".join(filter(None, [n.get("label_en"), n.get("label_ko"), n.get("definition_en"), n.get("definition_ko")]))
        for n in l3_nodes
    ]
    x = encode(card_text, OUT / "card_embeddings_bge_m3.npy")
    seed_mu = encode(node_text, OUT / "l3_seed_embeddings_bge_m3.npy")
    published_mu = centroids(x, labels, len(ids))

    nearest_scores = x @ published_mu.T
    order = np.argsort(-nearest_scores, axis=1)
    ranks = np.empty(len(cards), dtype=np.int32)
    for row in range(len(cards)):
        ranks[row] = int(np.where(order[row] == labels[row])[0][0]) + 1
    topk = {f"top_{k}": float(np.mean(ranks <= k)) for k in (1, 2, 3, 5, 10)}
    assigned_similarity = nearest_scores[np.arange(len(cards)), labels]
    observed_cohesion = float(assigned_similarity.mean())
    family_sizes = np.bincount(labels, minlength=len(ids))

    em_labels, em_trace = em_assignment(x, seed_mu)
    em_objectives = [row["objective"] for row in em_trace]
    monotonic = all(b + 1e-7 >= a for a, b in zip(em_objectives, em_objectives[1:]))
    em_vs_published = float(np.mean(em_labels == labels))
    permutation = permutation_test(x, family_sizes, observed_cohesion)
    perturbation = perturbation_test(x, published_mu)

    new_mask = np.array([c["primary_l3_id"] in NEW_L3 for c in cards])
    remapped_ids = {r["l4_id"] for r in load(ROOT / "reports/data_quality/agentic_l3_expansion_v2.8.0/remapping_audit.json")}
    remapped_mask = np.array([c["l4_id"] in remapped_ids for c in cards])

    def subset(mask: np.ndarray) -> dict:
        subset_ranks = ranks[mask]
        sims = assigned_similarity[mask]
        margins = nearest_scores[mask, labels[mask]] - np.partition(nearest_scores[mask], -2, axis=1)[:, -2]
        return {
            "n": int(mask.sum()),
            "top_1": float(np.mean(subset_ranks <= 1)),
            "top_2": float(np.mean(subset_ranks <= 2)),
            "top_3": float(np.mean(subset_ranks <= 3)),
            "mean_assigned_similarity": float(sims.mean()),
            "median_assignment_margin": float(np.median(margins)),
        }

    per_l3 = []
    for idx, node in enumerate(l3_nodes):
        mask = labels == idx
        per_l3.append({
            "node_id": node["node_id"], "label_en": node["label_en"], "n": int(mask.sum()),
            "mean_assigned_similarity": float(assigned_similarity[mask].mean()),
            "top_1": float(np.mean(ranks[mask] == 1)),
            "top_3": float(np.mean(ranks[mask] <= 3)),
        })

    v27_cards = load(ROOT / "public/data/releases/v2.7.0/cards.json")["cards"]
    v27_hierarchy = load(ROOT / "public/data/releases/v2.7.0/hierarchy.json")["nodes"]
    v27_comparator = comparator_metrics(x, v27_cards, v27_hierarchy)

    summary = {
        "release_id": "v2.8.0", "seed": SEED, "encoder": "BAAI/bge-m3 dense",
        "embedding_dimension": int(x.shape[1]), "cards": len(cards), "l3_families": len(ids),
        "em": {
            "iterations_to_fixed_point": len(em_trace), "trace": em_trace,
            "objective_monotonic_non_decreasing": monotonic,
            "agreement_with_published_assignment": em_vs_published,
        },
        "published_assignment_geometry": {
            "mean_within_family_cohesion": observed_cohesion, "top_k_containment": topk,
        },
        "label_permutation_test": permutation,
        "embedding_perturbation": perturbation,
        "new_l3_subset": subset(new_mask),
        "v2_8_remapped_subset": subset(remapped_mask),
        "v2_7_comparator": v27_comparator,
        "per_l3": per_l3,
        "interpretation_rule": {
            "strong": "top-1 >= 0.90, top-2 >= 0.95, permutation p < 0.001, and >=97% perturbation agreement through sigma=0.05",
            "caution": "Failure of a geometric threshold indicates a need for human review; it does not alone prove semantic misclassification.",
        },
    }
    (OUT / "reliability_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    (OUT / "per_l3_metrics.json").write_text(json.dumps(per_l3, ensure_ascii=False, indent=2) + "\n")

    plt.rcParams.update({
        "font.family": "sans-serif", "font.size": 8, "axes.linewidth": 0.7,
        "axes.spines.top": False, "axes.spines.right": False,
    })
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.1), constrained_layout=True)
    it = [r["iteration"] for r in em_trace]
    axes[0].plot(it, em_objectives, color="#2166ac", marker="o", markersize=3)
    ax2 = axes[0].twinx()
    ax2.bar(it, [r["reassigned"] for r in em_trace], color="#bdbdbd", alpha=.45)
    axes[0].set(xlabel="EM iteration", ylabel="Mean cosine objective", title="a  EM convergence")
    ax2.set_ylabel("Cards reassigned")
    ks = [1, 2, 3, 5]
    vals = [100 * topk[f"top_{k}"] for k in ks]
    axes[1].bar([str(k) for k in ks], vals, color="#4393c3")
    axes[1].set(xlabel="Top-k", ylabel="Containment (%)", ylim=(0, 100), title="b  Published assignment geometry")
    for i, value in enumerate(vals):
        axes[1].text(i, min(value + 1, 98), f"{value:.1f}", ha="center", fontsize=7)
    sig = [r["sigma"] for r in perturbation]
    mean = np.array([r["mean_agreement"] for r in perturbation]) * 100
    low = np.array([r["ci95_low"] for r in perturbation]) * 100
    high = np.array([r["ci95_high"] for r in perturbation]) * 100
    axes[2].plot(sig, mean, color="#d6604d")
    axes[2].fill_between(sig, low, high, color="#f4a582", alpha=.35)
    axes[2].axhline(97, color="#777777", linestyle="--", linewidth=.7)
    axes[2].set(xlabel="Gaussian perturbation sigma", ylabel="Agreement (%)", ylim=(0, 101), title="c  Perturbation stability")
    fig.savefig(OUT / "reliability_validation.png", dpi=300)
    fig.savefig(OUT / "reliability_validation.pdf")
    print(json.dumps({k: summary[k] for k in ["em", "published_assignment_geometry", "label_permutation_test", "new_l3_subset", "v2_8_remapped_subset"]}, indent=2))


if __name__ == "__main__":
    main()
