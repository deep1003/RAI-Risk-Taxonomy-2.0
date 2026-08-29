#!/usr/bin/env python3
"""Remove language-only operations that became inapplicable after explicit deletion."""

from __future__ import annotations

import csv
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "02_working" / "specifications" / "human_review_round2"
ARCHIVE = SPEC / "archive" / "pre_delete_correction_20260829"
REMOVALS = {
    "L4_Korean_Copyedit_Approved_20260829.csv": {"KOC-0066"},
    "L4_English_Copyedit_Approved_20260829.csv": {"EOC-0122"},
}


def main() -> None:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for filename, decision_ids in REMOVALS.items():
        path = SPEC / filename
        archive = ARCHIVE / filename
        if not archive.exists():
            shutil.copy2(path, archive)
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames
            rows = list(reader)
        found = {row["Decision_ID"] for row in rows} & decision_ids
        if found != decision_ids:
            raise ValueError(f"Expected deletion-only copy-edits not found in {filename}: {decision_ids - found}")
        retained = [row for row in rows if row["Decision_ID"] not in decision_ids]
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(retained)
        print(f"{filename}: {len(rows)} -> {len(retained)}")


if __name__ == "__main__":
    main()
