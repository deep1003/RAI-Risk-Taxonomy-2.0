#!/usr/bin/env python3
"""Apply two-frontier-expert confirmation to strict initial proposals."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import build_release as build  # noqa: E402
from rai_taxonomy.codebook import RELEASE_ID  # noqa: E402

FRONTIER_REVIEW_FILES = ["expert_a.json", "expert_b.json"]
LOCAL_SENSITIVITY_FILES = ["gemma3_4b.json", "qwen3_4b.json"]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_frontier_reviews(review_envelopes: list[dict], expected_ids: set[str]) -> list[dict[str, dict]]:
    validated = []
    for envelope in review_envelopes:
        if envelope.get("hierarchy_blind") is not True:
            raise ValueError(f"Reviewer is not hierarchy-blind: {envelope.get('reviewer')}")
        rows = envelope.get("results", [])
        by_id = {row["l4_id"]: row for row in rows}
        if len(rows) != len(expected_ids) or set(by_id) != expected_ids:
            raise ValueError(f"Reviewer coverage mismatch: {envelope.get('reviewer')}")
        if any(row.get("decision") not in {"APPROVE", "REJECT"} for row in rows):
            raise ValueError(f"Invalid reviewer decision: {envelope.get('reviewer')}")
        validated.append(by_id)
    return validated


def local_sensitivity_summary(review_dir: Path) -> dict:
    envelopes = [read_json(review_dir / filename) for filename in LOCAL_SENSITIVITY_FILES]
    by_model = [{row["key"]: row for row in envelope["results"]} for envelope in envelopes]
    common = set(by_model[0]) & set(by_model[1])
    same = [key for key in common if by_model[0][key]["decision"] == by_model[1][key]["decision"]]
    same_non_needs = [key for key in same if by_model[0][key]["decision"] != "NEEDS"]
    return {
        "purpose": "sensitivity audit only; not an approval authority",
        "models": [envelope["model"] for envelope in envelopes],
        "reviewed_cards": len(common),
        "same_decision": len(same),
        "both_needs": sum(by_model[0][key]["decision"] == "NEEDS" for key in same),
        "same_non_needs_l3": len(same_non_needs),
        "disagreement": len(common) - len(same),
        "interpretation": "Low non-NEEDS agreement supports conservative abstention and human validation; small local models are not treated as ground truth.",
    }


def main() -> None:
    release_dir = PROJECT_ROOT / "data" / "releases" / RELEASE_ID
    public_dir = PROJECT_ROOT / "public" / "data" / "releases" / RELEASE_ID
    validation_dir = PROJECT_ROOT / "reports" / "validation" / RELEASE_ID
    frontier_dir = validation_dir / "frontier_expert_reviews"
    local_review_dir = validation_dir / "expert_model_reviews"

    packet = read_json(frontier_dir / "review_packet.json")
    packet_by_id = {row["l4_id"]: row for row in packet["cards"]}
    expected_ids = set(packet_by_id)
    review_envelopes = [read_json(frontier_dir / filename) for filename in FRONTIER_REVIEW_FILES]
    review_maps = validate_frontier_reviews(review_envelopes, expected_ids)

    placements = read_json(release_dir / "placements.json")
    consensus_rows = []
    for placement in placements:
        l4_id = placement["l4_id"]
        if placement["assignment_status"] == "locked_physical":
            placement["frontier_expert_reviews"] = []
            continue
        if l4_id not in expected_ids:
            placement["frontier_expert_reviews"] = []
            continue
        proposed_l3_id = packet_by_id[l4_id]["proposed_l3_id"]
        rows = [review_map[l4_id] for review_map in review_maps]
        if any(row.get("proposed_l3_id") != proposed_l3_id for row in rows):
            raise ValueError(f"Reviewer changed proposed L3 for {l4_id}")
        decisions = [row["decision"] for row in rows]
        both_approve = decisions == ["APPROVE", "APPROVE"]
        placement["frontier_expert_reviews"] = [
            {
                "reviewer": envelope["reviewer"],
                "decision": row["decision"],
                "reason_code": row["reason_code"],
                "rationale": row["rationale"],
                "hierarchy_blind": True,
            }
            for envelope, row in zip(review_envelopes, rows, strict=True)
        ]
        if both_approve:
            placement["primary_l3_id"] = proposed_l3_id
            placement["assignment_status"] = "algorithm_proposed"
            placement["assignment_method"] = "bge_rules_plus_two_frontier_expert_confirmation"
            placement["abstention_reason"] = None
            placement["rationale"] = (
                f"Strict hierarchy-blind BGE-M3/rule proposal {proposed_l3_id} confirmed by two independent frontier expert agents; "
                "provisional pending human gold-set validation."
            )
            placement["review_status"] = "provisional_two_frontier_experts_confirmed"
        else:
            placement["primary_l3_id"] = None
            placement["assignment_status"] = "needs_taxonomy_decision"
            placement["assignment_method"] = "open_set_abstention_after_frontier_review"
            reason = "FRONTIER_EXPERT_REJECTED" if decisions == ["REJECT", "REJECT"] else "FRONTIER_EXPERT_DISAGREEMENT"
            placement["abstention_reason"] = reason
            placement["rationale"] = f"Open-set abstention after independent frontier review: {reason}."
            placement["review_status"] = "pending_taxonomy_decision"
        placement["approved_by"] = None
        placement["approved_at"] = None
        consensus_rows.append(
            {
                "l4_id": l4_id,
                "proposed_l3_id": proposed_l3_id,
                "expert_a_decision": decisions[0],
                "expert_b_decision": decisions[1],
                "both_approve": both_approve,
                "final_status": placement["assignment_status"],
                "final_l3_id": placement["primary_l3_id"],
                "abstention_reason": placement["abstention_reason"],
            }
        )

    decision_number = 0
    for placement in placements:
        if placement["assignment_status"] == "needs_taxonomy_decision":
            decision_number += 1
            placement["decision_id"] = f"TD-{decision_number:04d}"
        else:
            placement["decision_id"] = None

    write_json(release_dir / "placements.json", placements)
    build.write_csv(release_dir / "placements.csv", placements)
    write_json(validation_dir / "frontier_expert_consensus.json", consensus_rows)
    build.write_csv(validation_dir / "frontier_expert_consensus.csv", consensus_rows)

    local_sensitivity = local_sensitivity_summary(local_review_dir)
    write_json(validation_dir / "local_model_sensitivity_summary.json", local_sensitivity)

    nodes = read_json(release_dir / "taxonomy_nodes.json")
    registry = read_json(release_dir / "l4_registry.json")
    build.build_site_bundle(release_dir, public_dir, nodes, registry, placements)

    global_cards = sorted(
        read_json(PROJECT_ROOT / "data" / "source_snapshots" / RELEASE_ID / "global_ai_risk_l4_overlay_nodes.json"),
        key=lambda row: row["id"],
    )
    for number, card in enumerate(global_cards, start=1):
        card["_l4_id"] = f"RAI4-{number:04d}"
        card["_classification_text"] = build.classification_text(card)
    coverage_summary, l3_rows, transition_rows, unresolved_rows = build.posthoc_coverage(
        global_cards, placements, nodes
    )
    write_json(validation_dir / "coverage_summary.json", coverage_summary)
    build.write_csv(validation_dir / "l3_distribution.csv", l3_rows)
    build.write_csv(validation_dir / "legacy_to_new_transition_reference_only.csv", transition_rows)
    write_json(validation_dir / "unresolved_cards.json", unresolved_rows)
    build.write_csv(validation_dir / "unresolved_cards.csv", unresolved_rows)

    global_by_l4 = {row["_l4_id"]: row for row in global_cards}
    unresolved_texts = [global_by_l4[row["l4_id"]]["_classification_text"] for row in unresolved_rows]
    unresolved_vectors, _ = build.encode_texts(unresolved_texts, batch_size=8, device="cpu")
    cluster_rows, cluster_card_rows, cluster_diagnostics = build.unresolved_clusters(
        unresolved_rows, unresolved_vectors, global_by_l4
    )
    write_json(validation_dir / "unresolved_clusters.json", cluster_rows)
    build.write_csv(validation_dir / "unresolved_cluster_cards.csv", cluster_card_rows)
    write_json(validation_dir / "unresolved_cluster_diagnostics.json", cluster_diagnostics)

    final_counts = Counter(row["assignment_status"] for row in placements)
    review_pair_counts = Counter((row["expert_a_decision"], row["expert_b_decision"]) for row in consensus_rows)
    consensus_summary = {
        "release_id": RELEASE_ID,
        "reviewed_initial_proposals": len(consensus_rows),
        "reviewers": [envelope["reviewer"] for envelope in review_envelopes],
        "hierarchy_blind": True,
        "legacy_hierarchy_used_as_feature": False,
        "both_approve_required": True,
        "both_approved": sum(row["both_approve"] for row in consensus_rows),
        "review_pair_counts": [
            {"expert_a": key[0], "expert_b": key[1], "count": count}
            for key, count in sorted(review_pair_counts.items())
        ],
        "final_status_counts": dict(final_counts),
        "human_validation": "not yet performed",
        "local_model_sensitivity": local_sensitivity,
    }
    write_json(validation_dir / "frontier_expert_consensus_summary.json", consensus_summary)

    run_record_path = release_dir / "algorithm_run.json"
    run_record = read_json(run_record_path)
    run_record["frontier_expert_review"] = {
        "reviewers": [envelope["reviewer"] for envelope in review_envelopes],
        "scope": "all initial strict BGE-M3 plus rule proposals",
        "reviewed": len(consensus_rows),
        "approval_rule": "both independent experts must approve exact proposed L3",
        "hierarchy_blind": True,
        "human_validation": "pending",
    }
    run_record["local_model_sensitivity"] = local_sensitivity
    run_record["final_consensus_policy"] = (
        "strict BGE-M3/rule eligibility plus two independent frontier expert approvals; "
        "all other non-Physical cards abstain"
    )
    write_json(run_record_path, run_record)

    manifest_path = release_dir / "manifest.json"
    manifest = read_json(manifest_path)
    manifest["algorithm"]["frontier_expert_reviewers"] = [envelope["reviewer"] for envelope in review_envelopes]
    manifest["algorithm"]["consensus_policy"] = "strict BGE/rules plus two frontier expert approvals"
    manifest["algorithm"]["local_model_sensitivity_only"] = ["gemma3:4b", "qwen3:4b"]
    manifest["counts"].update(
        {
            "algorithm_proposed": final_counts["algorithm_proposed"],
            "human_approved": final_counts["human_approved"],
            "needs_taxonomy_decision": final_counts["needs_taxonomy_decision"],
        }
    )
    manifest["validation"]["status"] = "PENDING_VALIDATOR"
    write_json(manifest_path, manifest)
    write_json(public_dir / "manifest.json", manifest)

    print(
        json.dumps(
            {
                "reviewed_initial_proposals": len(consensus_rows),
                "both_approved": consensus_summary["both_approved"],
                "algorithm_proposed": final_counts["algorithm_proposed"],
                "needs_taxonomy_decision": final_counts["needs_taxonomy_decision"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

