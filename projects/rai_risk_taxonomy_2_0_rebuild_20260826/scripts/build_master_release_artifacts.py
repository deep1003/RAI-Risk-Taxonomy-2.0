#!/usr/bin/env python3
"""Synchronise the reviewed rebuild into the public master release."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parents[1]
SOURCE_RELEASE = PROJECT / "03_outputs/release"
AUDIT = PROJECT / "03_outputs/audit"
MASTER = REPO / "releases/RAI-Risk-Taxonomy-2.0-master"
MASTER_DATA = MASTER / "data"
FIGURES = MASTER / "figures"
TABLES = PROJECT / "reports/tables"
PROJECT_FIGURES = PROJECT / "output/figures"

DOMAINS = ["General AI", "Agentic AI", "Physical AI"]
COLORS = {"General AI": "#3366CC", "Agentic AI": "#E68613", "Physical AI": "#2A9D6F"}
SOURCE_COUNTS = {"General AI": 591, "Agentic AI": 83, "Physical AI": 218}
CSV_FILES = ["L1_Master.csv", "L1_L2_L3_Master.csv", "L4_General.csv", "L4_Agentic.csv", "L4_Physical.csv"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    for directory in (MASTER_DATA, FIGURES, MASTER / "reports", MASTER / "validation", TABLES, PROJECT_FIGURES):
        directory.mkdir(parents=True, exist_ok=True)
    for name in CSV_FILES:
        shutil.copy2(SOURCE_RELEASE / name, MASTER_DATA / name)

    manifest = json.loads((SOURCE_RELEASE / "release_manifest.json").read_text(encoding="utf-8"))
    manifest["pipeline_script"] = "projects/rai_risk_taxonomy_2_0_rebuild_20260826/scripts/run_rebuild_pipeline.py"
    manifest["primary_outputs"] = {
        name: {"sha256": sha256(MASTER_DATA / name), "rows": len(pd.read_csv(MASTER_DATA / name))}
        for name in CSV_FILES
    }
    manifest["human_review"] = {
        "candidate_count": 2,
        "score_fields": ["base EM", "hybrid EM"],
        "vote_log": "GitHub Issues",
        "daily_aggregation": True,
        "minimum_unique_reviewers": 3,
        "strict_majority_required": True,
        "automatic_reassignment": False,
        "application_policy": "Only after an explicit user instruction to analyse and apply review logs",
    }
    (MASTER / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    validation = pd.read_csv(AUDIT / "Validation_Report.csv", dtype=str, keep_default_na=False)
    checks = []
    for _, row in validation.iterrows():
        detail = row["Detail"]
        try:
            evidence = json.loads(detail.replace("'", '"'))
        except Exception:
            evidence = detail
        checks.append({"check": row["Check"], "status": row["Status"], "evidence": evidence})
    qa = {
        "status": "PASS" if validation["Status"].eq("PASS").all() else "FAIL",
        "passed": int(validation["Status"].eq("PASS").sum()),
        "failed": int(validation["Status"].eq("FAIL").sum()),
        "checks": checks,
    }
    (MASTER / "validation/final_release_qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cards = pd.concat(
        [pd.read_csv(MASTER_DATA / f"L4_{domain}.csv") for domain in ("General", "Agentic", "Physical")],
        ignore_index=True,
    )
    build_tables(cards)
    build_figures(cards)
    for figure in FIGURES.glob("*.png"):
        shutil.copy2(figure, PROJECT_FIGURES / figure.name)
    write_readme(manifest, qa)
    report_pairs = {
        PROJECT / "output/pdf/rai_risk_taxonomy_2_0_rebuild_technical_report_ko.pdf": MASTER / "reports/technical_report_ko.pdf",
        PROJECT / "output/pdf/rai_risk_taxonomy_2_0_rebuild_technical_report_en.pdf": MASTER / "reports/technical_report_en.pdf",
        PROJECT / "technical_report/rai_risk_taxonomy_2_0_rebuild_technical_report_ko.tex": MASTER / "reports/technical_report_ko.tex",
        PROJECT / "technical_report/rai_risk_taxonomy_2_0_rebuild_technical_report_en.tex": MASTER / "reports/technical_report_en.tex",
    }
    for source, destination in report_pairs.items():
        if source.exists():
            shutil.copy2(source, destination)
    print(json.dumps({"rows": len(cards), "validation": qa["status"], "manifest": str(MASTER / "manifest.json")}, ensure_ascii=False))


def build_tables(cards: pd.DataFrame) -> None:
    summary = json.loads((SOURCE_RELEASE / "release_manifest.json").read_text(encoding="utf-8"))["summary"]
    actions = pd.read_csv(AUDIT / "Transformation_Log.csv", dtype=str, keep_default_na=False)["action"].value_counts()
    source_total = summary["source_total"]
    explicit = int(actions.get("DELETE", 0))
    merged = int(actions.get("MERGED_AWAY", 0))
    split = summary["split_net_addition"]
    eligibility = int(actions.get("DELETE_NON_RISK", 0))
    peer = int(actions.get("DELETE_PEER_REVIEW", 0))
    scope = int(actions.get("DELETE_L3_SCOPE_MISMATCH", 0))
    semantic_dedup = int(actions.get("DELETE_NEAR_DUPLICATE", 0))
    after_explicit = source_total - explicit
    after_merge = after_explicit - merged
    after_split = after_merge + split
    after_eligibility = after_split - eligibility
    after_peer = after_eligibility - peer
    after_scope = after_peer - scope
    transformation = pd.DataFrame([
        {"Stage": "Source L4", "Count": source_total, "Change": 0},
        {"Stage": "After explicit deletion", "Count": after_explicit, "Change": -explicit},
        {"Stage": "After merge consolidation", "Count": after_merge, "Change": -merged},
        {"Stage": "After split", "Count": after_split, "Change": split},
        {"Stage": "After risk-eligibility deletion", "Count": after_eligibility, "Change": -eligibility},
        {"Stage": "After peer-review deletion", "Count": after_peer, "Change": -peer},
        {"Stage": "After immutable-L3 scope gate", "Count": after_scope, "Change": -scope},
        {"Stage": "After semantic deduplication", "Count": summary["cleaned_total"],
         "Change": -semantic_dedup},
    ])
    transformation.to_csv(TABLES / "transformation_summary.csv", index=False, encoding="utf-8-sig")

    rows = []
    for domain in DOMAINS:
        subset = cards[cards["L1_Title_en"].eq(domain)]
        rows.append({
            "Domain": domain, "Source": SOURCE_COUNTS[domain], "Final": len(subset),
            "EM": int(subset["Mapping_Method"].eq("EM").sum()),
            "HD_Others": int(subset["Mapping_Method"].eq("HD").sum()),
            "Mean_Score": subset["EM_Score"].mean(), "Median_Margin": subset["EM_Margin"].median(),
            "Mean_Stability": subset["EM_Stability"].mean(),
            "Bilingual_Top1_Agreement": subset["KO_Top_L3_ID"].eq(subset["EN_Top_L3_ID"]).mean(),
        })
    pd.DataFrame(rows).to_csv(TABLES / "domain_mapping_summary.csv", index=False, encoding="utf-8-sig")
    pd.read_csv(AUDIT / "EM_Run_Diagnostics.csv").to_csv(TABLES / "em_run_diagnostics.csv", index=False, encoding="utf-8-sig")
    cards.groupby(["L1_Title_en", "Definition_Grounding_Action"], as_index=False).size().rename(
        columns={"size": "Count"}
    ).to_csv(TABLES / "definition_grounding_summary.csv", index=False, encoding="utf-8-sig")
    baseline_root = PROJECT / "04_baseline_pre_keyword/release"
    baseline_cards = pd.concat([
        pd.read_csv(baseline_root / f"L4_{domain}.csv", dtype=str, keep_default_na=False)
        for domain in ("General", "Agentic", "Physical")
    ], ignore_index=True)
    pd.DataFrame([
        {"Pipeline": "Pre-keyword baseline", "EM": int(baseline_cards["Mapping_Method"].eq("EM").sum()),
         "HD_Others": int(baseline_cards["Mapping_Method"].eq("HD").sum())},
        {"Pipeline": "Final keyword-augmented", "EM": int(cards["Mapping_Method"].eq("EM").sum()),
         "HD_Others": int(cards["Mapping_Method"].eq("HD").sum())},
    ]).to_csv(TABLES / "baseline_mapping_comparison.csv", index=False, encoding="utf-8-sig")
    cards.groupby(["L1_Title_en", "L3_ID", "L3_Title_en", "Mapping_Method"], as_index=False).size().rename(
        columns={"size": "Count"}
    ).to_csv(TABLES / "l3_distribution.csv", index=False, encoding="utf-8-sig")
    pd.read_csv(AUDIT / "Semantic_Near_Duplicate_Decisions.csv").to_csv(
        TABLES / "semantic_near_duplicate_decisions.csv", index=False, encoding="utf-8-sig"
    )
    pd.read_csv(AUDIT / "Title_Normalisation_Ledger.csv").groupby(
        ["normalisation_rule", "title_changed"], as_index=False
    ).size().rename(columns={"size": "Count"}).to_csv(
        TABLES / "title_normalisation_summary.csv", index=False, encoding="utf-8-sig"
    )


def build_figures(cards: pd.DataFrame) -> None:
    sns.set_theme(style="whitegrid", context="paper")
    final = [int(cards["L1_Title_en"].eq(d).sum()) for d in DOMAINS]
    source = [SOURCE_COUNTS[d] for d in DOMAINS]
    labels = [d.replace(" AI", "") for d in DOMAINS]

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    x, width = np.arange(3), 0.34
    a = ax.bar(x - width / 2, source, width, label="Source", color="#A8B5C7")
    b = ax.bar(x + width / 2, final, width, label="Final", color=[COLORS[d] for d in DOMAINS])
    ax.bar_label(a, padding=3); ax.bar_label(b, padding=3)
    ax.set(xticks=x, xticklabels=labels, ylabel="Number of L4 risks", title="Domain counts before and after rebuilding")
    ax.legend(frameon=False); sns.despine(ax=ax); fig.tight_layout()
    fig.savefig(FIGURES / "domain_counts_before_after.png", dpi=300, bbox_inches="tight"); plt.close(fig)

    transformation = pd.read_csv(TABLES / "transformation_summary.csv")
    stages = ["Source", "Explicit\ndeletions", "Merges", "Split", "Eligibility\ngate", "Peer review",
              "L3 scope\ngate", "Semantic\ndeduplication"]
    counts = transformation["Count"].astype(int).tolist()
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    bars = ax.bar(range(len(counts)), counts, color=["#596780", "#C65D4B", "#C65D4B", "#2A9D6F",
                                                   "#C65D4B", "#C65D4B", "#C65D4B", "#C65D4B"])
    ax.bar_label(bars, padding=3, fontsize=9)
    ax.set(xticks=range(len(counts)), xticklabels=stages, ylabel="Number of L4 risks", title="L4 cleaning and immutable-L3 scope reconciliation", ylim=(0, 980))
    sns.despine(ax=ax); fig.tight_layout()
    fig.savefig(FIGURES / "cleaning_reconciliation.png", dpi=300, bbox_inches="tight"); plt.close(fig)

    pivot = cards.groupby(["L1_Title_en", "Mapping_Method"]).size().unstack(fill_value=0).reindex(DOMAINS)
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    em, hd = pivot["EM"], pivot["HD"]
    ax.bar(range(3), em, color=[COLORS[d] for d in DOMAINS], label="EM assignment")
    ax.bar(range(3), hd, bottom=em, color="#D4D7DC", hatch="///", edgecolor="#777777", label="HD / Others")
    for i, (e, h) in enumerate(zip(em, hd)):
        ax.text(i, e / 2, str(e), ha="center", va="center", color="white", fontweight="bold")
        ax.text(i, e + h + 5, f"HD {h}", ha="center", fontsize=9)
    ax.set(xticks=range(3), xticklabels=labels, ylabel="Number of L4 risks", title="EM assignments and human-decision queues")
    ax.legend(frameon=False); sns.despine(ax=ax); fig.tight_layout()
    fig.savefig(FIGURES / "mapping_method_by_domain.png", dpi=300, bbox_inches="tight"); plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.8))
    for ax, metric, label in zip(axes, ["EM_Score", "EM_Margin", "EM_Stability"], ["Top similarity", "Top-2 margin", "Run stability"]):
        sns.boxplot(data=cards, x="L1_Title_en", y=metric, hue="L1_Title_en", order=DOMAINS,
                    hue_order=DOMAINS, palette=COLORS, legend=False, width=0.58, fliersize=1.5, ax=ax)
        ax.set_xticks(range(3)); ax.set_xticklabels(labels, rotation=18); ax.set_xlabel(""); ax.set_ylabel(label); sns.despine(ax=ax)
    fig.suptitle("EM mapping diagnostics by domain", y=1.02); fig.tight_layout()
    fig.savefig(FIGURES / "em_quality_diagnostics.png", dpi=300, bbox_inches="tight"); plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(12.2, 5.4), gridspec_kw={"width_ratios": [1.25, 1, 1]})
    for ax, domain in zip(axes, DOMAINS):
        counts = cards[cards["L1_Title_en"].eq(domain) & cards["Mapping_Method"].eq("EM")]["L3_Title_en"].value_counts().head(10).sort_values()
        ax.barh(counts.index, counts.values, color=COLORS[domain])
        for y, value in enumerate(counts.values): ax.text(value + 0.3, y, str(value), va="center", fontsize=8)
        ax.set_title(domain); ax.set_xlabel("L4 risks"); ax.tick_params(axis="y", labelsize=7.5); sns.despine(ax=ax)
    fig.suptitle("Largest EM-assigned L3 categories", y=1.01); fig.tight_layout()
    fig.savefig(FIGURES / "largest_l3_categories.png", dpi=300, bbox_inches="tight"); plt.close(fig)

    grounding_pivot = cards.groupby(["L1_Title_en", "Definition_Grounding_Action"]).size().unstack(fill_value=0).reindex(DOMAINS)
    validated = grounding_pivot.get("L3_MASTER_VALIDATED", pd.Series(0, index=DOMAINS))
    rewritten = grounding_pivot.get("L3_MASTER_AI_REWRITE", pd.Series(0, index=DOMAINS))
    fig, ax = plt.subplots(figsize=(7.4, 4.5))
    ax.bar(range(3), validated, color=[COLORS[d] for d in DOMAINS], label="Validated without rewriting")
    ax.bar(range(3), rewritten, bottom=validated, color="#D7DEE8", hatch="///", edgecolor="#697586",
           label="AI-technology grounding rewrite")
    for i, (kept, changed) in enumerate(zip(validated, rewritten)):
        ax.text(i, kept + changed + 5, f"{int(kept)} + {int(changed)}", ha="center", fontsize=9)
    ax.set(xticks=range(3), xticklabels=labels, ylabel="Number of L4 definitions",
           title="Immutable-L3 and AI-technology definition review")
    ax.legend(frameon=False, fontsize=8); sns.despine(ax=ax); fig.tight_layout()
    fig.savefig(FIGURES / "definition_grounding_by_domain.png", dpi=300, bbox_inches="tight"); plt.close(fig)

    duplicate_candidates = pd.read_csv(AUDIT / "Semantic_Near_Duplicate_Candidates.csv")
    duplicate_counts = duplicate_candidates["Decision"].value_counts().reindex(
        ["RETAIN_DISTINCT_SCOPE", "DROP_LESS_REPRESENTATIVE"], fill_value=0
    )
    fig, ax = plt.subplots(figsize=(6.8, 4.3))
    bars = ax.bar(["Retained as distinct", "Discarded as redundant"], duplicate_counts.values,
                  color=["#3366CC", "#C65D4B"])
    ax.bar_label(bars, padding=3)
    ax.set(ylabel="Candidate pairs", title="Bilingual semantic near-duplicate review")
    sns.despine(ax=ax); fig.tight_layout()
    fig.savefig(FIGURES / "semantic_near_duplicate_review.png", dpi=300, bbox_inches="tight"); plt.close(fig)

    baseline_root = PROJECT / "04_baseline_pre_keyword/release"
    baseline_cards = pd.concat([
        pd.read_csv(baseline_root / f"L4_{domain}.csv", dtype=str, keep_default_na=False)
        for domain in ("General", "Agentic", "Physical")
    ], ignore_index=True)
    comparison = pd.DataFrame({
        "Pipeline": ["Pre-keyword baseline", "Final keyword-augmented"],
        "EM": [int(baseline_cards["Mapping_Method"].eq("EM").sum()), int(cards["Mapping_Method"].eq("EM").sum())],
        "HD / Others": [int(baseline_cards["Mapping_Method"].eq("HD").sum()), int(cards["Mapping_Method"].eq("HD").sum())],
    })
    fig, ax = plt.subplots(figsize=(6.6, 4.3))
    x, width = np.arange(2), 0.34
    em_bars = ax.bar(x - width / 2, comparison["EM"], width, label="EM", color="#2F6BFF")
    hd_bars = ax.bar(x + width / 2, comparison["HD / Others"], width, label="HD / Others", color="#C6CBD4")
    ax.bar_label(em_bars, padding=3); ax.bar_label(hd_bars, padding=3)
    ax.set(xticks=x, xticklabels=["Pre-keyword\nbaseline", "Final keyword-\naugmented"],
           ylabel="Number of L4 risks", title="Mapping outcomes before and after keyword augmentation")
    ax.legend(frameon=False); sns.despine(ax=ax); fig.tight_layout()
    fig.savefig(FIGURES / "em_baseline_comparison.png", dpi=300, bbox_inches="tight"); plt.close(fig)


def write_readme(manifest: dict, qa: dict) -> None:
    summary = manifest["summary"]
    text = f"""# RAI Risk Taxonomy 2.0 master release

