#!/usr/bin/env python3
"""Reconcile expert language-review selectors to immutable baseline IDs."""

from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT
    / "02_working/specifications/human_review_round2"
    / "L4_Final_Terminology_L3_Alignment_Approved_20260829.csv"
)

AGENT_CURRENT_FINAL_IDS = {
    "FQA-101": "A_SYS_DECEPT_001",
    "FQA-102": "A_SYS_AUTH_001",
    "FQA-103": "A_SYS_AUTH_002",
    "FQA-104": "A_SYS_AUTH_003",
    "FQA-105": "A_INT_COORD_005",
    "FQA-106": "A_SYS_TRACE_001",
    "FQA-107": "A_SYS_TRACE_004",
    "FQA-108": "P_INT_SAFETY_006",
    "FQA-109": "P_INT_SAFETY_007",
    "FQA-110": "P_INT_SAFETY_009",
    "FQA-111": "P_INT_TAMPER_002",
    "FQA-112": "P_INT_TAMPER_004",
    "FQA-113": "P_SYS_CONTROL_003",
    "FQA-114": "P_SYS_CONTROL_018",
    "FQA-115": "P_SYS_CONTROL_019",
    "FQA-116": "P_SYS_CONTROL_021",
    "FQA-117": "P_SYS_CONTROL_022",
    "FQA-118": "P_SYS_CONTROL_024",
    "FQA-119": "P_SYS_CONTROL_034",
    "FQA-120": "P_SYS_CONTROL_035",
    "FQA-121": "P_SYS_CONTROL_039",
    "FQA-122": "P_SYS_CONTROL_041",
    "FQA-123": "P_SYS_CONTROL_042",
    "FQA-124": "P_SYS_CONTROL_043",
    "FQA-125": "P_SYS_CONTROL_046",
    "FQA-126": "P_SYS_CONTROL_049",
    "FQA-127": "P_SYS_HARDWARE_004",
    "FQA-128": "P_SYS_HARDWARE_005",
    "FQA-129": "P_SYS_STATE_008",
    "FQA-130": "P_SYS_STATE_009",
    "FQA-131": "P_SYS_STATE_010",
    "FQA-132": "G_SYS_INPUT_002",
    "FQA-133": "P_Others_011",
    "FQA-134": "P_Others_013",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def tokens(value: str) -> tuple[str, ...]:
    value = (value or "").replace("|", ";").replace(",", ";")
    return tuple(sorted(part.strip() for part in value.split(";") if part.strip()))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: reconcile_agent_final_qa_selectors_20260829.py PRE_FINAL_QA_DIR"
        )
    prefinal = Path(sys.argv[1]).resolve()
    ledger = read_csv(prefinal / "Human_Review_Round2_Decision_Ledger.csv")
    current_outputs: list[dict[str, str]] = []
    prefinal_outputs: list[dict[str, str]] = []
    for domain in ("General", "Agentic", "Physical"):
        current_outputs.extend(
            read_csv(ROOT / "05_human_review_round2" / f"L4_{domain}_Human_Review_Round2_Applied.csv")
        )
        prefinal_outputs.extend(
            read_csv(prefinal / f"L4_{domain}_Human_Review_Round2_Applied.csv")
        )
    current_by_id = {row["L4_ID"]: row for row in current_outputs}
    rows = read_csv(MANIFEST)
    header = list(rows[0])
    by_id = {row["Decision_ID"]: row for row in rows}

    for decision_id, current_final_id in AGENT_CURRENT_FINAL_IDS.items():
        operation = by_id[decision_id]
        current = current_by_id[current_final_id]
        prefinal_matches = [
            row
            for row in prefinal_outputs
            if tokens(row.get("source_row_id", ""))
            == tokens(current.get("source_row_id", ""))
            and tokens(row.get("Source_L4_IDs", ""))
            == tokens(current.get("Source_L4_IDs", ""))
        ]
        if len(prefinal_matches) != 1:
            raise ValueError(
                f"pre-final lineage selector failed for {decision_id}: "
                f"{len(prefinal_matches)}"
            )
        prefinal_id = prefinal_matches[0]["L4_ID"]
        baseline_sources = sorted(
            row["L4_ID_Before"]
            for row in ledger
            if prefinal_id
            in {
                part.strip()
                for part in row["L4_ID_After"].split("|")
                if part.strip()
            }
        )
        if not baseline_sources:
            raise ValueError(f"no immutable source for {decision_id}={current_final_id}")
        operation["Source_L4_ID_Before"] = baseline_sources[0]

    rows.sort(key=lambda row: int(row["Decision_ID"].split("-", 1)[1]))
    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    print(
        f"reconciled={len(AGENT_CURRENT_FINAL_IDS)} total={len(rows)} "
        f"sha256={hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}"
    )


if __name__ == "__main__":
    main()
