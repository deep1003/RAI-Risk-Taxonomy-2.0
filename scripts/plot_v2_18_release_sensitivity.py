#!/usr/bin/env python3
"""Render the v2.18.0-rc sensitivity results with release-focused labels."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RESULTS = (
    ROOT
    / "reports"
    / "validation"
    / "v2.18.0-rc"
    / "hold_sensitivity_bge_m3"
    / "sensitivity_results.json"
)
OUTPUT = RESULTS.parent


def render() -> None:
    payload = json.loads(RESULTS.read_text(encoding="utf-8"))
    included, excluded = payload["conditions"]
    series = (
        (included, "#1668B2", "o", "-", "All active cards"),
        (excluded, "#E67E00", "s", "--", "Released subset"),
    )

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
        "Release assignment sensitivity",
        x=0.025,
        y=0.98,
        ha="left",
        fontsize=15,
        fontweight="bold",
    )

    ax = axes[0]
    for result, color, marker, linestyle, label in series:
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
    for offset, item, hatch in (
        (-width / 2, series[0], None),
        (width / 2, series[1], "//"),
    ):
        result, color, _marker, _linestyle, label = item
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
    for result, color, marker, linestyle, label in series:
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

    for ax in axes:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.text(
        0.025,
        0.015,
        "BGE-M3, 54 semantic L3 families. All active cards: n=1,660; "
        "released subset: n=1,046. Shaded bands show 95% intervals "
        "across 200 perturbation repeats.",
        fontsize=8.4,
        color="#667085",
    )
    fig.tight_layout(rect=(0.02, 0.06, 0.995, 0.93))
    for suffix, options in (
        ("png", {"dpi": 220}),
        ("pdf", {}),
    ):
        fig.savefig(
            OUTPUT / f"release_assignment_sensitivity_3panel.{suffix}",
            bbox_inches="tight",
            facecolor="white",
            **options,
        )
    plt.close(fig)


if __name__ == "__main__":
    render()