This master release contains five canonical CSV artifacts, bilingual technical reports, result figures, and the final QA record.

## Release summary

- L1 domains: 3
- L2 dimensions: 3
- L3 categories: 49, comprising 46 immutable master categories and 3 derived Others categories
- L4 risk cards: {summary['cleaned_total']}
- L4 title terminology normalisations: {summary['title_terminology_normalisations']}
- Semantic near-duplicate review: {summary['semantic_near_duplicate_candidates']} candidate pairs, {summary['semantic_near_duplicate_deletions']} lower-representativeness cards discarded
- General / Agentic / Physical: {summary['final_domain_counts']['General AI']} / {summary['final_domain_counts']['Agentic AI']} / {summary['final_domain_counts']['Physical AI']}
- EM assignments: {summary['em_total']}
- HD/Others assignments: {summary['others_total']}
- L3-referenced AI-technology definition rewrites: {summary['definition_ai_grounding_rewrites']}
- Cleaning reconciliation: {summary['source_total']} source rows minus {summary['deleted']} deletions minus {summary['merged_away']} absorbed merge rows plus {summary['split_net_addition']} net split addition equals {summary['cleaned_total']} final rows
- Post-build validation: {qa['passed']} passed, {qa['failed']} failed

## Canonical CSV files

- `data/L1_Master.csv`
- `data/L1_L2_L3_Master.csv`
- `data/L4_General.csv`
- `data/L4_Agentic.csv`
- `data/L4_Physical.csv`

All 46 source-defined L3 rows are preserved exactly. The three domain-specific Others categories are derived human-decision queues and do not modify the source L3 master.
Every Korean and English L4 definition explicitly names an AI technology and follows an L3-style risk-statement structure. Each L4 also contains three representative concepts per language and two reviewable non-Others L3 candidates with base and hybrid EM scores.

## Reports and validation

- `reports/technical_report_ko.pdf`
- `reports/technical_report_en.pdf`
- `validation/final_release_qa.json`
- `manifest.json`
"""
    (MASTER / "README.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
