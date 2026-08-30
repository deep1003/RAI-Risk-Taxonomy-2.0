#!/usr/bin/env python3
"""Synchronize the canonical master release and every active derived bundle."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import zipfile
from collections import Counter
from pathlib import Path

import build_master_site_release


ROOT = Path(__file__).resolve().parents[1]
RELEASE_ID = "RAI-Risk-Taxonomy-2.0-master"
SOURCE = ROOT / "releases" / RELEASE_ID
DATA = SOURCE / "data"
PUBLIC = ROOT / "public" / "data" / "releases" / RELEASE_ID
HANDOVER = ROOT / "handover" / "RAI-Risk-Taxonomy-2.0-master_20260829"
FULL_DATA = HANDOVER / "01_data"
L4_FILES = ("L4_General.csv", "L4_Agentic.csv", "L4_Physical.csv")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def synchronize_source_manifest() -> None:
    path = SOURCE / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    outputs = {}
    for name in ("L1_Master.csv", "L1_L2_L3_Master.csv", *L4_FILES):
        artifact = DATA / name
        outputs[name] = {"sha256": sha256(artifact), "rows": len(read_csv(artifact))}
    manifest["primary_outputs"] = outputs
    manifest["l3_master_sha256"] = outputs["L1_L2_L3_Master.csv"]["sha256"]

    full_rows = [row for name in L4_FILES for row in read_csv(FULL_DATA / name)]
    score_status = Counter(
        (row.get("Definition_Grounding_Action") or "NOT_APPLICABLE").strip()
        for row in full_rows
    )
    summary = manifest["summary"]
    summary["cleaned_total"] = len(full_rows)
    summary["final_total"] = len(full_rows)
    summary["final_domain_counts"] = {
        "General AI": len(read_csv(DATA / "L4_General.csv")),
        "Agentic AI": len(read_csv(DATA / "L4_Agentic.csv")),
        "Physical AI": len(read_csv(DATA / "L4_Physical.csv")),
    }
    summary["score_status_counts"] = dict(score_status)
    manifest["audit_correction_20260830_ac15"] = (
        "AC-15: synchronized the 50-node hierarchy, current artifact row counts and SHA-256 hashes, "
        "public manifest, active handover checksums, and master-site regression tests."
    )
    write_json(path, manifest)


def copy_active_artifacts() -> None:
    pairs = {
        SOURCE / "manifest.json": HANDOVER / "03_validation" / "manifest.json",
        SOURCE / "validation" / "final_release_qa.json": HANDOVER / "03_validation" / "final_release_qa.json",
        PUBLIC / "cards.json": HANDOVER / "04_web" / "cards.json",
        PUBLIC / "hierarchy.json": HANDOVER / "04_web" / "hierarchy.json",
        PUBLIC / "manifest.json": HANDOVER / "04_web" / "public_manifest.json",
        ROOT / "index.html": HANDOVER / "04_web" / "index.html",
        SOURCE / "reports" / "technical_report_en.tex": HANDOVER / "02_reports" / "technical_report_en.tex",
        SOURCE / "reports" / "technical_report_en.pdf": HANDOVER / "02_reports" / "technical_report_en.pdf",
        SOURCE / "reports" / "technical_report_ko.tex": HANDOVER / "02_reports" / "technical_report_ko.tex",
        SOURCE / "reports" / "technical_report_ko.pdf": HANDOVER / "02_reports" / "technical_report_ko.pdf",
    }
    for source, target in pairs.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def update_handover_checksums_and_zip() -> None:
    checksum_path = HANDOVER / "SHA256SUMS.txt"
    files = sorted(
        path for path in HANDOVER.rglob("*")
        if path.is_file() and path != checksum_path
    )
    checksum_path.write_text(
        "\n".join(f"{sha256(path)}  {path.relative_to(HANDOVER)}" for path in files) + "\n",
        encoding="utf-8",
    )
    archive = HANDOVER.parent / f"{HANDOVER.name}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(p for p in HANDOVER.rglob("*") if p.is_file()):
            bundle.write(path, Path(HANDOVER.name) / path.relative_to(HANDOVER))


def main() -> None:
    synchronize_source_manifest()
    build_master_site_release.main()
    copy_active_artifacts()
    update_handover_checksums_and_zip()


if __name__ == "__main__":
    main()
