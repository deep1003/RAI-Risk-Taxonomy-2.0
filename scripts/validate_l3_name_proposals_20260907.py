#!/usr/bin/env python3
"""Validate the L3 before/after glossary section and its audit files."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    glossary = (ROOT / "glossary.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(glossary, "html.parser")
    section = soup.select_one("#L3NAMES")
    assert section is not None, "L3 proposal section is missing"
    assert len(section.select("tbody tr")) == 47, "HTML must contain all 47 L3 rows"
    assert soup.select_one(".letterbar a").get("href") == "#L3NAMES"
    assert soup.select_one("#list > .letter").get_text(strip=True) == "A"

    payload = json.loads(
        (ROOT / "data/glossary/l3_name_proposals_20260907.json").read_text(encoding="utf-8")
    )
    assert payload["master_changed"] is False
    assert len(payload["items"]) == 47
    assert len({item["L3_ID"] for item in payload["items"]}) == 47

    with (ROOT / "data/glossary/l3_name_proposals_20260907.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        csv_rows = list(csv.DictReader(handle))
    assert len(csv_rows) == 47
    assert [row["L3_ID"] for row in csv_rows] == [item["L3_ID"] for item in payload["items"]]

    changed = sum(item["status"] == "개정 제안" for item in payload["items"])
    retained = sum(item["status"] == "유지" for item in payload["items"])
    assert changed + retained == 47
    print(f"L3_NAME_PROPOSALS_PASS total=47 changed={changed} retained={retained}")


if __name__ == "__main__":
    main()
