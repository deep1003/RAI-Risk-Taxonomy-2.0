#!/usr/bin/env python3
"""Build a conservative L4-to-source evidence ledger.

The source evidence is the MIT AI Risk Repository export, whose Description
field stores the source excerpt and whose DOI/URL fields identify the work.
This script only selects from journal articles, conference papers, and reports.
It does not alter taxonomy content or the public release.
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
SOURCE = Path("/Users/deep1003/data3/ai_risk_coevolution_1990_2026/02_raw/uploaded_20260611/AI_Risk_Database_lowest_level.csv")
WORK = ROOT / "projects/rai_risk_taxonomy_2_0_rebuild_20260826/11_golden_reference_enrichment"
OUTPUT = WORK / "L4_Golden_Reference_Candidates.csv"

ALLOWED_TYPES = {"Journal Article", "Conference Paper", "Report", "Technical Report", "Policy brief"}
TRUSTED_REPORT_TITLES = {
    "Artificial Intelligence Risk Management Framework: Generative Artificial  Intelligence Profile",
    "International AI Safety Report 2025",
    "International Scientific  Report on the Safety of  Advanced AI",
    "Frontier AI Risk Management Framework (v1.0)",
    "Future Risks of Frontier AI",
    "Capabilities and Risks from frontier AI",
    "AI Safety Governance Framework",
    "Advancing AI Governance: A Literature Review of Problems, Options, and Proposals",
    "Regulating under Uncertainty: Governance Options for Generative AI",
    "Emerging Risks and Mitigations for Public Chatbots: LILAC v1",
    "Cataloguing LLM Evaluations",
    "Generating Harms: Generative AI's Impact & Paths Forward",
    "Governing General Purpose AI: A Comprehensive Map of Unreliability, Misuse and Systemic Risks",
}
TOKEN_RE = re.compile(r"[a-z][a-z0-9-]{2,}")
STOP = {
    "about", "after", "against", "also", "among", "because", "been", "being", "between", "both",
    "could", "from", "have", "into", "more", "most", "other", "over", "such", "than", "that",
    "their", "there", "these", "they", "this", "through", "under", "using", "when", "where",
    "which", "while", "with", "would", "risk", "risks", "system", "systems", "artificial",
    "intelligence", "machine", "learning", "model", "models", "technology", "technologies", "may",
    "can", "cause", "causes", "causing", "result", "results", "include", "including", "related",
}


def tokens(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall((text or "").lower()) if t not in STOP]


def compact_quote(text: str, query_tokens: set[str], maximum_words: int = 24) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not sentences:
        sentences = [text]
    sentence = max(sentences, key=lambda s: (len(set(tokens(s)) & query_tokens), -len(s)))
    words = sentence.split()
    if len(words) <= maximum_words:
        return sentence
    positions = [i for i, word in enumerate(words) if tokens(word) and tokens(word)[0] in query_tokens]
    centre = positions[len(positions) // 2] if positions else maximum_words // 2
    start = max(0, min(len(words) - maximum_words, centre - maximum_words // 2))
    excerpt = " ".join(words[start:start + maximum_words]).strip(" ,;:")
    return ("… " if start else "") + excerpt + (" …" if start + maximum_words < len(words) else "")


def main() -> None:
    cards = json.loads(CARDS.read_text(encoding="utf-8"))["cards"]
    source = pd.read_csv(SOURCE, dtype=str).fillna("")
    source = source[source["Item type"].isin(ALLOWED_TYPES) & source["Description"].str.strip().ne("")].copy()
    report_mask = source["Item type"].isin({"Report", "Technical Report", "Policy brief"})
    source = source[~report_mask | source["SourceTitle"].isin(TRUSTED_REPORT_TITLES)].reset_index(drop=True)

    postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
    lengths, title_sets = [], []
    for i, row in source.iterrows():
        heading = f"{row['Risk category']} {row['Risk subcategory']}"
        heading_tokens = tokens(heading)
        body = heading_tokens * 5 + tokens(row["Description"])
        counts = Counter(body)
        lengths.append(sum(counts.values()))
        title_sets.append(set(heading_tokens))
        for token, frequency in counts.items():
            postings[token].append((i, frequency))

    n = len(source)
    avg_len = sum(lengths) / n
    rows = []
    for card in cards:
        query_text = " ".join([card["label_en"], card["definition_en"], " ".join(card.get("keywords_en", []))])
        query = Counter(tokens(query_text))
        query_set = set(query)
        scores: dict[int, float] = defaultdict(float)
        for token, qf in query.items():
            entries = postings.get(token, [])
            if not entries:
                continue
            idf = math.log(1 + (n - len(entries) + 0.5) / (len(entries) + 0.5))
            for i, frequency in entries:
                denominator = frequency + 1.2 * (0.25 + 0.75 * lengths[i] / avg_len)
                scores[i] += idf * frequency * 2.2 / denominator * (1 + 0.1 * min(qf, 3))
        ranked = []
        for i, score in scores.items():
            overlap = len(query_set & title_sets[i])
            score += 1.8 * overlap
            item_type = source.iloc[i]["Item type"]
            quality_bonus = 1.25 if item_type in {"Journal Article", "Conference Paper"} else 0.75
            ranked.append((score + quality_bonus, overlap, i))
        ranked.sort(reverse=True)
        for rank, (score, overlap, i) in enumerate(ranked[:12], 1):
            evidence = source.iloc[i]
            url = evidence["URL"].strip()
            if not url and evidence["DOI"].strip():
                url = "https://doi.org/" + evidence["DOI"].removeprefix("https://doi.org/")
            rows.append({
                "L4_ID": card["l4_id"], "L3_ID": card["primary_l3_id"],
                "L4_Title_ko": card["label_ko"], "L4_Title_en": card["label_en"],
                "candidate_rank": rank, "retrieval_score": round(score, 6), "heading_overlap": overlap,
                "source_ev_id": evidence["Ev_ID"], "source_risk_category": evidence["Risk category"],
                "source_risk_subcategory": evidence["Risk subcategory"], "source_excerpt_full": evidence["Description"],
                "direct_quote": compact_quote(evidence["Description"], query_set),
                "ref_title": evidence["SourceTitle"], "ref_authors": evidence["Authors (short)"],
                "ref_year": evidence["Year"].replace(".0", ""), "reference_type": evidence["Item type"],
                "doi": evidence["DOI"], "ref_url": url, "source_domain": evidence["Domain"],
                "source_subdomain": evidence["Sub-domain"],
            })
    WORK.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"cards={len(cards)} eligible_source_rows={len(source)} candidates={len(rows)}")
    print(OUTPUT)


if __name__ == "__main__":
    main()
