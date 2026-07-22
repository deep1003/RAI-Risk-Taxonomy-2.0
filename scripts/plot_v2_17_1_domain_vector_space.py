#!/usr/bin/env python3
"""Plot v2.17.1 L4 cards in a two-dimensional embedding space.

The figure uses the pinned BGE-M3 card embeddings generated for v2.17.0.
Release v2.17.1 changes only seven routing decisions, not the card text, so
the embedding matrix remains valid for the v2.17.1 visualization.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize


ROOT = Path(__file__).resolve().parents[1]
RELEASE = "v2.17.1"
SOURCE_EMBEDDINGS = ROOT / "reports/validation/v2.17.0/audit_bge"
OUT_DIR = ROOT / f"reports/validation/{RELEASE}/vector_space"


PALETTE = {
    "General": "#3167D5",
    "Agentic": "#159276",
    "Physical": "#C63C30",
    "HOLD": "#D08A1D",
}


def load_cards() -> dict[str, dict]:
    data = json.loads((ROOT / f"public/data/releases/{RELEASE}/cards.json").read_text())
    return {card["l4_id"]: card for card in data["cards"]}


def classify(card: dict) -> str:
    if card.get("decision_required"):
        return "HOLD"
    l3_id = card.get("primary_l3_id") or ""
    if l3_id.startswith("RAI3-G-"):
        return "General"
    if l3_id.startswith("RAI3-A-"):
        return "Agentic"
    if l3_id.startswith("RAI3-P-"):
        return "Physical"
    return "HOLD"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index = json.loads((SOURCE_EMBEDDINGS / "index.json").read_text())
    l4_ids = index["l4_ids"]
    embeddings = np.load(SOURCE_EMBEDDINGS / "card_embeddings.npy")
    if embeddings.shape[0] != len(l4_ids):
        raise ValueError("Embedding row count does not match index length.")

    cards = load_cards()
    missing = sorted(set(l4_ids) - set(cards))
    if missing:
        raise ValueError(f"Missing cards in {RELEASE}: {missing[:5]}")

    groups = np.array([classify(cards[l4_id]) for l4_id in l4_ids])
    counts = Counter(groups)

    reducer = PCA(n_components=2, random_state=20260722)
    coords = reducer.fit_transform(normalize(embeddings))
    explained = reducer.explained_variance_ratio_

    summary = {
        "release_id": RELEASE,
        "embedding_source": "v2.17.0 BGE-M3 card_embeddings.npy",
        "method": "PCA on L2-normalized BGE-M3 embeddings, n_components=2, seed=20260722",
        "explained_variance_ratio": [round(float(x), 6) for x in explained],
        "counts": dict(counts),
        "files": {
            "pdf": str(OUT_DIR / "domain_hold_vector_space.pdf"),
            "png": str(OUT_DIR / "domain_hold_vector_space.png"),
            "coordinates": str(OUT_DIR / "domain_hold_vector_space_coordinates.csv"),
        },
    }
    (OUT_DIR / "domain_hold_vector_space_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2)
    )

    with (OUT_DIR / "domain_hold_vector_space_coordinates.csv").open("w") as f:
        f.write("l4_id,group,x,y\\n")
        for l4_id, group, (x, y) in zip(l4_ids, groups, coords):
            f.write(f"{l4_id},{group},{x:.8f},{y:.8f}\\n")

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.labelsize": 8,
            "axes.titlesize": 10,
            "legend.fontsize": 7,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "axes.linewidth": 0.6,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    fig, ax = plt.subplots(figsize=(7.2, 5.0), dpi=220)
    order = ["General", "Agentic", "Physical", "HOLD"]
    alpha = {"General": 0.62, "Agentic": 0.70, "Physical": 0.82, "HOLD": 0.55}
    size = {"General": 9, "Agentic": 12, "Physical": 18, "HOLD": 8}
    zorder = {"HOLD": 1, "General": 2, "Agentic": 3, "Physical": 4}

    for group in order:
        mask = groups == group
        ax.scatter(
            coords[mask, 0],
            coords[mask, 1],
            s=size[group],
            c=PALETTE[group],
            alpha=alpha[group],
            edgecolors="white",
            linewidths=0.18,
            zorder=zorder[group],
        )

    ax.set_title("Two-dimensional L4 risk-card vector space by release group", loc="left", pad=10)
    ax.set_xlabel(f"PC1 ({explained[0] * 100:.1f}% variance)")
    ax.set_ylabel(f"PC2 ({explained[1] * 100:.1f}% variance)")
    ax.grid(True, color="#E6E9EF", linewidth=0.45)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#9AA4B2")
    ax.spines["bottom"].set_color("#9AA4B2")

    handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=PALETTE[group],
            markeredgecolor="white",
            markeredgewidth=0.4,
            markersize=6,
            label=f"{group} ({counts[group]})",
        )
        for group in order
    ]
    ax.legend(handles=handles, loc="upper right", frameon=True, framealpha=0.95)

    note = (
        "L2-normalized BGE-M3 embeddings projected with PCA. HOLD is a review state, not a semantic family. "
        "Physical includes 182 locked source cards plus 7 conservative v2.17.1 transfers."
    )
    fig.text(0.02, 0.015, note, ha="left", va="bottom", fontsize=7, color="#4B5563")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT_DIR / "domain_hold_vector_space.pdf", bbox_inches="tight")
    fig.savefig(OUT_DIR / "domain_hold_vector_space.png", bbox_inches="tight")
    plt.close(fig)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
