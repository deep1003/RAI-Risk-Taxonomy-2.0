#!/usr/bin/env python3
"""Build the portable technical report for the v2.7 Anthropomorphism review."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/data_quality/anthropomorphism_review_v2.7.0"


def read_csv() -> list[dict]:
    with (OUT / "card_level_review.csv").open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def source(source_id: str, label: str, path: str, description: str) -> dict:
    return {
        "id": source_id,
        "label": label,
        "path": path,
        "query": {
            "language": "sql",
            "engine": "DuckDB",
            "sql": f"SELECT * FROM read_csv_auto('{path}');",
            "description": description,
            "tables_used": [path],
            "filters": ["Release v2.7.0", "Current primary_l3_id = RAI3-G-INT-10", "All 245 matching cards"],
            "metric_definitions": [
                "Retain: human-likeness is a necessary causal mechanism.",
                "High-confidence remap: title, definition, and source directly satisfy another L3.",
                "Remap with HOLD: another L3 is closer but covers only part of the mechanism.",
                "Taxonomy-gap HOLD: no current L3 accepts the card without forcing.",
            ],
        },
    }


def main() -> None:
    summary = json.loads((OUT / "summary.json").read_text())
    rows = read_csv()
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    verdict_labels = {
        "RETAIN_ANTHROPOMORPHISM": "Retain in Anthropomorphism",
        "REMAP_HIGH_CONFIDENCE": "High-confidence remap",
        "REMAP_WITH_HOLD": "Closer L3, retain HOLD",
        "HOLD_TAXONOMY_GAP": "No valid L3; HOLD",
    }
    verdict_rows = [
        {"verdict": verdict_labels[key], "count": summary["verdict_counts"].get(key, 0), "denominator": 245}
        for key in verdict_labels
    ]
    target_rows = []
    for l3_id, count in summary["proposed_target_counts"].items():
        match = next(row for row in rows if row["proposed_l3_id"] == l3_id)
        target_rows.append({"l3_id": l3_id, "l3_label": match["proposed_l3_label"], "count": count})
    target_rows.sort(key=lambda row: (-row["count"], row["l3_id"]))
    remap_rows = [row for row in rows if row["verdict"].startswith("REMAP")]
    retain_rows = [row for row in rows if row["verdict"] == "RETAIN_ANTHROPOMORPHISM"]
    headline = [{
        "reviewed": 245,
        "retained": summary["verdict_counts"]["RETAIN_ANTHROPOMORPHISM"],
        "remapped": summary["verdict_counts"]["REMAP_HIGH_CONFIDENCE"] + summary["verdict_counts"]["REMAP_WITH_HOLD"],
        "taxonomy_gap": summary["verdict_counts"]["HOLD_TAXONOMY_GAP"],
    }]
    audit_source = source(
        "anthropomorphism-review", "Anthropomorphism card-level review",
        "reports/data_quality/anthropomorphism_review_v2.7.0/card_level_review.csv",
        "Exhaustive mechanism-first review of every v2.7 card assigned to Anthropomorphism.",
    )
    release_source = {
        "id": "v2.7-release",
        "label": "RAI Risk Taxonomy v2.7.0",
        "path": "public/data/releases/v2.7.0/cards.json",
        "query": {
            "language": "sql", "engine": "DuckDB",
            "sql": "SELECT * FROM read_json_auto('public/data/releases/v2.7.0/cards.json');",
            "description": "Published card labels, mechanism definitions, references, and current L3 paths.",
            "tables_used": ["public/data/releases/v2.7.0/cards.json"],
            "filters": ["1,711 canonical L4 cards", "Published v2.7.0 snapshot"],
            "metric_definitions": ["Operational assignment is not equivalent to human-approved semantic fit."],
        },
    }
    title = "Anthropomorphism L3 Full Review — v2.7.0"
    artifact = {
        "surface": "report",
        "manifest": {
            "version": 1, "surface": "report", "title": title,
            "description": "Necessary-condition audit of all 245 L4 cards assigned to Anthropomorphism.",
            "generatedAt": now, "sources": [audit_source, release_source],
            "blocks": [
                {"id": "title", "type": "markdown", "layout": "full", "body": f"# {title}"},
                {"id": "summary", "type": "markdown", "layout": "full", "sourceId": "anthropomorphism-review", "body": "## Technical summary\n\nThe apparent 245-card category is not semantically defensible. Under a necessary-condition test, only **13 cards (5.31%)** treat human-likeness as the causal risk mechanism. **32 cards** have a direct, high-confidence destination elsewhere; **24 cards** have a closer L3 but must remain HOLD because that destination covers only part of the mechanism; and **176 cards** expose gaps in the current 50-L3 design. Redistributing cards to hit a target count would weaken the standard. The defensible action is to apply the 56 evidence-based remaps and treat the remaining 176 as unresolved taxonomy decisions."},
                {"id": "metrics", "type": "metric-strip", "layout": "full", "cardIds": ["reviewed", "retained", "remapped", "gap"]},
                {"id": "verdict-finding", "type": "markdown", "layout": "full", "sourceId": "anthropomorphism-review", "body": "## Human-likeness is necessary in only 13 cards\n\nAnthropomorphism means attributing human qualities to a non-human system. The card must therefore depend on perceived consciousness, emotion, personhood, embodiment, reciprocal sociality, or human-like intentionality. Dependence, overreliance, persuasion, governance, labor, environmental harm, bias, privacy, political interference, crime, weaponization, and information integrity do not qualify unless human-likeness is necessary to the harm pathway."},
                {"id": "verdict-chart", "type": "chart", "layout": "full", "chartId": "verdicts"},
                {"id": "target-finding", "type": "markdown", "layout": "full", "sourceId": "anthropomorphism-review", "body": "## Fifty-six cards can move without quota-driven redistribution\n\nThe largest defensible destination is Hate and Unfairness, followed by Political Neutrality and Privacy. Twenty-four moves remain HOLD because the existing target is narrower than the card—for example, allocative discrimination placed under a content-oriented unfairness node. These are operational improvements, not final approval of the 50-L3 design."},
                {"id": "target-chart", "type": "chart", "layout": "full", "chartId": "targets"},
                {"id": "retain-heading", "type": "markdown", "layout": "full", "body": "## Thirteen cards satisfy the strict Anthropomorphism rule\n\nThese cards explicitly make human-like attribution, presentation, or social reciprocity part of the causal mechanism."},
                {"id": "retain-table", "type": "table", "layout": "full", "tableId": "retained"},
                {"id": "remap-heading", "type": "markdown", "layout": "full", "body": "## Proposed card-level remaps\n\nEvery proposed move identifies its destination, whether human review remains required, and the rule supporting the move."},
                {"id": "remap-table", "type": "table", "layout": "full", "tableId": "remaps"},
                {"id": "scope", "type": "markdown", "layout": "full", "body": "## Scope, evidence, and definitions\n\n**Population:** every card whose published v2.7.0 `primary_l3_id` is `RAI3-G-INT-10` (245 of 1,711 L4 cards). **Evidence per card:** English title, mechanism-only English definition, citation identity, and the frozen definitions of all candidate L3 nodes. **Comparison baseline:** the current operational assignment. **Primary metric:** card count by review verdict; percentages use 245 as the denominator."},
                {"id": "method", "type": "markdown", "layout": "full", "body": "## Necessary-condition review method\n\n1. Retain only when human-like attribution is necessary to the harm mechanism.\n2. Exclude coincidental words such as *human*, *emotion*, *agent*, *trust*, or *interaction* when the risk persists without anthropomorphism.\n3. Remap only when the title, mechanism definition, and cited source directly satisfy another existing L3.\n4. Keep HOLD after a closest-fit move when the target L3 is narrower than the card.\n5. Do not use existing global L1–L3 names as ground truth and do not redistribute to satisfy a desired category size.\n6. Leave cards without a valid destination as taxonomy-gap HOLD pending a human decision on L3 expansion or creation."},
                {"id": "limits", "type": "markdown", "layout": "full", "body": "## Limitations and robustness\n\nThis is an expert-rule review, not an empirical inter-rater reliability estimate. The 176 taxonomy-gap cards include dependency/manipulation, governance/accountability, labor/economic, environmental, explainability, general security, existential, and capability risks absent from the current non-Physical L3 set. Their continued operational placement under Anthropomorphism would keep the visible count at 189 after the 56 remaps, but only 13 should be interpreted as approved members. The published dataset has not been changed by this review."},
                {"id": "next", "type": "markdown", "layout": "full", "body": "## Recommended next steps\n\n1. Human-approve or amend the 56 proposed remaps.\n2. Display L3 counts as approved plus HOLD, rather than one undifferentiated total.\n3. Review the 176 gaps by missing mechanism family before changing L3 definitions.\n4. Add an automated necessary-cue test for Anthropomorphism and prohibit quota-based refill.\n5. Apply the approved crosswalk in a new immutable release; do not rewrite v2.7.0."},
                {"id": "questions", "type": "markdown", "layout": "full", "body": "## Further questions\n\nShould dependency and manipulation become a new General-purpose Interaction Safety L3? Should governance/accountability, labor/economic, and environmental risks be represented under the currently Physical-only Societal Safety branch for non-Physical AI, or introduced as separate General-purpose societal nodes?"},
            ],
            "cards": [
                {"id": "reviewed", "description": "All published v2.7 cards assigned to Anthropomorphism.", "dataset": "headline", "sourceId": "anthropomorphism-review", "metrics": [{"label": "Cards reviewed", "field": "reviewed", "format": "number"}]},
                {"id": "retained", "description": "Cards satisfying the necessary human-likeness mechanism.", "dataset": "headline", "sourceId": "anthropomorphism-review", "metrics": [{"label": "Strictly retained", "field": "retained", "format": "number"}]},
                {"id": "remapped", "description": "Direct or closest-fit proposed moves to existing L3 nodes.", "dataset": "headline", "sourceId": "anthropomorphism-review", "metrics": [{"label": "Proposed remaps", "field": "remapped", "format": "number"}]},
                {"id": "gap", "description": "Cards without a valid destination in the current 50 L3 nodes.", "dataset": "headline", "sourceId": "anthropomorphism-review", "metrics": [{"label": "Taxonomy gaps", "field": "taxonomy_gap", "format": "number"}]},
            ],
            "charts": [
                {"id": "verdicts", "title": "Review verdicts for Anthropomorphism-assigned cards", "subtitle": "All 245 cards; counts by necessary-condition verdict", "showDescription": True, "type": "horizontalBar", "intent": "composition", "dataset": "verdicts", "sourceId": "anthropomorphism-review", "encodings": {"x": {"field": "verdict", "type": "nominal", "label": "Verdict"}, "y": {"field": "count", "type": "quantitative", "label": "L4 cards", "format": "number"}, "tooltip": [{"field": "count", "type": "quantitative", "format": "number"}, {"field": "denominator", "type": "quantitative", "format": "number"}]}, "valueFormat": "number", "layout": "full", "maxRows": 4},
                {"id": "targets", "title": "Proposed destination L3 nodes", "subtitle": "Fifty-six remaps; exact card counts by destination", "showDescription": True, "type": "horizontalBar", "intent": "ranking", "dataset": "targets", "sourceId": "anthropomorphism-review", "encodings": {"x": {"field": "l3_label", "type": "nominal", "label": "Destination L3"}, "y": {"field": "count", "type": "quantitative", "label": "Proposed cards", "format": "number"}, "tooltip": [{"field": "l3_id", "type": "nominal"}, {"field": "count", "type": "quantitative", "format": "number"}]}, "valueFormat": "number", "layout": "full", "maxRows": 9},
            ],
            "tables": [
                {"id": "retained", "title": "Strict Anthropomorphism members", "subtitle": "Thirteen cards where human-likeness is a necessary mechanism", "dataset": "retained", "sourceId": "anthropomorphism-review", "density": "spacious", "defaultSort": {"field": "l4_id", "direction": "asc"}, "columns": [{"field": "l4_id", "label": "L4 ID", "type": "text"}, {"field": "label_en", "label": "Risk", "type": "text"}, {"field": "basis", "label": "Retention basis", "type": "text"}, {"field": "reference_titles", "label": "Evidence", "type": "text"}]},
                {"id": "remaps", "title": "Proposed remaps from Anthropomorphism", "subtitle": "Thirty-two direct moves and 24 closest-fit moves retaining HOLD", "dataset": "remaps", "sourceId": "anthropomorphism-review", "density": "dense", "defaultSort": {"field": "l4_id", "direction": "asc"}, "columns": [{"field": "l4_id", "label": "L4 ID", "type": "text"}, {"field": "label_en", "label": "Risk", "type": "text"}, {"field": "proposed_l3_label", "label": "Destination L3", "type": "text"}, {"field": "verdict", "label": "Verdict", "type": "text"}, {"field": "decision_required", "label": "HOLD", "type": "text"}, {"field": "basis", "label": "Review basis", "type": "text"}]},
            ],
        },
        "snapshot": {"version": 1, "generatedAt": now, "status": "ready", "datasets": {"headline": headline, "verdicts": verdict_rows, "targets": target_rows, "retained": retain_rows, "remaps": remap_rows}, "accessIssues": []},
        "sources": [audit_source, release_source],
    }
    (OUT / "artifact.json").write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "chart_map.md").write_text(
        "# Chart map\n\n"
        "- Verdicts: comparison, horizontal bar, verdict/count/denominator, hard two-root cap, report.html.\n"
        "- Destinations: ranking, horizontal bar, L3 label/count/ID, single-root preferred, report.html.\n",
        encoding="utf-8",
    )
    print(OUT / "artifact.json")


if __name__ == "__main__":
    main()
