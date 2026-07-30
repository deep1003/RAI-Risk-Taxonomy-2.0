#!/usr/bin/env python3
"""Re-run final v2.17.2 L4-to-L3 mapping and sensitivity validation.

The operational audit preserves the 189 released Physical AI assignments,
comprising 182 canonical Physical AI cards and seven conservatively migrated
global cards. It prevents other cards from entering Physical L3 families.
Sensitivity metrics include Physical AI in the overall population.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/data/releases/v2.17.2"
OUT = ROOT / "reports/validation/v2.17.2/full_mapping_sensitivity_bge_m3_20260724"
MODEL = (
    "/Users/deep1003/.cache/huggingface/hub/"
    "models--BAAI--bge-m3/snapshots/"
    "5617a9f61b028005a4858fdac845db406aefb181"
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mapping = load_module(
    "mapping_v2172",
    ROOT / "scripts/run_v2_17_2_bge_m3_active_reliability.py",
)
plots = load_module(
    "sensitivity_v2172",
    ROOT / "scripts/plot_v2_17_2_three_scope_sensitivity.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def semantic_l3(card: dict) -> str:
    primary = card.get("primary_l3_id") or ""
    if "HLD" in primary and card.get("hold_semantic_path"):
        return card["hold_semantic_path"]["l3_id"]
    if "HLD" in primary and card.get("previous_primary_l3_id"):
        return card["previous_primary_l3_id"]
    return primary


def encode(texts: list[str], path: Path) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL)
    model.max_seq_length = 256
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=24,
        show_progress_bar=True,
    ).astype("float32")
    np.save(path, vectors)
    return vectors


def write_summary_table(results: list[dict]) -> None:
    rows = []
    for result in results:
        rows.append(
            {
                "condition": result["condition"],
                "cards": result["cards"],
                "families": result["families"],
                "em_iterations": result["em_iterations"],
                "em_final_objective": result["em_final_objective"],
                "top1": result["topk"]["1"],
                "top2": result["topk"]["2"],
                "top3": result["topk"]["3"],
                "top5": result["topk"]["5"],
                "em_agreement": result["em_agreement"],
                "median_margin": result["median_margin"],
                "negative_margin_share": result["negative_margin_share"],
                "permutation_p": result["permutation_p"],
                "sigma_0.01_stability": next(
                    point["mean"]
                    for point in result["perturbation"]
                    if point["sigma"] == 0.01
                ),
                "sigma_0.05_stability": next(
                    point["mean"]
                    for point in result["perturbation"]
                    if point["sigma"] == 0.05
                ),
            }
        )
    with (OUT / "sensitivity_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cards_all = json.loads((SOURCE / "cards.json").read_text(encoding="utf-8"))[
        "cards"
    ]
    cards = [card for card in cards_all if card.get("status") == "active"]
    hierarchy = json.loads(
        (SOURCE / "hierarchy.json").read_text(encoding="utf-8")
    )["nodes"]
    semantic_l3_nodes = [
        node
        for node in hierarchy
        if node.get("level") == 3 and "HLD" not in node["node_id"]
    ]
    if len(cards) != 1660:
        raise ValueError(f"Expected 1,660 active cards, got {len(cards)}")
    if len(semantic_l3_nodes) != 50:
        raise ValueError(
            f"Expected 50 semantic L3 families, got {len(semantic_l3_nodes)}"
        )

    family_ids = [node["node_id"] for node in semantic_l3_nodes]
    family_index = {
        family_id: index for index, family_id in enumerate(family_ids)
    }
    current = np.array(
        [family_index[semantic_l3(card)] for card in cards], dtype=int
    )
    review = np.array(
        [bool(card.get("decision_required")) for card in cards], dtype=bool
    )
    physical_locked = np.array(
        [
            (card.get("primary_l3_id") or "").startswith("RAI3-P-")
            for card in cards
        ],
        dtype=bool,
    )
    physical_semantic = np.array(
        [(semantic_l3(card) or "").startswith("RAI3-P-") for card in cards],
        dtype=bool,
    )
    canonical_physical = np.array(
        [
            card.get("metrics_source") == "physical_ai_taxonomy_local_sync_v2.4"
            for card in cards
        ],
        dtype=bool,
    )
    if int(physical_locked.sum()) != 189:
        raise ValueError(
            f"Expected 189 released Physical cards, got {physical_locked.sum()}"
        )
    if int(canonical_physical.sum()) != 182:
        raise ValueError(
            "Expected 182 canonical Physical cards, "
            f"got {canonical_physical.sum()}"
        )

    card_texts = [mapping.card_text(card) for card in cards]
    seed_texts = [mapping.seed_text(node) for node in semantic_l3_nodes]
    card_embeddings = encode(card_texts, OUT / "card_embeddings.npy")
    seed_embeddings = encode(seed_texts, OUT / "l3_seed_embeddings.npy")

    audited, move_events = mapping.constrained_em_audit(
        cards,
        semantic_l3_nodes,
        family_ids,
        card_embeddings,
        seed_embeddings,
        current,
    )
    if np.any(audited[physical_locked] != current[physical_locked]):
        raise RuntimeError("Released Physical assignments changed")
    np.save(OUT / "released_assignment.npy", current)
    np.save(OUT / "audited_assignment.npy", audited)
    (OUT / "reassignment_events.json").write_text(
        json.dumps(move_events, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUT / "index.json").write_text(
        json.dumps(
            {
                "l4_ids": [card["l4_id"] for card in cards],
                "l3_ids": family_ids,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    pre_overall = plots.evaluate(
        "Released mapping, all active cards, Physical included",
        card_embeddings,
        current,
        seed_embeddings,
    )
    post_overall = plots.evaluate(
        "Audited mapping, all active cards, Physical included",
        card_embeddings,
        audited,
        seed_embeddings,
    )
    post_review_excluded = plots.evaluate(
        "Audited mapping, Review Set excluded, Physical included",
        card_embeddings[~review],
        audited[~review],
        seed_embeddings,
    )
    post_physical = plots.evaluate(
        "Released Physical AI cards only",
        card_embeddings[physical_locked],
        audited[physical_locked],
        seed_embeddings,
    )
    results = [
        pre_overall,
        post_overall,
        post_review_excluded,
        post_physical,
    ]

    plots.OUT = OUT
    plots.plot_condition(
        post_overall,
        "overall_physical_included",
        "Sensitivity analysis, all active L4 cards with Physical AI included",
        "#0072B2",
        None,
    )
    plots.plot_condition(
        post_review_excluded,
        "overall_review_excluded_physical_included",
        "Sensitivity analysis, Review Set excluded with Physical AI included",
        "#E69F00",
        "//",
    )
    plots.plot_condition(
        post_physical,
        "physical_released_only",
        "Sensitivity analysis, released Physical AI cards",
        "#009E73",
        None,
    )
    write_summary_table(results)

    final_moved = np.flatnonzero(audited != current)
    final_moves = [
        {
            "l4_id": cards[index]["l4_id"],
            "label_en": cards[index].get("label_en", ""),
            "from": family_ids[current[index]],
            "to": family_ids[audited[index]],
            "review_set": bool(review[index]),
        }
        for index in final_moved
    ]
    (OUT / "final_mapping_changes.json").write_text(
        json.dumps(final_moves, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = {
        "release": "v2.17.2",
        "model": "BAAI/bge-m3",
        "model_snapshot": MODEL,
        "seed": plots.SEED,
        "scope": (
            "1,660 active L4 cards and 50 semantic L3 families; "
            "189 released Physical AI assignments locked during operational "
            "audit: 182 canonical cards and seven conservatively migrated cards"
        ),
        "input_hashes": {
            "cards_json_sha256": sha256(SOURCE / "cards.json"),
            "hierarchy_json_sha256": sha256(SOURCE / "hierarchy.json"),
            "card_embeddings_sha256": sha256(OUT / "card_embeddings.npy"),
            "l3_seed_embeddings_sha256": sha256(
                OUT / "l3_seed_embeddings.npy"
            ),
        },
        "counts": {
            "registered_ids": len(cards_all),
            "active_cards": len(cards),
            "semantic_l3_families": len(family_ids),
            "review_set_cards": int(review.sum()),
            "non_review_cards": int((~review).sum()),
            "physical_released_cards": int(physical_locked.sum()),
            "physical_canonical_cards": int(canonical_physical.sum()),
            "physical_conservatively_migrated_cards": int(
                physical_locked.sum() - canonical_physical.sum()
            ),
            "physical_semantic_scope_cards": int(physical_semantic.sum()),
            "mapping_event_count": len(move_events),
            "mapping_event_unique_cards": len(
                {event["l4_id"] for event in move_events}
            ),
            "final_changed_cards": int(len(final_moved)),
        },
        "conditions": results,
    }
    (OUT / "full_mapping_sensitivity_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(OUT.relative_to(ROOT)),
                "counts": summary["counts"],
                "conditions": [
                    {
                        "condition": result["condition"],
                        "cards": result["cards"],
                        "em_iterations": result["em_iterations"],
                        "em_final_objective": result[
                            "em_final_objective"
                        ],
                        "top1": result["topk"]["1"],
                        "top5": result["topk"]["5"],
                        "sigma_0.05_stability": round(
                            next(
                                point["mean"]
                                for point in result["perturbation"]
                                if point["sigma"] == 0.05
                            ),
                            1,
                        ),
                    }
                    for result in results
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
