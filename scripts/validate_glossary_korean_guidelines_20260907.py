#!/usr/bin/env python3
"""Validate the Korean-guideline glossary update without network access."""

from __future__ import annotations

import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GlossaryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.terms: list[dict[str, str]] = []
        self._term: dict[str, str] | None = None
        self._field: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "article" and "term" in classes:
            self._term = {"cat": attributes.get("data-cat") or ""}
        elif self._term is not None and tag == "h3":
            self._field = "en"
        elif self._term is not None and tag == "span" and "ko" in classes:
            self._field = "ko"
        elif self._term is not None and tag == "p" and "def--en" in classes:
            self._field = "definition_en"
        elif self._term is not None and tag == "p" and "def--ko" in classes:
            self._field = "definition_ko"
        elif self._term is not None and tag == "a" and "href" in attributes:
            self._term["source_url"] = attributes["href"] or ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "article" and self._term is not None:
            self.terms.append(self._term)
            self._term = None
            self._field = None
        elif tag in {"h3", "span", "p"}:
            self._field = None

    def handle_data(self, data: str) -> None:
        if self._term is not None and self._field:
            self._term[self._field] = self._term.get(self._field, "") + data


def main() -> None:
    glossary = (ROOT / "glossary.html").read_text(encoding="utf-8")
    payload = json.loads((ROOT / "data/glossary/korean_guideline_terms_20260907.json").read_text(encoding="utf-8"))
    parser = GlossaryParser()
    parser.feed(glossary)

    assert len(parser.terms) == 379
    assert Counter(item["cat"] for item in parser.terms) == Counter({"risk": 154, "law": 123, "gen": 102})
    titles = [item.get("en", "").strip() for item in parser.terms]
    assert len(titles) == len(set(titles))
    assert titles == sorted(titles, key=str.casefold)
    assert all(item.get(field, "").strip() for item in parser.terms for field in ("en", "ko", "definition_en", "definition_ko", "source_url"))

    expected = payload["new_terms"] + payload["updated_terms"]
    indexed = {item["en"].strip(): item for item in parser.terms}
    for item in expected:
        rendered = indexed[item["en"]]
        assert rendered["ko"].strip() == item["ko"]
        assert rendered["definition_en"].strip() == item["definition_en"]
        assert rendered["definition_ko"].strip() == item["definition_ko"]
        assert rendered["source_url"] == item["source_url"]

    for label, count in (("전체", 379), ("일반", 102), ("리스크·보안", 154), ("법·제도", 123)):
        assert re.search(fr">{re.escape(label)} {count}</button>", glossary)
    assert "379 terms · 한·영 · A–Z · HTML" in (ROOT / "index.html").read_text(encoding="utf-8")
    print("GLOSSARY_KOREAN_GUIDELINES_PASS terms=379 new=56 updated=1 sources=7")


if __name__ == "__main__":
    main()
