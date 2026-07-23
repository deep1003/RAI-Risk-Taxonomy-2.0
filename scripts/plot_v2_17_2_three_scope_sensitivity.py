#!/usr/bin/env python3
"""Generate three standalone sensitivity figures and tables for v2.17.2.

Scopes:
1. Overall active cards, Physical AI included, HOLD included.
2. Overall active cards, Physical AI included, HOLD excluded.
3. Physical AI active cards only.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.preprocessing import normalize


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/data/releases/v2.17.2"
BGE = ROOT / "reports/validation/v2.17.2/bge_m3_active"
OUT = ROOT / "reports/validation/v2.17.2/three_scope_sensitivity_bge_m3"
SEED = 20260723
SIGMAS = [0.00, 0.01, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50]
TOPK = [1, 2, 3, 5]


def semantic_l3(card: dict) -> str:
    primary = card.get("primary_l3_id") or ""
    if "HLD" in primary and card.get("hold_semantic_path"):
        return card["hold_semantic_path"]["l3_id"]
    if "HLD" in primary and card.get("previous_primary_l3_id"):
        return card["previous_primary_l3_id"]
    return primary


def load_inputs() -> tuple[list[dict], list[str], np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    cards_all = json.loads((SOURCE / "cards.json").read_text())["cards"]
    cards = [card for card in cards_all if card.get("status") == "active"]
    hierarchy = json.loads((SOURCE / "hierarchy.json").read_text())["nodes"]
    l3_ids = [node["node_id"] for node in hierarchy if node.get("level") == 3 and "HLD" not in node["node_id"]]
    l3_index = {l3_id: i for i, l3_id in enumerate(l3_ids)}
    index = json.loads((BGE / "index.json").read_text())
    position = {l4_id: i for i, l4_id in enumerate(index["l4_ids"])}
    embeddings_all = np.load(BGE / "card_embeddings.npy")
    embeddings = embeddings_all[[position[card["l4_id"]] for card in cards]]
    seeds = np.load(BGE / "l3_seed_embeddings.npy")
    assignment = np.array([l3_index[semantic_l3(card)] for card in cards], dtype=int)
    hold = np.array([bool(card.get("decision_required")) for card in cards])
    physical = np.array([(semantic_l3(card) or "").startswith("RAI3-P-") for card in cards])
    if len(cards) != 1660:
        raise ValueError(f"Expected 1,660 active cards, got {len(cards)}")
    if int(physical.sum()) != 189:
        raise ValueError(f"Expected 189 Physical AI cards, got {int(physical.sum())}")
    return cards, l3_ids, embeddings, seeds, assignment, hold, physical


def centroids(embeddings: np.ndarray, assignment: np.ndarray, seeds: np.ndarray) -> np.ndarray:
    output = np.zeros((seeds.shape[0], embeddings.shape[1]), dtype="float32")
    for family in range(seeds.shape[0]):
        members = embeddings[assignment == family]
        output[family] = members.mean(axis=0) if len(members) else seeds[family]
    return normalize(output)


def em_curve(embeddings: np.ndarray, seeds: np.ndarray, max_iter: int = 60) -> tuple[list[int], list[float], np.ndarray]:
    z = (embeddings @ seeds.T).argmax(axis=1)
    xs: list[int] = []
    ys: list[float] = []
    for iteration in range(1, max_iter + 1):
        centers = centroids(embeddings, z, seeds)
        objective = float((embeddings @ centers.T).max(axis=1).mean())
        xs.append(iteration)
        ys.append(objective)
        z_next = (embeddings @ centers.T).argmax(axis=1)
        if np.array_equal(z, z_next):
            z = z_next
            break
        z = z_next
    return xs, ys, z


def cohesion(embeddings: np.ndarray, assignment: np.ndarray, family_count: int) -> float:
    total = 0.0
    count = 0
    for family in range(family_count):
        members = embeddings[assignment == family]
        if len(members) >= 2:
            center = members.mean(axis=0)
            center = center / np.linalg.norm(center)
            total += float((members @ center).sum())
            count += len(members)
    return total / count if count else 0.0


def evaluate(label: str, embeddings: np.ndarray, assignment: np.ndarray, seeds: np.ndarray) -> dict:
    centers = centroids(embeddings, assignment, seeds)
    sims = embeddings @ centers.T
    order = np.argsort(-sims, axis=1)
    pos = (order == assignment[:, None]).argmax(axis=1)
    top1 = sims.argmax(axis=1)
    sorted_sims = np.sort(sims, axis=1)
    margins = sims[np.arange(len(assignment)), assignment] - np.where(
        top1 == assignment, sorted_sims[:, -2], sorted_sims[:, -1]
    )
    xs, ys, em_assignment = em_curve(embeddings, seeds)
    observed = cohesion(embeddings, assignment, seeds.shape[0])
    rng = np.random.default_rng(SEED)
    null = np.array([cohesion(embeddings, rng.permutation(assignment), seeds.shape[0]) for _ in range(5000)])
    perturb_rng = np.random.default_rng(SEED)
    perturbation = []
    for sigma in SIGMAS:
        if sigma == 0:
            vals = np.ones(200)
        else:
            vals = []
            for _ in range(200):
                perturbed = embeddings + perturb_rng.normal(0, sigma, embeddings.shape).astype("float32")
                perturbed = normalize(perturbed)
                vals.append(float(((perturbed @ centers.T).argmax(axis=1) == top1).mean()))
            vals = np.array(vals)
        perturbation.append({
            "sigma": sigma,
            "mean": float(vals.mean()) * 100,
            "low_95": float(np.quantile(vals, 0.025)) * 100,
            "high_95": float(np.quantile(vals, 0.975)) * 100,
        })
    return {
        "condition": label,
        "cards": int(len(assignment)),
        "families": int(seeds.shape[0]),
        "topk": {str(k): round(float((pos < k).mean()) * 100, 1) for k in TOPK},
        "median_margin": round(float(np.median(margins)), 4),
        "negative_margin_share": round(float((margins < 0).mean()) * 100, 1),
        "mean_within_family_cosine": round(float(observed), 4),
        "null_mean": round(float(null.mean()), 4),
        "permutation_p": round(float((1 + (null >= observed).sum()) / (len(null) + 1)), 4),
        "em_iterations": int(xs[-1]),
        "em_final_objective": round(float(ys[-1]), 4),
        "em_agreement": round(float((em_assignment == assignment).mean()) * 100, 1),
        "ari": round(float(adjusted_rand_score(assignment, em_assignment)), 3),
        "nmi": round(float(normalized_mutual_info_score(assignment, em_assignment)), 3),
        "em_curve": [{"iteration": x, "objective": y} for x, y in zip(xs, ys)],
        "perturbation": perturbation,
    }


def plot_condition(result: dict, slug: str, title: str, color: str, hatch: str | None) -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "figure.dpi": 170,
        "axes.edgecolor": "#D0D5DD",
        "axes.labelcolor": "#344054",
        "xtick.color": "#667085",
        "ytick.color": "#344054",
        "text.color": "#101828",
    })
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.8))
    ax = axes[0]
    xs = [point["iteration"] for point in result["em_curve"]]
    ys = [point["objective"] for point in result["em_curve"]]
    ax.plot(xs, ys, color=color, marker="o", linewidth=1.9, markersize=4)
    ax.set_title("a  EM convergence", loc="left", fontsize=11, fontweight="bold")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Mean cosine objective")
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    ax.text(0.98, 0.08, f"{result['em_iterations']} steps, objective {result['em_final_objective']:.3f}", transform=ax.transAxes, ha="right", va="bottom", fontsize=8.5, color="#475467")

    ax = axes[1]
    vals = [result["topk"][str(k)] for k in TOPK]
    bars = ax.bar(range(len(TOPK)), vals, color=color, alpha=0.22, edgecolor=color, linewidth=1.2, hatch=hatch)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 1.0, f"{val:.1f}", ha="center", va="bottom", fontsize=8, color="#475467")
    ax.set_title("b  Top-k containment", loc="left", fontsize=11, fontweight="bold")
    ax.set_xlabel("Released L3 within top-k centroids")
    ax.set_ylabel("Cards contained (%)")
    ax.set_xticks(range(len(TOPK)), [str(k) for k in TOPK])
    ax.set_ylim(0, 108)
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)

    ax = axes[2]
    sigmas = [point["sigma"] for point in result["perturbation"]]
    means = [point["mean"] for point in result["perturbation"]]
    lows = [point["low_95"] for point in result["perturbation"]]
    highs = [point["high_95"] for point in result["perturbation"]]
    ax.plot(sigmas, means, color=color, marker="o", linewidth=1.9, markersize=4)
    ax.fill_between(sigmas, lows, highs, color=color, alpha=0.10, linewidth=0)
    ax.set_title("c  Assignment stability", loc="left", fontsize=11, fontweight="bold")
    ax.set_xlabel("Gaussian perturbation sigma")
    ax.set_ylabel("Agreement with unperturbed assignment (%)")
    ax.set_ylim(0, 104)
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)

    for axis in axes:
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
    fig.suptitle(title, x=0.04, y=1.02, ha="left", fontsize=14, fontweight="bold")
    fig.text(0.04, -0.03, "v2.17.2 BGE-M3. Retired merged records remain in the 1,711-ID registry but are excluded from reliability metrics. Shaded bands show 95% intervals across 200 perturbation repeats.", fontsize=8.5, color="#667085")
    fig.tight_layout(rect=(0.03, 0.03, 1, 0.96))
    fig.savefig(OUT / f"{slug}_3panel.png", bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / f"{slug}_3panel.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_tables(results: list[dict]) -> None:
    rows = []
    for result in results:
        rows.append({
            "condition": result["condition"],
            "cards": result["cards"],
            "families": result["families"],
            "em_iterations": result["em_iterations"],
            "em_final_objective": result["em_final_objective"],
            "top1": result["topk"]["1"],
            "top2": result["topk"]["2"],
            "top3": result["topk"]["3"],
            "top5": result["topk"]["5"],
            "median_margin": result["median_margin"],
            "negative_margin_share": result["negative_margin_share"],
            "permutation_p": result["permutation_p"],
            "sigma_0.01_stability": next(point["mean"] for point in result["perturbation"] if point["sigma"] == 0.01),
            "sigma_0.05_stability": next(point["mean"] for point in result["perturbation"] if point["sigma"] == 0.05),
        })
    with (OUT / "three_scope_sensitivity_table.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cards, _l3_ids, embeddings, seeds, assignment, hold, physical = load_inputs()
    masks = {
        "Overall, Physical included, HOLD included": np.ones(len(cards), dtype=bool),
        "Overall, Physical included, HOLD excluded": ~hold,
        "Physical AI only": physical,
    }
    configs = {
        "Overall, Physical included, HOLD included": ("overall_hold_included", "Sensitivity analysis, Overall active cards with Physical AI included, HOLD included", "#0072B2", None),
        "Overall, Physical included, HOLD excluded": ("overall_hold_excluded", "Sensitivity analysis, Overall active cards with Physical AI included, HOLD excluded", "#E69F00", "//"),
        "Physical AI only": ("physical_only", "Sensitivity analysis, Physical AI active cards only", "#009E73", None),
    }
    results = []
    for label, mask in masks.items():
        result = evaluate(label, embeddings[mask], assignment[mask], seeds)
        results.append(result)
        slug, title, color, hatch = configs[label]
        plot_condition(result, slug, title, color, hatch)
    summary = {
        "release": "v2.17.2",
        "model": "BAAI/bge-m3 cached local embeddings",
        "seed": SEED,
        "registered_ids": 1711,
        "active_cards": int(len(cards)),
        "active_hold_cards": int(hold.sum()),
        "active_non_hold_cards": int((~hold).sum()),
        "active_physical_cards": int(physical.sum()),
        "conditions": results,
    }
    (OUT / "three_scope_sensitivity_bge_m3_v2172.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    write_tables(results)
    print(json.dumps({
        "output": str(OUT),
        "conditions": [
            {
                "condition": result["condition"],
                "cards": result["cards"],
                "em_iterations": result["em_iterations"],
                "em_final_objective": result["em_final_objective"],
                "top1": result["topk"]["1"],
                "top5": result["topk"]["5"],
                "stability_sigma_0.05": round(next(point["mean"] for point in result["perturbation"] if point["sigma"] == 0.05), 1),
            }
            for result in results
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
