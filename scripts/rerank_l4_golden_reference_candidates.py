#!/usr/bin/env python3
"""Rerank trustworthy L4 evidence candidates with BGE-M3 semantic similarity."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "projects/rai_risk_taxonomy_2_0_rebuild_20260826/11_golden_reference_enrichment"
INPUT = WORK / "L4_Golden_Reference_Candidates.csv"
OUTPUT = WORK / "L4_Golden_Reference_Candidates_Reranked.csv"
MODEL = Path("/Users/deep1003/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181")


def main() -> None:
    frame = pd.read_csv(INPUT, dtype=str).fillna("")
    card_text = (
        frame["L4_Title_en"] + ". "
        + frame.groupby("L4_ID")["L4_ID"].transform(lambda _: "")
    )
    # Definitions are read from the current release to avoid losing mechanism
    # and adverse-outcome terms that are absent from short titles.
    import json
    payload = json.loads((ROOT / "public/data/releases/RAI-Risk-Taxonomy-2.0-master/cards.json").read_text(encoding="utf-8"))
    definitions = {card["l4_id"]: card["definition_en"] for card in payload["cards"]}
    query_by_id = {
        l4: f"{group.iloc[0]['L4_Title_en']}. {definitions[l4]}"
        for l4, group in frame.groupby("L4_ID", sort=False)
    }
    evidence_by_id = {
        ev: f"{group.iloc[0]['source_risk_category']}. {group.iloc[0]['source_risk_subcategory']}. {group.iloc[0]['source_excerpt_full']}"
        for ev, group in frame.groupby("source_ev_id", sort=False)
    }

    model = SentenceTransformer(str(MODEL), local_files_only=True, device="cpu")
    query_ids = list(query_by_id)
    evidence_ids = list(evidence_by_id)
    query_matrix = model.encode(list(query_by_id.values()), batch_size=24, normalize_embeddings=True, show_progress_bar=True)
    evidence_matrix = model.encode(list(evidence_by_id.values()), batch_size=24, normalize_embeddings=True, show_progress_bar=True)
    query_lookup = dict(zip(query_ids, query_matrix))
    evidence_lookup = dict(zip(evidence_ids, evidence_matrix))
    query_embeddings = np.stack([query_lookup[l4] for l4 in frame["L4_ID"]])
    evidence_embeddings = np.stack([evidence_lookup[ev] for ev in frame["source_ev_id"]])
    cosine = np.sum(query_embeddings * evidence_embeddings, axis=1)
    lexical = pd.to_numeric(frame["retrieval_score"], errors="coerce").fillna(0).to_numpy()
    lexical = np.log1p(lexical)
    lexical = (lexical - lexical.min()) / max(lexical.max() - lexical.min(), 1e-9)
    frame["semantic_similarity"] = cosine.round(6)
    frame["combined_score"] = (0.9 * cosine + 0.1 * lexical).round(6)
    frame = frame.sort_values(["L4_ID", "combined_score"], ascending=[True, False], kind="stable")
    frame["semantic_rank"] = frame.groupby("L4_ID").cumcount() + 1
    frame.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    selected = frame[frame["semantic_rank"].eq(1)]
    print(f"selected={len(selected)} mean={selected.semantic_similarity.mean():.4f} min={selected.semantic_similarity.min():.4f}")
    print(OUTPUT)


if __name__ == "__main__":
    main()
