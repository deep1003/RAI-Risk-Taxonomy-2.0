#!/usr/bin/env python3
"""Create an immutable successor release from approved placement decisions.

The script never edits the source release. It refuses an existing target,
preserves RAI4 identity and Physical locks, and writes one migration event for
every changed placement.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import build_release as build  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-release", required=True)
    parser.add_argument("--to-release", required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--approved-by", required=True)
    parser.add_argument("--approved-at", required=True, help="ISO date or date-time")
    parser.add_argument("--reviewer", action="append", required=True)
    parser.add_argument(
        "--allow-prepublication-source",
        action="store_true",
        help="Testing only: normally successor releases must derive from a published release.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate and preview without writing files")
    return parser.parse_args()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def version_tuple(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        raise ValueError(f"Invalid semantic release ID: {value}")
    return tuple(int(part) for part in match.groups())


def next_migration_number(migrations: list[dict]) -> int:
    numbers = []
    for row in migrations:
        match = re.fullmatch(r"MIG-(\d{6})", row.get("migration_id", ""))
        if match:
            numbers.append(int(match.group(1)))
    return max(numbers, default=0) + 1


def main() -> None:
    args = parse_args()
    if version_tuple(args.to_release) <= version_tuple(args.from_release):
        raise ValueError("The successor release must be greater than the source release")
    source_release_dir = PROJECT_ROOT / "data" / "releases" / args.from_release
    target_release_dir = PROJECT_ROOT / "data" / "releases" / args.to_release
    source_snapshot_dir = PROJECT_ROOT / "data" / "source_snapshots" / args.from_release
    target_snapshot_dir = PROJECT_ROOT / "data" / "source_snapshots" / args.to_release
    target_public_dir = PROJECT_ROOT / "public" / "data" / "releases" / args.to_release
    target_validation_dir = PROJECT_ROOT / "reports" / "validation" / args.to_release

    if not source_release_dir.is_dir():
        raise FileNotFoundError(source_release_dir)
    if target_release_dir.exists() or target_snapshot_dir.exists() or target_public_dir.exists():
        raise FileExistsError(f"Target release already exists and will not be overwritten: {args.to_release}")
    source_manifest = read_json(source_release_dir / "manifest.json")
    if source_manifest.get("release_status") != "published" and not args.allow_prepublication_source:
        raise ValueError("Successor releases require a published source release")

    decisions = read_json(args.decisions)
    jsonschema.Draft202012Validator(
        read_json(PROJECT_ROOT / "schemas" / "remap-decision.schema.json")
    ).validate(decisions)
    if not isinstance(decisions, list) or not decisions:
        raise ValueError("Decision file must be a non-empty JSON list")
    decision_by_l4 = {row.get("l4_id"): row for row in decisions}
    if None in decision_by_l4 or len(decision_by_l4) != len(decisions):
        raise ValueError("Decision L4 IDs must be populated and unique")

    nodes = read_json(source_release_dir / "taxonomy_nodes.json")
    registry = read_json(source_release_dir / "l4_registry.json")
    crosswalk = read_json(source_release_dir / "source_crosswalk.json")
    locks = read_json(source_release_dir / "physical_lock.json")
    placements = copy.deepcopy(read_json(source_release_dir / "placements.json"))
    prior_migrations = copy.deepcopy(read_json(source_release_dir / "placement_migrations.json"))
    node_ids = {row["node_id"] for row in nodes if row["level"] == 3 and row["status"] == "active"}
    registry_ids = {row["l4_id"] for row in registry}
    locked_ids = {row["l4_id"] for row in locks}
    if not set(decision_by_l4) <= registry_ids:
        raise ValueError(f"Unknown L4 IDs: {sorted(set(decision_by_l4) - registry_ids)}")
    if set(decision_by_l4) & locked_ids:
        raise ValueError("Physical locked cards cannot be changed by the standard remap workflow")

    migration_number = next_migration_number(prior_migrations)
    new_migrations = []
    for placement in placements:
        placement["release_id"] = args.to_release
        decision = decision_by_l4.get(placement["l4_id"])
        if decision is None:
            continue
        to_l3_id = decision.get("to_l3_id")
        if to_l3_id is not None and to_l3_id not in node_ids:
            raise ValueError(f"Inactive or unknown target L3 for {placement['l4_id']}: {to_l3_id}")
        reason = str(decision.get("reason") or "").strip()
        evidence_refs = decision.get("evidence_refs") or []
        if not reason or not isinstance(evidence_refs, list):
            raise ValueError(f"Decision requires reason and evidence_refs: {placement['l4_id']}")

        from_l3_id = placement.get("primary_l3_id")
        from_status = placement.get("assignment_status")
        to_status = "human_approved" if to_l3_id is not None else "needs_taxonomy_decision"
        if from_l3_id == to_l3_id and from_status == to_status:
            raise ValueError(f"Decision does not change placement: {placement['l4_id']}")
        if to_l3_id is None:
            event_type = "unassign"
        elif from_l3_id is None:
            event_type = "resolve"
        else:
            event_type = "remap"

        migration_id = f"MIG-{migration_number:06d}"
        migration_number += 1
        new_migrations.append(
            {
                "migration_id": migration_id,
                "l4_id": placement["l4_id"],
                "from_release": args.from_release,
                "to_release": args.to_release,
                "from_l3_id": from_l3_id,
                "to_l3_id": to_l3_id,
                "from_status": from_status,
                "to_status": to_status,
                "event_type": event_type,
                "reason": reason,
                "algorithm_run_id": placement.get("algorithm_run_id"),
                "evidence_refs": [str(value) for value in evidence_refs],
                "reviewers": args.reviewer,
                "approved_by": args.approved_by,
                "approved_at": args.approved_at,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        placement.update(
            {
                "primary_l3_id": to_l3_id,
                "assignment_status": to_status,
                "assignment_method": "human_taxonomy_decision",
                "algorithm_run_id": None,
                "confidence": None,
                "confidence_calibrated": None,
                "abstention_reason": None if to_l3_id is not None else "HUMAN_TAXONOMY_DECISION",
                "rationale": reason,
                "review_status": "approved_human" if to_l3_id is not None else "pending_taxonomy_decision",
                "reviewers": args.reviewer,
                "approved_by": args.approved_by,
                "approved_at": args.approved_at,
            }
        )

    decision_number = 0
    for placement in placements:
        if placement["assignment_status"] == "needs_taxonomy_decision":
            decision_number += 1
            placement["decision_id"] = f"TD-{decision_number:04d}"
        else:
            placement["decision_id"] = None

    if args.dry_run:
        status_counts = Counter(row["assignment_status"] for row in placements)
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "from_release": args.from_release,
                    "to_release": args.to_release,
                    "changed_placements": len(new_migrations),
                    "human_approved": status_counts["human_approved"],
                    "needs_taxonomy_decision": status_counts["needs_taxonomy_decision"],
                    "writes_performed": 0,
                },
                ensure_ascii=False,
            )
        )
        return

    target_release_dir.mkdir(parents=True)
    target_public_dir.mkdir(parents=True)
    target_validation_dir.mkdir(parents=True)
    shutil.copytree(source_snapshot_dir, target_snapshot_dir)
    for filename in [
        "taxonomy_nodes.json",
        "taxonomy_nodes.csv",
        "l4_registry.json",
        "l4_registry.csv",
        "source_crosswalk.json",
        "source_crosswalk.csv",
        "physical_lock.json",
        "physical_lock.csv",
        "algorithm_config.json",
        "algorithm_run.json",
        "algorithm_scores.json",
        "algorithm_scores.csv",
    ]:
        shutil.copy2(source_release_dir / filename, target_release_dir / filename)

    write_json(target_release_dir / "placements.json", placements)
    build.write_csv(target_release_dir / "placements.csv", placements)
    migrations = prior_migrations + new_migrations
    write_json(target_release_dir / "placement_migrations.json", migrations)
    build.write_csv(target_release_dir / "placement_migrations.csv", migrations)
    build.build_site_bundle(
        target_release_dir,
        target_public_dir,
        nodes,
        registry,
        placements,
        release_id=args.to_release,
    )

    global_cards = sorted(
        read_json(target_snapshot_dir / "global_ai_risk_l4_overlay_nodes.json"),
        key=lambda row: row["id"],
    )
    for number, card in enumerate(global_cards, start=1):
        card["_l4_id"] = f"RAI4-{number:04d}"
        card["_classification_text"] = build.classification_text(card)
    coverage, l3_rows, transition_rows, unresolved_rows = build.posthoc_coverage(
        global_cards,
        placements,
        nodes,
        release_id=args.to_release,
    )
    write_json(target_validation_dir / "coverage_summary.json", coverage)
    build.write_csv(target_validation_dir / "l3_distribution.csv", l3_rows)
    build.write_csv(target_validation_dir / "legacy_to_new_transition_reference_only.csv", transition_rows)
    write_json(target_validation_dir / "unresolved_cards.json", unresolved_rows)
    build.write_csv(target_validation_dir / "unresolved_cards.csv", unresolved_rows)
    write_json(target_validation_dir / "release_diff.json", new_migrations)

    status_counts = Counter(row["assignment_status"] for row in placements)
    manifest = copy.deepcopy(source_manifest)
    manifest.update(
        {
            "release_id": args.to_release,
            "previous_release": args.from_release,
            "release_status": "prepublication_draft",
            "provisional": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "git_commit": None,
            "artifacts": [],
            "validation": {
                "status": "PENDING_VALIDATOR",
                "report": f"reports/validation/{args.to_release}/validation_summary.json",
            },
        }
    )
    for source in manifest["sources"]:
        source["path"] = source["path"].replace(
            f"data/source_snapshots/{args.from_release}/",
            f"data/source_snapshots/{args.to_release}/",
        )
    manifest["counts"].update(
        {
            "algorithm_proposed": status_counts["algorithm_proposed"],
            "human_approved": status_counts["human_approved"],
            "needs_taxonomy_decision": status_counts["needs_taxonomy_decision"],
        }
    )
    manifest["approvals"] = list(manifest.get("approvals", [])) + [
        {
            "scope": f"{len(new_migrations)} placement changes in {args.to_release}",
            "status": f"approved_by:{args.approved_by}",
        }
    ]
    write_json(target_release_dir / "manifest.json", manifest)
    write_json(target_public_dir / "manifest.json", manifest)

    print(
        json.dumps(
            {
                "from_release": args.from_release,
                "to_release": args.to_release,
                "changed_placements": len(new_migrations),
                "human_approved": status_counts["human_approved"],
                "needs_taxonomy_decision": status_counts["needs_taxonomy_decision"],
                "next_step": f"python3 scripts/validate_release.py --release-id {args.to_release}",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
