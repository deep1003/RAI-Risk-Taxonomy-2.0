#!/usr/bin/env python3
"""Build the reproducible Algorithm 2 validation notebook for v2.12.0."""

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/jupyter-notebook/algorithm2_em_l3_nonphysical_validation_v2_12.ipynb"


def md(text: str):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text: str):
    return nbf.v4.new_code_cell(text.strip())


cells = [
    md(r"""
# Algorithm 2: EM-Based L3 Family Assignment for Non-Physical AI Risks

**Objective.** Re-run the Technical Report's Algorithm 2 on every currently mapped non-Physical L4 card, compare the converged EM partition with the released mapping, and quantify convergence, geometric consistency, non-random cohesion, perturbation stability, and card-level assignment confidence.

**Safety boundary.** This notebook is validation-only. It excludes all 182 authoritative Physical AI cards and all Physical L3 destinations, and it never edits a release file. Candidate remaps are exported for human review.

**Success criteria.** The run must preserve 1,711 unique L4 IDs, operate on 1,529 non-Physical cards and 30 non-Physical L3 families, converge to a fixed point, and produce auditable reliability outputs.
"""),
    md(r"""
## Experimental plan

1. Load `v2.12.0` and verify grain, uniqueness, hierarchy integrity, and the Physical lock.
2. Reuse the BGE-M3 dense embedding cache only after proving that the ordered card and L3 text fingerprints match the cache-source release.
3. Run seed-initialized spherical EM exactly as Algorithm 2: nearest-centroid E-step and normalized-mean M-step, retaining a seed for any empty family.
4. Compare the converged assignment with the current mapping using exact agreement, ARI, NMI, top-k containment, score margins, and per-L3 diagnostics.
5. Test cohesion against matched-size label permutations and assignment stability under Gaussian score perturbations.
6. Export candidate remaps and reliability summaries without changing the taxonomy.
"""),
    code(r"""
from __future__ import annotations

import hashlib
import json
import os
import random
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

SEED = 20260721
RELEASE_ID = "v2.12.0"
CACHE_RELEASE_ID = "v2.8.0"
PERMUTATIONS = 5_000
PERTURBATIONS = 200
SIGMAS = [0.0, 0.01, 0.025, 0.05, 0.075, 0.10]
MAX_ITERATIONS = 100
REVIEW_MARGIN = 0.05

random.seed(SEED)
np.random.seed(SEED)

def find_repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "public/data/releases").exists():
            return candidate
    raise FileNotFoundError("Run the notebook from inside the RAI-Risk-Taxonomy repository.")

ROOT = find_repo_root()
RELEASE = ROOT / "public/data/releases" / RELEASE_ID
CACHE_RELEASE = ROOT / "public/data/releases" / CACHE_RELEASE_ID
CACHE_DIR = ROOT / "reports/validation/v2.8.0/reliability"
OUT = ROOT / "reports/validation/v2.12.0/em_all_nonphysical"
OUT.mkdir(parents=True, exist_ok=True)

print({"repo": str(ROOT), "release": RELEASE_ID, "seed": SEED})
"""),
    code(r"""
def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def normalized_text(parts) -> str:
    return " | ".join(" ".join(str(value).split()) for value in parts if value)

def card_text(card: dict) -> str:
    evidence = card.get("evidence_keywords") or card.get("evidence_keywords_en") or []
    if isinstance(evidence, list):
        evidence = " ".join(map(str, evidence))
    return normalized_text([
        card.get("label_en"), card.get("label_ko"),
        card.get("definition_en"), card.get("definition_ko"), evidence,
    ])

def node_text(node: dict) -> str:
    return normalized_text([
        node.get("label_en"), node.get("label_ko"),
        node.get("definition_en"), node.get("definition_ko"),
    ])

def fingerprint(texts: list[str]) -> str:
    return hashlib.sha256("\n".join(texts).encode("utf-8")).hexdigest()

cards = read_json(RELEASE / "cards.json")["cards"]
nodes = read_json(RELEASE / "hierarchy.json")["nodes"]
cache_cards = read_json(CACHE_RELEASE / "cards.json")["cards"]
cache_nodes = read_json(CACHE_RELEASE / "hierarchy.json")["nodes"]

l3_nodes_all = sorted((node for node in nodes if node["level"] == 3), key=lambda node: node["node_id"])
cache_l3_nodes = sorted((node for node in cache_nodes if node["level"] == 3), key=lambda node: node["node_id"])
card_texts = [card_text(card) for card in cards]
cache_card_texts = [card_text(card) for card in cache_cards]
l3_texts = [node_text(node) for node in l3_nodes_all]
cache_l3_texts = [node_text(node) for node in cache_l3_nodes]

profile = {
    "all_l4": len(cards),
    "unique_l4_ids": len({card["l4_id"] for card in cards}),
    "all_l3": len(l3_nodes_all),
    "physical_locked": sum(card.get("assignment_status") == "locked_physical" for card in cards),
    "card_text_fingerprint": fingerprint(card_texts),
    "cache_card_text_fingerprint": fingerprint(cache_card_texts),
    "l3_text_fingerprint": fingerprint(l3_texts),
    "cache_l3_text_fingerprint": fingerprint(cache_l3_texts),
}
assert profile["all_l4"] == profile["unique_l4_ids"] == 1711
assert profile["physical_locked"] == 182
assert profile["card_text_fingerprint"] == profile["cache_card_text_fingerprint"]
assert profile["l3_text_fingerprint"] == profile["cache_l3_text_fingerprint"]
profile
"""),
    md(r"""
## The cache is valid for the current release

The cache is accepted only when the complete ordered text fingerprints match. This prevents a stale embedding matrix from being silently applied after labels, definitions, row order, or L3 seeds change. The current schema has no populated canonical `evidence_keywords` field; the text therefore matches the report validation implementation: bilingual label plus bilingual definition.
"""),
    code(r"""
card_embeddings = np.load(CACHE_DIR / "card_embeddings_bge_m3.npy").astype(np.float32)
seed_embeddings_all = np.load(CACHE_DIR / "l3_seed_embeddings_bge_m3.npy").astype(np.float32)
assert card_embeddings.shape[0] == len(cards)
assert seed_embeddings_all.shape[0] == len(l3_nodes_all)

nonphysical_card_mask = np.array([
    not card["primary_l3_id"].startswith("RAI3-P-") for card in cards
])
nonphysical_l3_mask = np.array([
    not node["node_id"].startswith("RAI3-P-") for node in l3_nodes_all
])

cards_np = [card for card, keep in zip(cards, nonphysical_card_mask) if keep]
l3_np = [node for node, keep in zip(l3_nodes_all, nonphysical_l3_mask) if keep]
x = card_embeddings[nonphysical_card_mask]
seed_mu = seed_embeddings_all[nonphysical_l3_mask]
l3_ids = [node["node_id"] for node in l3_np]
l3_index = {node_id: index for index, node_id in enumerate(l3_ids)}
current_labels = np.array([l3_index[card["primary_l3_id"]] for card in cards_np], dtype=np.int32)

assert len(cards_np) == 1529
assert len(l3_np) == 30
assert not any(card["primary_l3_id"].startswith("RAI3-P-") for card in cards_np)
assert not any(node_id.startswith("RAI3-P-") for node_id in l3_ids)

pd.DataFrame({
    "population": ["All L4", "Physical locked/excluded", "Non-Physical evaluated", "Non-Physical L3 candidates"],
    "count": [len(cards), 182, len(cards_np), len(l3_np)],
})
"""),
    md(r"""
## Algorithm 2 implementation

All embeddings and centroids are unit-normalized. The E-step assigns each card to the highest cosine-similarity centroid. The M-step replaces every non-empty centroid with the normalized mean of its assigned embeddings; an empty family keeps its original seed and is flagged. Ties are deterministic because `numpy.argmax` selects the first sorted L3 ID.
"""),
    code(r"""
def unit_rows(values: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    return values / np.maximum(norms, 1e-12)

def centroids(
    values: np.ndarray,
    labels: np.ndarray,
    k: int,
    fallback: np.ndarray,
) -> tuple[np.ndarray, list[int]]:
    result = np.empty((k, values.shape[1]), dtype=np.float32)
    empty = []
    for cluster in range(k):
        members = values[labels == cluster]
        if len(members):
            result[cluster] = members.mean(axis=0)
        else:
            result[cluster] = fallback[cluster]
            empty.append(cluster)
    return unit_rows(result), empty

def em_assignment(
    values: np.ndarray,
    seed_centroids: np.ndarray,
    max_iterations: int = 100,
) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    mu = unit_rows(seed_centroids.copy())
    prior = None
    trace = []
    for iteration in range(1, max_iterations + 1):
        scores = values @ mu.T
        labels = scores.argmax(axis=1).astype(np.int32)
        objective = float(scores[np.arange(len(values)), labels].mean())
        changed = len(values) if prior is None else int(np.sum(labels != prior))
        next_mu, empty = centroids(values, labels, len(mu), fallback=seed_centroids)
        trace.append({
            "iteration": iteration,
            "objective": objective,
            "reassigned": changed,
            "empty_families": [l3_ids[index] for index in empty],
        })
        if prior is not None and changed == 0:
            return labels, mu, trace
        prior = labels.copy()
        mu = next_mu
    raise RuntimeError("EM did not converge within the configured iteration limit")

em_labels, em_mu, em_trace = em_assignment(x, seed_mu, MAX_ITERATIONS)
trace_df = pd.DataFrame(em_trace)
trace_df
"""),
    code(r"""
objectives = trace_df["objective"].to_numpy()
convergence_checks = {
    "fixed_point_reached": int(trace_df.iloc[-1]["reassigned"]) == 0,
    "iterations": len(trace_df),
    "objective_monotonic_non_decreasing": bool(np.all(np.diff(objectives) >= -1e-7)),
    "final_empty_l3_count": len(trace_df.iloc[-1]["empty_families"]),
}
assert convergence_checks["fixed_point_reached"]
assert convergence_checks["objective_monotonic_non_decreasing"]
convergence_checks
"""),
    md(r"""
## Released mapping geometry and EM agreement

Top-k containment asks whether each released L3 appears among the card's nearest released-family centroids. This is a diagnostic of semantic geometry, not a ground-truth accuracy score. Exact EM agreement, ARI, and NMI compare the released partition with the fully automated partition from Algorithm 2.
"""),
    code(r"""
current_mu, current_empty = centroids(x, current_labels, len(l3_ids), fallback=seed_mu)
current_scores = x @ current_mu.T
current_order = np.argsort(-current_scores, axis=1)
current_ranks = np.array([
    int(np.where(current_order[row] == current_labels[row])[0][0]) + 1
    for row in range(len(x))
])
assigned_similarity = current_scores[np.arange(len(x)), current_labels]
best_alternative = np.max(
    np.where(np.eye(len(l3_ids), dtype=bool)[current_labels], -np.inf, current_scores), axis=1
)
current_margin = assigned_similarity - best_alternative

agreement = {
    "exact_assignment_agreement": float(np.mean(em_labels == current_labels)),
    "adjusted_rand_index": float(adjusted_rand_score(current_labels, em_labels)),
    "normalized_mutual_information": float(normalized_mutual_info_score(current_labels, em_labels)),
    "current_mean_within_family_cohesion": float(assigned_similarity.mean()),
    "current_median_assignment_margin": float(np.median(current_margin)),
    "current_negative_margin_share": float(np.mean(current_margin < 0)),
    "top_k_containment": {
        f"top_{k}": float(np.mean(current_ranks <= k)) for k in (1, 2, 3, 5, 10)
    },
}
agreement
"""),
    md(r"""
## Reliability tests

The matched-size permutation test compares observed within-family cohesion with random partitions that preserve every L3 family size. The perturbation test adds Gaussian noise in centroid-score space and measures agreement with the unperturbed nearest-centroid assignment. A plus-one permutation p-value is reported to avoid zero p-values.
"""),
    code(r"""
def cohesion(values: np.ndarray, labels: np.ndarray, mu: np.ndarray) -> float:
    return float((values * mu[labels]).sum(axis=1).mean())

def permutation_test(
    values: np.ndarray,
    labels: np.ndarray,
    observed: float,
    permutations: int,
    seed: int,
) -> dict:
    rng = np.random.default_rng(seed)
    sizes = np.bincount(labels, minlength=len(l3_ids))
    nonzero_sizes = sizes[sizes > 0]
    boundaries = np.cumsum(nonzero_sizes)[:-1]
    null = np.empty(permutations, dtype=np.float32)
    for iteration in range(permutations):
        shuffled = values[rng.permutation(len(values))]
        sums = np.add.reduceat(shuffled, np.r_[0, boundaries], axis=0)
        null[iteration] = np.linalg.norm(sums, axis=1).sum() / len(values)
    exceedances = int(np.sum(null >= observed))
    return {
        "permutations": permutations,
        "observed_cohesion": observed,
        "null_mean": float(null.mean()),
        "null_sd": float(null.std(ddof=1)),
        "null_p95": float(np.quantile(null, 0.95)),
        "exceedances": exceedances,
        "p_value_plus_one": float((exceedances + 1) / (permutations + 1)),
    }

def perturbation_test(
    values: np.ndarray,
    mu: np.ndarray,
    sigmas: list[float],
    repeats: int,
    seed: int,
) -> tuple[list[dict], np.ndarray]:
    rng = np.random.default_rng(seed)
    base_scores = values @ mu.T
    baseline = base_scores.argmax(axis=1)
    covariance = mu @ mu.T
    covariance = (covariance + covariance.T) / 2
    covariance += np.eye(len(mu), dtype=np.float32) * 1e-7
    chol = np.linalg.cholesky(covariance).astype(np.float32)
    results = []
    card_agreement_at_005 = np.zeros(len(values), dtype=np.float32)
    for sigma in sigmas:
        agreements = np.empty(repeats, dtype=np.float32)
        card_hits = np.zeros(len(values), dtype=np.int32)
        if sigma == 0:
            agreements.fill(1.0)
            card_hits.fill(repeats)
        else:
            for repeat in range(repeats):
                z = rng.standard_normal((len(values), len(mu)), dtype=np.float32)
                noisy = base_scores + sigma * (z @ chol.T)
                matched = noisy.argmax(axis=1) == baseline
                agreements[repeat] = matched.mean()
                card_hits += matched
        if np.isclose(sigma, 0.05):
            card_agreement_at_005 = card_hits / repeats
        results.append({
            "sigma": sigma,
            "mean_agreement": float(agreements.mean()),
            "ci95_low": float(np.quantile(agreements, 0.025)),
            "ci95_high": float(np.quantile(agreements, 0.975)),
        })
    return results, card_agreement_at_005

current_cohesion = cohesion(x, current_labels, current_mu)
em_cohesion = cohesion(x, em_labels, em_mu)
permutation_current = permutation_test(x, current_labels, current_cohesion, PERMUTATIONS, SEED)
permutation_em = permutation_test(x, em_labels, em_cohesion, PERMUTATIONS, SEED + 1)
perturbation, card_stability_005 = perturbation_test(x, em_mu, SIGMAS, PERTURBATIONS, SEED + 2)

pd.DataFrame(perturbation)
"""),
    code(r"""
em_scores = x @ em_mu.T
em_sorted = np.sort(em_scores, axis=1)
em_margin = em_sorted[:, -1] - em_sorted[:, -2]

candidate_rows = []
for row, card in enumerate(cards_np):
    proposed = l3_ids[int(em_labels[row])]
    current = card["primary_l3_id"]
    candidate_rows.append({
        "l4_id": card["l4_id"],
        "label_en": card.get("label_en"),
        "current_l3_id": current,
        "em_l3_id": proposed,
        "changed": proposed != current,
        "em_best_similarity": float(em_scores[row, em_labels[row]]),
        "em_margin": float(em_margin[row]),
        "stability_at_sigma_0_05": float(card_stability_005[row]),
        "review_priority": "high" if em_margin[row] < 0.02 else "medium" if em_margin[row] < REVIEW_MARGIN else "low",
    })

candidates_df = pd.DataFrame(candidate_rows)
changed_df = candidates_df[candidates_df["changed"]].sort_values(
    ["review_priority", "em_margin", "l4_id"]
).reset_index(drop=True)

counts_current = pd.Series(current_labels).value_counts().reindex(range(len(l3_ids)), fill_value=0)
counts_em = pd.Series(em_labels).value_counts().reindex(range(len(l3_ids)), fill_value=0)
per_l3_df = pd.DataFrame({
    "l3_id": l3_ids,
    "label_en": [node["label_en"] for node in l3_np],
    "current_n": counts_current.to_numpy(),
    "em_n": counts_em.to_numpy(),
})
per_l3_df["delta"] = per_l3_df["em_n"] - per_l3_df["current_n"]

{
    "candidate_remaps": int(changed_df.shape[0]),
    "candidate_remap_share": float(changed_df.shape[0] / len(cards_np)),
    "low_margin_candidates": int((changed_df["em_margin"] < REVIEW_MARGIN).sum()),
    "empty_em_families": int((per_l3_df["em_n"] == 0).sum()),
}
"""),
    code(r"""
per_l3_metrics = []
for index, node in enumerate(l3_np):
    mask = current_labels == index
    per_l3_metrics.append({
        "l3_id": node["node_id"],
        "label_en": node["label_en"],
        "n": int(mask.sum()),
        "mean_assigned_similarity": float(assigned_similarity[mask].mean()) if mask.any() else None,
        "median_current_margin": float(np.median(current_margin[mask])) if mask.any() else None,
        "top_1": float(np.mean(current_ranks[mask] <= 1)) if mask.any() else None,
        "top_3": float(np.mean(current_ranks[mask] <= 3)) if mask.any() else None,
        "em_agreement": float(np.mean(em_labels[mask] == current_labels[mask])) if mask.any() else None,
    })
per_l3_metrics_df = pd.DataFrame(per_l3_metrics).sort_values(["em_agreement", "median_current_margin"])
per_l3_metrics_df.head(10)
"""),
    md(r"""
## Export and decision rules

The output is deliberately a review queue, not an automatic taxonomy rewrite. Low margins, low perturbation stability, empty or sparse destination families, and large per-L3 count shifts require semantic adjudication. Physical AI remains outside the experiment by construction.
"""),
    code(r"""
summary = {
    "release_id": RELEASE_ID,
    "algorithm": "Algorithm 2 - seed-initialized spherical EM",
    "encoder": "BAAI/bge-m3 dense embeddings (validated cache)",
    "seed": SEED,
    "scope": {
        "all_l4": len(cards),
        "physical_excluded": 182,
        "nonphysical_l4_evaluated": len(cards_np),
        "nonphysical_l3_candidates": len(l3_np),
    },
    "convergence": convergence_checks,
    "released_mapping_geometry": agreement,
    "em_vs_released": {
        "exact_agreement": agreement["exact_assignment_agreement"],
        "adjusted_rand_index": agreement["adjusted_rand_index"],
        "normalized_mutual_information": agreement["normalized_mutual_information"],
        "candidate_remaps": int(changed_df.shape[0]),
        "candidate_remap_share": float(changed_df.shape[0] / len(cards_np)),
    },
    "permutation_current": permutation_current,
    "permutation_em": permutation_em,
    "perturbation_em": perturbation,
    "interpretation": {
        "strong_geometry": "top-1 >= 0.90, top-2 >= 0.95, permutation p < 0.001, and >= 0.97 perturbation agreement through sigma=0.05",
        "caution": "Geometric disagreement proposes review; it does not prove semantic misclassification.",
        "publication_policy": "No candidate is applied without ontology gates and human review.",
    },
}

(OUT / "reliability_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
changed_df.to_csv(OUT / "candidate_remaps.csv", index=False)
per_l3_df.to_csv(OUT / "l3_count_comparison.csv", index=False)
per_l3_metrics_df.to_csv(OUT / "per_l3_reliability.csv", index=False)
pd.DataFrame(em_trace).to_csv(OUT / "em_trace.csv", index=False)

print(json.dumps({
    "output_dir": str(OUT),
    "converged_iterations": convergence_checks["iterations"],
    "exact_agreement": agreement["exact_assignment_agreement"],
    "ari": agreement["adjusted_rand_index"],
    "nmi": agreement["normalized_mutual_information"],
    "candidate_remaps": int(changed_df.shape[0]),
    "current_permutation_p": permutation_current["p_value_plus_one"],
    "sigma_0_05_agreement": next(row["mean_agreement"] for row in perturbation if np.isclose(row["sigma"], 0.05)),
}, indent=2))
"""),
    md(r"""
## Interpretation and next step

Use `reliability_summary.json` for the aggregate trust assessment, `per_l3_reliability.csv` to identify weak families, and `candidate_remaps.csv` as the human-review queue. A subsequent constrained pass may apply L1/L2 compatibility, agentic-uniqueness rules, destination-definition keyword gates, and locked mappings before any approved release is generated.
"""),
]

notebook = nbf.v4.new_notebook(
    cells=cells,
    metadata={
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3"},
    },
)
OUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(notebook, OUT)
print(f"Wrote {OUT}")
