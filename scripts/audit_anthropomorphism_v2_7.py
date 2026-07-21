#!/usr/bin/env python3
"""Exhaustively review v2.7 cards operationally assigned to Anthropomorphism.

This script is non-mutating: it produces a review packet and a proposed
crosswalk.  It does not change the published card bundle.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "public/data/releases/v2.7.0"
OUT = ROOT / "reports/data_quality/anthropomorphism_review_v2.7.0"
SOURCE_L3 = "RAI3-G-INT-10"


RETAIN = {
    "RAI4-0131", "RAI4-0144", "RAI4-0869", "RAI4-0871", "RAI4-0872",
    "RAI4-0877", "RAI4-0884", "RAI4-0888", "RAI4-0893", "RAI4-0907",
    "RAI4-0989", "RAI4-0991", "RAI4-1143",
}


def remaps(ids: str, target: str, hold: bool, basis: str) -> dict[str, tuple[str, bool, str]]:
    return {l4_id: (target, hold, basis) for l4_id in ids.split()}


REMAP: dict[str, tuple[str, bool, str]] = {}
REMAP.update(remaps("RAI4-0056", "RAI3-G-SYS-09", False, "DIRECT_RECOURSE_FAILURE"))
REMAP.update(remaps("RAI4-0117", "RAI3-G-SYS-09", True, "HUMAN_OVERRIDE_CLOSEST_TO_CONTESTABILITY"))
REMAP.update(remaps("RAI4-0385", "RAI3-G-SYS-04", True, "IMPORTED_JURISDICTIONAL_GOVERNANCE_MISMATCH"))
REMAP.update(remaps(
    "RAI4-0450 RAI4-0459 RAI4-0643 RAI4-0739 RAI4-0964 RAI4-1205 RAI4-1358",
    "RAI3-G-INT-06", False, "DIRECT_PRIVACY_SURVEILLANCE_OR_CONSENT_MECHANISM",
))
REMAP.update(remaps(
    "RAI4-0425 RAI4-0702 RAI4-0997 RAI4-0999 RAI4-1309 RAI4-1344",
    "RAI3-G-INT-04", False, "DIRECT_GROUP_STEREOTYPING_OR_DISCRIMINATORY_CONTENT",
))
REMAP.update(remaps(
    "RAI4-0396 RAI4-0403 RAI4-0404 RAI4-0417 RAI4-0423 RAI4-0429 RAI4-0677 "
    "RAI4-0697 RAI4-0720 RAI4-0883 RAI4-0955 RAI4-1029 RAI4-1266 RAI4-1274 "
    "RAI4-1503 RAI4-1611 RAI4-1713",
    "RAI3-G-INT-04", True, "BROADER_OR_ALLOCATIVE_BIAS_CLOSEST_TO_HATE_UNFAIRNESS",
))
REMAP.update(remaps(
    "RAI4-0611 RAI4-0656 RAI4-0806 RAI4-0960 RAI4-1291 RAI4-1421 RAI4-1423",
    "RAI3-G-INT-05", False, "DIRECT_POLITICAL_MANIPULATION_EXTREMISM_OR_INTERFERENCE",
))
REMAP.update(remaps(
    "RAI4-0416 RAI4-0498 RAI4-0805 RAI4-1395 RAI4-1716",
    "RAI3-G-INT-05", True, "BROADER_DEMOCRATIC_OR_IDEOLOGICAL_HARM_CLOSEST_TO_POLITICAL_NEUTRALITY",
))
REMAP.update(remaps(
    "RAI4-0448 RAI4-0449 RAI4-1087 RAI4-1193 RAI4-1391",
    "RAI3-G-INT-07", False, "DIRECT_FRAUD_IDENTITY_CRIME_OR_UNLAWFUL_ASSISTANCE",
))
REMAP.update(remaps(
    "RAI4-0612 RAI4-0650 RAI4-1614 RAI4-1618",
    "RAI3-G-INT-09", False, "DIRECT_CBRN_CYBER_OR_CRITICAL_INFRASTRUCTURE_WEAPONIZATION",
))
REMAP.update(remaps("RAI4-0844", "RAI3-G-SYS-03", False, "UNINTENTIONAL_FALSE_INFORMATION_GENERATION"))
REMAP.update(remaps("RAI4-1424", "RAI3-G-SYS-08", False, "DIRECT_DIVERGENCE_FROM_HUMAN_GOALS_AND_VALUES"))


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    cards = read(RELEASE / "cards.json")["cards"]
    hierarchy = read(RELEASE / "hierarchy.json")["nodes"]
    nodes = {row["node_id"]: row for row in hierarchy}
    population = [row for row in cards if row["primary_l3_id"] == SOURCE_L3]
    population_ids = {row["l4_id"] for row in population}
    configured = RETAIN | set(REMAP)
    if configured - population_ids:
        raise ValueError(f"Configured IDs are not in the v2.7 Anthropomorphism population: {sorted(configured - population_ids)}")

    rows: list[dict] = []
    for card in population:
        l4_id = card["l4_id"]
        if l4_id in RETAIN:
            verdict = "RETAIN_ANTHROPOMORPHISM"
            target = SOURCE_L3
            hold = False
            basis = "HUMANLIKE_ATTRIBUTION_IS_NECESSARY_CAUSAL_MECHANISM"
        elif l4_id in REMAP:
            target, hold, basis = REMAP[l4_id]
            verdict = "REMAP_WITH_HOLD" if hold else "REMAP_HIGH_CONFIDENCE"
        else:
            verdict = "HOLD_TAXONOMY_GAP"
            target = SOURCE_L3
            hold = True
            basis = "NO_EXISTING_L3_SATISFIES_THE_CARD_WITHOUT_FORCING"
        references = card.get("references", [])
        rows.append({
            "l4_id": l4_id,
            "label_en": card["label_en"],
            "label_ko": card["label_ko"],
            "current_l3_id": SOURCE_L3,
            "verdict": verdict,
            "proposed_l3_id": target,
            "proposed_l3_label": nodes[target]["label_en"],
            "decision_required": hold,
            "basis": basis,
            "definition_en": card["definition_en"],
            "reference_count": len(references),
            "reference_titles": " | ".join(ref.get("title", "") for ref in references),
            "reference_urls": " | ".join(ref.get("url", "") for ref in references),
        })

    OUT.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with (OUT / "card_level_review.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    verdict_counts = Counter(row["verdict"] for row in rows)
    target_counts = Counter(row["proposed_l3_id"] for row in rows if row["proposed_l3_id"] != SOURCE_L3)
    summary = {
        "release_id": "v2.7.0",
        "review_scope": {
            "published_anthropomorphism_cards": len(population),
            "reviewed_cards": len(rows),
            "coverage_pct": round(100 * len(rows) / len(population), 2),
        },
        "necessary_condition": "The risk mechanism requires attribution or performance of human qualities such as consciousness, emotion, personhood, human embodiment, social reciprocity, or human-like intentionality.",
        "exclusions": [
            "Dependency, overreliance, persuasion, or manipulation without a necessary human-likeness mechanism.",
            "Governance, labor, environmental, privacy, discrimination, political, crime, weaponization, or information-integrity risks whose operative mechanism is independent of anthropomorphism.",
            "AI capabilities such as theory of mind, situational awareness, or autonomy that do not themselves attribute human status to the AI.",
        ],
        "verdict_counts": dict(verdict_counts),
        "proposed_target_counts": dict(target_counts),
        "approved_anthropomorphism_after_review": verdict_counts["RETAIN_ANTHROPOMORPHISM"],
        "operational_anthropomorphism_after_high_confidence_remaps": len(population) - sum(target_counts.values()),
        "human_approval_required_before_mutation": True,
        "published_data_mutated": False,
    }
    write(OUT / "summary.json", summary)
    (OUT / "methodology.md").write_text(
        "# Anthropomorphism L3 full review methodology\n\n"
        "The unit of analysis is one v2.7.0 L4 card operationally assigned to RAI3-G-INT-10. "
        "Review uses the L4 title, mechanism-only English definition, cited source identity, and the frozen definitions of all candidate L3 nodes.\n\n"
        "A card is retained only when human-likeness is a necessary causal mechanism rather than incidental wording. "
        "A high-confidence remap requires a direct match to the target L3's necessary mechanism. "
        "A closest-fit remap remains HOLD when the target covers only part of a broader or allocative risk. "
        "Cards with no defensible target remain operationally assigned but HOLD; they are not redistributed to satisfy a desired category size.\n\n"
        "Evidence basis includes NIST AI 600-1 Human-AI Configuration and empirical studies defining anthropomorphism as attribution of human-like characteristics or design cues to AI systems.\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
