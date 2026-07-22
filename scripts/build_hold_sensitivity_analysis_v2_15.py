#!/usr/bin/env python3
"""Build the v2.15 HOLD sensitivity comparison figure and summary."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
INCLUDED = ROOT / "reports/validation/v2.14.0/reliability/reliability_summary.json"
EXCLUDED = ROOT / "reports/validation/v2.15.0/non_hold_reliability/reliability_summary.json"
OUT = ROOT / "reports/validation/v2.15.0/hold_sensitivity"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def pct(value: float) -> float:
    return float(value) * 100.0


def topk(summary: dict, k: int) -> float:
    return pct(summary["published_assignment_geometry"]["top_k_containment"][f"top_{k}"])


def trace_xy(summary: dict) -> tuple[list[int], list[float]]:
    trace = summary["em"]["trace"]
    return [row["iteration"] for row in trace], [float(row["objective"]) for row in trace]


def perturbation_xy(summary: dict) -> tuple[list[float], list[float], list[float], list[float]]:
    rows = summary["embedding_perturbation"]
    x = [float(row["sigma"]) for row in rows]
    y = [pct(row["mean_agreement"]) for row in rows]
    low = [pct(row["ci95_low"]) for row in rows]
    high = [pct(row["ci95_high"]) for row in rows]
    return x, y, low, high


def build_summary(hold_included: dict, hold_excluded: dict) -> dict:
    included_top = hold_included["published_assignment_geometry"]["top_k_containment"]
    excluded_top = hold_excluded["published_assignment_geometry"]["top_k_containment"]
    included_pert = {row["sigma"]: row for row in hold_included["embedding_perturbation"]}
    excluded_pert = {row["sigma"]: row for row in hold_excluded["embedding_perturbation"]}
    return {
        "release_id": "v2.15.0",
        "analysis": "HOLD sensitivity analysis",
        "conditions": {
            "hold_included": {
                "source_release": hold_included["release_id"],
                "cards": hold_included["population"]["cards"],
                "hold_cards": hold_included["population"]["decision_required"],
                "semantic_l3_families": hold_included["population"]["active_l3"],
            },
            "hold_excluded": {
                "source_release": hold_excluded["release_id"],
                "cards": hold_excluded["population"]["assessed_non_hold_cards"],
                "excluded_hold_cards": hold_excluded["population"]["excluded_hold_cards"],
                "semantic_l3_families": hold_excluded["population"]["semantic_l3_families"],
            },
        },
        "method_controls": {
            "encoder": hold_excluded["encoder"],
            "seed": hold_excluded["seed"],
            "permutations": hold_excluded["label_permutation_test"]["permutations"],
            "perturbation_repeats": 200,
            "l3_review_nodes_excluded_from_centroids": True,
        },
        "metrics": {
            "em_iterations_to_fixed_point": {
                "hold_included": hold_included["em"]["iterations_to_fixed_point"],
                "hold_excluded": hold_excluded["em"]["iterations_to_fixed_point"],
            },
            "em_objective_end": {
                "hold_included": hold_included["em"]["objective_end"],
                "hold_excluded": hold_excluded["em"]["objective_end"],
            },
            "em_release_agreement": {
                "hold_included": hold_included["em"]["exact_assignment_agreement"],
                "hold_excluded": hold_excluded["em"]["exact_assignment_agreement"],
                "delta_percentage_points": pct(
                    hold_excluded["em"]["exact_assignment_agreement"]
                    - hold_included["em"]["exact_assignment_agreement"]
                ),
            },
            "top_k_containment": {
                f"top_{k}": {
                    "hold_included": included_top[f"top_{k}"],
                    "hold_excluded": excluded_top[f"top_{k}"],
                    "delta_percentage_points": pct(excluded_top[f"top_{k}"] - included_top[f"top_{k}"]),
                }
                for k in (1, 2, 3, 5)
            },
            "perturbation_agreement": {
                f"sigma_{sigma:g}": {
                    "hold_included": included_pert[sigma]["mean_agreement"],
                    "hold_excluded": excluded_pert[sigma]["mean_agreement"],
                    "delta_percentage_points": pct(
                        excluded_pert[sigma]["mean_agreement"] - included_pert[sigma]["mean_agreement"]
                    ),
                }
                for sigma in (0.01, 0.05)
            },
        },
        "interpretation": (
            "HOLD exclusion improves the conditional non-HOLD geometry across all three diagnostics. "
            "This is a selection sensitivity result, not a same-population accuracy estimate."
        ),
    }


def draw_figure(hold_included: dict, hold_excluded: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 8,
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.7,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    blue = "#0072B2"
    orange = "#D55E00"
    grey = "#6B6B6B"
    light_blue = "#D8EAF7"
    light_orange = "#F7DCCF"

    fig, axes = plt.subplots(1, 3, figsize=(11.6, 3.65))
    fig.patch.set_facecolor("white")

    inc_x, inc_y = trace_xy(hold_included)
    exc_x, exc_y = trace_xy(hold_excluded)
    axes[0].plot(inc_x, inc_y, color=blue, marker="o", markersize=3, linewidth=1.6, label="HOLD included")
    axes[0].plot(
        exc_x,
        exc_y,
        color=orange,
        marker="s",
        markersize=3,
        linewidth=1.6,
        linestyle="--",
        label="HOLD excluded",
    )
    axes[0].set_title("a  EM convergence")
    axes[0].set_xlabel("Iteration")
    axes[0].set_ylabel("Mean cosine objective")
    axes[0].set_xlim(1, max(max(inc_x), max(exc_x)))
    axes[0].set_ylim(0.64, 0.815)
    axes[0].grid(axis="y", color="#D9D9D9", linewidth=0.5)
    axes[0].legend(frameon=False, loc="lower right")

    ks = [1, 2, 3, 5]
    pos = np.arange(len(ks))
    width = 0.36
    included_vals = [topk(hold_included, k) for k in ks]
    excluded_vals = [topk(hold_excluded, k) for k in ks]
    axes[1].bar(pos - width / 2, included_vals, width, color=light_blue, edgecolor=blue, linewidth=1.0)
    axes[1].bar(pos + width / 2, excluded_vals, width, color=light_orange, edgecolor=orange, linewidth=1.0, hatch="//")
    axes[1].set_title("b  Top-k containment")
    axes[1].set_xlabel("Released L3 within top-k centroids")
    axes[1].set_ylabel("Cards contained (%)")
    axes[1].set_xticks(pos)
    axes[1].set_xticklabels([str(k) for k in ks])
    axes[1].set_ylim(0, 105)
    axes[1].grid(axis="y", color="#D9D9D9", linewidth=0.5)
    for x_pos, val in zip(pos - width / 2, included_vals):
        axes[1].text(x_pos, val + 1.5, f"{val:.1f}", ha="center", va="bottom", fontsize=6.5, color=grey)
    for x_pos, val in zip(pos + width / 2, excluded_vals):
        axes[1].text(x_pos, val + 1.5, f"{val:.1f}", ha="center", va="bottom", fontsize=6.5, color=grey)

    inc_s, inc_m, inc_l, inc_h = perturbation_xy(hold_included)
    exc_s, exc_m, exc_l, exc_h = perturbation_xy(hold_excluded)
    axes[2].plot(inc_s, inc_m, color=blue, marker="o", markersize=3, linewidth=1.6, label="HOLD included")
    axes[2].fill_between(inc_s, inc_l, inc_h, color=blue, alpha=0.12, linewidth=0)
    axes[2].plot(
        exc_s,
        exc_m,
        color=orange,
        marker="s",
        markersize=3,
        linewidth=1.6,
        linestyle="--",
        label="HOLD excluded",
    )
    axes[2].fill_between(exc_s, exc_l, exc_h, color=orange, alpha=0.12, linewidth=0)
    axes[2].set_title("c  Assignment stability")
    axes[2].set_xlabel("Gaussian perturbation sigma")
    axes[2].set_ylabel("Agreement with unperturbed assignment (%)")
    axes[2].set_ylim(0, 105)
    axes[2].set_xlim(0, 0.6)
    axes[2].grid(axis="y", color="#D9D9D9", linewidth=0.5)
    axes[2].legend(frameon=False, loc="upper right")

    for ax in axes:
        ax.tick_params(length=3)

    fig.tight_layout(w_pad=2.0)
    fig.savefig(OUT / "hold_sensitivity_analysis.pdf", bbox_inches="tight")
    fig.savefig(OUT / "hold_sensitivity_analysis.png", dpi=240, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    hold_included = load_json(INCLUDED)
    hold_excluded = load_json(EXCLUDED)
    summary = build_summary(hold_included, hold_excluded)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "hold_sensitivity_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    draw_figure(hold_included, hold_excluded)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
