#!/usr/bin/env python3
"""Build data-derived figures and tables for the integrated technical report."""

from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
REPO = ROOT.parents[3]
RELEASE = REPO / "releases" / "RAI-Risk-Taxonomy-2.0-master"
FIG = ROOT / "figures"
DATA = ROOT / "data"
TABLES = ROOT / "tables"
FIG.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)
TABLES.mkdir(parents=True, exist_ok=True)

COLORS = {
    "General": "#3568D4",
    "Agentic": "#9B59B6",
    "Physical": "#E67E22",
    "neutral": "#5B6573",
    "light": "#E9EEF6",
    "green": "#2E8B57",
    "red": "#C94C4C",
}


def finish(fig, name):
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.png", dpi=600, bbox_inches="tight")
    plt.close(fig)


plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.titlesize": 12,
    "axes.labelsize": 9,
    "figure.dpi": 150,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


# Figure 1. End-to-end workflow.
fig, ax = plt.subplots(figsize=(11.2, 4.2))
ax.set_xlim(0, 11.2)
ax.set_ylim(0, 4.2)
ax.axis("off")
boxes = [
    (0.20, 2.35, 1.55, 1.10, "Evidence\nacquisition", "3,906,767 records"),
    (2.05, 2.35, 1.55, 1.10, "Risk-source\nfiltering", "82,971 records"),
    (3.90, 2.35, 1.55, 1.10, "Candidate\nconstruction", "1,725 candidates"),
    (5.75, 2.35, 1.55, 1.10, "Registry and\nsemantic mapping", "1,660 active (archive)"),
    (7.60, 2.35, 1.55, 1.10, "Rebuild\nbaseline", "798 cards"),
    (9.45, 2.35, 1.55, 1.10, "Audited\nmaster", "622 cards"),
]
for x, y, w, h, title, subtitle in boxes:
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.08",
                           linewidth=1.2, edgecolor="#38506B", facecolor="#F7F9FC")
    ax.add_patch(patch)
    ax.text(x+w/2, y+0.69, title, ha="center", va="center", weight="bold", fontsize=9.5)
    ax.text(x+w/2, y+0.20, subtitle, ha="center", va="center", fontsize=7.5, color=COLORS["neutral"])
for i in range(len(boxes)-1):
    x1 = boxes[i][0] + boxes[i][2]
    x2 = boxes[i+1][0]
    ax.add_patch(FancyArrowPatch((x1+0.05, 2.90), (x2-0.05, 2.90), arrowstyle="-|>",
                                 mutation_scale=12, linewidth=1.1, color="#38506B"))
ax.text(5.60, 1.50, "Historical semantic construction", ha="center", fontsize=9, color="#38506B")
ax.plot([0.25, 7.25], [1.35, 1.35], color="#9AA7B5", linewidth=1.0)
ax.text(9.35, 1.50, "Human-review rebuild and audit", ha="center", fontsize=9, color="#38506B")
ax.plot([7.65, 11.00], [1.35, 1.35], color="#9AA7B5", linewidth=1.0)
ax.text(9.35, 0.78, "merge | split | reassign | delete | rewrite", ha="center",
        fontsize=10, weight="bold", color="#8A4B08")
ax.set_title("Versioned construction of RAI Risk Taxonomy 2.0", loc="left", weight="bold")
finish(fig, "fig01_end_to_end_workflow")


# Figure 2. Evidence funnel.
stages = ["AI evidence", "AI-risk evidence", "Card candidates", "Registered IDs", "Active L4\n(archive)"]
values = [3_906_767, 82_971, 1_725, 1_711, 1_660]
fig, ax = plt.subplots(figsize=(8.4, 4.8))
bars = ax.barh(stages[::-1], values[::-1], color=["#6A7FDB", "#7086D8", "#7790D6", "#7F99D4", "#88A3D2"])
ax.set_xscale("log")
ax.set_xlabel("Count, logarithmic scale")
ax.set_title("Evidence-to-registry funnel in the historical construction stage", loc="left", weight="bold")
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="x", alpha=0.25)
for b, v in zip(bars, values[::-1]):
    ax.text(v*1.08, b.get_y()+b.get_height()/2, f"{v:,}", va="center", fontsize=8)
