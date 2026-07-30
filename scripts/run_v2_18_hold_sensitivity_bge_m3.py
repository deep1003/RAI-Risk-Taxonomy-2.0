#!/usr/bin/env python3
"""Compare v2.18.0-rc sensitivity with HOLD included and excluded."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "public/data/releases/v2.18.0-rc"
EMBEDDING_ROOT = (
    ROOT
    / "reports/validation/v2.17.2"
    / "full_mapping_sensitivity_bge_m3_20260724"
)
SEED_ROOT = (
    ROOT
    / "reports/validation/v2.18.0-rc"
    / "general_societal_extension"
)
OUT = (
    ROOT
    / "reports/validation/v2.18.0-rc"
    / "hold_sensitivity_bge_m3"
)

sys.path.insert(0, str(ROOT / "scripts"))
import plot_v2_17_2_three_scope_sensitivity as sensitivity  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def semantic_l3(card: dict) -> str:
    primary = card.get("primary_l3_id") or ""
    if "HLD" in primary:
        return (card.get("hold_semantic_path") or {}).get("l3_id") or ""
    return primary


def load_inputs() -> tuple[list[dict], list[str], np.ndarray, np.ndarray, np.ndarray]:
    hierarchy = json.loads(
        (RELEASE / "hierarchy.json").read_text(encoding="utf-8")
    )["nodes"]
    cards = [
        card
        for card in json.loads(
            (RELEASE / "cards.json").read_text(encoding="utf-8")
        )["cards"]
        if card.get("status") == "active"
    ]
    l3_nodes = [
        node
        for node in hierarchy
        if node.get("level") == 3
        and node.get("status") == "active"
        and "HLD" not in node["node_id"]
    ]
    l3_ids = [node["node_id"] for node in l3_nodes]
    l3_index = {l3_id: index for index, l3_id in enumerate(l3_ids)}
    embedding_index = json.loads(
        (EMBEDDING_ROOT / "index.json").read_text(encoding="utf-8")
    )
    positions = {
        l4_id: index
        for index, l4_id in enumerate(embedding_index["l4_ids"])
    }
    source_embeddings = np.load(
        EMBEDDING_ROOT / "card_embeddings.npy"
    )
    embeddings = source_embeddings[
        [positions[card["l4_id"]] for card in cards]
    ].astype("float32")
    seeds = np.load(SEED_ROOT / "l3_seed_embeddings.npy").astype("float32")
    assignment = np.array(
        [l3_index[semantic_l3(card)] for card in cards],
        dtype=int,
    )
    hold = np.array(
        [bool(card.get("decision_required")) for card in cards],
        dtype=bool,
    )
    if len(cards) != 1660:
        raise ValueError(f"Expected 1,660 active cards, got {len(cards)}")
    if len(l3_ids) != 54 or seeds.shape[0] != 54:
        raise ValueError(
            f"Expected 54 semantic L3 families, got {len(l3_ids)} "
            f"and {seeds.shape[0]} seed rows"
        )
    if int(hold.sum()) != 614:
        raise ValueError(f"Expected 614 HOLD cards, got {int(hold.sum())}")
    if embeddings.shape != (1660, 1024):
        raise ValueError(f"Unexpected embedding shape: {embeddings.shape}")
    return cards, l3_ids, embeddings, seeds, assignment, hold


def plot_comparison(included: dict, excluded: dict) -> None:
    blue = "#1668B2"
    orange = "#E67E00"
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "figure.dpi": 180,
            "axes.edgecolor": "#D0D5DD",
            "axes.labelcolor": "#344054",
            "xtick.color": "#667085",
            "ytick.color": "#344054",
            "text.color": "#101828",
        }
    )
    fig, axes = plt.subplots(1, 3, figsize=(15.2, 5.1))
    fig.suptitle(
        "HOLD sensitivity analysis",
        x=0.025,
        y=0.98,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )

    ax = axes[0]
    for result, color, marker, linestyle, label in (
        (included, blue, "o", "-", "HOLD included"),
        (excluded, orange, "s", "--", "HOLD excluded"),
    ):
        xs = [point["iteration"] for point in result["em_curve"]]
        ys = [point["objective"] for point in result["em_curve"]]
        ax.plot(
            xs,
            ys,
            color=color,
            marker=marker,
            linestyle=linestyle,
            linewidth=1.8,
            markersize=3.8,
            label=label,
        )
    ax.set_title("a  EM convergence", loc="left", fontweight="bold")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Mean cosine objective")
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")

    ax = axes[1]
    topk = [1, 2, 3, 5]
    x = np.arange(len(topk))
    width = 0.36
    for offset, result, color, hatch, label in (
        (-width / 2, included, blue, None, "HOLD included"),
        (width / 2, excluded, orange, "//", "HOLD excluded"),
    ):
        values = [result["topk"][str(k)] for k in topk]
        bars = ax.bar(
            x + offset,
            values,
            width,
            color=color,
            alpha=0.22,
            edgecolor=color,
            linewidth=1.1,
            hatch=hatch,
            label=label,
        )
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + 0.8,
                f"{value:.1f}",
                ha="center",
                va="bottom",
                fontsize=7.6,
                color="#475467",
            )
    ax.set_title("b  Top-k containment", loc="left", fontweight="bold")
    ax.set_xlabel("Released L3 within top-k centroids")
    ax.set_ylabel("Cards contained (%)")
    ax.set_xticks(x, [str(k) for k in topk])
    ax.set_ylim(0, 106)
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)

    ax = axes[2]
    for result, color, marker, linestyle, label in (
        (included, blue, "o", "-", "HOLD included"),
        (excluded, orange, "s", "--", "HOLD excluded"),
    ):
        points = result["perturbation"]
        xs = np.array([point["sigma"] for point in points])
        means = np.array([point["mean"] for point in points])
        lows = np.array([point["low_95"] for point in points])
        highs = np.array([point["high_95"] for point in points])
        ax.plot(
            xs,
            means,
            color=color,
            marker=marker,
            linestyle=linestyle,
            linewidth=1.8,
            markersize=3.8,
            label=label,
        )
        ax.fill_between(xs, lows, highs, color=color, alpha=0.10)
    ax.set_title("c  Assignment stability", loc="left", fontweight="bold")
    ax.set_xlabel("Gaussian perturbation sigma")
    ax.set_ylabel("Agreement with unperturbed assignment (%)")
    ax.set_ylim(0, 104)
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")

    fig.text(
        0.025,
        0.015,
        "BGE-M3, 54 semantic L3 families. HOLD included: n=1,660; "
        "HOLD excluded: n=1,046. Shaded bands show 95% intervals "
        "across 200 perturbation repeats.",
        fontsize=8.4,
        color="#667085",
    )
    fig.tight_layout(rect=(0.02, 0.06, 0.995, 0.93))
    fig.savefig(
        OUT / "hold_included_excluded_sensitivity_3panel.png",
        dpi=220,
        bbox_inches="tight",
        facecolor="white",
    )
    fig.savefig(
        OUT / "hold_included_excluded_sensitivity_3panel.pdf",
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)


def main() -> None:
    if OUT.exists():
        raise FileExistsError(f"Output already exists: {OUT}")
    OUT.mkdir(parents=True)
    cards, l3_ids, embeddings, seeds, assignment, hold = load_inputs()
    included = sensitivity.evaluate(
        "HOLD included",
        embeddings,
        assignment,
        seeds,
    )
    excluded = sensitivity.evaluate(
        "HOLD excluded",
        embeddings[~hold],
        assignment[~hold],
        seeds,
    )
    summary = {
        "release_id": "v2.18.0-rc",
        "model": "BAAI/bge-m3",
        "seed": sensitivity.SEED,
        "scope": {
            "registered_ids": 1711,
            "active_cards": len(cards),
            "semantic_l3": len(l3_ids),
            "hold_cards": int(hold.sum()),
            "non_hold_cards": int((~hold).sum()),
        },
        "input_hashes": {
            "cards_json": sha256(RELEASE / "cards.json"),
            "hierarchy_json": sha256(RELEASE / "hierarchy.json"),
            "card_embeddings": sha256(
                EMBEDDING_ROOT / "card_embeddings.npy"
            ),
            "l3_seed_embeddings": sha256(
                SEED_ROOT / "l3_seed_embeddings.npy"
            ),
        },
        "conditions": [included, excluded],
    }
    (OUT / "sensitivity_results.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    fields = [
        "condition",
        "cards",
        "families",
        "em_iterations",
        "em_final_objective",
        "top1",
        "top2",
        "top3",
        "top5",
        "em_agreement",
        "ari",
        "nmi",
        "median_margin",
        "negative_margin_share",
        "mean_within_family_cosine",
        "permutation_p",
        "sigma_0.01_stability",
        "sigma_0.05_stability",
    ]
    with (OUT / "sensitivity_summary.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for result in (included, excluded):
            perturbation = {
                point["sigma"]: point["mean"]
                for point in result["perturbation"]
            }
            writer.writerow(
                {
                    "condition": result["condition"],
                    "cards": result["cards"],
                    "families": result["families"],
                    "em_iterations": result["em_iterations"],
                    "em_final_objective": result[
                        "em_final_objective"
                    ],
                    "top1": result["topk"]["1"],
                    "top2": result["topk"]["2"],
                    "top3": result["topk"]["3"],
                    "top5": result["topk"]["5"],
                    "em_agreement": result["em_agreement"],
                    "ari": result["ari"],
                    "nmi": result["nmi"],
                    "median_margin": result["median_margin"],
                    "negative_margin_share": result[
                        "negative_margin_share"
                    ],
                    "mean_within_family_cosine": result[
                        "mean_within_family_cosine"
                    ],
                    "permutation_p": result["permutation_p"],
                    "sigma_0.01_stability": perturbation[0.01],
                    "sigma_0.05_stability": perturbation[0.05],
                }
            )
    plot_comparison(included, excluded)
    print(
        json.dumps(
            {
                result["condition"]: {
                    "cards": result["cards"],
                    "em_iterations": result["em_iterations"],
                    "em_final_objective": result[
                        "em_final_objective"
                    ],
                    "top1": result["topk"]["1"],
                    "top5": result["topk"]["5"],
                    "sigma_0.05_stability": next(
                        point["mean"]
                        for point in result["perturbation"]
                        if point["sigma"] == 0.05
                    ),
                }
                for result in (included, excluded)
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
