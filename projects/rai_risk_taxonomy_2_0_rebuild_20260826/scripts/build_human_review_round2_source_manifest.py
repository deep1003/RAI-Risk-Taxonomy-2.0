#!/usr/bin/env python3
"""Freeze checksums and dimensions for second-round KTSPACE review exports."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "00_source_snapshot"
CSV_ROOT = SOURCE_ROOT / "csv"
OUTPUT = SOURCE_ROOT / "source_manifest_human_review_round2_20260828.json"
SOURCES = (
    ("L3", "933496461", "L3_Human_Review_Round2_KTSPACE_933496461_20260828.csv"),
    ("L4_General", "932056034", "L4_General_Human_Review_Round2_KTSPACE_932056034_20260828.csv"),
    ("L4_Agentic", "931437538", "L4_Agentic_Human_Review_Round2_KTSPACE_931437538_20260828.csv"),
    ("L4_Physical", "930753013", "L4_Physical_Human_Review_Round2_KTSPACE_930753013_20260828.csv"),
)


def dimensions(path: Path) -> tuple[int, int]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        return sum(1 for _ in reader), len(header)


def main() -> None:
    files = []
    for label, page_id, filename in SOURCES:
        path = CSV_ROOT / filename
        rows, columns = dimensions(path)
        files.append(
            {
                "label": label,
                "path": str(path.relative_to(ROOT)),
                "ktspace_page_id": page_id,
                "rows": rows,
                "columns": columns,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    manifest = {
        "manifest_version": "1.0",
        "source_snapshot_date": "2026-08-28",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "immutability_policy": "These review exports are read-only inputs; regenerate this manifest only after an explicitly authorised source refresh.",
        "files": files,
    }
    OUTPUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