finish(fig, "fig02_evidence_funnel")


# Figure 3. Rebuild trajectory.
trajectory = pd.DataFrame([
    ("Rebuild baseline", 798),
    ("Review recovery", 791),
    ("Deduplication", 778),
    ("Semantic splitting", 783),
    ("Scope curation", 777),
    ("AC-01", 778),
    ("AC-02", 720),
    ("AC-05", 725),
    ("AC-06", 711),
    ("AC-07", 645),
    ("AC-08", 629),
    ("Round 3 / AC-18", 623),
    ("AC-19", 623),
    ("Round 4 / current", 622),
], columns=["stage", "cards"])
trajectory.to_csv(DATA / "rebuild_card_trajectory.csv", index=False)
fig, ax = plt.subplots(figsize=(10.6, 4.8))
ax.plot(range(len(trajectory)), trajectory.cards, marker="o", linewidth=2.0, color="#3568D4")
ax.fill_between(range(len(trajectory)), trajectory.cards, min(trajectory.cards)-15, color="#3568D4", alpha=0.08)
ax.set_xticks(range(len(trajectory)), trajectory.stage, rotation=35, ha="right")
ax.set_ylabel("Active L4 cards")
ax.set_ylim(590, 820)
ax.set_title("Card-count trajectory through review recovery and audit corrections", loc="left", weight="bold")
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=0.25)
for i, v in enumerate(trajectory.cards):
    ax.text(i, v+6, str(v), ha="center", fontsize=7.5)
finish(fig, "fig03_rebuild_trajectory")


# Figure 4. Final domain composition.
domain = pd.DataFrame({"domain": ["General AI", "Agentic AI", "Physical AI"], "cards": [492, 67, 63]})
domain.to_csv(DATA / "final_domain_counts.csv", index=False)
fig, ax = plt.subplots(figsize=(7.8, 4.2))
bars = ax.bar(domain.domain, domain.cards, color=[COLORS["General"], COLORS["Agentic"], COLORS["Physical"]], width=0.62)
ax.set_ylabel("Active L4 cards")
ax.set_title("Final audited master by L1 domain", loc="left", weight="bold")
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", alpha=0.25)
for b, v in zip(bars, domain.cards):
    ax.text(b.get_x()+b.get_width()/2, v+8, f"{v}\n({v/622:.1%})", ha="center", fontsize=9)
ax.set_ylim(0, 560)
finish(fig, "fig04_final_domain_counts")


# Figure 5. Human-review operations.
manifest = json.loads((RELEASE / "manifest.json").read_text())
ops = manifest["summary"]["recovery_actions"]
labels = ["Reassign", "Rewrite and keep", "Split", "Merge", "Delete"]
counts = [ops["REMAP"], ops["REWRITE_KEEP"], ops["SPLIT"], ops["MERGE"], ops["DELETE"]]
pd.DataFrame({"operation": labels, "review_rows": counts}).to_csv(DATA / "round2_review_actions.csv", index=False)
fig, ax = plt.subplots(figsize=(8.8, 4.5))
order = list(reversed(range(len(labels))))
bars = ax.barh([labels[i] for i in order], [counts[i] for i in order], color="#5577B9")
ax.set_xlabel("Human-review rows")
ax.set_title("Second-round instructions applied by operation", loc="left", weight="bold")
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="x", alpha=0.25)
for b in bars:
    ax.text(b.get_width()+1.5, b.get_y()+b.get_height()/2, f"{int(b.get_width())}", va="center")
finish(fig, "fig05_review_operations")


# Figure 6. Round-3 and AC-19 domain-routing matrix.
round3 = pd.read_csv(RELEASE / "validation" / "Human_Review_Round3_Application_Log.csv", dtype=str).fillna("")
ac19 = pd.read_csv(RELEASE / "validation" / "Physical_Minimal_Corrections_AC19_Ledger.csv", dtype=str).fillna("")
def short_domain(l1):
    return {"L1_G": "General", "L1_A": "Agentic", "L1_P": "Physical"}.get(l1, "Deleted")
rows=[]
for _, r in round3.iterrows():
    if r["Action"] == "DELETE":
        continue
    rows.append((short_domain(r["L1_ID_Before"]), short_domain(r["L1_ID_After"])))
