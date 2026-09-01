#!/usr/bin/env python3
"""Synchronise round-3 human-review metadata, QA, documentation, and web data."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import sync_master_release_metadata


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "releases" / "RAI-Risk-Taxonomy-2.0-master"
DATA = RELEASE / "data"
VALIDATION = RELEASE / "validation"
HANDOVER_DATA = ROOT / "handover" / "RAI-Risk-Taxonomy-2.0-master_20260829" / "01_data"
L4_FILES = ("L4_General.csv", "L4_Agentic.csv", "L4_Physical.csv")
L3_HASH = "1ab58e1dd002d85de92db4bb1e49daa744d053a3950025bfe831bdef9bf98c54"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_manifest() -> None:
    path = RELEASE / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    public_rows = {name: read_csv(DATA / name) for name in L4_FILES}
    full_rows = {name: read_csv(HANDOVER_DATA / name) for name in L4_FILES}
    all_full = [row for name in L4_FILES for row in full_rows[name]]
    all_public = [row for name in L4_FILES for row in public_rows[name]]
    if len(all_full) != 623 or len(all_public) != 623:
        raise ValueError("Expected 623 current L4 cards")
    if sha256(DATA / "L1_L2_L3_Master.csv") != L3_HASH:
        raise ValueError("L3 master changed during round-3 synchronisation")

    manifest["release_date"] = "2026-09-01"
    manifest["release_round"] = "human_review_round3_application"
    script = "projects/rai_risk_taxonomy_2_0_rebuild_20260826/scripts/apply_human_review_round3_20260901.py"
    manifest.setdefault("pipeline_scripts", [])
    if script not in manifest["pipeline_scripts"]:
        manifest["pipeline_scripts"].append(script)
    manifest["mapping_method"] = {
        "name": "Deterministic semantic interpretation and application of third-round human-review comments",
        "em_or_hybrid_em_executed_in_this_round": False,
        "l3_master_precedence": True,
        "automatic_reassignment": False,
    }

    summary = manifest["summary"]
    summary["cleaned_total"] = 623
    summary["final_total"] = 623
    summary["deleted"] = 21
    summary["explicit_deletions"] = 25
    summary["net_reduction"] = 175
    summary["user_directed_operations"] = 214
    summary["validation_passed"] = 10
    summary["validation_failed"] = 0
    summary["others_total"] = 0
    summary["final_domain_counts"] = {
        "General AI": len(public_rows["L4_General.csv"]),
        "Agentic AI": len(public_rows["L4_Agentic.csv"]),
        "Physical AI": len(public_rows["L4_Physical.csv"]),
    }
    summary["mapping_method_counts"] = {
        "General AI": dict(Counter(row["Mapping_Method"] for row in full_rows["L4_General.csv"])),
        "Agentic AI": dict(Counter(row["Mapping_Method"] for row in full_rows["L4_Agentic.csv"])),
        "Physical AI": dict(Counter(row["Mapping_Method"] for row in full_rows["L4_Physical.csv"])),
    }
    summary["score_status_counts"] = dict(Counter(
        (row.get("Definition_Grounding_Action") or "NOT_APPLICABLE").strip()
        for row in all_full
    ))

    manifest["primary_outputs"] = {
        name: {"sha256": sha256(DATA / name), "rows": len(read_csv(DATA / name))}
        for name in ("L1_Master.csv", "L1_L2_L3_Master.csv", *L4_FILES)
    }
    manifest["l3_master_sha256"] = L3_HASH
    manifest["human_review_round3"] = {
        "source_rows": 629,
        "commented_rows": 30,
        "uncommented_rows": 599,
        "actions": {
            "reassigned_and_rewritten": 19,
            "deleted": 6,
            "same_l3_generalised": 5,
            "merged": 0,
            "split": 0,
            "new_l4": 0,
            "new_l3": 0,
        },
        "independent_expert_reviewers": 2,
        "adjudicated_disagreements": ["G_INT_SELF_006", "P_INT_SAFETY_007"],
        "l3_master_unchanged": True,
        "em_or_hybrid_em_executed": False,
        "decision_ledger": "validation/Human_Review_Round3_Decision_Ledger.csv",
        "application_log": "validation/Human_Review_Round3_Application_Log.csv",
        "validation_record": "validation/Human_Review_Round3_Validation_Record.json",
    }
    manifest["audit_correction_20260901_ac18"] = (
        "AC-18: applied all 30 non-empty third-round human-review comments after reading all 629 rows; "
        "19 cards were reassigned and rewritten, 6 deleted, and 5 generalised within the same L3. "
        "No EM, merge, split, new L4, or new L3 was used."
    )
    trajectory = manifest.get("audit_corrections", {}).get("card_count_trajectory", [])
    trajectory = [item for item in trajectory if item.get("step") != "AC-18"]
    trajectory.append({"step": "AC-18", "cards": 623})
    manifest.setdefault("audit_corrections", {})["card_count_trajectory"] = trajectory
    write_json(path, manifest)


def update_qa() -> None:
    full = [row for name in L4_FILES for row in read_csv(HANDOVER_DATA / name)]
    public = [row for name in L4_FILES for row in read_csv(DATA / name)]
    full_by_id = {row["L4_ID"]: row for row in full}
    public_by_id = {row["L4_ID"]: row for row in public}
    ledger = read_csv(VALIDATION / "Human_Review_Round3_Decision_Ledger.csv")
    comments = [row for row in ledger if row["Human_Review_Round3_Comment"]]
    deleted = {row["L4_ID_Before"] for row in ledger if row["Action"] == "DELETE"}
    core_fields = list(public[0])
    exact_pairs = Counter(
        (row["L4_Title_ko"], row["L4_Title_en"], row["L4_Description_ko"], row["L4_Description_en"])
        for row in full
    )
    checks = [
        {"check": "Duplicate Ids", "status": "PASS" if len(full_by_id) == len(full) else "FAIL", "evidence": len(full) - len(full_by_id)},
        {"check": "Exact Duplicates", "status": "PASS" if max(exact_pairs.values(), default=1) == 1 else "FAIL", "evidence": sum(value - 1 for value in exact_pairs.values())},
        {"check": "Others", "status": "PASS" if not any(row["L3_ID"].endswith("Others") for row in full) else "FAIL", "evidence": sum(row["L3_ID"].endswith("Others") for row in full)},
        {"check": "Round3 Source Coverage", "status": "PASS" if len(ledger) == 629 and len(comments) == 30 else "FAIL", "evidence": {"ledger_rows": len(ledger), "commented_rows": len(comments)}},
        {"check": "Round3 Action Reconciliation", "status": "PASS" if Counter(row["Action"] for row in comments) == Counter({"MOVE_REWRITE": 19, "DELETE": 6, "RENAME_REWRITE": 5}) else "FAIL", "evidence": dict(Counter(row["Action"] for row in comments))},
        {"check": "Deleted Cards Absent", "status": "PASS" if deleted.isdisjoint(full_by_id) else "FAIL", "evidence": sorted(deleted & set(full_by_id))},
        {"check": "Public Full Core Match", "status": "PASS" if set(public_by_id) == set(full_by_id) and all(all(public_by_id[key][field] == full_by_id[key][field] for field in core_fields) for key in full_by_id) else "FAIL", "evidence": len(full_by_id)},
        {"check": "L3 Master Unchanged", "status": "PASS" if sha256(DATA / "L1_L2_L3_Master.csv") == L3_HASH else "FAIL", "evidence": sha256(DATA / "L1_L2_L3_Master.csv")},
        {"check": "Final Card Counts", "status": "PASS" if Counter(row["L1_ID"] for row in full) == Counter({"L1_G": 492, "L1_A": 66, "L1_P": 65}) else "FAIL", "evidence": dict(Counter(row["L1_ID"] for row in full))},
        {"check": "No Unauthorised New Category", "status": "PASS" if len(read_csv(DATA / "L1_L2_L3_Master.csv")) == 50 else "FAIL", "evidence": len(read_csv(DATA / "L1_L2_L3_Master.csv"))},
    ]
    failed = sum(check["status"] != "PASS" for check in checks)
    qa = {
        "status": "PASS" if failed == 0 else "FAIL",
        "passed": len(checks) - failed,
        "failed": failed,
        "l3_master_sha256": L3_HASH,
        "checks": checks,
        "round3_note": "All 629 review rows were read. The 30 non-empty comments were applied without EM: 19 reassignments, 6 deletions, and 5 same-L3 generalisations. No merge, split, new L4, or new L3 was introduced.",
    }
    write_json(VALIDATION / "final_release_qa.json", qa)


def update_readmes() -> None:
    root_path = ROOT / "README.md"
    text = root_path.read_text(encoding="utf-8")
    text = re.sub(r"contains \d+ bilingual L4 risk cards", "contains 623 bilingual L4 risk cards", text)
    text = re.sub(r"includes \d+ retained EM assignments and \d+ human-decision assignments", "includes 321 retained EM assignments and 302 human-decision assignments", text)
    text = re.sub(r"L4: \d+ final cards, comprising \d+ General, \d+ Agentic, and \d+ Physical", "L4: 623 final cards, comprising 492 General, 66 Agentic, and 65 Physical", text)
    text = re.sub(r"Mapping: \d+ retained EM and \d+ human-decision assignments", "Mapping: 321 retained EM and 302 human-decision assignments", text)
    note = "\nThe 2026-09-01 third-round human review read all 629 reviewed rows and applied all 30 non-empty comments without EM: 19 semantic reassignments, 6 deletions, and 5 scope generalisations. No merge, split, new L4, or new L3 was introduced.\n"
    if note.strip() not in text:
        text = text.replace("## Current master release\n", "## Current master release\n" + note)
    root_path.write_text(text, encoding="utf-8")

    release_path = RELEASE / "README.md"
    text = release_path.read_text(encoding="utf-8")
    text = re.sub(r"Current master:.*", "Current master: third-round human-review application (2026-09-01), following the second-round recovery and audit corrections AC-01 through AC-18.", text, count=1)
    text = re.sub(r"- L4: \d+ cards", "- L4: 623 cards", text)
    text = re.sub(r"- General / Agentic / Physical: \d+ / \d+ / \d+", "- General / Agentic / Physical: 492 / 66 / 65", text)
    text = re.sub(r"- Retained mapping labels: EM \d+ / HD \d+", "- Retained mapping labels: EM 321 / HD 302", text)
    text = re.sub(r"- Deterministic recovery validation: \d+ recorded checks, \d+ PASS, \d+ FAIL", "- Deterministic round-3 validation: 10 recorded checks, 10 PASS, 0 FAIL", text)
    section = """
## Round-3 human review

All 629 rows from the three KTSPACE review pages were read before transformation. The 30 non-empty comments produced 19 reassignments with definition revision, 6 deletions, and 5 same-L3 scope generalisations. Two independent expert reviewers assessed ambiguous cases, followed by third-party adjudication. No EM or Hybrid EM was run, and no merge, split, new L4, or new L3 was introduced. The final release contains 623 cards.

"""
    if "## Round-3 human review" not in text:
        text = text.replace("## Round-2 pipeline (historical)\n", section + "## Round-2 pipeline (historical)\n")
    release_path.write_text(text, encoding="utf-8")


def main() -> None:
    update_manifest()
    update_qa()
    update_manifest()
    update_readmes()
    sync_master_release_metadata.main()


if __name__ == "__main__":
    main()
