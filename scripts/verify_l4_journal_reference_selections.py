#!/usr/bin/env python3
"""Verify selected L4 journal references with Crossref and DOI resolution."""

from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "projects/rai_risk_taxonomy_2_0_rebuild_20260826/08_journal_reference_enrichment"
INPUT = WORK / "L4_Journal_Reference_Selections.csv"
OUTPUT = WORK / "L4_Journal_Reference_Verified.csv"
USER_AGENT = "RAI-Taxonomy-Research/1.0 (mailto:youngsam.dream@gmail.com)"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def crossref(doi: str) -> dict:
    url = f"https://api.crossref.org/works/{quote(doi, safe='')}"
    request = Request(url, headers={"User-Agent": USER_AGENT})
    return json.load(urlopen(request, timeout=30))["message"]


def resolver_status(doi: str) -> tuple[int, str]:
    url = f"https://doi.org/{doi}"
    request = Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        response = build_opener(NoRedirect).open(request, timeout=30)
        return response.status, response.headers.get("Location", "")
    except HTTPError as error:
        if 300 <= error.code < 400:
            return error.code, error.headers.get("Location", "")
        return error.code, ""


def first_author(message: dict) -> str:
    authors = message.get("author") or []
    if not authors:
        return "Unknown author"
    return authors[0].get("family") or authors[0].get("name") or "Unknown author"


def publication_year(message: dict) -> int:
    for field in ("published-print", "published-online", "published", "issued"):
        parts = (message.get(field) or {}).get("date-parts") or []
        if parts and parts[0]:
            return int(parts[0][0])
    raise ValueError("No publication year")


def main() -> None:
    selections = pd.read_csv(INPUT, dtype=str).fillna("")
    rows = []
    for row in selections.to_dict("records"):
        doi = row["doi"].lower().strip()
        message = crossref(doi)
        status, landing_page = resolver_status(doi)
        title = (message.get("title") or [""])[0]
        journal = (message.get("container-title") or [""])[0]
        year = publication_year(message)
        author = first_author(message)
        reference_type = message.get("type", "")
        verified = reference_type == "journal-article" and bool(title and journal) and 300 <= status < 400
        rows.append(
            {
                **row,
                "ref_label": f"{author} et al. {year}",
                "ref_url": f"https://doi.org/{doi}",
                "verified_title": title,
                "verified_journal": journal,
                "verified_year": year,
                "crossref_type": reference_type,
                "doi_resolver_status": status,
                "landing_page": landing_page,
                "verification_status": "PASS" if verified else "REJECT",
            }
        )
        time.sleep(0.08)
    result = pd.DataFrame(rows)
    result.to_csv(OUTPUT, index=False)
    print(result["verification_status"].value_counts().to_dict())
    if not result["verification_status"].eq("PASS").all():
        print(result.loc[result["verification_status"].ne("PASS"), ["L4_ID", "doi", "crossref_type", "doi_resolver_status"]])
        raise SystemExit(1)
    print(OUTPUT)


if __name__ == "__main__":
    main()