for _, r in ac19.iterrows():
    if r.get("Action", "") == "MOVE_REASSIGN":
        rows.append((short_domain(r["L1_ID_Before"]), short_domain(r["L1_ID_After"])))
flow = pd.DataFrame(rows, columns=["before", "after"])
matrix = pd.crosstab(flow.before, flow.after).reindex(index=["General","Agentic","Physical"], columns=["General","Agentic","Physical"], fill_value=0)
matrix.to_csv(DATA / "round3_ac19_domain_routing_matrix.csv")
fig, ax = plt.subplots(figsize=(6.2, 5.2))
im = ax.imshow(matrix.values, cmap="Blues", vmin=0)
ax.set_xticks(range(3), matrix.columns)
ax.set_yticks(range(3), matrix.index)
ax.set_xlabel("Domain after review")
ax.set_ylabel("Domain before review")
ax.set_title("Domain routing in Round 3 and AC-19", loc="left", weight="bold")
for i in range(3):
    for j in range(3):
        ax.text(j, i, str(matrix.iloc[i, j]), ha="center", va="center",
                color="white" if matrix.iloc[i, j] > matrix.values.max()/2 else "#1B2A41", weight="bold")
fig.colorbar(im, ax=ax, shrink=0.78, label="Cards")
finish(fig, "fig06_domain_routing_matrix")


# Figure 7. Validation gates.
fig, ax = plt.subplots(figsize=(10.8, 4.2))
ax.set_xlim(0, 10.8)
ax.set_ylim(0, 4.2)
ax.axis("off")
gates = [
    (0.35, "Source freeze", "hashes and row counts"),
    (2.45, "Lineage", "old-to-new IDs and tombstones"),
    (4.55, "Semantic QA", "L3 fit, atomicity, bilingual equivalence"),
    (6.65, "Data QA", "IDs, duplicates, Others, schema"),
    (8.75, "Release sync", "public/full CSV and website parity"),
]
for x, title, subtitle in gates:
    p = FancyBboxPatch((x, 1.35), 1.7, 1.45, boxstyle="round,pad=0.05,rounding_size=0.08",
                       linewidth=1.4, edgecolor=COLORS["green"], facecolor="#F2FAF5")
    ax.add_patch(p)
    ax.text(x+0.85, 2.22, title, ha="center", weight="bold", fontsize=9)
    ax.text(x+0.85, 1.72, subtitle, ha="center", va="center", fontsize=7.2, color=COLORS["neutral"], wrap=True)
for i in range(4):
    ax.add_patch(FancyArrowPatch((gates[i][0]+1.75, 2.08), (gates[i+1][0]-0.05, 2.08),
                                 arrowstyle="-|>", mutation_scale=12, color=COLORS["green"]))
ax.text(5.4, 0.72, "Release accepted only when every gate passes", ha="center", fontsize=10, weight="bold")
ax.set_title("Auditable validation chain", loc="left", weight="bold")
finish(fig, "fig07_validation_chain")


# Figure 8. Archived algorithm diagnostics and observed human intervention.
algorithm = pd.DataFrame({
    "diagnostic": ["Top-1 containment", "Top-2 containment", "Top-3 containment", "Top-5 containment", "Stability at sigma=0.01", "Stability at sigma=0.05"],
    "all_active_percent": [71.9, 85.3, 91.3, 95.2, 95.0, 75.0],
    "released_subset_percent": [81.6, 91.2, 94.6, 97.2, 96.0, 80.7],
})
algorithm.to_csv(DATA / "archived_algorithm_reliability.csv", index=False)
intervention = pd.DataFrame({
    "stage": ["Round 2", "Round 3", "AC-19 Physical audit"],
    "rows_reviewed": [808, 629, 65],
    "rows_with_comment_or_change": [251, 30, 3],
    "reassignments": [80, 19, 2],
})
intervention["comment_or_change_rate"] = intervention.rows_with_comment_or_change / intervention.rows_reviewed * 100
intervention["reassignment_rate"] = intervention.reassignments / intervention.rows_reviewed * 100
intervention.to_csv(DATA / "human_review_intervention_rates.csv", index=False)
fig, axes = plt.subplots(1, 2, figsize=(12.0, 4.9), gridspec_kw={"width_ratios": [1.35, 1]})
ax = axes[0]
x = range(len(algorithm))
ax.bar([i-0.18 for i in x], algorithm.all_active_percent, width=0.36, label="All active cards", color="#6C84C7")
ax.bar([i+0.18 for i in x], algorithm.released_subset_percent, width=0.36, label="Released subset", color="#A3B6E0")
ax.set_xticks(list(x), ["Top-1", "Top-2", "Top-3", "Top-5", "Stability\n0.01", "Stability\n0.05"])
ax.set_ylim(0, 105)
ax.set_ylabel("Percent")
ax.set_title("Archived semantic-mapping diagnostics", loc="left", weight="bold")
ax.legend(frameon=False, fontsize=8, loc="lower right")
ax.grid(axis="y", alpha=0.25)
ax.spines[["top", "right"]].set_visible(False)
for container in ax.containers:
    ax.bar_label(container, fmt="%.1f", fontsize=7, padding=2)
