#!/usr/bin/env python3
"""Publish the reviewed 800-card human-review round-two release.

This synchronisation step does not run EM or Hybrid EM. It preserves prior
scores only as explicitly labelled historical evidence and marks scores that
became unavailable after human review.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parents[1]
BASE_RELEASE = PROJECT / "03_outputs" / "release"
ROUND2 = PROJECT / "05_human_review_round2"
MASTER = REPO / "releases" / "RAI-Risk-Taxonomy-2.0-master"
MASTER_DATA = MASTER / "data"
VALIDATION = MASTER / "validation"
FIGURES = MASTER / "figures"
TABLES = MASTER / "tables"
PROJECT_FIGURES = PROJECT / "output" / "figures"

DOMAINS = ("General", "Agentic", "Physical")
DOMAIN_LABELS = {"General": "General AI", "Agentic": "Agentic AI", "Physical": "Physical AI"}
COLORS = {"General": "#3366CC", "Agentic": "#E68613", "Physical": "#2A9D6F"}
PREVIOUS_COUNTS = {"General": 599, "Agentic": 90, "Physical": 119}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    for directory in (MASTER_DATA, VALIDATION, FIGURES, TABLES, PROJECT_FIGURES, MASTER / "reports"):
        directory.mkdir(parents=True, exist_ok=True)

    shutil.copy2(BASE_RELEASE / "L1_Master.csv", MASTER_DATA / "L1_Master.csv")
    shutil.copy2(BASE_RELEASE / "L1_L2_L3_Master.csv", MASTER_DATA / "L1_L2_L3_Master.csv")
    for domain in DOMAINS:
        shutil.copy2(
            ROUND2 / f"L4_{domain}_Human_Review_Round2_Applied.csv",
            MASTER_DATA / f"L4_{domain}.csv",
        )

    rows = [row for domain in DOMAINS for row in read_csv(MASTER_DATA / f"L4_{domain}.csv")]
    ledger = read_csv(ROUND2 / "Human_Review_Round2_Decision_Ledger.csv")
    round2_summary = json.loads((ROUND2 / "Human_Review_Round2_Summary.json").read_text(encoding="utf-8"))
    self_validation = json.loads((ROUND2 / "Human_Review_Round2_Self_Validation.json").read_text(encoding="utf-8"))
    previous_manifest = json.loads((BASE_RELEASE / "release_manifest.json").read_text(encoding="utf-8"))
    language_review_path = ROUND2 / "Expert_Language_Review_Final_20260829.json"
    language_review = (
        json.loads(language_review_path.read_text(encoding="utf-8"))
        if language_review_path.exists()
        else {"status": "PENDING", "reviews": []}
    )

    domain_counts = Counter(row["L1_Title_en"] for row in rows)
    mapping_counts = {
        DOMAIN_LABELS[domain]: Counter(
            row["Mapping_Method"] for row in rows if row["L1_Title_en"] == DOMAIN_LABELS[domain]
        )
        for domain in DOMAINS
    }
    action_counts = Counter(row["Definition_Grounding_Action"] for row in rows)
    text_edited_cards = sum(
        "KOREAN_COPYEDIT" in row["Transformation_Action"]
        or "ENGLISH_COPYEDIT" in row["Transformation_Action"]
        for row in rows
    )
    score_available = sum(bool(row["EM_Score"].strip()) for row in rows)
    others_total = sum(row["L3_ID"].endswith("Others") for row in rows)
    ledger_after_ids = [
        final_id.strip()
        for row in ledger
        for final_id in row["L4_ID_After"].split("|")
        if final_id.strip()
    ]
    explicit_deletions = sum(not row["L4_ID_After"].strip() for row in ledger)
    split_net_addition = sum(
        max(
            len([final_id for final_id in row["L4_ID_After"].split("|") if final_id.strip()]) - 1,
            0,
        )
        for row in ledger
    )
    merged_away = len(ledger_after_ids) - len(set(ledger_after_ids))
    validation_checks = [
        {
            "check": name.replace("_", " ").title(),
            "status": "PASS" if passed else "FAIL",
            "evidence": validation_evidence(name, self_validation),
        }
        for name, passed in self_validation["checks"].items()
    ]
    qa = {
        "status": self_validation["status"],
        "passed": sum(item["status"] == "PASS" for item in validation_checks),
        "failed": sum(item["status"] == "FAIL" for item in validation_checks),
        "checks": validation_checks,
        "independent_language_review": language_review,
        "l3_master_sha256": self_validation["l3_master_sha256"],
    }
    write_json(VALIDATION / "final_release_qa.json", qa)

    audit_files = (
        "Human_Review_Round2_Decision_Ledger.csv",
        "L3_Human_Review_Round2_Decision_Ledger.csv",
        "L4_Korean_Copyedit_Approved_20260829.csv",
        "L4_English_Copyedit_Approved_20260829.csv",
        "L4_Final_Terminology_L3_Alignment_Approved_20260829.csv",
        "Expert_Language_Review_Final_20260829.json",
        "user_directed_operations.csv",
        "L4_Top10_Similar_Pairs.csv",
        "L4_Top10_Similar_Pairs_Metadata.json",
        "L4_Top20_Similar_Pairs.csv",
        "L4_Top20_Similar_Pairs_Metadata.json",
        "L4_Top200_Similar_Pairs.csv",
        "L4_Top200_Similar_Pairs_Metadata.json",
        "L4_Top1000_SameL3_Similar_Pairs.csv",
        "L4_Top1000_SameL3_Similar_Pairs_Metadata.json",
    )
    for name in audit_files:
        source = ROUND2 / name
        if source.exists():
            shutil.copy2(source, VALIDATION / name)

    summary = {
        "date": "2026-08-29",
        "round": "human_review_round2",
        "input_rows": round2_summary["input_rows"],
        "source_total": round2_summary["input_rows"],
        "final_total": len(rows),
        "cleaned_total": len(rows),
        "net_reduction": round2_summary["input_rows"] - len(rows),
        "explicit_deletions": explicit_deletions,
        "deleted": explicit_deletions,
        "net_consolidation_after_splits": merged_away - split_net_addition,
        "merged_away": merged_away,
        "split_net_addition": split_net_addition,
        "source_counts": PREVIOUS_COUNTS,
        "final_domain_counts": {label: domain_counts[label] for label in DOMAIN_LABELS.values()},
        "mapping_method_counts": {
            label: {"EM": counts["EM"], "HD": counts["HD"]}
            for label, counts in mapping_counts.items()
        },
        "em_total": sum(row["Mapping_Method"] == "EM" for row in rows),
        "hd_total": sum(row["Mapping_Method"] == "HD" for row in rows),
        "others_total": others_total,
        "user_directed_operations": round2_summary["user_directed_operations"],
        "korean_copyedit_operations": round2_summary["korean_copyedit_operations"],
        "english_copyedit_operations": round2_summary["english_copyedit_operations"],
        "final_terminology_l3_qa_operations": round2_summary[
            "final_terminology_l3_qa_operations"
        ],
        "text_edited_cards": text_edited_cards,
        "score_available_from_previous_run": score_available,
        "score_unavailable_after_human_review": len(rows) - score_available,
        "score_status_counts": dict(action_counts),
        "similarity_ranked_pairs": 200,
        "similarity_top_pairs_published": 20,
        "l3_source_rows": 46,
        "l3_derived_others_rows": 3,
        "validation_passed": qa["passed"],
        "validation_failed": qa["failed"],
    }
    primary_outputs = {
        name: {"sha256": sha256(MASTER_DATA / name), "rows": len(read_csv(MASTER_DATA / name))}
        for name in (
            "L1_Master.csv", "L1_L2_L3_Master.csv", "L4_General.csv", "L4_Agentic.csv", "L4_Physical.csv"
        )
    }
    manifest = {
        "release_date": "2026-08-29",
        "release_id": "RAI-Risk-Taxonomy-2.0-master",
        "release_round": "human_review_round2",
        "pipeline_script": "projects/rai_risk_taxonomy_2_0_rebuild_20260826/scripts/apply_human_review_round2.py",
        "source_hashes": {
            "L3_Master": round2_summary["l3_master_sha256"],
            "Round2_Source_Manifest": round2_summary["round2_source_manifest_sha256"],
            "User_Directed_Operations": round2_summary["user_directed_operations_sha256"],
            "Korean_Copyedit_Manifest": round2_summary["korean_copyedit_manifest_sha256"],
            "English_Copyedit_Manifest": round2_summary["english_copyedit_manifest_sha256"],
            "Final_Terminology_L3_QA_Manifest": round2_summary[
                "final_terminology_l3_qa_manifest_sha256"
            ],
        },
        "model": previous_manifest["model"],
        "mapping_method": {
            "name": "Human-review application over the previous constrained-EM release",
            "em_or_hybrid_em_executed_in_this_round": False,
            "score_status": "Previous-run scores are retained only where available and are explicitly marked stale after text edits",
            "l3_master_precedence": True,
            "automatic_reassignment": False,
        },
        "definition_method": {
            "name": "Immutable-L3-referenced bilingual AI-technology and language review",
            "korean_ai_technology_required": True,
            "english_ai_technology_required": True,
            "causal_risk_mechanism_required": True,
            "l3_tone_required": True,
        },
        "title_terminology_method": {
            "name": "Human-reviewed policy, legal, and technical terminology normalisation",
            "formulaic_ai_involvement_qualifiers_removed": True,
            "technical_object_ai_terms_retained": True,
        },
        "similarity_review": {
            "model": "BAAI/bge-m3",
            "purpose": "Near-duplicate candidate review only; not L3 reassignment",
            "ranked_pairs": 200,
            "top_pairs_published": 20,
            "automatic_deletion": False,
        },
        "primary_outputs": primary_outputs,
        "summary": summary,
        "human_review": {
            "candidate_count": 2,
            "score_fields": ["base EM", "hybrid EM"],
            "score_warning": "Scores may be stale after text or hierarchy edits; unavailable scores are shown as unavailable",
            "vote_log": "GitHub Issues",
            "daily_aggregation": True,
            "minimum_unique_reviewers": 3,
            "strict_majority_required": True,
            "automatic_reassignment": False,
            "application_policy": "Only after an explicit user instruction to analyse and apply review logs",
        },
        "human_review_round2": {
            "method": round2_summary["method"],
            "independent_language_review": language_review,
            "provenance": {
                "operative_specifications_sha256": round2_summary["operative_specifications_sha256"],
                "baseline_inputs_sha256": round2_summary["baseline_inputs_sha256"],
                "pipeline_scripts_sha256": round2_summary["pipeline_scripts_sha256"],
                "output_sha256": round2_summary["output_sha256"],
            },
        },
    }
    write_json(MASTER / "manifest.json", manifest)
    build_tables(rows, summary)
    build_figures(rows, summary, qa)
    write_readme(summary, qa)
    copy_technical_reports()
    update_report_shells(qa["passed"])
    print(json.dumps({"rows": len(rows), "validation": qa["status"], "manifest": str(MASTER / "manifest.json")}, ensure_ascii=False))


def validation_evidence(name: str, validation: dict[str, object]) -> object:
    if name == "output_rows_match_summary":
        return validation["counts"]["output_rows"]
    if name == "domain_counts_match_summary":
        return validation["counts"]["output_domain_rows"]
    if name == "l3_master_hash_unchanged":
        return validation["l3_master_sha256"]
    if name.endswith("copyedit_exact"):
        key = "korean_copyedit_operations" if name.startswith("korean") else "english_copyedit_operations"
        return validation["counts"][key]
    if name == "final_terminology_l3_qa_exact":
        return validation["counts"]["final_terminology_l3_qa_operations"]
    return "Verified by deterministic round-two validator"


def build_tables(rows: list[dict[str, str]], summary: dict[str, object]) -> None:
    domain_table = pd.DataFrame(
        [
            {
                "Domain": domain,
                "Previous_release": PREVIOUS_COUNTS[domain],
                "Current_release": summary["final_domain_counts"][DOMAIN_LABELS[domain]],
                "Net_change": summary["final_domain_counts"][DOMAIN_LABELS[domain]] - PREVIOUS_COUNTS[domain],
            }
            for domain in DOMAINS
        ]
    )
    domain_table.to_csv(TABLES / "round2_domain_counts.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            {"Language": "Korean", "Approved_operations": summary["korean_copyedit_operations"]},
            {"Language": "English", "Approved_operations": summary["english_copyedit_operations"]},
        ]
    ).to_csv(TABLES / "round2_language_edit_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [{"Score_status": key or "unlabelled", "Cards": value} for key, value in summary["score_status_counts"].items()]
    ).to_csv(TABLES / "round2_mapping_score_status.csv", index=False, encoding="utf-8-sig")
    shutil.copy2(ROUND2 / "L4_Top20_Similar_Pairs.csv", TABLES / "round2_top20_similarity.csv")


def build_figures(rows: list[dict[str, str]], summary: dict[str, object], qa: dict[str, object]) -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False})
    domains = list(DOMAINS)
    previous = [PREVIOUS_COUNTS[domain] for domain in domains]
    current = [summary["final_domain_counts"][DOMAIN_LABELS[domain]] for domain in domains]
    x = range(len(domains))
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.bar([i - 0.18 for i in x], previous, 0.36, label="Previous release", color="#AAB4C3")
    bars = ax.bar([i + 0.18 for i in x], current, 0.36, label="Human-review round 2", color=[COLORS[d] for d in domains])
    ax.bar_label(bars, padding=3)
    ax.set_xticks(list(x), domains); ax.set_ylabel("L4 cards"); ax.set_title("L4 domain counts after second-round human review")
    ax.legend(frameon=False); fig.tight_layout(); save_figure(fig, "round2_domain_counts.png")

    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    labels = ["Korean", "English"]
    values = [summary["korean_copyedit_operations"], summary["english_copyedit_operations"]]
    bars = ax.bar(labels, values, color=["#3366CC", "#E68613"])
    ax.bar_label(bars, padding=3); ax.set_ylabel("Approved operations"); ax.set_title("Approved bilingual language-quality operations")
    fig.tight_layout(); save_figure(fig, "round2_language_edits.png")

    status = Counter(row["Definition_Grounding_Action"] for row in rows)
    status_order = [
        "STALE_AFTER_TEXT_EDIT_NO_EM_RERUN",
        "STALE_AFTER_HUMAN_REVIEW_NO_EM_RERUN",
        "L3_MASTER_VALIDATED",
        "L3_MASTER_AI_REWRITE",
    ]
    status_labels = ["Text edited\nscore stale", "Human review\nscore unavailable", "Prior score\ntext unchanged", "Prior AI rewrite\ntext unchanged"]
    values = [status[key] for key in status_order]
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    bars = ax.bar(status_labels, values, color=["#C65D4B", "#7A5AF8", "#2A9D6F", "#66A8E8"])
    ax.bar_label(bars, padding=3); ax.set_ylabel("L4 cards"); ax.set_title("Mapping-score status after human review without EM rerun")
    fig.tight_layout(); save_figure(fig, "round2_mapping_score_status.png")

    top = pd.read_csv(ROUND2 / "L4_Top20_Similar_Pairs.csv", nrows=10)
    labels = [f"{left}\n{right}" for left, right in zip(top["Left_L4_ID"], top["Right_L4_ID"])]
    fig, ax = plt.subplots(figsize=(9.2, 5.0))
    bars = ax.barh(labels[::-1], top["Bilingual_Similarity"].iloc[::-1], color="#3366CC")
    ax.bar_label(bars, fmt="%.3f", padding=3); ax.set_xlim(max(0.0, top["Bilingual_Similarity"].min() - 0.05), 1.0)
    ax.set_xlabel("Bilingual cosine similarity"); ax.set_title("Highest-similarity L4 pairs after language review")
    fig.tight_layout(); save_figure(fig, "round2_similarity_top10.png")

    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    bars = ax.bar(["PASS", "FAIL"], [qa["passed"], qa["failed"]], color=["#2A9D6F", "#C65D4B"])
    ax.bar_label(bars, padding=3); ax.set_ylabel("Validation checks"); ax.set_title("Deterministic validation result")
    fig.tight_layout(); save_figure(fig, "round2_validation.png")


def save_figure(fig: plt.Figure, name: str) -> None:
    fig.savefig(FIGURES / name, dpi=300, bbox_inches="tight")
    fig.savefig(PROJECT_FIGURES / name, dpi=300, bbox_inches="tight")
    plt.close(fig)


def write_readme(summary: dict[str, object], qa: dict[str, object]) -> None:
    text = f"""# RAI Risk Taxonomy 2.0 master release

