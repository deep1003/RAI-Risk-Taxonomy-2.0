#!/usr/bin/env python3
"""Classify v2.15 HOLD cards by remediability before evidence enrichment."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "public/data/releases/v2.15.0"
OUT = ROOT / "reports/data_quality/hold_remediation_candidates_v2.16.0"


TAXONOMY_GAP_RE = re.compile(r"TAXONOMY_GAP[:_]")
DIRECTLY_REWRITABLE_REASONS = {
    "ANTHROPOMORPHISM_DIRECT_MECHANISM_NOT_ESTABLISHED",
    "OVERLOADED_L3_LOW_EVIDENCE_FIT",
    "CONSTRAINED_EM_REMAP_REQUIRES_HUMAN_REVIEW",
    "LOW_ABSOLUTE_FIT",
}
HUMAN_TAXONOMY_REASONS = {
    "EXPERT_REVIEW_NO_CONSENSUS",
    "FRONTIER_EXPERT_REJECTED",
    "FRONTIER_EXPERT_DISAGREEMENT",
    "MULTI_MECHANISM",
    "PHYSICAL_OUTSIDE_LOCK",
}
WEAK_SOURCE_PATTERNS = [
    "NIST Artificial Intelligence Risk Management Framework",
    "OECD AI Principles",
    "A Framework for Ethical AI at the United Nations",
    "Ethical and social risks of harm from Language Models",
    "Mapping the Ethics of Generative AI",
    "Sociotechnical Harms of Algorithmic Systems",
    "A Collaborative, Human-Centred Taxonomy",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(text: str) -> set[str]:
    stop = {
        "a", "an", "and", "are", "as", "at", "by", "for", "from", "in", "into",
        "is", "of", "or", "risk", "the", "to", "with", "without", "ai", "system",
        "systems", "model", "models", "failure", "gap",
    }
    return {tok for tok in re.findall(r"[a-z][a-z0-9]+", text.lower()) if tok not in stop and len(tok) > 2}


def title_definition_overlap(card: dict) -> float:
    title = normalize(card.get("label_en", ""))
    definition = normalize(card.get("definition_en", ""))
    if not title:
        return 0.0
    return len(title & definition) / len(title)


def source_specificity(card: dict) -> str:
    refs = card.get("references") or []
    titles = [ref.get("title", "") for ref in refs]
    if not refs:
        return "missing_reference"
    if any(any(pattern in title for pattern in WEAK_SOURCE_PATTERNS) for title in titles):
        return "broad_reference"
    if any(ref.get("url") for ref in refs):
        return "url_backed_reference"
    return "title_only_reference"


def remediation_class(card: dict, overlap: float, source_class: str) -> tuple[str, str]:
    reason = card.get("decision_reason") or ""
    if reason in HUMAN_TAXONOMY_REASONS:
        return "human_taxonomy_decision", "expert disagreement, multi-mechanism, or Physical lock boundary"
    if TAXONOMY_GAP_RE.search(reason):
        if source_class in {"missing_reference", "broad_reference", "title_only_reference"}:
            return "evidence_and_taxonomy_review", "taxonomy gap plus weak or broad evidence"
        return "taxonomy_structure_review", "taxonomy gap remains even with reference support"
    if reason == "RETIRED_SPARSE_AGENTIC_L3_FORCED_MIGRATION":
        return "mapping_revalidation", "retired Agentic L3 lineage requires semantic-path review"
    if reason in DIRECTLY_REWRITABLE_REASONS:
        if source_class in {"missing_reference", "broad_reference", "title_only_reference"}:
            return "evidence_enrichment_candidate", "definition or mapping can be repaired after stronger source support"
        if overlap < 0.34:
            return "title_definition_rewrite_candidate", "title terms are weakly reflected in the definition"
        return "mapping_revalidation", "source exists but current L3 fit is weak"
    if source_class in {"missing_reference", "broad_reference", "title_only_reference"}:
        return "evidence_enrichment_candidate", "weak source support is the primary actionable defect"
    if overlap < 0.34:
        return "title_definition_rewrite_candidate", "title and definition are weakly aligned"
    return "mapping_revalidation", "requires rerun after candidate edits"


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    cards = load_json(RELEASE / "cards.json")["cards"]
    hold_cards = [card for card in cards if card.get("decision_required")]
    rows: list[dict] = []
    for card in hold_cards:
        overlap = title_definition_overlap(card)
        src_class = source_specificity(card)
        klass, rationale = remediation_class(card, overlap, src_class)
        semantic = card.get("hold_semantic_path") or {}
        refs = card.get("references") or []
        rows.append({
            "l4_id": card["l4_id"],
            "label_en": card.get("label_en", ""),
            "current_hold_l3": card.get("primary_l3_id", ""),
            "semantic_l3_id": semantic.get("l3_id", ""),
            "semantic_l3_label": semantic.get("l3_label_en", ""),
            "decision_reason": card.get("decision_reason") or "",
            "review_status": card.get("review_status") or "",
            "remediation_class": klass,
            "remediation_rationale": rationale,
            "title_definition_overlap": f"{overlap:.3f}",
            "source_specificity": src_class,
            "reference_count": len(refs),
            "reference_titles": "; ".join(ref.get("title", "") for ref in refs),
            "reference_urls": "; ".join(ref.get("url", "") for ref in refs if ref.get("url")),
        })

    class_counts = Counter(row["remediation_class"] for row in rows)
    reason_counts = Counter(row["decision_reason"] for row in rows)
    source_counts = Counter(row["source_specificity"] for row in rows)
    class_by_reason: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        class_by_reason[row["decision_reason"]][row["remediation_class"]] += 1

    summary = {
        "release_id": "v2.15.0",
        "analysis": "HOLD remediation candidate audit",
        "hold_cards": len(rows),
        "remediation_class_counts": dict(class_counts.most_common()),
        "decision_reason_counts": dict(reason_counts.most_common()),
        "source_specificity_counts": dict(source_counts.most_common()),
        "directly_actionable_classes": {
            "evidence_enrichment_candidate": class_counts["evidence_enrichment_candidate"],
            "title_definition_rewrite_candidate": class_counts["title_definition_rewrite_candidate"],
            "evidence_and_taxonomy_review": class_counts["evidence_and_taxonomy_review"],
        },
        "non_automatic_classes": {
            "taxonomy_structure_review": class_counts["taxonomy_structure_review"],
            "human_taxonomy_decision": class_counts["human_taxonomy_decision"],
            "mapping_revalidation": class_counts["mapping_revalidation"],
        },
        "class_by_reason": {
            reason: dict(counter.most_common()) for reason, counter in sorted(class_by_reason.items())
        },
        "interpretation": (
            "The audit separates HOLD cards that can be improved through title-definition rewriting "
            "or stronger evidence from cards that still require taxonomy-structure or human boundary decisions."
        ),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(
        OUT / "hold_remediation_candidates.csv",
        rows,
        [
            "l4_id", "label_en", "current_hold_l3", "semantic_l3_id", "semantic_l3_label",
            "decision_reason", "review_status", "remediation_class", "remediation_rationale",
            "title_definition_overlap", "source_specificity", "reference_count",
            "reference_titles", "reference_urls",
        ],
    )
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