ax = axes[1]
y = range(len(intervention))
ax.barh([i+0.18 for i in y], intervention.comment_or_change_rate, height=0.34, label="Commented or flagged", color="#C77B30")
ax.barh([i-0.18 for i in y], intervention.reassignment_rate, height=0.34, label="Reassignment rate", color="#2E8B57")
ax.set_yticks(list(y), intervention.stage)
ax.set_xlim(0, 35)
ax.set_xlabel("Percent of reviewed rows")
ax.set_title("Observed human intervention", loc="left", weight="bold")
ax.legend(frameon=False, fontsize=8, loc="lower right")
ax.grid(axis="x", alpha=0.25)
ax.spines[["top", "right"]].set_visible(False)
for container in ax.containers:
    ax.bar_label(container, fmt="%.1f%%", fontsize=7, padding=2)
fig.suptitle("Algorithmic reliability and human-review divergence are different quantities", x=0.04, ha="left", weight="bold", fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.93])
finish(fig, "fig08_algorithm_human_reliability")


# Figure 9. Domain composition across the rebuild stages.
stages = pd.DataFrame([
    ("Rebuild baseline", 630, 74, 94),
    ("Round-2 recovery", 607, 77, 93),
    ("AC-08 audited", 487, 65, 77),
    ("Round 3", 492, 66, 65),
    ("AC-19 final", 494, 66, 63),
    ("Round 4 / current", 492, 67, 63),
], columns=["stage", "General", "Agentic", "Physical"])
stages.to_csv(DATA / "domain_counts_by_review_stage.csv", index=False)
fig, ax = plt.subplots(figsize=(10.0, 5.0))
bottom = pd.Series([0]*len(stages))
for domain_name in ["General", "Agentic", "Physical"]:
    ax.bar(stages.stage, stages[domain_name], bottom=bottom, label=domain_name,
           color=COLORS[domain_name], width=0.66)
    bottom += stages[domain_name]
for i, total in enumerate(stages[["General","Agentic","Physical"]].sum(axis=1)):
    ax.text(i, total+10, str(total), ha="center", fontsize=8, weight="bold")
ax.set_ylabel("Active L4 cards")
ax.set_ylim(0, 860)
ax.set_title("Domain composition changed through curation and boundary review", loc="left", weight="bold")
ax.legend(frameon=False, ncol=3, loc="upper right")
ax.grid(axis="y", alpha=0.25)
ax.spines[["top", "right"]].set_visible(False)
ax.tick_params(axis="x", rotation=20)
finish(fig, "fig09_domain_review_trajectory")


# Figure 10. Concentration of third-round review comments by source domain.
review_pressure = pd.DataFrame({
    "domain": ["General AI", "Agentic AI", "Physical AI"],
    "rows": [487, 65, 77],
    "commented": [13, 0, 17],
})
review_pressure["comment_rate"] = review_pressure.commented / review_pressure.rows * 100
review_pressure.to_csv(DATA / "round3_review_pressure_by_domain.csv", index=False)
fig, ax = plt.subplots(figsize=(8.2, 4.3))
bars = ax.bar(review_pressure.domain, review_pressure.comment_rate,
              color=[COLORS["General"], COLORS["Agentic"], COLORS["Physical"]], width=0.62)
