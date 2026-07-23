#!/usr/bin/env python3
"""Build the static data payload for the RAI Risk Taxonomy Space page."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "public" / "data" / "releases" / "v2.17.2"
EMBED_DIR = ROOT / "reports" / "validation" / "v2.17.2" / "bge_m3_active"
OUTPUT = RELEASE_DIR / "risk_space.json"


DOMAIN_DISPLAY = {
    "RAI1-G": ("General-purpose AI", "범용 AI", "brain"),
    "RAI1-A": ("Agentic AI", "에이전틱 AI", "compass"),
    "RAI1-P": ("Physical AI", "피지컬 AI", "robot"),
}


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_num(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _path_for_card(card: dict, node_by_id: dict) -> dict:
    breadcrumb = card.get("breadcrumb") or []
    if len(breadcrumb) >= 4:
        l1_id = breadcrumb[1]["node_id"]
        l2_id = breadcrumb[2]["node_id"]
        l3_id = breadcrumb[3]["node_id"]
    else:
        l3_id = card.get("primary_l3_id")
        l3 = node_by_id.get(l3_id, {})
        l2_id = l3.get("parent_id")
        l2 = node_by_id.get(l2_id, {})
        l1_id = l2.get("parent_id")

    l1 = node_by_id.get(l1_id, {})
    l2 = node_by_id.get(l2_id, {})
    l3 = node_by_id.get(l3_id, {})
    domain_en, domain_ko, icon = DOMAIN_DISPLAY.get(
        l1_id,
        (l1.get("label_en", "Unknown"), l1.get("label_ko", ""), "circle"),
    )
    return {
        "l1_id": l1_id,
        "l1_label_en": domain_en,
        "l1_label_ko": domain_ko,
        "l1_icon": icon,
        "l2_id": l2_id,
        "l2_label_en": l2.get("label_en", ""),
        "l2_label_ko": l2.get("label_ko", ""),
        "l3_id": l3_id,
        "l3_label_en": l3.get("label_en", ""),
        "l3_label_ko": l3.get("label_ko", ""),
    }


def _semantic_review_path(card: dict) -> dict | None:
    path = card.get("hold_semantic_path")
    if not path:
        return None
    return {
        "l2_id": path.get("l2_id"),
        "l2_label_en": path.get("l2_label_en"),
        "l2_label_ko": path.get("l2_label_ko"),
        "l3_id": path.get("l3_id"),
        "l3_label_en": path.get("l3_label_en"),
        "l3_label_ko": path.get("l3_label_ko"),
    }


def _pca_2d(x: np.ndarray) -> np.ndarray:
    x = x.astype(np.float64, copy=False)
    centered = x - x.mean(axis=0, keepdims=True)
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    coords = centered @ vt[:2].T
    coords -= coords.mean(axis=0, keepdims=True)
    scale = np.percentile(np.abs(coords), 99, axis=0)
    scale[scale == 0] = 1
    coords = np.clip(coords / scale, -1.2, 1.2)
    return coords


def main() -> None:
    cards_payload = _load_json(RELEASE_DIR / "cards.json")
    hierarchy = _load_json(RELEASE_DIR / "hierarchy.json")
    index = _load_json(EMBED_DIR / "index.json")
    embeddings = np.load(EMBED_DIR / "card_embeddings.npy")

    all_cards = cards_payload["cards"]
    active_cards = [card for card in all_cards if card.get("status") == "active"]
    card_by_id = {card["l4_id"]: card for card in active_cards}
    node_by_id = {node["node_id"]: node for node in hierarchy["nodes"]}

    l4_ids = index["l4_ids"]
    active_ids = [l4_id for l4_id in l4_ids if l4_id in card_by_id]
    if len(active_ids) != len(active_cards):
        missing = sorted(set(card_by_id) - set(active_ids))[:10]
        raise RuntimeError(f"Embedding index does not cover active cards. Missing examples: {missing}")

    rows = [l4_ids.index(l4_id) for l4_id in active_ids]
    coords = _pca_2d(embeddings[rows])

    points = []
    domain_counts = Counter()
    l2_counts = Counter()
    l3_counts = Counter()
    hold_count = 0

    for l4_id, xy in zip(active_ids, coords):
        card = card_by_id[l4_id]
        path = _path_for_card(card, node_by_id)
        decision_required = bool(card.get("decision_required"))
        hold_count += int(decision_required)
        domain_counts[path["l1_label_en"]] += 1
        l2_counts[path["l2_label_en"]] += 1
        l3_counts[path["l3_label_en"]] += 1
        points.append(
            {
                "id": l4_id,
                "label_en": card.get("label_en", ""),
                "label_ko": card.get("label_ko", ""),
                "definition_en": card.get("definition_en", ""),
                "definition_ko": card.get("definition_ko", ""),
                "x": round(float(xy[0]), 6),
                "y": round(float(xy[1]), 6),
                "path": path,
                "semantic_review_path": _semantic_review_path(card),
                "decision_required": decision_required,
                "review_status": card.get("review_status"),
                "severity": _safe_num(card.get("severity_1to5")),
                "probability": _safe_num(card.get("probability_0to1")),
                "impact": _safe_num(card.get("impact_score")),
                "references_count": len(card.get("references") or []),
                "references": [
                    {
                        "title": ref.get("title", ""),
                        "url": ref.get("url", ""),
                        "type": ref.get("type", ""),
                    }
                    for ref in (card.get("references") or [])[:3]
                ],
            }
        )

    metadata = {
        "title": "RAI Risk Taxonomy Space",
        "release_id": "v2.17.2",
        "projection": "BGE-M3 card embeddings projected by deterministic PCA",
        "registered_ids": len(all_cards),
        "active_cards": len(active_cards),
        "merged_records": sum(1 for card in all_cards if card.get("status") == "retired"),
        "hold_cards": hold_count,
        "domains": dict(sorted(domain_counts.items())),
        "l2_counts": dict(sorted(l2_counts.items())),
        "l3_count": len(l3_counts),
    }
    payload = {"metadata": metadata, "points": points}
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