Current master: second-round human-review application, 2026-08-29.

- L3 master: 46 immutable source categories plus 3 derived Others queues
- L4: {summary['final_total']} cards
- General / Agentic / Physical: {summary['final_domain_counts']['General AI']} / {summary['final_domain_counts']['Agentic AI']} / {summary['final_domain_counts']['Physical AI']}
- User-directed merge operations: {summary['user_directed_operations']}
- Explicit deletions: {summary['explicit_deletions']}
- Korean / English approved language operations: {summary['korean_copyedit_operations']} / {summary['english_copyedit_operations']}
- Final terminology and L3-alignment QA operations: {summary['final_terminology_l3_qa_operations']}
- Deterministic validation: {qa['passed']} PASS, {qa['failed']} FAIL
- EM and Hybrid EM rerun in this review round: no

Prior-run mapping scores are retained only as historical evidence. Cards edited in this round are explicitly marked as stale, and cards whose hierarchy or cardinality changed expose no inherited score.

Canonical CSVs are under `data/`. The complete decision ledger, language manifests, validation record, and top-20 similarity review are under `validation/`.
"""
    (MASTER / "README.md").write_text(text, encoding="utf-8")


def copy_technical_reports() -> None:
    report_dir = PROJECT / "technical_report"
    for name in (
        "rai_risk_taxonomy_2_0_rebuild_technical_report_ko.tex",
        "rai_risk_taxonomy_2_0_rebuild_technical_report_ko.pdf",
        "rai_risk_taxonomy_2_0_rebuild_technical_report_en.tex",
        "rai_risk_taxonomy_2_0_rebuild_technical_report_en.pdf",
    ):
        source = report_dir / name
        if source.exists():
            shutil.copy2(source, MASTER / "reports" / name)


def update_report_shells(check_count: int) -> None:
    validation_html = MASTER / "validation.html"
    html = validation_html.read_text(encoding="utf-8")
    import re

    html = re.sub(r"\d+개 최종 검증", f"{check_count}개 최종 검증", html)
    html = html.replace("정제 결과, EM 매핑", "2차 휴먼검수 결과, 이전 EM 상태")
    validation_html.write_text(html, encoding="utf-8")

    manifest_html = MASTER / "manifest.html"
    html = manifest_html.read_text(encoding="utf-8")
    html = html.replace("정제 결과, EM 매핑", "2차 휴먼검수 결과, 이전 EM 상태")
    manifest_html.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
