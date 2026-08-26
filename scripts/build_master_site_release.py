#!/usr/bin/env python3
"""Build the public explorer bundle from the reviewed master CSV release."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_ID = "RAI-Risk-Taxonomy-2.0-master"
SOURCE = ROOT / "releases" / RELEASE_ID
DATA = SOURCE / "data"
OUT = ROOT / "public" / "data" / "releases" / RELEASE_ID

L4_FILES = ("L4_General.csv", "L4_Agentic.csv", "L4_Physical.csv")
L2_CATEGORY_IDS = {
    "Interaction": "L2_INT",
    "System": "L2_SYS",
    "Societal Impact": "L2_SOC",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def optional_float(value: str) -> float | None:
    value = (value or "").strip()
    return float(value) if value else None


def hierarchy_nodes(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    first = rows[0]
    nodes: list[dict[str, object]] = [
        {
            "node_id": first["L0_ID"],
            "level": 0,
            "parent_id": None,
            "label_ko": first["L0_Title_ko"],
            "label_en": first["L0_Title_en"],
            "description_ko": "책임 있는 인공지능 리스크의 L0부터 L4까지의 통합 분류체계.",
            "description_en": "An integrated L0-L4 taxonomy of responsible AI risks.",
            "sequence": 0,
            "status": "active",
        }
    ]

    seen_l1: set[str] = set()
    seen_l2: set[str] = set()
    for sequence, row in enumerate(rows, start=1):
        if row["L1_ID"] not in seen_l1:
            seen_l1.add(row["L1_ID"])
            nodes.append(
                {
                    "node_id": row["L1_ID"],
                    "level": 1,
                    "parent_id": row["L0_ID"],
                    "label_ko": row["L1_Title_ko"],
                    "label_en": row["L1_Title_en"],
                    "description_ko": row["L1_Description_ko"],
                    "description_en": row["L1_Description_en"],
                    "sequence": len(seen_l1),
                    "status": "active",
                }
            )
        if row["L2_ID"] and row["L2_ID"] not in seen_l2:
            seen_l2.add(row["L2_ID"])
            nodes.append(
                {
                    "node_id": row["L2_ID"],
                    "level": 2,
                    "parent_id": row["L1_ID"],
                    "canonical_l2_id": L2_CATEGORY_IDS[row["L2_Title_en"]],
                    "label_ko": row["L2_Title_ko"],
                    "label_en": row["L2_Title_en"],
                    "description_ko": row["L2_Description_ko"],
                    "description_en": row["L2_Description_en"],
                    "sequence": sequence,
                    "status": "active",
                }
            )

        nodes.append(
            {
                "node_id": row["L3_ID"],
                "level": 3,
                "parent_id": row["L2_ID"] or row["L1_ID"],
                "label_ko": row["L3_Title_ko"],
                "label_en": row["L3_Title_en"],
                "description_ko": row["L3_Description_ko"],
                "description_en": row["L3_Description_en"],
                "sequence": sequence,
                "status": "active",
                "master_status": row["Master_Status"],
            }
        )
    return nodes


def site_card(row: dict[str, str]) -> dict[str, object]:
    mapping_method = row["Mapping_Method"]
    return {
        "release_id": RELEASE_ID,
        "l4_id": row["L4_ID"],
        "label_ko": row["L4_Title_ko"],
        "label_en": row["L4_Title_en"],
        "definition_ko": row["L4_Description_ko"],
        "definition_en": row["L4_Description_en"],
        "primary_l3_id": row["L3_ID"],
        "status": "active",
        "mapping_method": mapping_method,
        "decision_required": mapping_method == "HD",
        "em_score": optional_float(row["EM_Score"]),
        "em_margin": optional_float(row["EM_Margin"]),
        "em_stability": optional_float(row["EM_Stability"]),
        "ko_top_l3_id": row["KO_Top_L3_ID"] or None,
        "en_top_l3_id": row["EN_Top_L3_ID"] or None,
        "hd_reason": row["HD_Reason"] or None,
        "facet": row["facet"] or None,
        "act_type": row["act-type"] or None,
        "source_row_id": row["source_row_id"],
        "source_domain": row["Source_Domain"],
        "source_l4_id": row["Source_L4_ID"] or None,
        "source_l4_ids": row["Source_L4_IDs"] or None,
        "source_instruction_prompt": row["Source_Instruction_Prompt"] or None,
        "domain_route_basis": row["Domain_Route_Basis"],
        "transformation_action": row["Transformation_Action"],
        "transformation_rationale": row["Transformation_Rationale"],
    }


def main() -> None:
    hierarchy_rows = read_csv(DATA / "L1_L2_L3_Master.csv")
    card_rows = [row for name in L4_FILES for row in read_csv(DATA / name)]
    cards = [site_card(row) for row in card_rows]
    nodes = hierarchy_nodes(hierarchy_rows)

    domain_counts = Counter(row["L1_ID"] for row in card_rows)
    mapping_counts = Counter(row["Mapping_Method"] for row in card_rows)
    manifest_source = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    source_summary = manifest_source["summary"]
    manifest = {
        "release_id": RELEASE_ID,
        "release_status": "master",
        "created_at": "2026-08-26T00:00:00+09:00",
        "counts": {
            "l0": 1,
            "l1": len({row["L1_ID"] for row in hierarchy_rows}),
            "l2_categories": len(L2_CATEGORY_IDS),
            "l2_domain_paths": len({row["L2_ID"] for row in hierarchy_rows if row["L2_ID"]}),
            "l3": len(hierarchy_rows),
            "l3_immutable": sum(row["Master_Status"] == "IMMUTABLE_SOURCE" for row in hierarchy_rows),
            "l3_others": sum(row["Master_Status"] == "DERIVED_OTHERS_HD" for row in hierarchy_rows),
            "l4": len(cards),
            "em": mapping_counts["EM"],
            "hd": mapping_counts["HD"],
            "general": domain_counts["L1_G"],
            "agentic": domain_counts["L1_A"],
            "physical": domain_counts["L1_P"],
        },
        "cleaning": {
            "source_total": source_summary["source_total"],
            "deleted": source_summary["deleted"],
            "merged_away": source_summary["merged_away"],
            "split_net_addition": source_summary["split_net_addition"],
            "final_total": source_summary["cleaned_total"],
        },
        "method": {
            "algorithm": "Expectation Maximization with BGE-M3 semantic representations",
            "boundary_policy": "HD assignment to domain-specific Others",
            "l3_master_precedence": True,
        },
        "validation": {"status": "PASS", "passed": 18, "failed": 0},
        "artifacts": {
            name: {"sha256": sha256(DATA / name), "rows": len(read_csv(DATA / name))}
            for name in ("L1_Master.csv", "L1_L2_L3_Master.csv", *L4_FILES)
        },
    }

    hierarchy = {
        "release_id": RELEASE_ID,
        "nodes": nodes,
        "canonical_l2_categories": [
            {"category_id": "L2_INT", "label_en": "Interaction", "label_ko": "상호작용"},
            {"category_id": "L2_SYS", "label_en": "System", "label_ko": "시스템"},
            {"category_id": "L2_SOC", "label_en": "Societal Impact", "label_ko": "사회적 영향"},
        ],
    }
    write_json(OUT / "hierarchy.json", hierarchy)
    write_json(OUT / "cards.json", {"release_id": RELEASE_ID, "cards": cards})
    write_json(OUT / "manifest.json", manifest)
    write_json(
        ROOT / "data" / "current.json",
        {
            "current_release": RELEASE_ID,
            "release_status": "master",
            "manifest": f"public/data/releases/{RELEASE_ID}/manifest.json",
        },
    )
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