ax.set_ylabel("Rows with review comments (%)")
ax.set_ylim(0, 26)
ax.set_title("The largest third-round disagreement concentrated in Physical AI", loc="left", weight="bold")
ax.grid(axis="y", alpha=0.25)
ax.spines[["top", "right"]].set_visible(False)
for b, rate, n, total in zip(bars, review_pressure.comment_rate, review_pressure.commented, review_pressure.rows):
    ax.text(b.get_x()+b.get_width()/2, rate+0.8, f"{rate:.1f}%\n({n}/{total})", ha="center", fontsize=9)
finish(fig, "fig10_round3_review_pressure")


# Annex hierarchy summary. L3 master paths govern display even if an L4 row retains a stale L2 field.
master = pd.read_csv(RELEASE / "data" / "L1_L2_L3_Master.csv", dtype=str).fillna("")
cards = []
for filename in ["L4_General.csv", "L4_Agentic.csv", "L4_Physical.csv"]:
    cards.append(pd.read_csv(RELEASE / "data" / filename, dtype=str).fillna(""))
cards = pd.concat(cards, ignore_index=True)
counts = cards.groupby("L3_ID").size().to_dict()
representatives = {}
for l3_id, group in cards.sort_values("L4_ID").groupby("L3_ID"):
    row = group.iloc[0]
    representatives[l3_id] = (row["L4_ID"], row["L4_Title_en"])
summary_rows = []
for _, row in master.iterrows():
    rep_id, rep_title = representatives.get(row["L3_ID"], ("", ""))
    summary_rows.append({
        "L1_ID": row["L1_ID"], "L1_Title_en": row["L1_Title_en"],
        "L2_ID": row["L2_ID"], "L2_Title_en": row["L2_Title_en"],
        "L3_ID": row["L3_ID"], "L3_Title_en": row["L3_Title_en"],
        "L4_Count": counts.get(row["L3_ID"], 0),
        "Representative_L4_ID": rep_id,
        "Representative_L4_Title_en": rep_title,
    })
hierarchy = pd.DataFrame(summary_rows)
hierarchy.to_csv(DATA / "final_hierarchy_summary.csv", index=False)
l2 = hierarchy.groupby(["L1_ID","L1_Title_en","L2_ID","L2_Title_en"], as_index=False).L4_Count.sum()
l2.to_csv(DATA / "final_l2_counts_master_aligned.csv", index=False)

def esc(value):
    value = str(value)
    for a, b in [("\\", "\\textbackslash{}"), ("&", "\\&"), ("%", "\\%"), ("#", "\\#"), ("_", "\\_")]:
        value = value.replace(a, b)
    return value

lines = [
    "\\begin{longtable}{L{0.09\\textwidth}L{0.11\\textwidth}L{0.15\\textwidth}L{0.23\\textwidth}rL{0.24\\textwidth}}",
    "\\caption{Final master hierarchy with L4 counts and one illustrative L4 card per L3.}\\label{tab:hierarchy-annex}\\\\",
    "\\toprule",
    "L1 & L2 & L3 ID & L3 title & L4 & Illustrative L4 \\\\",
    "\\midrule",
    "\\endfirsthead",
    "\\toprule",
    "L1 & L2 & L3 ID & L3 title & L4 & Illustrative L4 \\\\",
    "\\midrule",
    "\\endhead",
]
for _, row in hierarchy.iterrows():
    illustrative = "None assigned" if not row.Representative_L4_ID else f"{row.Representative_L4_ID}: {row.Representative_L4_Title_en}"
    lines.append("{} & {} & {} & {} & {} & {} \\\\".format(
        esc(row.L1_Title_en), esc(row.L2_Title_en), esc(row.L3_ID), esc(row.L3_Title_en),
        int(row.L4_Count), esc(illustrative)))
lines += ["\\bottomrule", "\\end{longtable}"]
(TABLES / "appendix_hierarchy_summary.tex").write_text("\n".join(lines) + "\n")


# Figure 11. Algorithm-supported mapping integrity across the three human-review rounds.
# Round 1 is a direct comparison with algorithmic Top-1. Rounds 2 and 3 measure
# retention of the incoming mapping, which already includes earlier human decisions.
em_diag = pd.read_csv(PROJECT / "03_outputs" / "audit" / "EM_Card_Diagnostics.csv", dtype=str).fillna("")
round1_reviewed = len(em_diag)
round1_changed = int((em_diag["mapping_method"] == "HD").sum())

