#!/usr/bin/env python3
"""Validate and synchronize the fourth-round human-review data release."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "projects" / "rai_risk_taxonomy_2_0_rebuild_20260826"
SOURCE = PROJECT / "00_source_snapshot" / "csv"
WORK = PROJECT / "10_human_review_round4"
RELEASE = ROOT / "releases" / "RAI-Risk-Taxonomy-2.0-master"
DATA = RELEASE / "data"
VALIDATION = RELEASE / "validation"
HANDOVER = ROOT / "handover" / "RAI-Risk-Taxonomy-2.0-master_20260829"
FULL_DATA = HANDOVER / "01_data"
HANDOVER_VALIDATION = HANDOVER / "03_validation"
REPORT_HANDOVER = ROOT / "handover" / "RAI-Risk-Taxonomy-2.0-technical-report_20260901"
WEB = ROOT / "public" / "data" / "releases" / "RAI-Risk-Taxonomy-2.0-master"

L4_FILES = ("L4_General.csv", "L4_Agentic.csv", "L4_Physical.csv")
REVIEW_FILES = {
    "General": "L4_General_Human_Review_Round4_KTSPACE_937139849_20260901.csv",
    "Agentic": "L4_Agentic_Human_Review_Round4_KTSPACE_937205808_20260901.csv",
    "Physical": "L4_Physical_Human_Review_Round4_KTSPACE_938216713_20260901.csv",
}
HIERARCHY_FIELDS = (
    "L0_ID", "L0_Title_ko", "L0_Title_en", "L1_ID", "L1_Title_ko", "L1_Title_en",
    "L1_Description_ko", "L1_Description_en", "L2_ID", "L2_Title_ko", "L2_Title_en",
    "L2_Description_ko", "L2_Description_en", "L3_ID", "L3_Title_ko", "L3_Title_en",
    "L3_Description_ko", "L3_Description_en",
)
CORE_FIELDS = (
    "L3_ID", "L4_Title_ko", "L4_Title_en", "L4_Description_ko", "L4_Description_en",
    "facet", "act-type",
)
RETIRED = {"G_SYS_SECADV_033", "G_SYS_SECADV_048"}
REQUIRED = {
    "G_SYS_POLICY_009", "G_SYS_POLICY_010", "G_INT_WEAP_032", "G_SYS_SECADV_060",
    "G_INT_WEAP_026", "A_SYS_AUTH_025", "G_SYS_SECADV_049", "G_INT_REPR_009",
    "G_SYS_POLICY_005", "G_SYS_SECADV_026", "G_SYS_PERF_019", "G_SYS_PERF_015",
}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    full_rows = [row for name in L4_FILES for row in read_csv(FULL_DATA / name)[1]]
    public_rows = [row for name in L4_FILES for row in read_csv(DATA / name)[1]]
    full_by_id = {row["L4_ID"]: row for row in full_rows}
    public_by_id = {row["L4_ID"]: row for row in public_rows}
    _, l3_rows = read_csv(DATA / "L1_L2_L3_Master.csv")
    l3_by_id = {row["L3_ID"]: row for row in l3_rows}
    _, ledger = read_csv(WORK / "Human_Review_Round4_Decision_Ledger.csv")

    review_rows: dict[str, list[dict[str, str]]] = {}
    for domain, name in REVIEW_FILES.items():
        review_rows[domain] = read_csv(SOURCE / name)[1]

    duplicate_ids = len(full_rows) - len(full_by_id)
    exact_duplicate_keys = Counter(
        (row["L3_ID"], row["L4_Title_ko"], row["L4_Title_en"], row["L4_Description_ko"], row["L4_Description_en"])
        for row in full_rows
    )
    exact_duplicates = sum(count - 1 for count in exact_duplicate_keys.values() if count > 1)
    core_mismatches = [
        l4_id for l4_id in full_by_id
        if l4_id not in public_by_id
        or any(full_by_id[l4_id].get(field, "") != public_by_id[l4_id].get(field, "") for field in CORE_FIELDS)
    ]
    hierarchy_mismatches = [
        row["L4_ID"] for row in full_rows
        if any(row.get(field, "") != l3_by_id[row["L3_ID"]].get(field, "") for field in HIERARCHY_FIELDS)
    ]
    changed_rows = [row for row in full_rows if "HUMAN_REVIEW_ROUND4" in row.get("Transformation_Action", "")]
    stale_scores = [
        row["L4_ID"] for row in changed_rows
        if any(row.get(field, "").strip() for field in ("EM_Score", "Hybrid_EM_Score", "Hybrid_EM_Margin", "EM_Stability"))
    ]
    refs = read_csv(VALIDATION / "L4_Journal_Reference_Verified.csv")[1]
    lineage = read_csv(VALIDATION / "Source_Output_Lineage_Edges.csv")[1]
    missing_ref_ids = sorted({row["L4_ID"] for row in refs if row["L4_ID"] not in full_by_id})
    missing_lineage_ids = sorted({row["L4_ID"] for row in lineage if row["L4_ID"] not in full_by_id})

    general_comments = Counter((row["휴먼검수 4차 의견"] or "").strip() for row in review_rows["General"])
    physical_comments = Counter((row["휴먼검수 4차 의견"] or "").strip() for row in review_rows["Physical"])
    agentic_blank = sum(not (row["휴먼검수 4차 의견"] or "").strip() for row in review_rows["Agentic"])
    domain_counts = Counter(row["L1_ID"] for row in full_rows)

    checks = [
        ("Unique L4 IDs", duplicate_ids == 0, duplicate_ids),
        ("Exact duplicate L4 cards", exact_duplicates == 0, exact_duplicates),
        ("Final card counts", domain_counts == {"L1_G": 492, "L1_A": 67, "L1_P": 63}, dict(domain_counts)),
        ("Zero final Others assignments", not any("Others" in row["L3_ID"] for row in full_rows), sum("Others" in row["L3_ID"] for row in full_rows)),
        ("Round4 source coverage", sum(len(rows) for rows in review_rows.values()) == 623 and len(ledger) == 623, {"source": sum(len(rows) for rows in review_rows.values()), "ledger": len(ledger)}),
        ("General review-state reconciliation", general_comments["ok"] == 473 and len(review_rows["General"]) == 492, {"no_objection": general_comments["ok"], "total": len(review_rows["General"])}),
        ("Agentic blank-state preservation", agentic_blank == 66, agentic_blank),
        ("Physical review-state reconciliation", physical_comments["stay"] == 61 and len(review_rows["Physical"]) == 65, {"stay": physical_comments["stay"], "total": len(review_rows["Physical"])}),
        ("Round4 result-column coverage", all(row.get("휴먼검수 4차 반영결과", "").strip() for row in full_rows), sum(bool(row.get("휴먼검수 4차 반영결과", "").strip()) for row in full_rows)),
        ("Public and full core-field match", not core_mismatches and set(public_by_id) == set(full_by_id), core_mismatches),
        ("L3 master metadata alignment", not hierarchy_mismatches, hierarchy_mismatches),
        ("Confidential Information Disclosure expansion", l3_by_id["G_SYS_POLICY"]["L3_Title_en"] == "Confidential Information Disclosure" and l3_by_id["G_SYS_POLICY"]["L3_Title_ko"] == "기밀정보 노출", l3_by_id["G_SYS_POLICY"]["L3_Title_en"]),
        ("Discussion dispositions present", REQUIRED <= set(full_by_id) and RETIRED.isdisjoint(full_by_id), {"required_missing": sorted(REQUIRED - set(full_by_id)), "retired_present": sorted(RETIRED & set(full_by_id))}),
        ("No rerun scores on Round4-changed cards", not stale_scores, stale_scores),
        ("Reference target integrity", not missing_ref_ids, missing_ref_ids),
        ("Lineage target integrity", not missing_lineage_ids, missing_lineage_ids),
    ]
    check_rows = [{"check": name, "status": "PASS" if passed else "FAIL", "evidence": evidence} for name, passed, evidence in checks]
    failed = sum(not passed for _, passed, _ in checks)
    qa = {
        "status": "PASS" if failed == 0 else "FAIL",
        "passed": len(checks) - failed,
        "failed": failed,
        "release_round": "human_review_round4",
        "l3_master_sha256": sha256(DATA / "L1_L2_L3_Master.csv"),
        "checks": check_rows,
        "round4_note": "All 623 rows were read without EM. General: 473 no-objection, 2 split, 8 move, 9 discussion. Agentic: 66 blank values excluded from approval. Physical: 61 stay, 4 special. All discussion rows were adjudicated and recorded in a dedicated Korean result column.",
        "structural_sync_note": "Two pre-existing Agentic parent-metadata mismatches were synchronized to the unchanged L3 master without inferring human approval or changing L3 placement.",
    }
    if failed:
        raise ValueError(json.dumps(qa, ensure_ascii=False, indent=2))

    for target in (VALIDATION / "final_release_qa.json", HANDOVER_VALIDATION / "final_release_qa.json", REPORT_HANDOVER / "04_analysis_validation" / "final_release_qa.json"):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for target in (WORK, VALIDATION, HANDOVER_VALIDATION):
        path = target / "Human_Review_Round4_Validation_Record.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["actions"]["structural_l3_master_alignment_rows"] = 2
        record["structural_l3_master_alignment_ids"] = ["A_SYS_GOAL_023", "A_SYS_AUTH_024"]
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest_path = RELEASE / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["summary"]["validation_passed"] = qa["passed"]
    manifest["summary"]["validation_failed"] = qa["failed"]
    manifest["primary_outputs"] = {
        name: {"sha256": sha256(DATA / name), "rows": len(read_csv(DATA / name)[1])}
        for name in ("L1_Master.csv", "L1_L2_L3_Master.csv", *L4_FILES)
    }
    manifest["human_review_round4"]["result_column"] = "휴먼검수 4차 반영결과"
    manifest["human_review_round4"]["discussion_rows_adjudicated"] = 9
    manifest["human_review_round4"]["structural_l3_master_alignment_rows"] = 2
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for name in ("cards.json", "hierarchy.json", "manifest.json"):
        shutil.copy2(WEB / name, HANDOVER / "04_web" / ("public_manifest.json" if name == "manifest.json" else name))
    shutil.copy2(ROOT / "index.html", HANDOVER / "04_web" / "index.html")
    shutil.copy2(manifest_path, HANDOVER_VALIDATION / "manifest.json")

    hierarchy_summary = []
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in full_rows:
        grouped.setdefault(row["L3_ID"], []).append(row)
    for l3 in l3_rows:
        cards = grouped.get(l3["L3_ID"], [])
        hierarchy_summary.append({
            "L1_ID": l3["L1_ID"], "L1_Title_en": l3["L1_Title_en"], "L2_ID": l3["L2_ID"],
            "L2_Title_en": l3["L2_Title_en"], "L3_ID": l3["L3_ID"], "L3_Title_en": l3["L3_Title_en"],
            "L4_Count": str(len(cards)), "Representative_L4_ID": cards[0]["L4_ID"] if cards else "",
            "Representative_L4_Title_en": cards[0]["L4_Title_en"] if cards else "",
        })
    summary_path = REPORT_HANDOVER / "04_analysis_validation" / "final_hierarchy_summary.csv"
    write_csv(summary_path, list(hierarchy_summary[0]), hierarchy_summary)

    l2_counts = Counter((row["L1_ID"], row["L1_Title_en"], row["L2_ID"], row["L2_Title_en"]) for row in full_rows)
    l2_rows = [
        {"L1_ID": key[0], "L1_Title_en": key[1], "L2_ID": key[2], "L2_Title_en": key[3], "L4_Count": str(count)}
        for key, count in sorted(l2_counts.items())
    ]
    write_csv(REPORT_HANDOVER / "04_analysis_validation" / "final_l2_counts_master_aligned.csv", list(l2_rows[0]), l2_rows)

    for base in (HANDOVER, REPORT_HANDOVER):
        checksum_path = base / "SHA256SUMS.txt"
        files = sorted(path for path in base.rglob("*") if path.is_file() and path != checksum_path)
        checksum_path.write_text("".join(f"{sha256(path)}  {path.relative_to(base)}\n" for path in files), encoding="utf-8")

    print(json.dumps({"status": qa["status"], "checks": len(checks), "counts": dict(domain_counts)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
