#!/usr/bin/env python3
"""Apply the three user-approved AC-19 Physical AI corrections.

This is a deterministic human decision overlay. It moves two existing cards,
corrects one Korean definition, preserves lineage, and never edits the L3
master or runs EM/Hybrid EM.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "projects" / "rai_risk_taxonomy_2_0_rebuild_20260826"
WORK = PROJECT / "10_physical_minimal_corrections_ac19"
RELEASE = ROOT / "releases" / "RAI-Risk-Taxonomy-2.0-master"
DATA = RELEASE / "data"
VALIDATION = RELEASE / "validation"
HANDOVER = ROOT / "handover" / "RAI-Risk-Taxonomy-2.0-master_20260829"
FULL_DATA = HANDOVER / "01_data"
HANDOVER_VALIDATION = HANDOVER / "03_validation"
L3_MASTER = DATA / "L1_L2_L3_Master.csv"
L3_HASH = "1ab58e1dd002d85de92db4bb1e49daa744d053a3950025bfe831bdef9bf98c54"
L4_FILES = {
    "General": "L4_General.csv",
    "Agentic": "L4_Agentic.csv",
    "Physical": "L4_Physical.csv",
}
HIERARCHY_FIELDS = (
    "L0_ID", "L0_Title_ko", "L0_Title_en",
    "L1_ID", "L1_Title_ko", "L1_Title_en", "L1_Description_ko", "L1_Description_en",
    "L2_ID", "L2_Title_ko", "L2_Title_en", "L2_Description_ko", "L2_Description_en",
    "L3_ID", "L3_Title_ko", "L3_Title_en", "L3_Description_ko", "L3_Description_en",
)
PUBLIC_FIELDS = HIERARCHY_FIELDS + (
    "L4_ID", "L4_Title_ko", "L4_Title_en", "L4_Description_ko", "L4_Description_en",
    "facet", "act-type",
)
SCORE_FIELDS = (
    "EM_Score", "EM_Margin", "EM_Stability", "EM_Anchor_Score",
    "Hybrid_EM_Score", "Hybrid_EM_Margin", "Keyword_Top_L3_ID",
    "Keyword_Support_Score", "Keyword_Semantic_Score", "Keyword_Prior",
    "Keyword_Evidence", "Candidate_1_L3_ID", "Candidate_1_EM_Score",
    "Candidate_1_Hybrid_Score", "Candidate_2_L3_ID", "Candidate_2_EM_Score",
    "Candidate_2_Hybrid_Score", "KO_Top_L3_ID", "EN_Top_L3_ID",
    "Candidate_Constraint_Reason", "Definition_L3_Anchor_Score",
)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str] | tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def append_token(value: str, token: str) -> str:
    parts = [part for part in (value or "").split("|") if part]
    if token not in parts:
        parts.append(token)
    return "|".join(parts)


def archive_current() -> None:
    target = WORK / "archive" / "pre_ac19_20260901"
    if target.exists():
        return
    for subdir, source in (("full_data", FULL_DATA), ("release_data", DATA)):
        destination = target / subdir
        destination.mkdir(parents=True, exist_ok=True)
        for name in (*L4_FILES.values(), "L1_L2_L3_Master.csv"):
            path = source / name
            if path.exists():
                shutil.copy2(path, destination / name)
    for name in ("manifest.json",):
        shutil.copy2(RELEASE / name, target / name)


def update_round3_ledger(corrections: dict[str, dict[str, str]]) -> None:
    for base in (VALIDATION, PROJECT / "09_human_review_round3", HANDOVER_VALIDATION):
        path = base / "Human_Review_Round3_Decision_Ledger.csv"
        fields, rows = read_csv(path)
        for row in rows:
            old_id = row["L4_ID_Before"]
            if old_id not in corrections:
                continue
            after = corrections[old_id]
            row.update({
                "Interpreted_Intent": after["rationale"],
                "Action": after["action"],
                "Final_Disposition": "APPLIED_AC19",
                "L4_ID_After": after["L4_ID"],
                "Domain_After": after["domain"],
                "L2_ID_After": after["L2_ID"],
                "L3_ID_After": after["L3_ID"],
                "L4_Title_ko_After": after["L4_Title_ko"],
                "L4_Title_en_After": after["L4_Title_en"],
                "L4_Description_ko_After": after["L4_Description_ko"],
                "L4_Description_en_After": after["L4_Description_en"],
                "Reviewer_A": "AGREE",
                "Reviewer_B": "AGREE",
                "Adjudication": "USER_APPROVED_AC19",
                "Ambiguity": "LOW",
                "Lineage_Status": "ID_CROSSWALK" if old_id != after["L4_ID"] else "ID_RETAINED",
            })
        write_csv(path, fields, rows)


def update_validation_artifacts(corrections: dict[str, dict[str, str]]) -> None:
    ledger_fields = [
        "Correction_ID", "Date", "Action", "L4_ID_Before", "L4_ID_After",
        "Source_Row_ID", "L1_ID_Before", "L2_ID_Before", "L3_ID_Before",
        "L1_ID_After", "L2_ID_After", "L3_ID_After", "Title_ko",
        "Description_ko_Before", "Description_ko_After", "Rationale",
        "Reviewer_A", "Reviewer_B", "Final_Decision",
    ]
    ledger_rows = []
    for index, (old_id, after) in enumerate(corrections.items(), start=1):
        ledger_rows.append({
            "Correction_ID": f"AC19-{index:02d}", "Date": "2026-09-01",
            "Action": after["action"], "L4_ID_Before": old_id,
            "L4_ID_After": after["L4_ID"], "Source_Row_ID": after["source_row_id"],
            "L1_ID_Before": after["before_l1"], "L2_ID_Before": after["before_l2"],
            "L3_ID_Before": after["before_l3"], "L1_ID_After": after["L1_ID"],
            "L2_ID_After": after["L2_ID"], "L3_ID_After": after["L3_ID"],
            "Title_ko": after["L4_Title_ko"],
            "Description_ko_Before": after["description_ko_before"],
            "Description_ko_After": after["L4_Description_ko"],
            "Rationale": after["rationale"], "Reviewer_A": "AGREE",
            "Reviewer_B": "AGREE", "Final_Decision": "USER_APPROVED_AND_APPLIED",
        })
    for base in (WORK, VALIDATION, HANDOVER_VALIDATION):
        write_csv(base / "Physical_Minimal_Corrections_AC19_Ledger.csv", ledger_fields, ledger_rows)

    record = {
        "correction_id": "AC-19", "date": "2026-09-01",
        "method": "Two independent semantic audits followed by user approval and deterministic application; no EM or Hybrid EM",
        "actions": {"cross_domain_reassignments": 2, "korean_definition_corrections": 1, "deletions": 0, "merges": 0, "splits": 0, "new_l4": 0, "new_l3": 0},
        "id_crosswalk": {old: row["L4_ID"] for old, row in corrections.items() if old != row["L4_ID"]},
        "counts": {"General": 494, "Agentic": 66, "Physical": 63, "total": 623},
        "l3_master_sha256": sha256(L3_MASTER), "l3_master_unchanged": sha256(L3_MASTER) == L3_HASH,
        "status": "PASS",
    }
    for base in (WORK, VALIDATION, HANDOVER_VALIDATION):
        base.mkdir(parents=True, exist_ok=True)
        (base / "Physical_Minimal_Corrections_AC19_Validation.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    methodology = """# AC-19 Physical AI minimum corrections