round2_decisions = pd.read_csv(
    PROJECT / "06_human_review_recovery" / "Human_Review_Round2_Recovery_Decisions.csv",
    dtype=str,
).fillna("")
round2_reviewed = 808
round2_changed = int((round2_decisions["Final_Action"] == "REMAP").sum())
round2_all_actions = len(round2_decisions)

round3_record = json.loads(
    (PROJECT / "09_human_review_round3" / "Human_Review_Round3_Validation_Record.json").read_text()
)
round3_reviewed = int(round3_record["source_rows"])
round3_changed = int(round3_record["actions"]["MOVE_REWRITE"])
round3_all_actions = int(round3_record["commented_rows"])

integrity = pd.DataFrame([
    {
        "review_round": "Round 1",
        "comparison_basis": "Direct algorithmic Top-1 vs adjudicated L3",
        "source_artifact": "03_outputs/audit/EM_Card_Diagnostics.csv",
        "reviewed_rows": round1_reviewed,
        "mapping_changes": round1_changed,
        "mapping_retained": round1_reviewed - round1_changed,
        "all_recorded_interventions": round1_changed,
        "non_mapping_interventions": "not separately reconstructable",
    },
    {
        "review_round": "Round 2",
        "comparison_basis": "Incoming algorithm-supported, Round-1-audited mapping",
        "source_artifact": "06_human_review_recovery/Human_Review_Round2_Recovery_Decisions.csv",
        "reviewed_rows": round2_reviewed,
        "mapping_changes": round2_changed,
        "mapping_retained": round2_reviewed - round2_changed,
        "all_recorded_interventions": round2_all_actions,
        "non_mapping_interventions": str(round2_all_actions - round2_changed),
    },
    {
        "review_round": "Round 3",
        "comparison_basis": "Incoming cumulative mapping after prior audit",
        "source_artifact": "09_human_review_round3/Human_Review_Round3_Validation_Record.json",
        "reviewed_rows": round3_reviewed,
        "mapping_changes": round3_changed,
        "mapping_retained": round3_reviewed - round3_changed,
        "all_recorded_interventions": round3_all_actions,
        "non_mapping_interventions": str(round3_all_actions - round3_changed),
    },
])
integrity["mapping_retention_pct"] = integrity.mapping_retained / integrity.reviewed_rows * 100
integrity["mapping_gap_pct"] = integrity.mapping_changes / integrity.reviewed_rows * 100
integrity["all_intervention_pct"] = integrity.all_recorded_interventions / integrity.reviewed_rows * 100
integrity.to_csv(DATA / "three_round_algorithm_human_integrity.csv", index=False)

fig, ax = plt.subplots(figsize=(8.8, 4.8))
x = range(len(integrity))
retained = integrity.mapping_retention_pct
changed = integrity.mapping_gap_pct
ax.bar(x, retained, color="#3568D4", width=0.62, label="Mapping retained")
ax.bar(x, changed, bottom=retained, color="#E67E22", width=0.62, label="Human reassignment")
for i, row in integrity.iterrows():
    ax.text(i, row.mapping_retention_pct / 2, f"{row.mapping_retention_pct:.1f}%\nretained",
            ha="center", va="center", color="white", weight="bold")
    ax.text(i, row.mapping_retention_pct + row.mapping_gap_pct / 2,
            f"{row.mapping_gap_pct:.1f}%", ha="center", va="center", color="white", weight="bold")
    basis = "direct Top-1" if i == 0 else "incremental audit"
    ax.text(i, -7.5, basis, ha="center", va="top", fontsize=8, color=COLORS["neutral"])
ax.set_xticks(list(x), integrity.review_round)
ax.set_ylim(-12, 105)
ax.set_ylabel("Share of reviewed rows (%)")
ax.set_title("Mapping retention increased across three human-review rounds", loc="left", weight="bold")
ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.02))
ax.grid(axis="y", alpha=0.25)
ax.spines[["top", "right"]].set_visible(False)
finish(fig, "fig11_three_round_algorithm_human_integrity")

print(f"Generated figures in {FIG}")
