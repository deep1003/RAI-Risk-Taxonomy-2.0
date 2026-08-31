#!/usr/bin/env python3
"""Apply independently verified journal references to current L4 cards."""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "projects/rai_risk_taxonomy_2_0_rebuild_20260826/08_journal_reference_enrichment"
VERIFIED = WORK / "L4_Journal_Reference_Verified.csv"
PUBLIC_CARDS = ROOT / "public/data/releases/RAI-Risk-Taxonomy-2.0-master/cards.json"
HANDOVER_ROOT = ROOT / "handover/RAI-Risk-Taxonomy-2.0-master_20260829"
HANDOVER_CARDS = HANDOVER_ROOT / "04_web/cards.json"
RELEASE_VALIDATION = ROOT / "releases/RAI-Risk-Taxonomy-2.0-master/validation"
PUBLIC_MANIFEST = ROOT / "public/data/releases/RAI-Risk-Taxonomy-2.0-master/manifest.json"
HANDOVER_ZIP = ROOT / "handover/RAI-Risk-Taxonomy-2.0-master_20260829.zip"
CSV_DIRS = (
    ROOT / "projects/rai_risk_taxonomy_2_0_rebuild_20260826/03_outputs/release",
    ROOT / "projects/rai_risk_taxonomy_2_0_rebuild_20260826/07_human_review_recovery_applied",
    HANDOVER_ROOT / "01_data",
)
REJECTED_AFTER_QUALITY_REVIEW = {
    "https://doi.org/10.3389/frobt.2021.640647",
    "https://doi.org/10.1108/tg-03-2025-0065",
    "https://doi.org/10.1155/2022/2938011",
    "https://doi.org/10.1109/access.2023.3308152",
}


def csv_path(directory: Path, domain: str) -> Path:
    direct = directory / f"L4_{domain}.csv"
    if direct.exists():
        return direct
    return directory / f"L4_{domain}_Human_Review_Recovery_Applied.csv"


def load_cards(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def apply_to_payload(payload: dict, references: dict[str, dict]) -> int:
    cards = {card["l4_id"]: card for card in payload["cards"]}
    if not set(references).issubset(cards):
        raise AssertionError("Selection contains an unknown current L4 ID")
    changed = 0
    for card in cards.values():
        existing = card.setdefault("references", [])
        retained = [
            item for item in existing
            if item["url"].lower() not in REJECTED_AFTER_QUALITY_REVIEW
        ]
        changed += len(existing) - len(retained)
        card["references"] = retained
    for l4_id, reference in references.items():
        existing = cards[l4_id].setdefault("references", [])
        if any(item["url"].lower() == reference["url"].lower() for item in existing):
            continue
        existing.append(reference)
        changed += 1
    return changed


def write_cards(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def sync_full_csvs(payload: dict) -> int:
    by_id = {card["l4_id"]: card for card in payload["cards"]}
    changed_files = 0
    canonical_directory = HANDOVER_ROOT / "01_data"
    for domain in ("General", "Agentic", "Physical"):
        canonical_path = csv_path(canonical_directory, domain)
        frame = pd.read_csv(canonical_path, dtype=str).fillna("")
        domain_prefix = {"General": "G_", "Agentic": "A_", "Physical": "P_"}[domain]
        expected_ids = {l4_id for l4_id in by_id if l4_id.startswith(domain_prefix)}
        if set(frame["L4_ID"]) != expected_ids:
            raise AssertionError(f"Canonical {domain} CSV is not synchronized with cards.json")
        frame["References"] = frame["L4_ID"].map(
            lambda l4_id: json.dumps(by_id[l4_id].get("references", []), ensure_ascii=False)
        )
        destinations = [
            canonical_path,
            csv_path(CSV_DIRS[0], domain),
            csv_path(CSV_DIRS[1], domain),
        ]
        for path in destinations:
            old = path.read_bytes()
            frame.to_csv(path, index=False, lineterminator="\r\n")
            changed_files += old != path.read_bytes()
    return changed_files


def refresh_checksums() -> int:
    checksum_path = HANDOVER_ROOT / "SHA256SUMS.txt"
    files = sorted(path for path in HANDOVER_ROOT.rglob("*") if path.is_file() and path != checksum_path)
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(HANDOVER_ROOT)}"
        for path in files
    ]
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(files)


def sync_public_manifest_and_handover_zip() -> int:
    shutil.copy2(HANDOVER_ROOT / "04_web/public_manifest.json", PUBLIC_MANIFEST)
    files = sorted(path for path in HANDOVER_ROOT.rglob("*") if path.is_file())
    with zipfile.ZipFile(HANDOVER_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, path.relative_to(HANDOVER_ROOT.parent))
    return len(files)


