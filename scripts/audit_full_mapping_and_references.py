#!/usr/bin/env python3
"""Audit every published L4 mapping and reference without changing release data."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import ssl
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rai_taxonomy.codebook import CLASSIFICATION_RULES  # noqa: E402
DEFAULT_RELEASE = "v2.6.0"
USER_AGENT = (
    "Mozilla/5.0 (compatible; RAI-Taxonomy-Reference-Audit/2.0; "
    "+https://deep1003.github.io/RAI-Risk-Taxonomy-2.0/)"
)
MAX_BODY_BYTES = 262_144
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
    "into", "is", "of", "on", "or", "the", "to", "using", "with", "ai",
    "artificial", "intelligence", "risk", "risks", "pdf", "www",
}


class TitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.title_parts: list[str] = []
        self.meta_titles: list[str] = []
        self.authors: list[str] = []
        self.published_year = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): (value or "") for key, value in attrs}
        if tag.lower() == "title":
            self.in_title = True
        if tag.lower() == "meta":
            key = (values.get("name") or values.get("property") or "").lower()
            if key in {"citation_title", "dc.title", "dcterms.title", "og:title", "twitter:title"}:
                content = values.get("content", "").strip()
                if content:
                    self.meta_titles.append(content)
            if key in {"citation_author", "dc.creator", "dcterms.creator", "author"}:
                content = values.get("content", "").strip()
                if content:
                    self.authors.append(content)
            if key in {"citation_date", "citation_publication_date", "dc.date", "dcterms.date", "article:published_time"}:
                match = re.search(r"(?:19|20)\d{2}", values.get("content", ""))
                if match and not self.published_year:
                    self.published_year = match.group(0)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)

    @property
    def best_title(self) -> str:
        if self.meta_titles:
            return normalize_space(self.meta_titles[0])
        return normalize_space(" ".join(self.title_parts))


@dataclass
class UrlResult:
    url: str
    status_class: str
    http_status: int | None
    final_url: str
    content_type: str
    page_title: str
    title_source: str
    authors: str
    published_year: str
    error: str
    elapsed_seconds: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", default=DEFAULT_RELEASE)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = columns or (list(rows[0]) if rows else [])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)


def normalize_space(value: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def normalize_key(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "").casefold()
    return re.sub(r"[^\w]+", " ", text).strip()


def title_tokens(value: str | None) -> set[str]:
    return {
        token for token in normalize_key(value).split()
        if len(token) >= 3 and token not in STOPWORDS
    }


def title_similarity(cited: str, observed: str) -> float | None:
    left, right = title_tokens(cited), title_tokens(observed)
    if not left or not right:
        return None
    return round(len(left & right) / len(left | right), 6)


def extract_pdf_title(data: bytes) -> str:
    match = re.search(rb"/Title\s*\((.{1,500}?)\)", data, flags=re.DOTALL)
    if not match:
        return ""
    raw = re.sub(rb"\\([()\\])", rb"\1", match.group(1))
    return normalize_space(raw.decode("utf-8", errors="replace"))


def arxiv_abstract_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.lower() not in {"arxiv.org", "www.arxiv.org"}:
        return url
    match = re.search(r"/(?:pdf|abs)/([^/?#]+?)(?:\.pdf)?$", parsed.path)
    if not match:
        return url
    return f"https://arxiv.org/abs/{match.group(1)}"


def registry_metadata_endpoint(url: str) -> tuple[str, str] | None:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    if host in {"doi.org", "dx.doi.org"}:
        doi = urllib.parse.unquote(parsed.path.lstrip("/")).replace("\\_", "_")
        return f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='')}", "crossref"
    if host == "openalex.org" and re.fullmatch(r"/W\d+/?", parsed.path):
        work_id = parsed.path.strip("/")
        return f"https://api.openalex.org/works/{work_id}", "openalex"
    return None


def fetch_registry_metadata(url: str, timeout: float) -> tuple[str, str, list[str], str]:
    endpoint = registry_metadata_endpoint(url)
    if not endpoint:
        return "", "", [], ""
    metadata_url, source = endpoint
    request = urllib.request.Request(
        metadata_url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read(MAX_BODY_BYTES).decode("utf-8"))
        if source == "crossref":
            message = payload.get("message", {})
            titles = message.get("title", [])
            authors = [
                normalize_space(" ".join(part for part in (item.get("given"), item.get("family")) if part))
                for item in message.get("author", [])
            ]
            year = ""
            for field in ("published", "published-print", "published-online", "issued", "created"):
                date_parts = message.get(field, {}).get("date-parts", [])
                if date_parts and date_parts[0]:
                    year = str(date_parts[0][0])
                    break
            return normalize_space(titles[0] if titles else ""), source, authors, year
        authorships = payload.get("authorships", [])
        authors = [normalize_space(item.get("author", {}).get("display_name")) for item in authorships]
        return normalize_space(payload.get("title", "")), source, authors, str(payload.get("publication_year") or "")
    except Exception:
        return "", "", [], ""


def identity_match(cited: str, observed_title: str, authors: str, published_year: str) -> tuple[str, float | None]:
    similarity = title_similarity(cited, observed_title)
    cited_title_tokens = title_tokens(cited)
    observed_title_tokens = title_tokens(observed_title)
    shared_title_tokens = cited_title_tokens & observed_title_tokens
    if similarity is not None and (
        similarity >= 0.12
        or len(shared_title_tokens) >= 2
        or any(len(token) >= 7 for token in shared_title_tokens)
    ):
        return "title", similarity
    cited_tokens = title_tokens(cited) - {"journal", "article", "conference", "paper", "preprint", "report", "survey", "technical"}
    author_tokens = title_tokens(authors)
    author_overlap = cited_tokens & author_tokens
    if author_overlap:
        return "author_year", similarity
    return "", similarity


def citation_style(value: str) -> str:
    has_year = bool(re.search(r"\((?:19|20)\d{2}\)", value))
    has_citation_marker = bool(re.search(r"\bet\s+al\.?\b|;\s*(?:Journal|Conference|Preprint|Report|Survey|Technical)|\s&\s", value, re.I))
    return "author_year" if has_year and has_citation_marker else "title"


def classify_http(status: int | None, error: str) -> str:
    if status is not None and 200 <= status < 400:
        return "reachable"
    if status in {401, 403, 407, 418, 429, 451}:
        return "access_controlled"
    if status in {404, 410}:
        return "broken"
    if status is not None and status >= 500:
        return "server_error"
    if status is not None:
        return "http_error"
    if error:
        return "network_error"
    return "unknown"


def fetch_url(url: str, timeout: float) -> UrlResult:
    started = time.monotonic()
    target = arxiv_abstract_url(url)
    request = urllib.request.Request(
        target,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
            "Range": f"bytes=0-{MAX_BODY_BYTES - 1}",
        },
    )
    status: int | None = None
    final_url = target
    content_type = ""
    body = b""
    error = ""
    try:
        context = ssl.create_default_context()
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            status = response.status
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
            body = response.read(MAX_BODY_BYTES)
    except urllib.error.HTTPError as exc:
        status = exc.code
        final_url = exc.geturl() or target
        content_type = exc.headers.get("Content-Type", "") if exc.headers else ""
        error = f"HTTP {exc.code}: {exc.reason}"
        try:
            body = exc.read(MAX_BODY_BYTES)
        except Exception:
            body = b""
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    page_title = ""
    title_source = ""
    authors: list[str] = []
    published_year = ""
    if body:
        if "pdf" in content_type.lower() or body.startswith(b"%PDF"):
            page_title = extract_pdf_title(body)
            title_source = "pdf_metadata" if page_title else ""
        else:
            parser = TitleParser()
            try:
                parser.feed(body.decode("utf-8", errors="replace"))
                page_title = parser.best_title
                title_source = "html_metadata" if page_title else ""
                authors = parser.authors
                published_year = parser.published_year
            except Exception:
                page_title = ""
    registry_title, registry_source, registry_authors, registry_year = fetch_registry_metadata(url, timeout)
    if registry_title:
        page_title = registry_title
        title_source = registry_source
        authors = registry_authors
        published_year = registry_year
    return UrlResult(
        url=url,
        status_class=classify_http(status, error),
        http_status=status,
        final_url=final_url,
        content_type=content_type,
        page_title=page_title,
        title_source=title_source,
        authors=" | ".join(authors),
        published_year=published_year,
        error=error,
        elapsed_seconds=round(time.monotonic() - started, 3),
    )


def path_to_root(node_id: str, nodes: dict[str, dict[str, Any]]) -> list[str]:
    path: list[str] = []
    seen: set[str] = set()
    current = node_id
    while current:
        if current in seen or current not in nodes:
            return []
        seen.add(current)
        path.append(current)
        current = nodes[current].get("parent_id")
    return list(reversed(path))


def decisive_rule_targets(card: dict[str, Any]) -> list[str]:
    definition = normalize_space(card.get("definition_en"))
    mechanism = definition.split("This L4 risk card treats", 1)[0]
    text = normalize_space(f"{card.get('label_en', '')}. {mechanism}").casefold()
    targets: list[str] = []
    for l3_id, rule in CLASSIFICATION_RULES.items():
        if "-P-" in l3_id:
            continue
        decisive = any(re.search(pattern, text, flags=re.I) for pattern in rule.get("decisive", []))
        excluded = any(re.search(pattern, text, flags=re.I) for pattern in rule.get("exclusions", []))
        if decisive and not excluded:
            targets.append(l3_id)
    return sorted(targets)


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir or ROOT / "reports" / "validation" / args.release / "full_audit"
    public_dir = ROOT / "public" / "data" / "releases" / args.release
    cards = read_json(public_dir / "cards.json")["cards"]
    node_rows = read_json(public_dir / "hierarchy.json")["nodes"]
    nodes = {row["node_id"]: row for row in node_rows}
    scores = {row["l4_id"]: row for row in read_json(ROOT / "data/releases/v1.0.0/algorithm_scores.json")}
    physical_locks = {row["l4_id"]: row for row in read_json(ROOT / "data/releases/v1.0.0/physical_lock.json")}
    crosswalk = read_json(ROOT / "data/releases/v1.0.0/source_crosswalk.json")
    crosswalk_ids = {row["l4_id"] for row in crosswalk}

    mapping_rows: list[dict[str, Any]] = []
    id_counts = Counter(card["l4_id"] for card in cards)
    l3_label_keys = {
        normalize_key(value)
        for node in node_rows if node["level"] == 3
        for value in (node.get("label_en"), node.get("label_ko")) if value
    }
    for card in cards:
        l4_id = card["l4_id"]
        l3_id = card.get("primary_l3_id")
        path = path_to_root(l3_id, nodes) if l3_id else []
        levels = [nodes[node_id]["level"] for node_id in path] if path else []
        score = scores.get(l4_id)
        is_physical = card.get("assignment_status") == "locked_physical"
        lock = physical_locks.get(l4_id)
        assigned_matches_top1 = None if is_physical or not score else l3_id == score.get("top1_l3_id")
        physical_lock_matches = None if not is_physical else bool(lock and lock.get("new_l3_id") == l3_id)
        rule_targets = [] if is_physical else decisive_rule_targets(card)
        decisive_mismatch = len(rule_targets) == 1 and l3_id != rule_targets[0]
        label_is_l3 = normalize_key(card.get("label_en")) in l3_label_keys or normalize_key(card.get("label_ko")) in l3_label_keys
        reasons: list[str] = []
        if id_counts[l4_id] != 1:
            reasons.append("DUPLICATE_L4_ID")
        if levels != [0, 1, 2, 3]:
            reasons.append("INVALID_L0_L3_PATH")
        if l4_id not in crosswalk_ids:
            reasons.append("MISSING_SOURCE_CROSSWALK")
        if label_is_l3:
            reasons.append("L3_LABEL_USED_AS_L4")
        if assigned_matches_top1 is False:
            reasons.append("ASSIGNMENT_DIFFERS_FROM_ALGORITHM_TOP1")
        if physical_lock_matches is False:
            reasons.append("PHYSICAL_LOCK_MISMATCH")
        if decisive_mismatch:
            reasons.append("DECISIVE_L3_RULE_MISMATCH")
        if card.get("decision_required"):
            reasons.append("DECISION_REQUIRED")
        if card.get("assignment_status") == "stage3_forced":
            reasons.append("STAGE3_FORCED")
        if score and float(score.get("top1_semantic_score") or 0) < 0.55:
            reasons.append("LOW_SEMANTIC_SCORE")
        if score and float(score.get("semantic_margin") or 0) < 0.01:
            reasons.append("LOW_SEMANTIC_MARGIN")
        mapping_rows.append(
            {
                "l4_id": l4_id,
                "label_en": card.get("label_en"),
                "primary_l3_id": l3_id,
                "l3_label_en": nodes.get(l3_id, {}).get("label_en"),
                "l1_id": path[1] if len(path) == 4 else "",
                "assignment_status": card.get("assignment_status"),
                "review_status": card.get("review_status"),
                "decision_required": bool(card.get("decision_required")),
                "human_approved": bool(card.get("human_approved")),
                "path_valid": levels == [0, 1, 2, 3],
                "assigned_matches_top1": assigned_matches_top1,
                "physical_lock_matches": physical_lock_matches,
                "decisive_rule_targets": "|".join(rule_targets),
                "decisive_rule_mismatch": decisive_mismatch,
                "top1_semantic_score": score.get("top1_semantic_score") if score else None,
                "semantic_margin": score.get("semantic_margin") if score else None,
                "stage2_suitability_score": card.get("stage2_suitability_score"),
                "label_is_l3": label_is_l3,
                "audit_flags": "|".join(reasons),
            }
        )

    reference_instances: list[dict[str, Any]] = []
    unique_urls: set[str] = set()
    for card in cards:
        for index, reference in enumerate(card.get("references", []), start=1):
            url = normalize_space(reference.get("url"))
            if url:
                unique_urls.add(url)
            reference_instances.append(
                {
                    "l4_id": card["l4_id"],
                    "label_en": card.get("label_en"),
                    "reference_index": index,
                    "reference_title": normalize_space(reference.get("title")),
                    "reference_url": url,
                    "reference_type": normalize_space(reference.get("type")),
                    "source_system": reference.get("source_system"),
                    "justification": normalize_space(reference.get("justification")),
                    "is_linked": reference.get("is_linked"),
                }
            )

    url_results: dict[str, UrlResult] = {}
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(fetch_url, url, args.timeout): url for url in sorted(unique_urls)}
        for future in as_completed(futures):
            result = future.result()
            url_results[result.url] = result
    # Crossref can throttle concurrent metadata calls. Retry only missing registry
    # metadata sequentially so DOI identity checks remain reproducible.
    for url, result in sorted(url_results.items()):
        if registry_metadata_endpoint(url) and result.title_source not in {"crossref", "openalex"}:
            title, source, authors, year = fetch_registry_metadata(url, args.timeout)
            if title:
                result.page_title = title
                result.title_source = source
                result.authors = " | ".join(authors)
                result.published_year = year
            time.sleep(0.1)

    reference_rows: list[dict[str, Any]] = []
    for reference in reference_instances:
        url = reference["reference_url"]
        result = url_results.get(url)
        identity_basis, similarity = identity_match(
            reference["reference_title"], result.page_title, result.authors, result.published_year
        ) if result else ("", None)
        reference_style = citation_style(reference["reference_title"])
        if not url:
            verdict = "UNLINKED"
        elif result and result.status_class in {"broken", "network_error", "server_error", "http_error"}:
            verdict = "URL_FAILED"
        elif result and result.status_class == "access_controlled":
            verdict = "ACCESS_CONTROLLED"
        elif result and result.page_title and not identity_basis and reference_style == "author_year":
            verdict = "CITATION_METADATA_UNVERIFIED"
        elif result and result.page_title and not identity_basis:
            verdict = "TITLE_MISMATCH_REVIEW"
        elif result and not result.page_title:
            verdict = "REACHABLE_TITLE_UNVERIFIED"
        else:
            verdict = "PASS"
        reference_rows.append(
            {
                **reference,
                "status_class": result.status_class if result else "unlinked",
                "http_status": result.http_status if result else None,
                "final_url": result.final_url if result else "",
                "content_type": result.content_type if result else "",
                "page_title": result.page_title if result else "",
                "title_source": result.title_source if result else "",
                "authors": result.authors if result else "",
                "published_year": result.published_year if result else "",
                "identity_basis": identity_basis,
                "citation_style": reference_style,
                "title_similarity": similarity,
                "verdict": verdict,
                "error": result.error if result else "",
            }
        )

    url_rows = [asdict(url_results[url]) for url in sorted(url_results)]
    mapping_flags = Counter(
        flag for row in mapping_rows for flag in row["audit_flags"].split("|") if flag
    )
    verdict_counts = Counter(row["verdict"] for row in reference_rows)
    url_status_counts = Counter(row["status_class"] for row in url_rows)
    cards_with_reference_issue = {
        row["l4_id"] for row in reference_rows if row["verdict"] != "PASS"
    }
    summary = {
        "audit_scope": {
            "release": args.release,
            "l4_cards": len(cards),
            "taxonomy_nodes": len(node_rows),
            "reference_instances": len(reference_rows),
            "unique_reference_urls": len(unique_urls),
        },
        "mapping": {
            "unique_l4_ids": len(id_counts),
            "duplicate_l4_ids": sum(count > 1 for count in id_counts.values()),
            "valid_l0_l3_paths": sum(row["path_valid"] for row in mapping_rows),
            "source_crosswalk_covered": sum(row["l4_id"] in crosswalk_ids for row in mapping_rows),
            "physical_locked": sum(row["assignment_status"] == "locked_physical" for row in mapping_rows),
            "physical_lock_exact_matches": sum(row["physical_lock_matches"] is True for row in mapping_rows),
            "algorithmic_assignments": sum(row["assigned_matches_top1"] is not None for row in mapping_rows),
            "algorithm_top1_exact_matches": sum(row["assigned_matches_top1"] is True for row in mapping_rows),
            "decisive_l3_rule_mismatches": sum(row["decisive_rule_mismatch"] for row in mapping_rows),
            "human_approved": sum(row["human_approved"] for row in mapping_rows),
            "decision_required": sum(row["decision_required"] for row in mapping_rows),
            "flag_counts": dict(sorted(mapping_flags.items())),
        },
        "references": {
            "cards_with_zero_references": sum(not card.get("references") for card in cards),
            "empty_or_unlinked_reference_instances": verdict_counts["UNLINKED"],
            "cards_with_any_reference_issue": len(cards_with_reference_issue),
            "instance_verdict_counts": dict(sorted(verdict_counts.items())),
            "unique_url_status_counts": dict(sorted(url_status_counts.items())),
        },
        "interpretation": {
            "structural_mapping": "pass" if all(row["path_valid"] for row in mapping_rows) else "fail",
            "physical_lock_integrity": "pass" if all(row["physical_lock_matches"] is not False for row in mapping_rows) else "fail",
            "semantic_mapping": "algorithmically reproducible but not human-validated",
            "reference_integrity": "requires remediation" if verdict_counts["UNLINKED"] or verdict_counts["URL_FAILED"] else "pass_with_caveats",
        },
    }

    write_csv(output_dir / "mapping_audit.csv", mapping_rows)
    write_csv(output_dir / "reference_instance_audit.csv", reference_rows)
    write_csv(output_dir / "unique_url_audit.csv", url_rows)
    write_json(output_dir / "audit_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
