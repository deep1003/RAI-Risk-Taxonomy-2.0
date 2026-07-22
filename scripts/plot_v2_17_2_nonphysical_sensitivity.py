#!/usr/bin/env python3
"""Plot General/Agentic AI sensitivity panels for v2.17.2."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.preprocessing import normalize


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/data/releases/v2.17.2"
BGE = ROOT / "reports/validation/v2.17.2/bge_m3_active"
OUT = ROOT / "reports/validation/v2.17.2/full_sensitivity_bge_m3"
SEED = 20260723


def semantic_l3(card: dict) -> str:
    primary = card.get("primary_l3_id") or ""
    if "HLD" in primary and card.get("hold_semantic_path"):
        return card["hold_semantic_path"]["l3_id"]
    if "HLD" in primary and card.get("previous_primary_l3_id"):
        return card["previous_primary_l3_id"]
    return primary


def centroids(embeddings: np.ndarray, assignment: np.ndarray, seeds: np.ndarray) -> np.ndarray:
    output = np.zeros((seeds.shape[0], embeddings.shape[1]), dtype="float32")
    for family in range(seeds.shape[0]):
        members = embeddings[assignment == family]
        output[family] = members.mean(axis=0) if len(members) else seeds[family]
    return normalize(output)


def em_curve(embeddings: np.ndarray, seeds: np.ndarray, max_iter: int = 30) -> tuple[list[int], list[float]]:
    z = (embeddings @ seeds.T).argmax(axis=1)
    xs, ys = [], []
    for iteration in range(1, max_iter + 1):
        centers = centroids(embeddings, z, seeds)
        objective = float((embeddings @ centers.T).max(axis=1).mean())
        xs.append(iteration)
        ys.append(objective)
        z_next = (embeddings @ centers.T).argmax(axis=1)
        if np.array_equal(z, z_next):
            break
        z = z_next
    return xs, ys


def topk_values(embeddings: np.ndarray, assignment: np.ndarray, seeds: np.ndarray) -> list[float]:
    centers = centroids(embeddings, assignment, seeds)
    sims = embeddings @ centers.T
    order = np.argsort(-sims, axis=1)
    pos = (order == assignment[:, None]).argmax(axis=1)
    return [float((pos < k).mean()) * 100 for k in (1, 2, 3, 5)]


def perturbation_curve(embeddings: np.ndarray, assignment: np.ndarray, seeds: np.ndarray) -> tuple[list[float], list[float], list[float], list[float]]:
    centers = centroids(embeddings, assignment, seeds)
    base = (embeddings @ centers.T).argmax(axis=1)
    rng = np.random.default_rng(SEED)
    sigmas = [0.00, 0.01, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50]
    means, lows, highs = [], [], []
    for sigma in sigmas:
        if sigma == 0:
            vals = np.ones(200)
        else:
            vals = []
            for _ in range(200):
                perturbed = embeddings + rng.normal(0, sigma, embeddings.shape).astype("float32")
                perturbed = normalize(perturbed)
                vals.append(float(((perturbed @ centers.T).argmax(axis=1) == base).mean()))
            vals = np.array(vals)
        means.append(float(vals.mean()) * 100)
        lows.append(float(np.quantile(vals, 0.025)) * 100)
        highs.append(float(np.quantile(vals, 0.975)) * 100)
    return sigmas, means, lows, highs


def main() -> None:
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

    conditions = {
        "General/Agentic HOLD included": ~physical,
        "General/Agentic HOLD excluded": (~physical) & (~hold),
    }
    results = {}
    for label, mask in conditions.items():
        emb = embeddings[mask]
        assn = assignment[mask]
        results[label] = {
            "n": int(mask.sum()),
            "em": em_curve(emb, seeds),
            "topk": topk_values(emb, assn, seeds),
            "perturbation": perturbation_curve(emb, assn, seeds),
        }

    summary = {
        "release": "v2.17.2",
        "scope": "active General/Agentic cards only; retired merged records excluded",
        "registered_ids": 1711,
        "active_cards": int(len(cards)),
        "active_physical_cards_excluded": int(physical.sum()),
        "conditions": {
            label: {
                "cards": item["n"],
                "em_iterations": item["em"][0][-1],
                "em_final_objective": round(item["em"][1][-1], 4),
                "topk": {str(k): round(v, 1) for k, v in zip([1, 2, 3, 5], item["topk"])},
                "stability_sigma_0.05": round(item["perturbation"][1][2], 1),
            }
            for label, item in results.items()
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "general_agentic_sensitivity_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "figure.dpi": 170,
        "axes.edgecolor": "#D0D5DD",
        "axes.labelcolor": "#344054",
        "xtick.color": "#667085",
        "ytick.color": "#344054",
        "text.color": "#101828",
    })
    styles = {
        "General/Agentic HOLD included": {"color": "#0072B2", "marker": "o", "linestyle": "-", "hatch": None},
        "General/Agentic HOLD excluded": {"color": "#E69F00", "marker": "s", "linestyle": "--", "hatch": "//"},
    }
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.8))

    ax = axes[0]
    for label, item in results.items():
        st = styles[label]
        ax.plot(item["em"][0], item["em"][1], label=f"{label} (n={item['n']})", color=st["color"], marker=st["marker"], linestyle=st["linestyle"], linewidth=1.8, markersize=4)
    ax.set_title("a  EM convergence", loc="left", fontsize=11, fontweight="bold")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Mean cosine objective")
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    ax.legend(frameon=False, fontsize=8, loc="lower right")

    ax = axes[1]
    topk = [1, 2, 3, 5]
    x = np.arange(len(topk))
    width = 0.34
    offsets = [-width / 2, width / 2]
    for offset, (label, item) in zip(offsets, results.items()):
        st = styles[label]
        vals = item["topk"]
        bars = ax.bar(x + offset, vals, width=width, label=label, color=st["color"], alpha=0.22, edgecolor=st["color"], linewidth=1.1, hatch=st["hatch"])
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, val + 1.0, f"{val:.1f}", ha="center", va="bottom", fontsize=8, color="#475467")
    ax.set_title("b  Top-k containment", loc="left", fontsize=11, fontweight="bold")
    ax.set_xlabel("Released L3 within top-k centroids")
    ax.set_ylabel("Cards contained (%)")
    ax.set_xticks(x, [str(k) for k in topk])
    ax.set_ylim(0, 108)
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)

    ax = axes[2]
    for label, item in results.items():
        sigmas, means, lows, highs = item["perturbation"]
        st = styles[label]
        ax.plot(sigmas, means, label=label, color=st["color"], marker=st["marker"], linestyle=st["linestyle"], linewidth=1.8, markersize=4)
        ax.fill_between(sigmas, lows, highs, color=st["color"], alpha=0.08, linewidth=0)
    ax.set_title("c  Assignment stability", loc="left", fontsize=11, fontweight="bold")
    ax.set_xlabel("Gaussian perturbation sigma")
    ax.set_ylabel("Agreement with unperturbed assignment (%)")
    ax.set_ylim(0, 104)
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    ax.legend(frameon=False, fontsize=8, loc="upper right")

    for axis in axes:
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
    fig.suptitle("Sensitivity analysis, General/Agentic AI only", x=0.04, y=1.02, ha="left", fontsize=14, fontweight="bold")
    fig.text(0.04, -0.03, "v2.17.2 BGE-M3. Physical AI active cards are excluded, leaving General and Agentic AI cards. Retired merged records remain in the 1,711-ID registry but are excluded from reliability metrics. Shaded bands show 95% intervals across 200 perturbation repeats.", fontsize=8.5, color="#667085")
    fig.tight_layout(rect=(0.03, 0.03, 1, 0.96))
    fig.savefig(OUT / "general_agentic_sensitivity_3panel.png", bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / "general_agentic_sensitivity_3panel.pdf", bbox_inches="tight", facecolor="white")


if __name__ == "__main__":
    main()
