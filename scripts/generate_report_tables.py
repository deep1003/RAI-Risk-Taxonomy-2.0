#!/usr/bin/env python3
"""Generate escaped LaTeX commands and table rows from validated release data."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "v1.0.0"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def tex(value) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def command(name: str, value) -> str:
    return rf"\newcommand{{\{name}}}{{{tex(value)}}}"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_rows(path: Path, rows: list[str]) -> None:
    """Write longtable rows with the closing rule in the same input stream."""
    write(path, "\n".join(rows + [r"\bottomrule"]))


def pct(numerator: int, denominator: int) -> str:
    return f"{100 * numerator / denominator:.1f}"


def main() -> None:
    data_dir = ROOT / "data" / "releases" / RELEASE
    validation_dir = ROOT / "reports" / "validation" / RELEASE
    generated = ROOT / "reports" / "latex" / "generated"

    nodes = load(data_dir / "taxonomy_nodes.json")
    registry = load(data_dir / "l4_registry.json")
    placements = load(data_dir / "placements.json")
    crosswalk = load(data_dir / "source_crosswalk.json")
    locks = load(data_dir / "physical_lock.json")
    manifest = load(data_dir / "manifest.json")
    coverage = load(validation_dir / "coverage_summary.json")
    consensus = load(validation_dir / "frontier_expert_consensus_summary.json")
    local_sensitivity = load(validation_dir / "local_model_sensitivity_summary.json")
    validation = load(validation_dir / "validation_summary.json")
    clusters = load(validation_dir / "unresolved_clusters.json")

    status_counts = Counter(row["assignment_status"] for row in placements)
    initial_proposals = consensus["reviewed_initial_proposals"]
    final_proposals = status_counts["algorithm_proposed"]
    needs = status_counts["needs_taxonomy_decision"]
    macro_lines = [
        command("TotalLFour", f"{len(registry):,}"),
        command("TotalNodes", f"{len(nodes):,}"),
        command("TotalLThree", f"{sum(row['level'] == 3 for row in nodes):,}"),
        command("PhysicalLocked", f"{status_counts['locked_physical']:,}"),
        command("InitialProposals", f"{initial_proposals:,}"),
        command("FinalProposals", f"{final_proposals:,}"),
        command("NeedsDecision", f"{needs:,}"),
        command("NonPhysicalTotal", "1,544"),
        command("ProposalRate", pct(final_proposals, 1544)),
        command("NeedsRate", pct(needs, 1544)),
        command("ExactMatches", f"{sum(row['relationship'] == 'exact_id' for row in crosswalk):,}"),
        command("ExplicitAliases", f"{sum(row['relationship'] == 'explicit_alias' for row in crosswalk):,}"),
        command("ExpertBothApprove", f"{consensus['both_approved']:,}"),
        command("LocalReviewed", f"{local_sensitivity['reviewed_cards']:,}"),
        command("LocalSameNonNeeds", f"{local_sensitivity['same_non_needs_l3']:,}"),
        command("LocalDisagreement", f"{local_sensitivity['disagreement']:,}"),
        command("ValidationStatus", validation["status"]),
        command("ValidationPassed", f"{validation['passed_checks']:,}"),
        command("ValidationFailed", f"{validation['failed_checks']:,}"),
        command("ValidationWarnings", f"{validation['warning_checks']:,}"),
        command("CoverageConclusion", coverage["fifty_l3_sufficiency_status"]),
        command("UnresolvedClusters", f"{len(clusters):,}"),
    ]
    write(generated / "metrics.tex", "\n".join(macro_lines))

    node_by_id = {row["node_id"]: row for row in nodes}
    l3_counts = Counter(row["primary_l3_id"] for row in placements if row["primary_l3_id"])
    l3_lines = []
    for node in [row for row in nodes if row["level"] == 3]:
        parent = node_by_id[node["parent_id"]]
        status = "Physical lock" if node["node_id"].startswith("RAI3-P-") else "Provisional"
        l3_lines.append(
            f"{tex(node['node_id'])} & {tex(parent['label_en'])} & {tex(node['label_en'])} & {l3_counts[node['node_id']]:,} & {tex(status)} \\\\"
        )
    write_rows(generated / "l3_distribution_rows.tex", l3_lines)

    gap_lines = [
        f"{tex(name)} & {count:,} \\\\"
        for name, count in sorted(coverage["gap_sentinel_counts"].items(), key=lambda item: (-item[1], item[0]))
    ]
    write_rows(generated / "gap_rows.tex", gap_lines)

    reason_counts = Counter(
        row["abstention_reason"] for row in placements if row["assignment_status"] == "needs_taxonomy_decision"
    )
    reason_lines = [
        f"{tex(name)} & {count:,} & {pct(count, 1544)}\\% \\\\"
        for name, count in reason_counts.most_common()
    ]
    write_rows(generated / "abstention_rows.tex", reason_lines)

    alias_lines = []
    for row in sorted(
        [row for row in crosswalk if row["relationship"] == "explicit_alias"],
        key=lambda item: item["source_id"],
    ):
        alias_lines.append(
            f"{tex(row['source_id'])} & {tex(row['canonical_source_id'])} & {tex(row['l4_id'])} \\\\"
        )
    write_rows(generated / "alias_rows.tex", alias_lines)

    cluster_lines = []
    for row in sorted(clusters, key=lambda item: -item["card_count"])[:12]:
        representatives = "; ".join(card["label"] for card in row["representative_cards"][:3])
        gaps = ", ".join(f"{name} ({count})" for name, count in row["dominant_gap_sentinels"][:2]) or "none"
        cluster_lines.append(
            f"{tex(row['cluster_id'])} & {row['card_count']:,} & {tex(representatives)} & {tex(gaps)} \\\\"
        )
    write_rows(generated / "cluster_rows.tex", cluster_lines)

    validation_lines = []
    for check in validation["checks"]:
        validation_lines.append(
            f"{tex(check['check_id'])} & {tex(check['description'])} & {tex(check['status'])} \\\\"
        )
    write_rows(generated / "validation_rows.tex", validation_lines)

    source_lines = []
    for source in manifest["sources"]:
        source_lines.append(
            f"{tex(source['name'])} & {source['record_count']:,} & \\texttt{{{tex(source['sha256'][:16])}...}} & \\texttt{{{tex((source.get('source_git_commit') or 'n/a')[:12])}}} \\\\"
        )
    write_rows(generated / "source_rows.tex", source_lines)

    proposed_lines = []
    registry_by_l4 = {row["l4_id"]: row for row in registry}
    for row in [row for row in placements if row["assignment_status"] == "algorithm_proposed"]:
        card = registry_by_l4[row["l4_id"]]
        proposed_lines.append(
            f"{tex(row['l4_id'])} & {tex(card['label_en'])} & {tex(row['primary_l3_id'])} \\\\"
        )
    write_rows(generated / "proposed_rows.tex", proposed_lines)

    print(
        json.dumps(
            {
                "generated_dir": str(generated),
                "initial_proposals": initial_proposals,
                "final_proposals": final_proposals,
                "needs": needs,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
