#!/usr/bin/env python3
"""Apply the verified golden reference ledger and synchronize full CSV copies."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "projects/rai_risk_taxonomy_2_0_rebuild_20260826/11_golden_reference_enrichment"
LEDGER = WORK / "L4_Golden_Reference_Ledger.csv"
URL_CHECK = WORK / "Golden_Reference_URL_Check.csv"
ARCHIVE = ROOT / "archives" / "pre_golden_reference_20260901"
DOMAINS = ("General", "Agentic", "Physical")
CANONICAL = ROOT / "handover/RAI-Risk-Taxonomy-2.0-master_20260829/01_data"
FULL_DESTINATIONS = (
    ROOT / "projects/rai_risk_taxonomy_2_0_rebuild_20260826/03_outputs/release",
    ROOT / "projects/rai_risk_taxonomy_2_0_rebuild_20260826/07_human_review_recovery_applied",
    ROOT / "projects/rai_risk_taxonomy_2_0_rebuild_20260826/10_human_review_round4",
    ROOT / "handover/RAI-Risk-Taxonomy-2.0-technical-report_20260901/01_data",
)


def locate(directory: Path, domain: str) -> Path | None:
    candidates = [
        directory / f"L4_{domain}.csv",
        directory / f"L4_{domain}_Human_Review_Recovery_Applied.csv",
        directory / f"L4_{domain}_Human_Review_Round4_Applied_20260901.csv",
    ]
    return next((path for path in candidates if path.exists()), None)


def main() -> None:
    ledger = pd.read_csv(LEDGER, dtype=str).fillna("")
    checks = pd.read_csv(URL_CHECK, dtype=str).fillna("")
    status_by_url = dict(zip(checks["ref_url"], checks["http_status"]))
    accepted = {"200", "202", "403"}
    bad = sorted(url for url in ledger["ref_url"].unique() if status_by_url.get(url) not in accepted)
    if bad:
        raise AssertionError(f"Unverified source URLs: {bad}")
    ledger["verification_status"] = ledger["ref_url"].map(
        lambda url: "PASS_LIVE" if status_by_url[url] in {"200", "202"} else "PASS_ACCESS_CONTROLLED"
    )
    ledger.to_csv(LEDGER, index=False, encoding="utf-8-sig")
    refs = {}
    for row in ledger.to_dict("records"):
        refs[row["L4_ID"]] = [{
            "title": row["ref_title"], "authors": row["ref_authors"], "year": row["ref_year"],
            "type": row["reference_type"], "url": row["ref_url"], "doi": row["doi"],
            "quote": row["direct_quote"], "quote_location": row["quote_location"],
            "source_evidence_id": row["source_ev_id"], "source_quality_tier": row["source_quality_tier"],
            "verification_status": row["verification_status"],
        }]

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    changed = []
    for domain in DOMAINS:
        canonical = CANONICAL / f"L4_{domain}.csv"
        frame = pd.read_csv(canonical, dtype=str).fillna("")
        if not set(frame["L4_ID"]).issubset(refs):
            raise AssertionError(f"Missing ledger IDs in {domain}")
        archive_path = ARCHIVE / f"L4_{domain}.csv"
        if not archive_path.exists():
            shutil.copy2(canonical, archive_path)
        frame["References"] = frame["L4_ID"].map(lambda value: json.dumps(refs[value], ensure_ascii=False))
        targets = [canonical]
        for directory in FULL_DESTINATIONS:
            path = locate(directory, domain)
            if path is not None:
                targets.append(path)
        for target in targets:
            frame.to_csv(target, index=False, lineterminator="\r\n")
            changed.append(str(target.relative_to(ROOT)))

    for destination in (
        ROOT / "releases/RAI-Risk-Taxonomy-2.0-master/validation/L4_Golden_Reference_Ledger.csv",
        ROOT / "handover/RAI-Risk-Taxonomy-2.0-master_20260829/03_validation/L4_Golden_Reference_Ledger.csv",
        ROOT / "handover/RAI-Risk-Taxonomy-2.0-technical-report_20260901/01_data/L4_Golden_Reference_Ledger.csv",
        ROOT / "public/data/releases/RAI-Risk-Taxonomy-2.0-master/validation/L4_Golden_Reference_Ledger.csv",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(LEDGER, destination)
    report = WORK / "GOLDEN_REFERENCE_VALIDATION.md"
    for destination in (
        ROOT / "releases/RAI-Risk-Taxonomy-2.0-master/validation/GOLDEN_REFERENCE_VALIDATION.md",
        ROOT / "handover/RAI-Risk-Taxonomy-2.0-master_20260829/03_validation/GOLDEN_REFERENCE_VALIDATION.md",
        ROOT / "handover/RAI-Risk-Taxonomy-2.0-technical-report_20260901/01_data/GOLDEN_REFERENCE_VALIDATION.md",
        ROOT / "public/data/releases/RAI-Risk-Taxonomy-2.0-master/validation/GOLDEN_REFERENCE_VALIDATION.md",
    ):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(report, destination)
    (WORK / "APPLIED_AT.txt").write_text(datetime.now().isoformat() + "\n", encoding="utf-8")
    print(f"cards={len(ledger)} changed_full_csv_files={len(changed)}")
    print("\n".join(changed))


if __name__ == "__main__":
    main()
