#!/usr/bin/env python3
"""Build a quota-calibrated Stage 2 placement proposal without editing v1.0.0.

Stage 2 preserves Physical locks and Stage 1 expert-consensus proposals. It
uses only the existing hierarchy-blind BGE/rule score evidence, applies a
small set of non-negotiable holds, and reserves the lowest-suitability cards
until approximately 10% of all 1,726 L4 cards remain unresolved.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_RELEASE = "v1.0.0"
STAGE2_ID = "stage2-v1"
TARGET_UNCLASSIFIED_RATE = 0.10
TARGET_UNCLASSIFIED_COUNT = round(1726 * TARGET_UNCLASSIFIED_RATE)
HARD_HOLD_REASONS = {
    "PHYSICAL_OUTSIDE_LOCK",
    "FRONTIER_EXPERT_REJECTED",
    "FRONTIER_EXPERT_DISAGREEMENT",
    "MULTI_MECHANISM",
    "LOW_ABSOLUTE_FIT",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def csv_value(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return value


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        if columns:
            writer.writeheader()
            for row in rows:
                writer.writerow({key: csv_value(row.get(key)) for key in columns})


def clip(value: float) -> float:
    return max(0.0, min(1.0, value))


def suitability_components(score: dict) -> dict[str, float]:
    semantic = clip((float(score["top1_semantic_score"]) - 0.45) / 0.25)
    semantic_margin = clip(float(score["semantic_margin"]) / 0.05)
    composite_margin = clip(float(score["composite_margin"]) / 0.05)
    anchor_agreement = float(score["anchor_top1_votes"]) / 3.0
    rule_support = 1.0 if score.get("eligible_l3_ids") else 0.0
    gap_penalty = 0.05 if score.get("gap_sentinels") else 0.0
    total = (
        0.55 * semantic
        + 0.20 * semantic_margin
        + 0.10 * composite_margin
        + 0.10 * anchor_agreement
        + 0.05 * rule_support
        - gap_penalty
    )
    return {
        "semantic_component": round(semantic, 6),
        "semantic_margin_component": round(semantic_margin, 6),
        "composite_margin_component": round(composite_margin, 6),
        "anchor_agreement_component": round(anchor_agreement, 6),
        "rule_support_component": round(rule_support, 6),
        "gap_penalty": round(gap_penalty, 6),
        "suitability_score": round(total, 6),
    }


def fit_tier(value: float) -> str:
    if value >= 0.65:
        return "stage2_high"
    if value >= 0.45:
        return "stage2_medium"
    return "stage2_low"


def main() -> None:
    release_dir = ROOT / "data" / "releases" / BASE_RELEASE
    output_dir = ROOT / "data" / "experiments" / STAGE2_ID
    validation_dir = ROOT / "reports" / "validation" / STAGE2_ID

    nodes = read_json(release_dir / "taxonomy_nodes.json")
    registry = read_json(release_dir / "l4_registry.json")
    placements = read_json(release_dir / "placements.json")
    scores = read_json(release_dir / "algorithm_scores.json")
    score_by_l4 = {row["l4_id"]: row for row in scores}
    registry_by_l4 = {row["l4_id"]: row for row in registry}
    l3_ids = {row["node_id"] for row in nodes if row["level"] == 3}

    needs = [row for row in placements if row["assignment_status"] == "needs_taxonomy_decision"]
    hard_holds = [row for row in needs if row.get("abstention_reason") in HARD_HOLD_REASONS]
    hard_hold_ids = {row["l4_id"] for row in hard_holds}
    if len(hard_holds) > TARGET_UNCLASSIFIED_COUNT:
        raise ValueError("Hard holds exceed the Stage 2 unresolved target")

    ranked_soft_holds = []
    components_by_l4: dict[str, dict[str, float]] = {}
    for placement in needs:
        score = score_by_l4[placement["l4_id"]]
        components = suitability_components(score)
        components_by_l4[placement["l4_id"]] = components
        if placement["l4_id"] not in hard_hold_ids:
            ranked_soft_holds.append(
                (
                    components["suitability_score"],
                    placement["l4_id"],
                )
            )
    ranked_soft_holds.sort()
    quota_hold_count = TARGET_UNCLASSIFIED_COUNT - len(hard_holds)
    quota_hold_ids = {l4_id for _, l4_id in ranked_soft_holds[:quota_hold_count]}
    final_hold_ids = hard_hold_ids | quota_hold_ids
    threshold_last_hold = ranked_soft_holds[quota_hold_count - 1][0]
    threshold_first_assignment = ranked_soft_holds[quota_hold_count][0]

    stage2_rows = []
    transition_rows = []
    for placement in placements:
        l4_id = placement["l4_id"]
        registry_card = registry_by_l4[l4_id]
        score = score_by_l4.get(l4_id)
        components = components_by_l4.get(l4_id)
        if placement["assignment_status"] == "locked_physical":
            stage2_status = "locked_physical"
            stage2_l3_id = placement["primary_l3_id"]
            tier = "physical_gold"
            hold_reason = None
            method = "physical_gold_lock"
            requires_human_review = False
        elif placement["assignment_status"] == "algorithm_proposed":
            stage2_status = "stage1_algorithm_proposed"
            stage2_l3_id = placement["primary_l3_id"]
            tier = "stage1_consensus"
            hold_reason = None
            method = "stage1_frontier_consensus_preserved"
            requires_human_review = True
        elif l4_id in final_hold_ids:
            stage2_status = "needs_taxonomy_decision"
            stage2_l3_id = None
            tier = "stage2_hold"
            hold_reason = (
                placement.get("abstention_reason")
                if l4_id in hard_hold_ids
                else "BOTTOM_10_PERCENT_SUITABILITY_RESERVE"
            )
            method = "stage2_open_set_hold"
            requires_human_review = True
        else:
            stage2_status = "algorithm_proposed_stage2"
            stage2_l3_id = score["top1_l3_id"]
            if stage2_l3_id not in l3_ids:
                raise ValueError(f"Unknown Stage 2 L3: {stage2_l3_id}")
            tier = fit_tier(components["suitability_score"])
            hold_reason = None
            method = "stage2_quota_calibrated_hierarchy_blind_top1"
            requires_human_review = True

        stage2_rows.append(
            {
                "stage2_id": STAGE2_ID,
                "base_release_id": BASE_RELEASE,
                "l4_id": l4_id,
                "label_en": registry_card["label_en"],
                "label_ko": registry_card.get("label_ko"),
                "stage1_status": placement["assignment_status"],
                "stage1_l3_id": placement.get("primary_l3_id"),
                "stage1_abstention_reason": placement.get("abstention_reason"),
                "stage2_status": stage2_status,
                "stage2_l3_id": stage2_l3_id,
                "stage2_method": method,
                "stage2_fit_tier": tier,
                "stage2_suitability_score": components.get("suitability_score") if components else None,
                "stage2_hold_reason": hold_reason,
                "top1_semantic_score": score.get("top1_semantic_score") if score else None,
                "semantic_margin": score.get("semantic_margin") if score else None,
                "composite_margin": score.get("composite_margin") if score else None,
                "anchor_top1_votes": score.get("anchor_top1_votes") if score else None,
                "rule_supported": bool(score.get("eligible_l3_ids")) if score else None,
                "gap_sentinels": score.get("gap_sentinels", []) if score else [],
                "taxonomy_gap_override": bool(score and score.get("gap_sentinels") and stage2_l3_id),
                "requires_human_review": requires_human_review,
                "human_approved": False,
                "legacy_hierarchy_used_as_feature": False,
            }
        )
        transition_rows.append(
            {
                "l4_id": l4_id,
                "stage1_status": placement["assignment_status"],
                "stage1_l3_id": placement.get("primary_l3_id"),
                "stage2_status": stage2_status,
                "stage2_l3_id": stage2_l3_id,
                "changed": placement.get("primary_l3_id") != stage2_l3_id
                or placement["assignment_status"] != stage2_status,
            }
        )

    status_counts = Counter(row["stage2_status"] for row in stage2_rows)
    tier_counts = Counter(row["stage2_fit_tier"] for row in stage2_rows)
    hold_reason_counts = Counter(
        row["stage2_hold_reason"] for row in stage2_rows if row["stage2_hold_reason"]
    )
    assigned_l3_counts = Counter(
        row["stage2_l3_id"] for row in stage2_rows if row["stage2_l3_id"]
    )
    newly_assigned = [row for row in stage2_rows if row["stage2_status"] == "algorithm_proposed_stage2"]
    gap_overrides = [row for row in newly_assigned if row["taxonomy_gap_override"]]
    no_rule_assignments = [row for row in newly_assigned if not row["rule_supported"]]

    l3_distribution = [
        {
            "l3_id": l3_id,
            "stage2_card_count": count,
            "share_of_all_assigned": round(count / (1726 - TARGET_UNCLASSIFIED_COUNT), 6),
            "new_stage2_count": sum(
                row["stage2_status"] == "algorithm_proposed_stage2" and row["stage2_l3_id"] == l3_id
                for row in stage2_rows
            ),
        }
        for l3_id, count in sorted(assigned_l3_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    summary = {
        "stage2_id": STAGE2_ID,
        "base_release_id": BASE_RELEASE,
        "classification_authority": "algorithmic_proposal_only_not_human_approved",
        "target_unclassified_rate": TARGET_UNCLASSIFIED_RATE,
        "target_unclassified_count": TARGET_UNCLASSIFIED_COUNT,
        "actual_unclassified_count": status_counts["needs_taxonomy_decision"],
        "actual_unclassified_rate": round(status_counts["needs_taxonomy_decision"] / 1726, 6),
        "actual_classified_count": 1726 - status_counts["needs_taxonomy_decision"],
        "actual_classified_rate": round((1726 - status_counts["needs_taxonomy_decision"]) / 1726, 6),
        "status_counts": dict(status_counts),
        "fit_tier_counts": dict(tier_counts),
        "hard_hold_count": len(hard_holds),
        "quota_hold_count": quota_hold_count,
        "hold_reason_counts": dict(hold_reason_counts),
        "new_stage2_assignments": len(newly_assigned),
        "new_assignments_without_rule_support": len(no_rule_assignments),
        "new_assignments_with_taxonomy_gap_override": len(gap_overrides),
        "soft_hold_threshold_last_hold": threshold_last_hold,
        "soft_hold_threshold_first_assignment": threshold_first_assignment,
        "largest_l3_count": l3_distribution[0]["stage2_card_count"],
        "largest_l3_share_of_all_assigned": l3_distribution[0]["share_of_all_assigned"],
        "legacy_hierarchy_used_as_feature": False,
        "physical_locks_changed": 0,
        "stage1_consensus_changed": 0,
        "warnings": [
            "Stage 2 assignments are not human-approved ground truth.",
            "Quota calibration deliberately assigns many cards that lacked Stage 1 rule eligibility.",
            "Taxonomy-gap overrides require priority human review before publication as authoritative placements.",
        ],
    }
    config = {
        "stage2_id": STAGE2_ID,
        "base_release_id": BASE_RELEASE,
        "target": {
            "unclassified_rate": TARGET_UNCLASSIFIED_RATE,
            "unclassified_count": TARGET_UNCLASSIFIED_COUNT,
            "rounding": "round(1726 * 0.10)",
        },
        "preserved": [
            "182 Physical locked placements",
            "37 Stage 1 frontier-consensus proposals",
            "RAI4 permanent identifiers",
            "legacy hierarchy exclusion",
        ],
        "hard_hold_reasons": sorted(HARD_HOLD_REASONS),
        "suitability_formula": {
            "semantic_component": "clip((top1_semantic_score - 0.45) / 0.25, 0, 1)",
            "semantic_margin_component": "clip(semantic_margin / 0.05, 0, 1)",
            "composite_margin_component": "clip(composite_margin / 0.05, 0, 1)",
            "anchor_agreement_component": "anchor_top1_votes / 3",
            "rule_support_component": "1 if eligible_l3_ids is non-empty else 0",
            "gap_penalty": "0.05 if gap_sentinels is non-empty else 0",
            "weighted_total": "0.55*semantic + 0.20*semantic_margin + 0.10*composite_margin + 0.10*anchor_agreement + 0.05*rule_support - gap_penalty",
        },
        "selection_rule": "After hard holds, reserve the lowest suitability scores with L4 ID as deterministic tie-break until 173 total cards remain unresolved; assign every other unresolved non-Physical card to its existing hierarchy-blind top1 L3.",
        "confidence_calibrated": False,
        "human_approved": False,
    }

    hold_queue = [row for row in stage2_rows if row["stage2_status"] == "needs_taxonomy_decision"]
    write_json(output_dir / "stage2_config.json", config)
    write_json(output_dir / "stage2_placements.json", stage2_rows)
    write_csv(output_dir / "stage2_placements.csv", stage2_rows)
    write_json(output_dir / "stage2_summary.json", summary)
    write_json(output_dir / "stage2_hold_queue.json", hold_queue)
    write_csv(output_dir / "stage2_hold_queue.csv", hold_queue)
    write_csv(output_dir / "stage1_stage2_transition.csv", transition_rows)
    write_csv(output_dir / "stage2_l3_distribution.csv", l3_distribution)
    write_json(validation_dir / "stage2_summary.json", summary)
    write_json(validation_dir / "stage2_hold_queue.json", hold_queue)
    write_csv(validation_dir / "stage2_l3_distribution.csv", l3_distribution)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