## Scope

Only three user-approved corrections were applied. No card was deleted, merged, split, or newly created. EM and Hybrid EM were not run.

## Decisions

1. `P_SYS_HARDWARE_001` was reidentified as `G_SYS_PERF_017` and moved to `G_SYS_PERF`, because its causal mechanism is deployment performance degradation under sensor and distribution drift rather than physical breakage or wear of hardware.
2. `P_INT_TAMPER_001` was reidentified as `G_SYS_SECADV_061` and moved to `G_SYS_SECADV`, because sensor spoofing and signal injection are adversarial-input attacks explicitly covered by that L3 and excluded from the physical-tampering boundary.
3. `P_SYS_HARDWARE_003` retained its hierarchy and ID, while the mistranslation `우주선(cosmic ray)` was corrected to `우주 방사선(cosmic ray)`.

## Integrity controls

The 50-row L3 master remained byte-identical. Source row IDs, source IDs, facet and act-type attributes, bilingual titles and definitions, and review lineage were preserved. The final release remains 623 cards with domain counts 494 General, 66 Agentic, and 63 Physical.
"""
    for base in (WORK, VALIDATION, HANDOVER_VALIDATION):
        (base / "Physical_Minimal_Corrections_AC19_Methodology.md").write_text(methodology, encoding="utf-8")


def main() -> None:
    if sha256(L3_MASTER) != L3_HASH:
        raise ValueError("L3 master hash does not match the frozen baseline")
    archive_current()

    all_rows: list[dict[str, str]] = []
    full_fields: list[str] | None = None
    for name in L4_FILES.values():
        fields, rows = read_csv(FULL_DATA / name)
        full_fields = full_fields or fields
        if fields != full_fields:
            raise ValueError("Full-column schemas differ by domain")
        all_rows.extend(rows)
    if len(all_rows) != 623:
        raise ValueError(f"Expected 623 current cards, found {len(all_rows)}")
    by_id = {row["L4_ID"]: row for row in all_rows}
    if len(by_id) != 623:
        raise ValueError("Duplicate L4 IDs before AC-19")
    if (
        {"G_SYS_PERF_017", "G_SYS_SECADV_061"}.issubset(by_id)
        and {"P_SYS_HARDWARE_001", "P_INT_TAMPER_001"}.isdisjoint(by_id)
    ):
        counts = Counter(row["L1_ID"] for row in all_rows)
        if counts != Counter({"L1_G": 494, "L1_A": 66, "L1_P": 63}):
            raise ValueError(f"AC-19 IDs exist but domain counts are inconsistent: {dict(counts)}")
        if "우주 방사선(cosmic ray)" not in by_id["P_SYS_HARDWARE_003"]["L4_Description_ko"]:
            raise ValueError("AC-19 IDs exist but the Korean cosmic-ray correction is absent")
        print(json.dumps({"status": "PASS", "already_applied": True, "total": 623, "l3_master_sha256": L3_HASH}, ensure_ascii=False, indent=2))
        return

    l3_fields, l3_rows = read_csv(L3_MASTER)
    l3_by_id = {row["L3_ID"]: row for row in l3_rows}
    corrections: dict[str, dict[str, str]] = {}
    moves = {
        "P_SYS_HARDWARE_001": ("G_SYS_PERF_017", "G_SYS_PERF",
            "The card describes deployed-system performance degradation caused by sensor and distribution drift. This belongs to Performance and Reliability Failure, not physical hardware breakage or wear."),
        "P_INT_TAMPER_001": ("G_SYS_SECADV_061", "G_SYS_SECADV",
            "Sensor spoofing and signal injection are adversarial-input attacks covered by G_SYS_SECADV and explicitly outside the physical-tampering boundary."),
    }
    if any(new_id in by_id for new_id, _, _ in moves.values()):
        raise ValueError("An AC-19 target ID already exists")
    for old_id, (new_id, l3_id, rationale) in moves.items():
        row = by_id[old_id]
        before = dict(row)
        anchor = l3_by_id[l3_id]
        for field in HIERARCHY_FIELDS:
            row[field] = anchor[field]
        row["L4_ID"] = new_id
        row["Mapping_Method"] = "HD"
        for field in SCORE_FIELDS:
            if field in row:
                row[field] = ""
        row["HD_Reason"] = rationale
        row["Domain_Route_Basis"] = append_token(row.get("Domain_Route_Basis", ""), "USER_APPROVED_AC19_L3_MASTER_BOUNDARY")
        row["Transformation_Action"] = append_token(row.get("Transformation_Action", ""), "AUDIT_CORRECTION_20260901_AC19")
        row["Transformation_Rationale"] = append_token(row.get("Transformation_Rationale", ""), rationale)
        row["Definition_L3_Anchor_ID"] = l3_id
        row["Definition_Grounding_Action"] = "HUMAN_REVIEWED_AC19"
        row["Human_Review_Result"] = append_token(row.get("Human_Review_Result", ""), f"AC-19: {old_id} was moved to {new_id} after two independent audits and user approval.")
        corrections[old_id] = {
            **row, "action": "MOVE_REASSIGN", "domain": "General",
            "before_l1": before["L1_ID"], "before_l2": before["L2_ID"], "before_l3": before["L3_ID"],
            "description_ko_before": before["L4_Description_ko"], "rationale": rationale,
        }

    old_id = "P_SYS_HARDWARE_003"
    row = by_id[old_id]
    before = dict(row)
    old_phrase = "우주선(cosmic ray)에 의한 비트 반전"
    new_phrase = "우주 방사선(cosmic ray)에 의한 비트 반전"
    if old_phrase not in row["L4_Description_ko"]:
        raise ValueError("Expected Korean mistranslation not found")
    row["L4_Description_ko"] = row["L4_Description_ko"].replace(old_phrase, new_phrase)
    row["Transformation_Action"] = append_token(row.get("Transformation_Action", ""), "AUDIT_CORRECTION_20260901_AC19")
    rationale = "Corrected the mistranslation of cosmic ray from 우주선 to 우주 방사선; hierarchy, identifier, and English definition remain unchanged."
    row["Transformation_Rationale"] = append_token(row.get("Transformation_Rationale", ""), rationale)
    row["Human_Review_Result"] = append_token(row.get("Human_Review_Result", ""), "AC-19: cosmic ray 용어를 우주 방사선으로 교정함.")
    corrections[old_id] = {
        **row, "action": "KOREAN_DEFINITION_CORRECTION", "domain": "Physical",
        "before_l1": before["L1_ID"], "before_l2": before["L2_ID"], "before_l3": before["L3_ID"],
        "description_ko_before": before["L4_Description_ko"], "rationale": rationale,
    }

    all_rows = [row for row in all_rows]
    order_by_l3 = {row["L3_ID"]: index for index, row in enumerate(l3_rows)}
    all_rows.sort(key=lambda row: (order_by_l3[row["L3_ID"]], int(row["L4_ID"].rsplit("_", 1)[-1]), row["L4_ID"]))
    domains = {"General": [], "Agentic": [], "Physical": []}
    for row in all_rows:
        domains[{"L1_G": "General", "L1_A": "Agentic", "L1_P": "Physical"}[row["L1_ID"]]].append(row)
    counts = {domain: len(rows) for domain, rows in domains.items()}
    if counts != {"General": 494, "Agentic": 66, "Physical": 63}:
        raise ValueError(f"Unexpected AC-19 counts: {counts}")
    if len({row["L4_ID"] for row in all_rows}) != 623:
        raise ValueError("Duplicate final L4 IDs")
    for domain, rows in domains.items():
        write_csv(FULL_DATA / L4_FILES[domain], full_fields or [], rows)
        write_csv(DATA / L4_FILES[domain], PUBLIC_FIELDS, rows)

    update_round3_ledger(corrections)
    update_validation_artifacts(corrections)

    for base in (VALIDATION, HANDOVER_VALIDATION):
        ref_path = base / "L4_Journal_Reference_Verified.csv"
        fields, rows = read_csv(ref_path)
        for ref in rows:
            if ref.get("L4_ID") == "P_SYS_HARDWARE_001":
                ref["L4_ID"] = "G_SYS_PERF_017"
            elif ref.get("L4_ID") == "P_INT_TAMPER_001":
                ref["L4_ID"] = "G_SYS_SECADV_061"
        write_csv(ref_path, fields, rows)

    for base in (VALIDATION, HANDOVER_VALIDATION):
        path = base / "Audit_Correction_Log.csv"
        fields, rows = read_csv(path)
        rows = [row for row in rows if row["Correction_ID"] != "AC-19"]
        rows.append({
            "Correction_ID": "AC-19", "Date": "2026-09-01",
            "Type": "PHYSICAL_AI_MINIMUM_CORRECTIONS", "Target": "3 L4 cards",
            "Action": "2_CROSS_DOMAIN_REASSIGN_1_KOREAN_DEFINITION_CORRECTION",
            "Detail": "Moved P_SYS_HARDWARE_001 to G_SYS_PERF_017 and P_INT_TAMPER_001 to G_SYS_SECADV_061; corrected cosmic ray terminology in P_SYS_HARDWARE_003. No deletion, merge, split, new semantic card, new L3, or EM rerun.",
            "Basis": "Two independent expert audits, frozen L3 master boundaries, and explicit user approval.",
        })
        write_csv(path, fields, rows)

    if sha256(L3_MASTER) != L3_HASH:
        raise ValueError("L3 master changed during AC-19")
    print(json.dumps({"status": "PASS", "counts": counts, "total": 623, "l3_master_sha256": L3_HASH}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
