#!/usr/bin/env python3
"""Build the canonical artifact for the v2.7 definition/mapping audit report."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "reports/data_quality/l4_definition_mapping_remediation_v2.7.0"


def rows(name: str) -> list[dict]:
    with (AUDIT / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


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
            "filters": ["Published v2.7.0", "1,529 non-Physical L4 cards", "182 locked Physical cards excluded from editorial changes"],
            "metric_definitions": [
                "Rule-supported rate: cards whose assigned L3 appears in the frozen conservative classifier's eligible_l3_ids.",
                "HOLD: an operational placement requiring a human taxonomy decision; it is not a separate hierarchy.",
                "Legacy scaffold: prose that circularly defined an L4 card through imported L1-L3 family names.",
            ],
        },
    }


def main() -> None:
    summary = json.loads((AUDIT / "summary.json").read_text())
    l3 = rows("l3_load_audit.csv")
    remaps = rows("remapped_cards.csv")
    review_queue = rows("definition_review_queue.csv")
    for row in l3:
        row["card_count"] = int(row["card_count"])
        row["rule_supported_count"] = int(row["rule_supported_count"])
        row["rule_supported_pct"] = float(row["rule_supported_pct"])
        row["hold_count"] = int(row["hold_count"])
    top_l3 = l3[:10]
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    audit_source = source(
        "remediation-audit", "v2.7.0 remediation audit",
        "reports/data_quality/l4_definition_mapping_remediation_v2.7.0/summary.json",
        "Counts and card-level outputs from the reproducible v2.7.0 remediation script.",
    )
    release_source = source(
        "release-data", "Published v2.7.0 card data",
        "public/data/releases/v2.7.0/cards.json",
        "Canonical L4 definitions, operational L3 placements, HOLD state, and citations used by the website.",
    )
    headline = [{
        "nonphysical": 1529,
        "scaffolds_removed": summary["definition_remediation"]["legacy_taxonomy_scaffolds_removed"],
        "remapped": summary["mapping_remediation"]["cards_remapped"],
        "holds": summary["mapping_remediation"]["decision_required_total"],
        "physical_unchanged": 182,
    }]
    title = "L4 Definition and Mapping Remediation — v2.7.0"
    artifact = {
        "surface": "report",
        "manifest": {
            "version": 1,
            "surface": "report",
            "title": title,
            "description": "Technical audit of non-Physical L4 definition cleanup, L3 overload, and conservative remapping.",
            "generatedAt": now,
            "sources": [audit_source, release_source],
            "blocks": [
                {"id": "title", "type": "markdown", "layout": "full", "body": f"# {title}"},
                {"id": "summary", "type": "markdown", "layout": "full", "sourceId": "remediation-audit", "body": f"## Technical summary\n\nThe published non-Physical layer contained a systemic provenance/definition defect: **1,129 of 1,529 cards (73.84%)** appended imported hierarchy names to the actual risk description. v2.7.0 removes that circular prose, preserves all 182 Physical AI locks, applies nine evidence-constrained remaps, and marks {summary['mapping_remediation']['decision_required_total']} cards HOLD where the assigned path remains provisional. The result improves definitional validity but does not claim that the current 50 L3 nodes provide complete semantic coverage."},
                {"id": "metrics", "type": "metric-strip", "layout": "full", "cardIds": ["cleaned", "remapped", "holds", "physical"]},
                {"id": "load-finding", "type": "markdown", "layout": "full", "sourceId": "remediation-audit", "body": "## Anthropomorphism was an allocation sink, not a coherent risk family\n\nThe largest non-Physical L3 contains 247 cards, but only six (2.43%) meet the frozen classifier's direct eligibility rules for Anthropomorphism. Other large nodes show the same pattern at lower magnitude. Card count is therefore used only as a triage signal; it never justifies movement by itself. The implication is that forced placement converted open-set taxonomy gaps into apparently precise hierarchy paths."},
                {"id": "load-chart", "type": "chart", "layout": "full", "chartId": "l3-load"},
                {"id": "mapping-finding", "type": "markdown", "layout": "full", "sourceId": "release-data", "body": "## Nine clear conflicts were corrected without inventing new L3 nodes\n\nA remap required agreement among the L4 label, the mechanism-only definition, and the cited evidence. Compute-governance accountability moved out of Anthropomorphism to the closest operational path, Non-Contestability, but remains HOLD because governance accountability is not fully represented by that L3. Privacy inference moved to Privacy; essentialist categorization and model bias moved to Hate and Unfairness; the L4 label that duplicated Goal Misalignment was rewritten as a concrete uncorrectable-goal-pursuit mechanism."},
                {"id": "remap-table", "type": "table", "layout": "full", "tableId": "remaps"},
                {"id": "scope", "type": "markdown", "layout": "full", "body": "## Scope, data, and metric definitions\n\n**Population:** 1,711 canonical L4 cards in v2.6.0, comprising 1,529 non-Physical cards and 182 locked Physical cards. **Definition defect:** presence of legacy scaffold phrases beginning with `This L4 risk card treats`, including imported family and L1-domain names. **Overload measures:** per-L3 card count, share of the non-Physical population, direct rule-support count/rate, and HOLD count. **Comparison baseline:** unchanged v2.6.0. Physical cards were excluded from editorial and mapping mutations."},
                {"id": "method", "type": "markdown", "layout": "full", "body": "## Mechanism-first remediation method\n\n1. Split each affected English definition before the first legacy scaffold marker and normalize whitespace and punctuation.\n2. Replace short or ambiguous high-risk cases with source-checked definitions that state the condition, mechanism, and consequence without hierarchy names.\n3. Inspect overloaded L3 nodes using load and conservative rule support.\n4. Remap only confirmed conflicts supported jointly by title, mechanism, and evidence.\n5. Retain a forced operational path but set HOLD when the frozen gap detector identifies governance, labor, environmental, transparency, security, dependency, robustness, plural-values, deliberate-disinformation, or out-of-lock Physical coverage gaps.\n6. Replace the unrelated RAI4-0109 citation with the directly relevant paper *Computing Power and the Governance of Artificial Intelligence*."},
                {"id": "limits", "type": "markdown", "layout": "full", "sourceId": "remediation-audit", "body": "## Limitations and robustness checks\n\nThe frozen keyword rules are deliberately high precision and have low recall; a low rule-support rate is evidence for review, not proof that every assignment is wrong. Seventy-three definitions remain under 12 words and are queued for human editorial review. Because Anthropomorphism has a narrow necessary mechanism, every card lacking direct anthropomorphic evidence is marked HOLD; the other three largest L3 nodes require both absent rule support and a Stage 2 suitability below 0.45 before this additional HOLD rule applies. HOLD is epistemic metadata: it prevents an operational path from being presented as an approved semantic fit. Automated tests confirm unique IDs, complete assignments, zero banned scaffold phrases, the nine remaps, all detected gap cards marked HOLD, and exact Physical-card equality apart from the release identifier."},
                {"id": "next", "type": "markdown", "layout": "full", "body": "## Recommended next steps\n\n1. Human-review the 73 short definitions against their primary papers.\n2. Decide whether labor, environment, governance/accountability, transparency/explainability, and existential risk require new non-Physical L3 nodes.\n3. Review HOLD cards in descending order of L3 overload and source specificity.\n4. Add the scaffold ban, Physical lock equality, and taxonomy-gap-to-HOLD rule to release CI.\n5. Re-run the full reference identity audit on v2.7.0 before publication."},
                {"id": "questions", "type": "markdown", "layout": "full", "body": "## Further questions\n\nCan the current 50 L3 definitions be expanded without erasing their discriminative boundaries, or should the missing societal/governance mechanisms become new L3 nodes? What level of human evidence review is required before a HOLD path can be approved as a final mapping?"},
            ],
            "cards": [
                {"id": "cleaned", "description": "Non-Physical definitions stripped of circular legacy hierarchy prose.", "dataset": "headline", "sourceId": "remediation-audit", "metrics": [{"label": "Scaffolds removed", "field": "scaffolds_removed", "format": "number"}]},
                {"id": "remapped", "description": "Confirmed mapping conflicts moved after mechanism/evidence review.", "dataset": "headline", "sourceId": "remediation-audit", "metrics": [{"label": "Cards remapped", "field": "remapped", "format": "number"}]},
                {"id": "holds", "description": "Operational paths that still require a taxonomy decision.", "dataset": "headline", "sourceId": "remediation-audit", "metrics": [{"label": "HOLD cards", "field": "holds", "format": "number"}]},
                {"id": "physical", "description": "Physical AI cards preserved from the authoritative locked source.", "dataset": "headline", "sourceId": "release-data", "metrics": [{"label": "Physical unchanged", "field": "physical_unchanged", "format": "number"}]},
            ],
            "charts": [{
                "id": "l3-load", "title": "Largest non-Physical L3 assignments", "subtitle": "Top 10 by card count; labels show count and direct rule-support rate", "showDescription": True,
                "type": "horizontalBar", "intent": "ranking", "dataset": "top_l3", "sourceId": "remediation-audit",
                "encodings": {
                    "x": {"field": "label_en", "type": "nominal", "label": "L3"},
                    "y": {"field": "card_count", "type": "quantitative", "label": "L4 cards", "format": "number"},
                    "tooltip": [{"field": "card_count", "type": "quantitative", "format": "number"}, {"field": "rule_supported_pct", "type": "quantitative", "format": "number"}, {"field": "hold_count", "type": "quantitative", "format": "number"}],
                },
                "valueFormat": "number", "layout": "full", "maxRows": 10,
            }],
            "tables": [{
                "id": "remaps", "title": "Confirmed mapping corrections", "subtitle": "Nine cards reviewed against their mechanism and cited evidence", "dataset": "remaps", "sourceId": "release-data", "density": "spacious", "defaultSort": {"field": "l4_id", "direction": "asc"},
                "columns": [{"field": "l4_id", "label": "L4 ID", "type": "text"}, {"field": "label_en", "label": "Risk", "type": "text"}, {"field": "from_l3", "label": "Previous L3", "type": "text"}, {"field": "to_l3", "label": "v2.7 L3", "type": "text"}, {"field": "hold", "label": "HOLD", "type": "text"}, {"field": "reason", "label": "Review basis", "type": "text"}],
            }],
        },
        "snapshot": {"version": 1, "generatedAt": now, "status": "ready", "datasets": {"headline": headline, "top_l3": top_l3, "remaps": remaps, "definition_review_queue": review_queue}, "accessIssues": []},
        "sources": [audit_source, release_source],
    }
    (AUDIT / "artifact.json").write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (AUDIT / "chart_map.md").write_text(
        "# Chart map\n\n- Section: L3 overload. Question: which L3 nodes carry the largest forced load? Form: sorted horizontal bar. Fields: label_en, card_count, rule_supported_pct, hold_count. Takeaway: Anthropomorphism is the largest allocation sink and has 2.43% direct rule support. Palette: single-root preferred. Delivery: report.html.\n",
        encoding="utf-8",
    )
    print(AUDIT / "artifact.json")


if __name__ == "__main__":
    main()