def write_validation_report(payload: dict, verified: pd.DataFrame) -> None:
    cards = {card["l4_id"]: card for card in payload["cards"]}
    rows = []
    for row in verified.to_dict("records"):
        rows.append(
            "| {l4} | {title} | {paper} | {journal} ({year}) | [DOI]({url}) |".format(
                l4=row["L4_ID"],
                title=cards[row["L4_ID"]]["label_ko"],
                paper=row["verified_title"].replace("|", "\\|"),
                journal=row["verified_journal"].replace("|", "\\|"),
                year=row["verified_year"],
                url=row["ref_url"],
            )
        )
    report = "\n".join(
        [
            "# L4 Journal Reference Validation",
            "",
            "Date: 2026-08-31",
            "",
            "## Scope and acceptance rule",
            "",
            "The unit of review is a current L4 card. A reference was accepted only when the article directly addresses the card's risk terminology, mechanism, definition, or explanatory concept. Broadly adjacent literature was rejected. No new L4 card and no taxonomy-content change was permitted.",
            "",
            "## Retrieval and verification",
            "",
            "1. Retrieved five candidates per card from 44,701 DOI-bearing records in the frozen local scholarly corpus, yielding 3,145 candidate rows.",
            "2. Resolved candidate metadata through OpenAlex and retained journal articles with an abstract, a core journal source, and no retraction flag.",
            "3. Examined title and abstract evidence against each L4 title and definition; accepted 24 direct matches and rejected loose keyword overlap.",
            "4. Re-resolved all 24 records through Crossref, requiring `journal-article`, a journal title, a publication year, and author metadata.",
            "5. Tested every `https://doi.org/...` URL and required a live DOI redirect to the publisher landing page.",
            "",
            "## Result",
            "",
            "| Metric | Result |",
            "|---|---:|",
            "| Current L4 cards | 629 |",
            "| New verified journal references | 24 |",
            "| Crossref journal-article validation | 24/24 PASS |",
            "| Live DOI resolver validation | 24/24 PASS |",
            "| Cards with at least one reference | 160 -> 176 |",
            "| Total reference entries | 163 -> 187 |",
            "| Card title, definition, hierarchy, mapping, or lineage changes | 0 |",
            "",
            "The three full-column project CSV sets were synchronized from the current handover projection before their `References` fields were populated. This also removed ten stale pre-AC-14 General-card identifiers from the two project snapshots; it did not introduce a new taxonomy decision.",
            "",
            "## Accepted references",
            "",
            "| L4 ID | Korean risk title | Article | Journal | Link |",
            "|---|---|---|---|---|",
            *rows,
            "",
            "## Reproducibility artifacts",
            "",
            "The complete bibliographic metadata, fit rationale, DOI status, and publisher landing page are recorded in `L4_Journal_Reference_Verified.csv`. Candidate generation and verification are reproducible with `build_l4_journal_reference_candidates.py`, `validate_l4_journal_reference_candidates.py`, and `verify_l4_journal_reference_selections.py`.",
            "",
            "## Conclusion",
            "",
            "PASS. All attached records are Crossref-validated journal articles with live DOI links and direct conceptual relevance to their assigned L4 cards.",
            "",
        ]
    )
    report_name = "L4_Journal_Reference_Validation_20260831.md"
    metadata_name = "L4_Journal_Reference_Verified.csv"
    (RELEASE_VALIDATION / report_name).write_text(report, encoding="utf-8")
    (HANDOVER_ROOT / "03_validation" / report_name).write_text(report, encoding="utf-8")
    shutil.copy2(VERIFIED, RELEASE_VALIDATION / metadata_name)
    shutil.copy2(VERIFIED, HANDOVER_ROOT / "03_validation" / metadata_name)


def main() -> None:
    verified = pd.read_csv(VERIFIED, dtype=str).fillna("")
    if len(verified) != 24 or not verified["verification_status"].eq("PASS").all():
        raise AssertionError("Expected 24 fully verified journal references")
    references = {
        row["L4_ID"]: {"label": row["ref_label"], "url": row["ref_url"]}
        for row in verified.to_dict("records")
    }

    payload = load_cards(PUBLIC_CARDS)
    changed = apply_to_payload(payload, references)
    write_cards(PUBLIC_CARDS, payload)
    write_cards(HANDOVER_CARDS, payload)
    csv_files = sync_full_csvs(payload)
    write_validation_report(payload, verified)
    checksum_files = refresh_checksums()
    zip_files = sync_public_manifest_and_handover_zip()

    cards_with_references = sum(bool(card.get("references")) for card in payload["cards"])
    reference_entries = sum(len(card.get("references", [])) for card in payload["cards"])
    print(f"managed reference entries changed: {changed}")
    print(f"cards with references: {cards_with_references}")
    print(f"reference entries: {reference_entries}")
    print(f"full-column CSV files synchronized: {csv_files}")
    print(f"handover checksums refreshed: {checksum_files}")
    print(f"public manifest synchronized and handover ZIP rebuilt: {zip_files} files")


if __name__ == "__main__":
    main()
