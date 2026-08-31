#!/usr/bin/env python3
"""Build conservative journal-article candidates for current L4 cards.

This script does not alter release data. It retrieves candidates from the
frozen local scholarly corpus using BM25-style lexical matching. Subsequent
DOI, venue, and conceptual-fit validation is required before attachment.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "public/data/releases/RAI-Risk-Taxonomy-2.0-master/cards.json"
CORPUS = Path(
    "/Users/deep1003/data3/integrated_ai_document_space_20260704/papers/"
    "physical_ai_risks/physical_ai_risks_papers_integrated_dedup.csv.gz"
)
OUTPUT = (
    ROOT
    / "projects/rai_risk_taxonomy_2_0_rebuild_20260826/08_journal_reference_enrichment"
    / "L4_Journal_Reference_Candidates.csv"
)

TOKEN_RE = re.compile(r"[a-z][a-z0-9-]{2,}")
STOPWORDS = {
    "about", "after", "against", "also", "among", "because", "been", "being",
    "between", "both", "could", "from", "have", "into", "more", "most", "other",
    "over", "such", "than", "that", "their", "there", "these", "they", "this",
    "through", "under", "using", "when", "where", "which", "while", "with", "would",
    "risk", "risks", "system", "systems", "artificial", "intelligence", "machine",
    "learning", "model", "models", "data", "technology", "technologies", "result",
    "results", "study", "paper", "analysis", "based", "may", "can", "use", "used",
}


def tokens(text: str) -> list[str]:
    return [token for token in TOKEN_RE.findall(text.lower()) if token not in STOPWORDS]


def main() -> None:
    cards = json.loads(CARDS.read_text(encoding="utf-8"))["cards"]
    columns = ["title", "abstract", "year", "publication_source", "doi", "url", "citation_count"]
    papers = pd.read_csv(CORPUS, usecols=columns, dtype=str).fillna("")
    papers = papers[papers["doi"].str.strip().ne("")].reset_index(drop=True)

    postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
    lengths: list[int] = []
    title_tokens: list[set[str]] = []
    for index, row in papers.iterrows():
        title = tokens(row["title"])
        body = title * 3 + tokens(row["abstract"])
        counts = Counter(body)
        lengths.append(sum(counts.values()))
        title_tokens.append(set(title))
        for token, frequency in counts.items():
            postings[token].append((index, frequency))

    average_length = sum(lengths) / len(lengths)
    document_count = len(papers)
    rows: list[dict] = []
    for card in cards:
        query_text = " ".join(
            [
                card["label_en"],
                card["definition_en"],
                " ".join(card.get("keywords_en", [])),
            ]
        )
        query = Counter(tokens(query_text))
        scores: dict[int, float] = defaultdict(float)
        query_set = set(query)
        for token, query_frequency in query.items():
            entries = postings.get(token, [])
            if not entries:
                continue
            inverse_document_frequency = math.log(
                1 + (document_count - len(entries) + 0.5) / (len(entries) + 0.5)
            )
            for index, frequency in entries:
                denominator = frequency + 1.2 * (0.25 + 0.75 * lengths[index] / average_length)
                scores[index] += inverse_document_frequency * frequency * 2.2 / denominator

        ranked = []
        for index, score in scores.items():
            title_overlap = len(query_set & title_tokens[index])
            if title_overlap:
                score += 1.25 * title_overlap
            ranked.append((score, title_overlap, index))
        ranked.sort(reverse=True)

        for rank, (score, title_overlap, index) in enumerate(ranked[:5], start=1):
            paper = papers.iloc[index]
            rows.append(
                {
                    "L4_ID": card["l4_id"],
                    "L3_ID": card["primary_l3_id"],
                    "L4_Title_en": card["label_en"],
                    "candidate_rank": rank,
                    "retrieval_score": round(score, 6),
                    "title_token_overlap": title_overlap,
                    "paper_title": paper["title"],
                    "abstract": paper["abstract"],
                    "year": paper["year"],
                    "journal": paper["publication_source"],
                    "doi": paper["doi"],
                    "url": f"https://doi.org/{paper['doi'].removeprefix('https://doi.org/')}",
                    "citation_count_local": paper["citation_count"],
                }
            )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUTPUT, index=False)
    print(f"cards: {len(cards)}")
    print(f"DOI-bearing local papers: {len(papers)}")
    print(f"candidate rows: {len(rows)}")
    print(OUTPUT)


if __name__ == "__main__":
    main()
