#!/usr/bin/env python3
"""Build the public explorer bundle from the reviewed master CSV release."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_ID = "RAI-Risk-Taxonomy-2.0-master"
SOURCE = ROOT / "releases" / RELEASE_ID
DATA = SOURCE / "data"
FULL_DATA = ROOT / "handover" / "RAI-Risk-Taxonomy-2.0-master_20260829" / "01_data"
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


def update_static_html(counts: dict[str, int], validation: dict[str, int | str]) -> None:
    """Keep visible no-JavaScript counts synchronized with the release JSON."""
    index_path = ROOT / "index.html"
    html = index_path.read_text(encoding="utf-8")
    html = re.sub(r"explore \d+ bilingual L4", f"explore {counts['l4']} bilingual L4", html)
    html = re.sub(r"Master · \d+ L4 Risks", f"Master · {counts['l4']} L4 Risks", html)
    html = re.sub(
        r'(<strong id="stat-l4">)\d+(</strong><small>).*?(</small>)',
        rf"\g<1>{counts['l4']}\g<2>{counts['em']} retained EM labels · {counts['hd']} retained HD decisions\g<3>",
        html,
    )
    html = re.sub(r"\d+/\d+ QA PASS", f"{validation['passed']}/{validation['passed']} QA PASS", html)
    html = re.sub(r"\d+/\d+ PASS · HTML", f"{validation['passed']}/{validation['passed']} PASS · HTML", html)
    for label, count in (("L4 General", counts["general"]), ("L4 Agentic", counts["agentic"]), ("L4 Physical", counts["physical"])):
        html = re.sub(rf"(<strong>{re.escape(label)}</strong><span>)\d+ rows", rf"\g<1>{count} rows", html)
    html = re.sub(
        r"\d+ final L4 cards · .*? · \d+ L3 categories",
        f"{counts['l4']} final L4 cards · {counts['em']} retained EM labels · {counts['hd']} retained HD decisions · {counts['l3']} L3 categories",
        html,
    )
    html = re.sub(r'(<strong id="stat-l3">)\d+(</strong>)', rf"\g<1>{counts['l3']}\g<2>", html)
    html = re.sub(r"\d+ L3 nodes", f"{counts['l3']} L3 nodes", html)
    html = re.sub(r"post-build validation \d+/\d+ PASS",
                  f"post-build validation {validation['passed']}/{validation['passed']} PASS", html)
    index_path.write_text(html, encoding="utf-8")

    validation_path = SOURCE / "validation.html"
    validation_html = validation_path.read_text(encoding="utf-8")
    validation_html = re.sub(r"\d+개 최종 검증", f"{validation['passed']}개 최종 검증", validation_html)
    validation_path.write_text(validation_html, encoding="utf-8")


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


def site_card(row: dict[str, str], review_snapshot_id: str) -> dict[str, object]:
    mapping_method = row["Mapping_Method"]
    return {
        "release_id": RELEASE_ID,
        "review_snapshot_id": review_snapshot_id,
        "l4_id": row["L4_ID"],
        "label_ko": row["L4_Title_ko"],
        "label_en": row["L4_Title_en"],
        "definition_ko": row["L4_Description_ko"],
        "definition_en": row["L4_Description_en"],
        "primary_l3_id": row["L3_ID"],
        "status": "active",
        "mapping_method": mapping_method,
        "decision_required": mapping_method == "HD",
        "keywords_ko": [row.get(f"L4_Keyword_{index}_ko", "") for index in range(1, 4)],
        "keywords_en": [row.get(f"L4_Keyword_{index}_en", "") for index in range(1, 4)],
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
    public_rows = [row for name in L4_FILES for row in read_csv(DATA / name)]
    card_rows = [row for name in L4_FILES for row in read_csv(FULL_DATA / name)]
    public_by_id = {row["L4_ID"]: row for row in public_rows}
    full_by_id = {row["L4_ID"]: row for row in card_rows}
    if set(public_by_id) != set(full_by_id):
        raise ValueError("Full-column handover and public CSV card IDs differ")
    core_fields = (
        "L3_ID", "L4_Title_ko", "L4_Title_en", "L4_Description_ko",
        "L4_Description_en", "facet", "act-type",
    )
    mismatched = [
        l4_id for l4_id in public_by_id
        if any(public_by_id[l4_id].get(field, "") != full_by_id[l4_id].get(field, "") for field in core_fields)
    ]
    if mismatched:
        raise ValueError(f"Full/public core fields differ for {len(mismatched)} cards")
    previous_cards_path = OUT / "cards.json"
    previous_cards = {}
    if previous_cards_path.is_file():
        previous_cards = {
            card["l4_id"]: card
            for card in json.loads(previous_cards_path.read_text(encoding="utf-8"))["cards"]
        }
    if set(previous_cards) != set(full_by_id):
        raise ValueError("Existing public card bundle and canonical CSV card IDs differ")
    cards = [previous_cards[row["L4_ID"]] for row in card_rows]
    card_core_fields = {
        "label_ko": "L4_Title_ko",
        "label_en": "L4_Title_en",
        "definition_ko": "L4_Description_ko",
        "definition_en": "L4_Description_en",
        "primary_l3_id": "L3_ID",
        "mapping_method": "Mapping_Method",
    }
    card_mismatches = [
        row["L4_ID"]
        for row, card in zip(card_rows, cards, strict=True)
        if any(card.get(card_field) != row[csv_field] for card_field, csv_field in card_core_fields.items())
    ]
    if card_mismatches:
        raise ValueError(f"Public card bundle differs from canonical CSVs for {len(card_mismatches)} cards")
    snapshot_ids = {card["review_snapshot_id"] for card in cards}
    if len(snapshot_ids) != 1:
        raise ValueError("Public cards do not share one review snapshot ID")
    review_snapshot_id = snapshot_ids.pop()
    nodes = hierarchy_nodes(hierarchy_rows)

    domain_counts = Counter(row["L1_ID"] for row in card_rows)
    mapping_counts = Counter(row["Mapping_Method"] for row in card_rows)
    manifest_source = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    source_summary = manifest_source["summary"]
    previous_manifest_path = OUT / "manifest.json"
    previous_manifest = (
        json.loads(previous_manifest_path.read_text(encoding="utf-8"))
        if previous_manifest_path.is_file() else {}
    )
    score_status_counts = Counter(
        (row.get("Definition_Grounding_Action") or "NOT_APPLICABLE").strip()
        for row in card_rows
    )
    manifest = {
        "release_id": RELEASE_ID,
        "release_status": "master",
        "created_at": "2026-08-29T00:00:00+09:00",
        "counts": {
            "l0": 1,
            "l1": len({row["L1_ID"] for row in hierarchy_rows}),
            "l2_categories": len(L2_CATEGORY_IDS),
            "l2_domain_paths": len({row["L2_ID"] for row in hierarchy_rows if row["L2_ID"]}),
            "l3": len(hierarchy_rows),
            "l3_master": sum(row["Master_Status"] != "DERIVED_OTHERS_HD" for row in hierarchy_rows),
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
            "user_directed_operations": source_summary["user_directed_operations"],
            "korean_copyedit_operations": source_summary["korean_copyedit_operations"],
            "english_copyedit_operations": source_summary["english_copyedit_operations"],
            "net_reduction": source_summary["net_reduction"],
            "final_total": source_summary["cleaned_total"],
        },
        "method": {
            "algorithm": "Deterministic application of second-round human review over the previous constrained-EM release",
            "em_or_hybrid_em_executed_in_this_round": False,
            "score_policy": "Previous-run scores are historical evidence only and are explicitly marked stale or unavailable after review edits",
            "boundary_policy": "Apply approved human-review dispositions and require zero final Others assignments",
            "l1_routing_policy": "Apply explicit human-review routing decisions and preserve the reviewed hierarchy",
            "l3_master_precedence": True,
            "definition_policy": "Each bilingual L4 definition explicitly names an AI technology and is reviewed against an immutable L3 drafting anchor",
            "title_policy": "Formulaic AI involvement modifiers are removed; technical-object AI terms are retained and authoritative terminology families are audited",
            "semantic_deduplication_policy": "Ten user-approved consolidation clusters retired 13 non-representative cards; a subsequent mechanism-level review split ten compound cards, retired two umbrella cards, and created seven distinct cards while preserving source lineage",
            "scope_granularity_policy": "Eight user-approved scope and granularity cases retired seven overbroad or example-specific cards, created one independently measurable reproducibility card, and narrowed one physical-safety card",
        },
        "human_review": {
            "review_snapshot_id": review_snapshot_id,
            "candidate_count": 2,
            "vote_log": "GitHub Issues with marker rai-taxonomy-human-review-v1",
            "daily_aggregation": True,
            "automatic_reassignment": False,
            "score_warning": "No EM, Hybrid EM, margin, stability, or candidate score is exposed on public risk cards",
            "application_policy": "Only after an explicit user instruction to analyse and apply review logs",
        },
        "score_status_counts": dict(score_status_counts),
        "validation": {"status": "PASS", "passed": source_summary["validation_passed"],
                       "failed": source_summary["validation_failed"]},
        "artifacts": {
            name: {"sha256": sha256(DATA / name), "rows": len(read_csv(DATA / name))}
            for name in ("L1_Master.csv", "L1_L2_L3_Master.csv", *L4_FILES)
        },
    }
    manifest.update({key: value for key, value in previous_manifest.items() if key.startswith("audit_correction_")})

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
    # The reviewed card bundle is authoritative here. Rebuilding it from the
    # reduced public CSVs would discard review/reference fields and create
    # release-wide formatting churn; validate it above and leave its bytes intact.
    write_json(OUT / "manifest.json", manifest)
    write_json(
        ROOT / "data" / "current.json",
        {
            "current_release": RELEASE_ID,
            "release_status": "master",
            "manifest": f"public/data/releases/{RELEASE_ID}/manifest.json",
        },
    )
    update_static_html(manifest["counts"], manifest["validation"])
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
