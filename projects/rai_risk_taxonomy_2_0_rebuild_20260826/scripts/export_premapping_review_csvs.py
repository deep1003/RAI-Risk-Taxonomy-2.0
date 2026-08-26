#!/usr/bin/env python3
"""Export the stopped pre-mapping L4 rewrite set as three review CSVs."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "02_working" / "L4_Risk_Text_Rewritten_PreMapping.csv"
OUTPUT = ROOT / "02_working" / "review_csv"

REVIEW_COLUMNS = [
    "target_domain", "source_row_id", "source_domain", "source_l4_id", "source_l4_ids",
    "title_ko", "title_en", "description_ko", "description_en", "facet", "act_type",
    "original_description_ko", "original_description_en", "human_edit_ko_used",
    "human_edit_en_used", "instruction_prompt", "transformation_action",
    "transformation_rationale", "domain_route_basis", "terminology_sources",
    "l3_candidate_hint", "human_audit_description", "human_audit_l3_mapping",
    "human_audit_duplicate", "coverage_change",
]


def main() -> None:
    data = pd.read_csv(SOURCE, dtype=str, keep_default_na=False)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for domain in ("General", "Agentic", "Physical"):
        subset = data.loc[data["target_domain"].eq(domain), REVIEW_COLUMNS].copy()
        subset = subset.sort_values(["source_domain", "source_row_id"], kind="stable")
        path = OUTPUT / f"L4_{domain}_PreMapping_Review.csv"
        subset.to_csv(path, index=False, encoding="utf-8-sig", lineterminator="\n")


if __name__ == "__main__":
    main()
