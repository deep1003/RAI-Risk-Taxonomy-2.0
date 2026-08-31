#!/usr/bin/env python3
"""Validate L4 reference candidates against OpenAlex journal metadata."""

from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "projects/rai_risk_taxonomy_2_0_rebuild_20260826/08_journal_reference_enrichment"
INPUT = WORK / "L4_Journal_Reference_Candidates.csv"
OUTPUT = WORK / "L4_Journal_Reference_Candidates_OpenAlex.csv"
USER_AGENT = "RAI-Taxonomy-Research/1.0 (mailto:youngsam.dream@gmail.com)"


def reconstruct_abstract(index: dict | None) -> str:
    if not index:
        return ""
    length = max(position for positions in index.values() for position in positions) + 1
    words = [""] * length
    for word, positions in index.items():
        for position in positions:
            words[position] = word
    return " ".join(words)


def fetch_batch(dois: list[str]) -> dict[str, dict]:
    values = "|".join(f"https://doi.org/{doi}" for doi in dois)
    url = (
        "https://api.openalex.org/works?filter=doi:"
        + quote(values, safe="|:/")
        + f"&per-page={len(dois)}&mailto=youngsam.dream@gmail.com"
    )
    for attempt in range(5):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            payload = json.load(urlopen(request, timeout=60))
            return {
                work["doi"].lower().removeprefix("https://doi.org/"): work
                for work in payload["results"]
                if work.get("doi")
            }
        except Exception:
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)
    return {}


def main() -> None:
    frame = pd.read_csv(INPUT, dtype=str).fillna("")
    dois = sorted(
        {
            value.lower().removeprefix("https://doi.org/").strip()
            for value in frame["doi"]
            if value.strip()
        }
    )
    metadata: dict[str, dict] = {}
    for start in range(0, len(dois), 50):
        metadata.update(fetch_batch(dois[start : start + 50]))
        time.sleep(0.12)

    rows = []
    for row in frame.to_dict("records"):
        doi = row["doi"].lower().removeprefix("https://doi.org/").strip()
        work = metadata.get(doi, {})
        location = work.get("primary_location") or {}
        source = location.get("source") or {}
        row.update(
            {
                "openalex_found": bool(work),
                "openalex_title": work.get("title", ""),
                "openalex_abstract": reconstruct_abstract(work.get("abstract_inverted_index")),
                "openalex_type": work.get("type", ""),
                "openalex_year": work.get("publication_year", ""),
                "openalex_cited_by_count": work.get("cited_by_count", ""),
                "openalex_is_retracted": work.get("is_retracted", ""),
                "openalex_journal": source.get("display_name", ""),
                "openalex_source_type": source.get("type", ""),
                "openalex_source_is_core": source.get("is_core", ""),
                "openalex_landing_page": location.get("landing_page_url", ""),
            }
        )
        rows.append(row)
    pd.DataFrame(rows).to_csv(OUTPUT, index=False)
    print(f"unique candidate DOIs: {len(dois)}")
    print(f"OpenAlex resolved: {len(metadata)}")
    print(OUTPUT)


if __name__ == "__main__":
    main()
