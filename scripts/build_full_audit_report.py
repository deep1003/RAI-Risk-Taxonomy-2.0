#!/usr/bin/env python3
"""Build the canonical portable HTML artifact for the v2.6 full audit."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "reports/validation/v2.6.0/full_audit"
OUT = ROOT / "reports/data_quality/full_mapping_reference_audit_v2.6.0"


def read_csv(name: str) -> list[dict[str, str]]:
    with (AUDIT / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def source(source_id: str, label: str, path: str, description: str) -> dict:
    return {
        "id": source_id,
        "label": label,
        "path": path,
        "query": {
            "language": "sql",
            "engine": "DuckDB",
            "sql": f"SELECT * FROM read_json_auto('{path}');",
            "description": description,
            "tables_used": [path],
            "filters": ["Published release v2.6.0", "All 1,711 canonical L4 cards"],
            "metric_definitions": [
                "Reachable URL: final HTTP response in the 2xx–3xx range.",
                "Access controlled: HTTP 401, 403, 407, 418, 429, or 451; not counted as broken.",
                "Semantic review queue: union of low semantic score, low margin, Stage 3 forced, decision-required, and L3-label leakage flags.",
            ],
        },
    }


def main() -> None:
    summary = json.loads((AUDIT / "audit_summary.json").read_text(encoding="utf-8"))
    mapping = read_csv("mapping_audit.csv")
    references = read_csv("reference_instance_audit.csv")
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    semantic_queue = [
        row for row in mapping
        if any(flag in row["audit_flags"] for flag in (
            "LOW_SEMANTIC_SCORE", "LOW_SEMANTIC_MARGIN", "STAGE3_FORCED",
            "DECISION_REQUIRED", "L3_LABEL_USED_AS_L4",
        ))
    ]
    confirmed_mapping = [
        {"l4_id": "RAI4-0116", "current_l3": "Copyrights", "issue": "Human override failure is not a copyright mechanism.", "recommended_action": "Review for Non-Contestability."},
        {"l4_id": "RAI4-0995", "current_l3": "Copyrights", "issue": "Job usurpation by automation is not a copyright mechanism.", "recommended_action": "HOLD; test whether a new non-physical labor-impact L3 is required."},
        {"l4_id": "RAI4-1002", "current_l3": "Sexual", "issue": "Essentialist social categorization is a discrimination mechanism; sexual orientation is only one example.", "recommended_action": "Review for Hate and Unfairness."},
        {"l4_id": "RAI4-1073", "current_l3": "Sexual", "issue": "The definition explicitly concerns inference of private information.", "recommended_action": "Review for Privacy."},
        {"l4_id": "RAI4-1221", "current_l3": "Sexual", "issue": "Algorithmic bias spans groups and decisions; sexual content is not the mechanism.", "recommended_action": "Review for Hate and Unfairness or taxonomy gap."},
        {"l4_id": "RAI4-1302", "current_l3": "Self-harm", "issue": "Human-extinction risk is not individual self-harm content.", "recommended_action": "HOLD; taxonomy decision required."},
        {"l4_id": "RAI4-1371", "current_l3": "Excessive Authority", "issue": "Labor-market job loss is not excessive agent permission.", "recommended_action": "HOLD; test whether a new non-physical labor-impact L3 is required."},
        {"l4_id": "RAI4-1431", "current_l3": "Goal Misalignment", "issue": "The L4 label exactly duplicates the L3 category label.", "recommended_action": "Remove or redefine as a concrete L4 mechanism."},
        {"l4_id": "RAI4-1581", "current_l3": "Anthropomorphism", "issue": "Sockpuppet-account creation does not attribute human qualities to AI.", "recommended_action": "Review for Misinformation/Disinformation or Illegal."},
        {"l4_id": "RAI4-1660", "current_l3": "Destabilising Dynamics", "issue": "General workforce effects do not require multi-agent feedback loops.", "recommended_action": "HOLD; taxonomy decision required."},
    ]
    mapping_by_id = {row["l4_id"]: row for row in mapping}
    for row in confirmed_mapping:
        row["label_en"] = mapping_by_id[row["l4_id"]]["label_en"]

    confirmed_reference_groups = [
        {"affected_instances": 12, "cards": "RAI4-0517 and 11 others", "issue": "AILUMINATE citation opens an unrelated fault-diagnosis paper (arXiv:2503.05732).", "recommended_url": "https://mlcommons.org/ailuminate/safety-methodology/"},
        {"affected_instances": 4, "cards": "RAI4-0028–0031", "issue": "InjecAgent / AgentDojo label opens a later computer-using-agent survey.", "recommended_url": "https://arxiv.org/abs/2403.02691 and https://arxiv.org/abs/2406.13352"},
        {"affected_instances": 3, "cards": "RAI4-0032–0034", "issue": "ToolEmu label opens the unrelated ASTRA paper.", "recommended_url": "https://arxiv.org/abs/2309.15817"},
        {"affected_instances": 1, "cards": "RAI4-0248", "issue": "DOI contains a literal backslash before the underscore and returns 404.", "recommended_url": "https://doi.org/10.1007/978-1-84996-220-9_4"},
        {"affected_instances": 1, "cards": "RAI4-0302", "issue": "Legacy Boston Dynamics URL returns 404.", "recommended_url": "https://bostondynamics.com/news/general-purpose-robots-should-not-be-weaponized/"},
        {"affected_instances": 7, "cards": "RAI4-0303, 0304, 0305, 0306, 0308, 0309, 0315", "issue": "Physical reference has justification text but empty title and URL.", "recommended_url": "Populate the verified source candidates listed in the audit narrative."},
    ]
    unlinked_candidates = [
        {"l4_id": "RAI4-0303", "candidate_title": "CCW Group of Governmental Experts on Lethal Autonomous Weapons Systems (2023)", "candidate_url": "https://meetings.unoda.org/ccw-/convention-on-certain-conventional-weapons-group-of-governmental-experts-on-lethal-autonomous-weapons-systems-2023", "basis": "Matches the stored 'UN CCW, 2023' justification; official UNODA page.", "status": "reachable"},
        {"l4_id": "RAI4-0304", "candidate_title": "A real-time intelligent intrusion detection framework for robotic system cybersecurity", "candidate_url": "https://doi.org/10.1007/s12083-025-02175-6", "basis": "Matches the truncated stored title; DOI resolves to the publisher.", "status": "reachable"},
        {"l4_id": "RAI4-0305", "candidate_title": "What the Law Can (and Can't) Do About Online Harassment", "candidate_url": "https://cyberlaw.stanford.edu/press/what-law-can-and-cant-do-about-online-harassment/", "basis": "Matches the stored Citron (2014) harassment citation; institutional page.", "status": "reachable; relevance review required"},
        {"l4_id": "RAI4-0306", "candidate_title": "First impressions of a humanoid social robot with natural language capabilities", "candidate_url": "https://researchprofiles.canberra.edu.au/en/publications/first-impressions-of-a-humanoid-social-robot-with-natural-languag/", "basis": "Matches Herath et al. (2025); university research portal.", "status": "reachable"},
        {"l4_id": "RAI4-0308", "candidate_title": "Ethics of Social Robotics: Individual and Societal Concerns and Opportunities", "candidate_url": "https://doi.org/10.1146/annurev-control-062023-082238", "basis": "Exact Torras (2024) article and DOI.", "status": "publisher access controlled; DOI registered"},
        {"l4_id": "RAI4-0309", "candidate_title": "Children with and without reading difficulty value robot reading companions that are smart, supportive, and personalised", "candidate_url": "https://www.nature.com/articles/s41598-025-15341-w", "basis": "Matches Moffat et al. (2025); publisher page.", "status": "reachable"},
        {"l4_id": "RAI4-0315", "candidate_title": "Algorithmic Management practices in regular workplaces: case studies in logistics and healthcare", "candidate_url": "https://www.ilo.org/publications/algorithmic-management-practices-regular-workplaces-case-studies-logistics", "basis": "Matches the 2024 algorithmic-management surveillance justification; ILO page.", "status": "reachable; relevance review required"},
    ]

    verdict_counts = summary["references"]["instance_verdict_counts"]
    chart_rows = [
        {"status": label, "count": verdict_counts.get(key, 0), "classification": group, "denominator": 1890}
        for label, key, group in (
            ("Verified identity", "PASS", "verified"),
            ("Reachable; title unavailable", "REACHABLE_TITLE_UNVERIFIED", "inconclusive"),
            ("Citation metadata unavailable", "CITATION_METADATA_UNVERIFIED", "inconclusive"),
            ("Title review flag", "TITLE_MISMATCH_REVIEW", "review"),
            ("Access controlled", "ACCESS_CONTROLLED", "inconclusive"),
            ("Unlinked", "UNLINKED", "failure"),
            ("URL failed", "URL_FAILED", "failure"),
        )
    ]
    headline = [{
        "l4_cards": 1711,
        "valid_paths": 1711,
        "physical_lock_matches": 182,
        "unique_urls": 333,
        "reachable_urls": 325,
        "confirmed_reference_fixes": 28,
        "semantic_review_queue": len(semantic_queue),
    }]

    audit_source = source(
        "full-audit",
        "Full mapping and reference audit outputs",
        "reports/validation/v2.6.0/full_audit/audit_summary.json",
        "Reproducible structural, semantic-risk, URL-response, redirect, and citation-identity checks.",
    )
    release_source = source(
        "published-release",
        "Published v2.6.0 card and hierarchy data",
        "public/data/releases/v2.6.0/cards.json",
        "Published L4 cards and L0–L3 placements used by the website.",
    )
    sources = [audit_source, release_source]

    title = "RAI Risk Taxonomy 2.0 — Full Mapping and Reference Audit (v2.6.0)"
    artifact = {
        "surface": "report",
        "manifest": {
            "version": 1,
            "surface": "report",
            "title": title,
            "description": "Exhaustive structural and reference audit of the published v2.6.0 snapshot.",
            "generatedAt": now,
            "sources": sources,
            "blocks": [
                {"id": "title", "type": "markdown", "layout": "full", "body": f"# {title}"},
                {"id": "summary", "type": "markdown", "layout": "full", "sourceId": "full-audit", "body": "## Technical summary\n\nThe release is structurally consistent, but it is **not yet semantically validated or reference-clean**. All 1,711 L4 cards have valid L0–L3 paths and source crosswalks, and all 182 Physical AI locks match their source taxonomy. However, 690 cards enter a conservative semantic review queue, including 165 Stage 3 forced placements and 76 cards already marked HOLD. Reference testing found 325 of 333 non-empty unique URLs reachable, six access-controlled, and two broken; seven Physical AI citations have no URL. Manual review confirms 28 reference instances that need concrete correction."},
                {"id": "headline-strip", "type": "metric-strip", "layout": "full", "cardIds": ["paths", "physical", "urls", "reference-fixes", "semantic-queue"]},
                {"id": "reference-finding", "type": "markdown", "layout": "full", "sourceId": "full-audit", "body": "## Most links open, but 28 reference instances require correction\n\nThe chart separates confirmed identity, inconclusive automated verification, review flags, access controls, and failures. A 403 or an unreadable PDF title is not classified as a broken source. Of the 33 automated title-review flags, manual verification found 19 direct-link mismatches across three reference groups; the other 14 are acceptable renamed headlines, dataset/repository pages, or title variants."},
                {"id": "reference-chart", "type": "chart", "layout": "full", "chartId": "reference-status"},
                {"id": "reference-table-heading", "type": "markdown", "layout": "full", "body": "## Confirmed reference corrections\n\nThese groups should be repaired before the reference layer is described as verified."},
                {"id": "reference-table", "type": "table", "layout": "full", "tableId": "reference-fixes"},
                {"id": "unlinked-heading", "type": "markdown", "layout": "full", "body": "## Candidate sources for the seven unlinked Physical AI citations\n\nThese candidates were located from the stored author/year or truncated-title evidence. They are not written into release data until a human confirms that each source supports the specific card claim."},
                {"id": "unlinked-table", "type": "table", "layout": "full", "tableId": "unlinked-candidates"},
                {"id": "mapping-finding", "type": "markdown", "layout": "full", "sourceId": "full-audit", "body": "## Structural placement passes; semantic correctness does not\n\nThe complete mapping is reproducible: every non-Physical card is assigned to the algorithm's recorded top-1 candidate. That confirms implementation consistency, not taxonomy validity. Low scores, low margins, forced placements, HOLD status, and L3-label leakage place 690 cards in the conservative review queue. Ten clear conflicts are listed below; they demonstrate that 100% placement must not be interpreted as 100% correct classification."},
                {"id": "mapping-table", "type": "table", "layout": "full", "tableId": "mapping-conflicts"},
                {"id": "scope", "type": "markdown", "layout": "full", "body": "## Scope, definitions, and methodology\n\n**Population.** Published release v2.6.0: 1,711 canonical L4 cards, 60 L0–L3 implementation nodes, 1,890 reference instances, and 333 non-empty unique URLs.\n\n**Mapping checks.** Identifier uniqueness, parent-child integrity, complete L0–L3 paths, source-crosswalk coverage, Physical lock equality, algorithm-score reproducibility, L3-label leakage, and conservative semantic-risk flags.\n\n**Reference checks.** HTTP GET with redirects and a bounded response body; arXiv abstract-page normalization; DOI title/author verification through Crossref; OpenAlex registry verification; HTML/PDF metadata extraction; citation-title or author identity comparison; and manual review of high-precision failures. Network requests were deduplicated by URL and expanded back to every card instance."},
                {"id": "limitations", "type": "markdown", "layout": "full", "body": "## Limitations, uncertainty, and robustness\n\nAutomated reachability is a dated observation and can vary with publisher bot controls. Six unique URLs returned access controls rather than evidence of deletion. Direct PDFs without extractable metadata and bibliographic citations without exposed author metadata remain inconclusive. Semantic scores and keyword rules cannot certify that a source actually supports every sentence in a card; source-content entailment and final remapping still require human review. The report therefore distinguishes structural PASS, confirmed errors, and unresolved verification rather than converting them into one accuracy percentage."},
                {"id": "next-steps", "type": "markdown", "layout": "full", "body": "## Recommended next steps\n\n1. Correct the 28 confirmed reference instances, beginning with the unrelated AILUMINATE URL and the two broken links.\n2. Populate the seven empty Physical AI citations from their named evidence candidates.\n3. Remove or redefine RAI4-1431 because its label duplicates the L3 category.\n4. Human-review the ten confirmed mapping conflicts, then process the remaining semantic queue in descending risk order.\n5. Add URL reachability, source-title identity, Physical lock equality, and L3-label leakage to release CI."},
                {"id": "questions", "type": "markdown", "layout": "full", "body": "## Further questions\n\nShould broadly scoped literature reviews remain valid evidence links when the displayed reference title names a benchmark discussed inside the review, or should every displayed title link directly to the benchmark's primary paper? Should non-Physical labor displacement, environmental impact, and extinction risks trigger new L3 taxonomy decisions rather than forced placement into the existing 20 General/Agentic L3 nodes?"},
            ],
            "cards": [
                {"id": "paths", "description": "Cards with a complete valid L0–L3 parent chain.", "dataset": "headline", "sourceId": "full-audit", "metrics": [{"label": "Valid paths", "field": "valid_paths", "format": "number"}]},
                {"id": "physical", "description": "Physical AI source locks reproduced exactly.", "dataset": "headline", "sourceId": "full-audit", "metrics": [{"label": "Physical lock matches", "field": "physical_lock_matches", "format": "number"}]},
                {"id": "urls", "description": "Unique non-empty URLs that returned 2xx–3xx.", "dataset": "headline", "sourceId": "full-audit", "metrics": [{"label": "Reachable unique URLs", "field": "reachable_urls", "format": "number"}, {"label": "of", "field": "unique_urls", "format": "number"}]},
                {"id": "reference-fixes", "description": "Reference instances with a confirmed correction.", "dataset": "headline", "sourceId": "full-audit", "metrics": [{"label": "Confirmed reference fixes", "field": "confirmed_reference_fixes", "format": "number"}]},
                {"id": "semantic-queue", "description": "Conservative union of semantic uncertainty flags.", "dataset": "headline", "sourceId": "full-audit", "metrics": [{"label": "Semantic review queue", "field": "semantic_review_queue", "format": "number"}]},
            ],
            "charts": [{
                "id": "reference-status",
                "title": "Reference-instance verification status",
                "subtitle": "All 1,890 displayed reference instances; exact counts",
                "showDescription": True,
                "type": "horizontalBar",
                "intent": "status",
                "dataset": "reference_status",
                "sourceId": "full-audit",
                "encodings": {
                    "x": {"field": "status", "type": "nominal", "label": "Verification status"},
                    "y": {"field": "count", "type": "quantitative", "label": "Reference instances", "format": "number"},
                    "tooltip": [{"field": "count", "type": "quantitative", "format": "number"}, {"field": "classification", "type": "nominal"}],
                },
                "valueFormat": "number",
                "layout": "full",
                "maxRows": 7,
            }],
            "tables": [
                {"id": "reference-fixes", "title": "Confirmed reference corrections", "subtitle": "28 affected reference instances across six correction groups", "dataset": "reference_fixes", "sourceId": "full-audit", "density": "spacious", "defaultSort": {"field": "affected_instances", "direction": "desc"}, "columns": [{"field": "affected_instances", "label": "Instances", "format": "number"}, {"field": "cards", "label": "Cards", "type": "text"}, {"field": "issue", "label": "Confirmed issue", "type": "text"}, {"field": "recommended_url", "label": "Correction candidate", "type": "text"}]},
                {"id": "mapping-conflicts", "title": "Confirmed or high-confidence mapping conflicts", "subtitle": "Examples established from the card definition and the assigned L3 definition", "dataset": "mapping_conflicts", "sourceId": "published-release", "density": "spacious", "defaultSort": {"field": "l4_id", "direction": "asc"}, "columns": [{"field": "l4_id", "label": "L4 ID", "type": "text"}, {"field": "label_en", "label": "Risk", "type": "text"}, {"field": "current_l3", "label": "Current L3", "type": "text"}, {"field": "issue", "label": "Conflict", "type": "text"}, {"field": "recommended_action", "label": "Recommended action", "type": "text"}]},
                {"id": "unlinked-candidates", "title": "Candidate sources for unlinked Physical AI citations", "subtitle": "Seven candidates; all require human relevance confirmation before release mutation", "dataset": "unlinked_candidates", "sourceId": "full-audit", "density": "spacious", "defaultSort": {"field": "l4_id", "direction": "asc"}, "columns": [{"field": "l4_id", "label": "L4 ID", "type": "text"}, {"field": "candidate_title", "label": "Candidate source", "type": "text"}, {"field": "candidate_url", "label": "URL", "type": "text"}, {"field": "basis", "label": "Match basis", "type": "text"}, {"field": "status", "label": "Observed status", "type": "text"}]},
            ],
        },
        "snapshot": {
            "version": 1,
            "generatedAt": now,
            "status": "ready",
            "datasets": {
                "headline": headline,
                "reference_status": chart_rows,
                "reference_fixes": confirmed_reference_groups,
                "mapping_conflicts": confirmed_mapping,
                "unlinked_candidates": unlinked_candidates,
            },
            "accessIssues": [],
        },
        "sources": sources,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(AUDIT / "semantic_review_queue.csv", semantic_queue)
    write_csv(AUDIT / "confirmed_mapping_conflicts.csv", confirmed_mapping)
    write_csv(AUDIT / "confirmed_reference_corrections.csv", confirmed_reference_groups)
    write_csv(AUDIT / "unlinked_physical_reference_candidates.csv", unlinked_candidates)
    (OUT / "artifact.json").write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUT / "artifact.json")


if __name__ == "__main__":
    main()
