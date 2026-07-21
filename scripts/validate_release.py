#!/usr/bin/env python3
"""Validate structural, provenance, Physical-lock, and release invariants."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import jsonschema

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rai_taxonomy.codebook import (  # noqa: E402
    PHYSICAL_ALIAS_TO_GLOBAL,
    PHYSICAL_LEGACY_TO_NEW,
    RELEASE_ID,
)

EXPECTED_HASHES = {
    "global_ai_risk_l4_overlay_nodes.json": "57d419a1a3aac23c5eed8639733f70c58fd093f9fa6f463851c999db12cb7528",
    "physical_l4_cards.json": "116973e340f96bcfc5e6c8ffaa847845d2b581c33195d5104c5f9139b56e61fd",
    "physical_l4_references.json": "79a805b0c58a1b9ce917ac8e745437ce9e7bcbdbc4ad5d9027aff817bb9db758",
    "physical_taxonomy_migrations.json": "10362bd0051c668384f7802c12c0cbfd0ce93985415896f1f037eed33cc45e1e",
    "l0_l3_definition_source.txt": "56076ebf7dacd297fe2f6c785bb68392796bfed766ce488fa21695b65e095b91",
}
PINNED_MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-id", default=RELEASE_ID)
    return parser.parse_args()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    return re.sub(r"\s+", " ", text).strip()


def split_bilingual_label(label: str) -> tuple[str | None, str | None]:
    match = re.match(r"^(.*?)\s*\(([^()]*)\)\s*$", normalize_text(label))
    if not match:
        return normalize_text(label) or None, None
    return match.group(1).strip() or None, match.group(2).strip() or None


def parse_three_h_one_r(value: str | None) -> list[dict]:
    parsed = []
    for token in (value or "").split("|"):
        match = re.match(r"^\s*(H1|H2|H3|RC)\s+([^\[]+?)\s*\[([PS])\]\s*$", token)
        if not match:
            continue
        axis_code, axis_name, priority_code = match.groups()
        parsed.append(
            {
                "axis_code": axis_code,
                "axis_name": axis_name.strip(),
                "priority_code": priority_code,
                "priority": "Primary" if priority_code == "P" else "Secondary",
            }
        )
    return parsed


def expected_registry_from_sources(
    source_global: list[dict],
    source_physical: list[dict],
    source_physical_references: list[dict],
) -> list[dict]:
    physical_by_global = {
        PHYSICAL_ALIAS_TO_GLOBAL.get(card["card_id"], card["card_id"]): card
        for card in source_physical
    }
    references_by_card: dict[str, list[dict]] = defaultdict(list)
    for reference in source_physical_references:
        references_by_card[reference["card_id"]].append(reference)

    expected = []
    for index, card in enumerate(sorted(source_global, key=lambda row: row["id"]), start=1):
        physical = physical_by_global.get(card["id"])
        label_ko, physical_label_en = (
            split_bilingual_label(physical["label"]) if physical else (None, None)
        )
        references = []
        if card.get("evidence_title") or card.get("evidence_url"):
            references.append(
                {
                    "title": card.get("evidence_title"),
                    "url": card.get("evidence_url"),
                    "type": card.get("evidence_type"),
                    "source_system": "global_1726",
                }
            )
        if physical:
            for reference in references_by_card.get(physical["card_id"], []):
                references.append(
                    {
                        "title": reference.get("reference_title"),
                        "url": reference.get("reference_url"),
                        "type": reference.get("reference_class"),
                        "source_system": "physical_182",
                        "reference_index": reference.get("reference_index"),
                        "justification": reference.get("justification"),
                        "is_linked": reference.get("is_linked"),
                    }
                )
        expected.append(
            {
                "l4_id": f"RAI4-{index:04d}",
                "label_en": normalize_text(card.get("l4_label") or physical_label_en),
                "label_ko": label_ko,
                "definition_en": normalize_text(card.get("definition")),
                "definition_ko": physical.get("definition") if physical else None,
                "severity_1to5": card.get("risk_severity_1to5"),
                "probability_0to1": card.get("risk_probability_proxy_0to1"),
                "impact_score": card.get("risk_impact_score"),
                "impact_percentile": card.get("risk_impact_percentile"),
                "metrics_source": "global_1726",
                "three_h_one_r_raw": physical.get("three_h_one_r") if physical else None,
                "three_h_one_r": parse_three_h_one_r(
                    physical.get("three_h_one_r") if physical else None
                ),
                "references": references,
                "status": "active",
                "introduced_in": RELEASE_ID,
                "retired_in": None,
                "merged_into": None,
                "allocation_basis": "ASCII lexicographic order of frozen global source ID",
            }
        )
    return expected


def hierarchy_path(node_id: str | None, nodes_by_id: dict[str, dict]) -> list[dict]:
    if node_id is None:
        return []
    result = []
    current = nodes_by_id[node_id]
    while current:
        result.append(
            {
                "node_id": current["node_id"],
                "label_en": current["label_en"],
                "label_ko": current["label_ko"],
            }
        )
        current = nodes_by_id.get(current.get("parent_id"))
    return list(reversed(result))


def integrity_paths(*roots: Path, extras: list[Path] | None = None) -> list[Path]:
    excluded_parts = {".git", "__pycache__", "build", "tmp"}
    paths: set[Path] = set()
    for root in roots:
        if root.is_file():
            paths.add(root)
            continue
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if (
                path.is_file()
                and path.name != "checksums.sha256"
                and not any(part in excluded_parts for part in path.parts)
                and path.suffix != ".pyc"
            ):
                paths.add(path)
    for path in extras or []:
        if path.is_file():
            paths.add(path)
    return sorted(paths)


def project_integrity_paths(
    release_dir: Path,
    source_dir: Path,
    public_dir: Path,
    validation_dir: Path,
    schemas_dir: Path,
) -> list[Path]:
    extras = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / ".gitignore",
        PROJECT_ROOT / "requirements.txt",
        PROJECT_ROOT / "requirements-lock.txt",
        PROJECT_ROOT / "environment.json",
        PROJECT_ROOT / "data" / "current.json",
        PROJECT_ROOT / "index.html",
        PROJECT_ROOT / "output" / "jupyter-notebook" / "rai_taxonomy_v1_data_quality_audit.ipynb",
        PROJECT_ROOT / "output" / "jupyter-notebook" / "stage2_classification_calibration_audit.ipynb",
        PROJECT_ROOT / "output" / "jupyter-notebook" / "stage3_forced_matching_audit.ipynb",
        PROJECT_ROOT / "reports" / "latex" / "rai_taxonomy_v1_data_generation_report_ko.tex",
        PROJECT_ROOT / "reports" / "latex" / "stage2_classification_criteria_and_results_ko.tex",
        PROJECT_ROOT / "reports" / "latex" / "stage3_forced_matching_results_ko.tex",
        PROJECT_ROOT / "reports" / "latex" / "stage3_review_hold_policy_ko.tex",
        PROJECT_ROOT / "reports" / "latex" / "rai_risk_taxonomy_technical_report_2_0_ko.tex",
        PROJECT_ROOT / "reports" / "latex" / "rai_risk_taxonomy_technical_report_2_0_en.tex",
        PROJECT_ROOT / "reports" / "pdf" / "rai_risk_taxonomy_technical_report_2_0_ko.pdf",
        PROJECT_ROOT / "reports" / "pdf" / "rai_risk_taxonomy_technical_report_2_0_en.pdf",
    ]
    return integrity_paths(
        release_dir,
        source_dir,
        public_dir,
        validation_dir,
        schemas_dir,
        PROJECT_ROOT / "src",
        PROJECT_ROOT / "scripts",
        PROJECT_ROOT / "tests",
        PROJECT_ROOT / "docs",
        PROJECT_ROOT / "assets",
        PROJECT_ROOT / "data" / "experiments",
        PROJECT_ROOT / "reports" / "validation" / "stage2-v1",
        PROJECT_ROOT / "reports" / "validation" / "stage3-v1",
        PROJECT_ROOT / "reports" / "statistics",
        PROJECT_ROOT / "reports" / "latex" / "generated",
        extras=extras,
    )


def csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return value


def json_safe(value: Any) -> Any:
    if isinstance(value, set):
        return sorted(json_safe(item) for item in value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def write_csv(path: Path, rows: list[dict], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = columns or (list(rows[0]) if rows else [])
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        if fieldnames:
            writer.writeheader()
            for row in rows:
                writer.writerow({key: csv_value(row.get(key)) for key in fieldnames})


class Audit:
    def __init__(self) -> None:
        self.checks: list[dict] = []

    def add(
        self,
        check_id: str,
        description: str,
        expected: Any,
        actual: Any,
        passed: bool,
        severity: str = "critical",
        details: str | None = None,
    ) -> None:
        self.checks.append(
            {
                "check_id": check_id,
                "description": description,
                "expected": json_safe(expected),
                "actual": json_safe(actual),
                "status": "PASS" if passed else ("WARN" if severity == "warning" else "FAIL"),
                "severity": severity,
                "details": details,
            }
        )


def schema_errors(records: list[dict], schema_path: Path) -> list[str]:
    schema = read_json(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for index, record in enumerate(records):
        for error in validator.iter_errors(record):
            path = ".".join(str(item) for item in error.path)
            errors.append(f"row={index} path={path} message={error.message}")
            if len(errors) >= 50:
                return errors
    return errors


def artifacts_for_manifest(paths: list[Path]) -> list[dict]:
    rows = []
    for path in sorted(set(paths)):
        if not path.is_file() or path.name in {"manifest.json", "checksums.sha256"}:
            continue
        row_count = None
        if path.suffix == ".json":
            try:
                value = read_json(path)
                if isinstance(value, list):
                    row_count = len(value)
                elif isinstance(value, dict) and isinstance(value.get("cards"), list):
                    row_count = len(value["cards"])
                elif isinstance(value, dict) and isinstance(value.get("nodes"), list):
                    row_count = len(value["nodes"])
            except json.JSONDecodeError:
                pass
        rows.append(
            {
                "path": str(path.relative_to(PROJECT_ROOT)),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "rows": row_count,
            }
        )
    return rows


def main() -> None:
    args = parse_args()
    release_id = args.release_id
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", release_id):
        raise ValueError(f"Invalid release ID: {release_id}")
    release_dir = PROJECT_ROOT / "data" / "releases" / release_id
    source_dir = PROJECT_ROOT / "data" / "source_snapshots" / release_id
    public_dir = PROJECT_ROOT / "public" / "data" / "releases" / release_id
    validation_dir = PROJECT_ROOT / "reports" / "validation" / release_id
    schemas_dir = PROJECT_ROOT / "schemas"

    nodes = read_json(release_dir / "taxonomy_nodes.json")
    registry = read_json(release_dir / "l4_registry.json")
    crosswalk = read_json(release_dir / "source_crosswalk.json")
    locks = read_json(release_dir / "physical_lock.json")
    placements = read_json(release_dir / "placements.json")
    migrations = read_json(release_dir / "placement_migrations.json")
    algorithm_config = read_json(release_dir / "algorithm_config.json")
    algorithm_run = read_json(release_dir / "algorithm_run.json")
    manifest = read_json(release_dir / "manifest.json")
    site_cards = read_json(public_dir / "cards.json")["cards"]
    hierarchy = read_json(public_dir / "hierarchy.json")["nodes"]
    search_index = read_json(public_dir / "search-index.json")
    source_global = read_json(source_dir / "global_ai_risk_l4_overlay_nodes.json")
    source_physical = read_json(source_dir / "physical_l4_cards.json")
    source_physical_references = read_json(source_dir / "physical_l4_references.json")
    source_physical_migrations = read_json(source_dir / "physical_taxonomy_migrations.json")

    audit = Audit()
    for index, (filename, expected_hash) in enumerate(EXPECTED_HASHES.items(), start=1):
        actual_hash = sha256_file(source_dir / filename)
        audit.add(
            f"SRC-{index:03d}",
            f"Frozen source hash: {filename}",
            expected_hash,
            actual_hash,
            actual_hash == expected_hash,
        )
    audit.add("SRC-006", "Global source row count", 1726, len(source_global), len(source_global) == 1726)
    audit.add("SRC-007", "Physical source row count", 182, len(source_physical), len(source_physical) == 182)
    audit.add(
        "SRC-008",
        "Global source ID uniqueness",
        1726,
        len({row["id"] for row in source_global}),
        len({row["id"] for row in source_global}) == 1726,
    )
    audit.add(
        "SRC-009",
        "Physical reference row/card coverage",
        {"rows": 360, "cards": 182},
        {"rows": len(source_physical_references), "cards": len({row["card_id"] for row in source_physical_references})},
        len(source_physical_references) == 360
        and {row["card_id"] for row in source_physical_references}
        == {row["card_id"] for row in source_physical},
    )
    audit.add(
        "SRC-010",
        "Physical source migration row count",
        2,
        len(source_physical_migrations),
        len(source_physical_migrations) == 2,
    )
    expected_manifest_source_names = {
        "global_1726",
        "physical_182",
        "physical_l4_references",
        "physical_taxonomy_migrations",
        "l0_l3_definition_source",
    }
    manifest_sources = {row.get("name"): row for row in manifest.get("sources", [])}
    manifest_source_failures = []
    for name, row in manifest_sources.items():
        path_value = row.get("path")
        path = PROJECT_ROOT / path_value if isinstance(path_value, str) else Path("/__invalid__")
        if not path.is_file() or row.get("sha256") != sha256_file(path):
            manifest_source_failures.append(name)
    audit.add(
        "SRC-011",
        "Manifest enumerates and hashes every frozen source snapshot",
        expected_manifest_source_names,
        set(manifest_sources),
        set(manifest_sources) == expected_manifest_source_names and not manifest_source_failures,
        details=str(manifest_source_failures),
    )
    integrity_set = {
        str(path.relative_to(PROJECT_ROOT)): path
        for path in project_integrity_paths(
            release_dir, source_dir, public_dir, validation_dir, schemas_dir
        )
    }
    checksum_path = validation_dir / "checksums.sha256"
    recorded_checksums: dict[str, str] = {}
    malformed_checksum_lines = []
    if checksum_path.is_file():
        for line in checksum_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            parts = line.split("  ", 1)
            if len(parts) != 2:
                malformed_checksum_lines.append(line)
                continue
            recorded_checksums[parts[1]] = parts[0]
    checksum_failures = [
        path
        for path, local_path in integrity_set.items()
        if recorded_checksums.get(path) != sha256_file(local_path)
    ]
    checksum_failures.extend(sorted(set(recorded_checksums) - set(integrity_set)))
    audit.add(
        "INT-001",
        "Checksum ledger exactly covers the project integrity scope",
        {"files": len(integrity_set), "mismatches": 0},
        {
            "files": len(recorded_checksums),
            "mismatches": len(checksum_failures) + len(malformed_checksum_lines),
        },
        bool(recorded_checksums)
        and set(recorded_checksums) == set(integrity_set)
        and not checksum_failures
        and not malformed_checksum_lines,
        details=str((checksum_failures + malformed_checksum_lines)[:20]),
    )

    level_counts = Counter(row["level"] for row in nodes)
    audit.add("NODE-001", "Taxonomy level counts", {0: 1, 1: 3, 2: 6, 3: 50}, dict(level_counts), dict(level_counts) == {0: 1, 1: 3, 2: 6, 3: 50})
    node_ids = [row["node_id"] for row in nodes]
    audit.add("NODE-002", "Taxonomy node ID uniqueness", len(nodes), len(set(node_ids)), len(nodes) == len(set(node_ids)))
    nodes_by_id = {row["node_id"]: row for row in nodes}
    parent_failures = []
    sibling_sequences: dict[str | None, list[int]] = defaultdict(list)
    for node in nodes:
        sibling_sequences[node.get("parent_id")].append(node["sequence"])
        if node["level"] == 0:
            if node.get("parent_id") is not None:
                parent_failures.append(node["node_id"])
        else:
            parent = nodes_by_id.get(node.get("parent_id"))
            if parent is None or parent["level"] != node["level"] - 1:
                parent_failures.append(node["node_id"])
    audit.add("NODE-003", "Parent-child level integrity", 0, len(parent_failures), not parent_failures, details=str(parent_failures[:20]))
    sequence_duplicates = {str(parent): values for parent, values in sibling_sequences.items() if len(values) != len(set(values))}
    audit.add("NODE-004", "Sibling sequence uniqueness", 0, len(sequence_duplicates), not sequence_duplicates, details=str(sequence_duplicates))

    expected_l4_ids = [f"RAI4-{index:04d}" for index in range(1, 1727)]
    actual_l4_ids = [row["l4_id"] for row in registry]
    audit.add("ID-001", "L4 registry row count", 1726, len(registry), len(registry) == 1726)
    audit.add("ID-002", "L4 ID uniqueness", 1726, len(set(actual_l4_ids)), len(set(actual_l4_ids)) == 1726)
    audit.add("ID-003", "L4 ID continuous allocation", expected_l4_ids, actual_l4_ids, actual_l4_ids == expected_l4_ids, details="RAI4-0001 through RAI4-1726")
    leaked_placements = [row["l4_id"] for row in registry if "primary_l3_id" in row]
    audit.add("ID-004", "Registry-placement separation", 0, len(leaked_placements), not leaked_placements)
    expected_registry = expected_registry_from_sources(
        source_global,
        source_physical,
        source_physical_references,
    )
    registry_source_failures = [
        expected["l4_id"]
        for expected, actual in zip(expected_registry, registry)
        if expected != actual
    ]
    if len(expected_registry) != len(registry):
        registry_source_failures.append("ROW_COUNT_OR_ORDER")
    audit.add(
        "REG-001",
        "Every canonical L4 registry row is the exact approved transformation of frozen sources",
        0,
        len(registry_source_failures),
        not registry_source_failures,
        details=str(registry_source_failures[:20]),
    )

    global_xw = [row for row in crosswalk if row["source_system"] == "global_1726"]
    physical_xw = [row for row in crosswalk if row["source_system"] == "physical_182"]
    exact_xw = [row for row in physical_xw if row["relationship"] == "exact_id"]
    alias_xw = [row for row in physical_xw if row["relationship"] == "explicit_alias"]
    audit.add("XW-001", "Crosswalk total rows", 1908, len(crosswalk), len(crosswalk) == 1908)
    audit.add("XW-002", "Global canonical rows", 1726, len(global_xw), len(global_xw) == 1726)
    audit.add("XW-003", "Physical exact-ID rows", 169, len(exact_xw), len(exact_xw) == 169)
    audit.add("XW-004", "Physical explicit aliases", 13, len(alias_xw), len(alias_xw) == 13)
    actual_aliases = {row["source_id"]: row["canonical_source_id"] for row in alias_xw}
    audit.add("XW-005", "Explicit alias table exact match", PHYSICAL_ALIAS_TO_GLOBAL, actual_aliases, actual_aliases == PHYSICAL_ALIAS_TO_GLOBAL)
    composite_keys = [(row["source_system"], row["source_snapshot_id"], row["source_id"]) for row in crosswalk]
    audit.add("XW-006", "Crosswalk composite key uniqueness", len(crosswalk), len(set(composite_keys)), len(crosswalk) == len(set(composite_keys)))
    mapped_l4_ids = {row["l4_id"] for row in crosswalk}
    audit.add("XW-007", "Crosswalk references valid L4 IDs", 0, len(mapped_l4_ids - set(actual_l4_ids)), not (mapped_l4_ids - set(actual_l4_ids)))
    expected_global_map = {
        row["id"]: f"RAI4-{index:04d}"
        for index, row in enumerate(sorted(source_global, key=lambda item: item["id"]), start=1)
    }
    global_xw_by_source = {row["source_id"]: row for row in global_xw}
    global_exact_failures = []
    for source_id, l4_id in expected_global_map.items():
        row = global_xw_by_source.get(source_id)
        if (
            row is None
            or row.get("l4_id") != l4_id
            or row.get("canonical_source_id") != source_id
            or row.get("relationship") != "canonical_source"
        ):
            global_exact_failures.append(source_id)
    global_exact_failures.extend(sorted(set(global_xw_by_source) - set(expected_global_map)))
    audit.add(
        "XW-008",
        "Every global source ID maps to its deterministic RAI4 allocation",
        0,
        len(global_exact_failures),
        not global_exact_failures,
        details=str(global_exact_failures[:20]),
    )
    physical_xw_by_source = {row["source_id"]: row for row in physical_xw}
    physical_exact_failures = []
    for card in source_physical:
        physical_id = card["card_id"]
        canonical_id = PHYSICAL_ALIAS_TO_GLOBAL.get(physical_id, physical_id)
        row = physical_xw_by_source.get(physical_id)
        expected_relationship = "explicit_alias" if physical_id in PHYSICAL_ALIAS_TO_GLOBAL else "exact_id"
        if (
            canonical_id not in expected_global_map
            or row is None
            or row.get("canonical_source_id") != canonical_id
            or row.get("l4_id") != expected_global_map.get(canonical_id)
            or row.get("relationship") != expected_relationship
        ):
            physical_exact_failures.append(physical_id)
    physical_exact_failures.extend(
        sorted(set(physical_xw_by_source) - {row["card_id"] for row in source_physical})
    )
    audit.add(
        "XW-009",
        "Every Physical source ID follows the approved exact/alias chain to RAI4",
        0,
        len(physical_exact_failures),
        not physical_exact_failures,
        details=str(physical_exact_failures[:20]),
    )

    placement_ids = [row["l4_id"] for row in placements]
    audit.add("PLC-001", "Placement row count", 1726, len(placements), len(placements) == 1726)
    audit.add("PLC-002", "One placement per L4", 1726, len(set(placement_ids)), len(set(placement_ids)) == 1726 and set(placement_ids) == set(actual_l4_ids))
    needs = [row for row in placements if row["assignment_status"] == "needs_taxonomy_decision"]
    bad_needs = [row["l4_id"] for row in needs if row["primary_l3_id"] is not None]
    audit.add("PLC-003", "Needs-decision cards have null primary L3", 0, len(bad_needs), not bad_needs)
    placed = [row for row in placements if row["assignment_status"] != "needs_taxonomy_decision"]
    bad_placed = [row["l4_id"] for row in placed if row["primary_l3_id"] not in nodes_by_id]
    audit.add("PLC-004", "Placed cards reference an active L3", 0, len(bad_placed), not bad_placed)
    leakage_flags = [row["l4_id"] for row in placements if row.get("legacy_hierarchy_used_as_feature") is not False]
    audit.add("PLC-005", "Legacy hierarchy excluded from predictive features", 0, len(leakage_flags), not leakage_flags)
    nonphysical_in_physical = [
        row["l4_id"]
        for row in placements
        if row["assignment_status"] != "locked_physical" and (row["primary_l3_id"] or "").startswith("RAI3-P-")
    ]
    audit.add("PLC-006", "No non-Physical algorithm proposal enters locked Physical L3", 0, len(nonphysical_in_physical), not nonphysical_in_physical)
    decision_ids = [row["decision_id"] for row in needs]
    audit.add("PLC-007", "Taxonomy decision queue IDs are unique and populated", len(needs), len(set(decision_ids) - {None}), len(set(decision_ids) - {None}) == len(needs))

    lock_by_l4 = {row["l4_id"]: row for row in locks}
    locked_placements = [row for row in placements if row["assignment_status"] == "locked_physical"]
    audit.add("PHY-001", "Physical locked placement count", 182, len(locked_placements), len(locked_placements) == 182)
    lock_mismatches = [
        row["l4_id"]
        for row in locked_placements
        if row["l4_id"] not in lock_by_l4 or row["primary_l3_id"] != lock_by_l4[row["l4_id"]]["new_l3_id"]
    ]
    audit.add("PHY-002", "Physical locked L3 equality", 0, len(lock_mismatches), not lock_mismatches)
    legacy_l2_counts = Counter(row["legacy_l2_id"] for row in locks)
    audit.add("PHY-003", "Physical L2 distribution", {"P2": 91, "I2": 62, "S2": 29}, dict(legacy_l2_counts), dict(legacy_l2_counts) == {"P2": 91, "I2": 62, "S2": 29})
    physical_source_counts = Counter(row["l3_id"] for row in source_physical)
    lock_counts = Counter(row["legacy_l3_id"] for row in locks)
    audit.add("PHY-004", "All 24 Physical L3 card counts preserved", dict(physical_source_counts), dict(lock_counts), dict(physical_source_counts) == dict(lock_counts) and len(lock_counts) == 24)
    expected_new_map = {
        row["card_id"]: PHYSICAL_LEGACY_TO_NEW[row["l3_id"]]
        for row in source_physical
    }
    actual_new_map = {row["physical_card_id"]: row["new_l3_id"] for row in locks}
    audit.add("PHY-005", "Physical legacy-to-new L3 map", expected_new_map, actual_new_map, expected_new_map == actual_new_map)
    if release_id == RELEASE_ID:
        audit.add("PHY-006", "Physical migration ledger remains empty for baseline", 0, len(migrations), len(migrations) == 0)
    else:
        physical_migrations = [row for row in migrations if row.get("event_type") == "lock_exception"]
        audit.add(
            "PHY-006",
            "No Physical lock exception without explicit migration events",
            0,
            len(physical_migrations),
            not physical_migrations,
            details="This release workflow does not authorize Physical lock exceptions.",
        )
    lock_by_physical = {row["physical_card_id"]: row for row in locks}
    placement_by_l4 = {row["l4_id"]: row for row in placements}
    physical_chain_failures = []
    for card in source_physical:
        physical_id = card["card_id"]
        canonical_id = PHYSICAL_ALIAS_TO_GLOBAL.get(physical_id, physical_id)
        expected_l4_id = expected_global_map.get(canonical_id)
        expected_l3_id = PHYSICAL_LEGACY_TO_NEW.get(card["l3_id"])
        lock = lock_by_physical.get(physical_id)
        placement = placement_by_l4.get(expected_l4_id)
        if (
            lock is None
            or expected_l4_id is None
            or lock.get("global_source_id") != canonical_id
            or lock.get("l4_id") != expected_l4_id
            or lock.get("legacy_l2_id") != card["l2_id"]
            or lock.get("legacy_l2_name") != card["l2_name"]
            or lock.get("legacy_l3_id") != card["l3_id"]
            or lock.get("legacy_l3_name") != card["l3_name"]
            or lock.get("new_l3_id") != expected_l3_id
            or lock.get("locked") is not True
            or placement is None
            or placement.get("assignment_status") != "locked_physical"
            or placement.get("primary_l3_id") != expected_l3_id
        ):
            physical_chain_failures.append(physical_id)
    physical_chain_failures.extend(
        sorted(set(lock_by_physical) - {row["card_id"] for row in source_physical})
    )
    audit.add(
        "PHY-007",
        "Card-level Physical source→alias→RAI4→new L3→placement chain",
        0,
        len(physical_chain_failures),
        not physical_chain_failures,
        details=str(physical_chain_failures[:20]),
    )
    physical_reference_counts = Counter(row["card_id"] for row in source_physical_references)
    registry_by_l4 = {row["l4_id"]: row for row in registry}
    physical_reference_failures = []
    for card in source_physical:
        canonical_id = PHYSICAL_ALIAS_TO_GLOBAL.get(card["card_id"], card["card_id"])
        l4_id = expected_global_map[canonical_id]
        embedded = [
            row
            for row in registry_by_l4[l4_id]["references"]
            if row.get("source_system") == "physical_182"
        ]
        if len(embedded) != physical_reference_counts[card["card_id"]]:
            physical_reference_failures.append(card["card_id"])
    audit.add(
        "PHY-008",
        "Physical per-card reference counts preserved in the L4 registry",
        0,
        len(physical_reference_failures),
        not physical_reference_failures,
        details=str(physical_reference_failures[:20]),
    )
    malformed_three_h = []
    for card in source_physical:
        canonical_id = PHYSICAL_ALIAS_TO_GLOBAL.get(card["card_id"], card["card_id"])
        registry_card = registry_by_l4[expected_global_map[canonical_id]]
        expected_tokens = [token.strip() for token in card.get("three_h_one_r", "").split("|") if token.strip()]
        if registry_card.get("three_h_one_r_raw") != card.get("three_h_one_r") or len(registry_card.get("three_h_one_r", [])) != len(expected_tokens):
            malformed_three_h.append(card["card_id"])
    audit.add(
        "PHY-009",
        "Physical 3H/Role tags preserve raw values and structured token counts",
        0,
        len(malformed_three_h),
        not malformed_three_h,
        details=str(malformed_three_h[:20]),
    )

    schema_specs = [
        ("SCH-001", nodes, schemas_dir / "taxonomy-node.schema.json"),
        ("SCH-002", registry, schemas_dir / "l4-card.schema.json"),
        ("SCH-003", crosswalk, schemas_dir / "source-crosswalk.schema.json"),
        ("SCH-004", placements, schemas_dir / "placement.schema.json"),
        ("SCH-005", migrations, schemas_dir / "migration.schema.json"),
    ]
    for check_id, records, schema_path in schema_specs:
        errors = schema_errors(records, schema_path)
        audit.add(check_id, f"JSON Schema: {schema_path.name}", 0, len(errors), not errors, details="\n".join(errors[:10]))

    audit.add("SITE-001", "Site card row count", 1726, len(site_cards), len(site_cards) == 1726)
    audit.add("SITE-002", "Site card L4 uniqueness", 1726, len({row["l4_id"] for row in site_cards}), len({row["l4_id"] for row in site_cards}) == 1726)
    audit.add("SITE-003", "Site hierarchy node count", 60, len(hierarchy), len(hierarchy) == 60)
    audit.add("SITE-004", "Search index row count", 1726, len(search_index), len(search_index) == 1726)
    site_count_by_l3 = Counter(row["primary_l3_id"] for row in site_cards if row["primary_l3_id"])
    hierarchy_count_by_l3 = {row["node_id"]: row.get("l4_count", 0) for row in hierarchy if row["level"] == 3}
    audit.add("SITE-005", "Hierarchy L3 counts equal site-card placements", dict(site_count_by_l3), {key: value for key, value in hierarchy_count_by_l3.items() if value}, all(hierarchy_count_by_l3.get(key) == value for key, value in site_count_by_l3.items()) and sum(hierarchy_count_by_l3.values()) == len(placed))
    site_by_l4 = {row["l4_id"]: row for row in site_cards}
    site_join_failures = []
    for l4_id, registry_card in registry_by_l4.items():
        site_card = site_by_l4.get(l4_id)
        placement = placement_by_l4[l4_id]
        if site_card is None:
            site_join_failures.append(l4_id)
            continue
        registry_equal = all(site_card.get(key) == value for key, value in registry_card.items())
        placement_equal = (
            site_card.get("release_id") == release_id
            and site_card.get("primary_l3_id") == placement.get("primary_l3_id")
            and site_card.get("assignment_status") == placement.get("assignment_status")
            and site_card.get("review_status") == placement.get("review_status")
            and site_card.get("breadcrumb") == hierarchy_path(placement.get("primary_l3_id"), nodes_by_id)
        )
        if not registry_equal or not placement_equal:
            site_join_failures.append(l4_id)
    audit.add(
        "SITE-006",
        "Every site card is the exact registry-plus-placement join",
        0,
        len(site_join_failures),
        not site_join_failures and set(site_by_l4) == set(registry_by_l4),
        details=str(site_join_failures[:20]),
    )
    hierarchy_by_id = {row["node_id"]: row for row in hierarchy}
    hierarchy_exact_failures = []
    for node_id, node in nodes_by_id.items():
        site_node = hierarchy_by_id.get(node_id)
        expected_count = site_count_by_l3.get(node_id, 0) if node["level"] == 3 else None
        if site_node is None or any(site_node.get(key) != value for key, value in node.items()):
            hierarchy_exact_failures.append(node_id)
        elif node["level"] == 3 and site_node.get("l4_count") != expected_count:
            hierarchy_exact_failures.append(node_id)
        elif node["level"] != 3 and "l4_count" in site_node:
            hierarchy_exact_failures.append(node_id)
    audit.add(
        "SITE-007",
        "Every site hierarchy node exactly matches canonical nodes and placement counts",
        0,
        len(hierarchy_exact_failures),
        not hierarchy_exact_failures and set(hierarchy_by_id) == set(nodes_by_id),
        details=str(hierarchy_exact_failures[:20]),
    )
    search_by_l4 = {row["l4_id"]: row for row in search_index}
    search_failures = []
    for l4_id, registry_card in registry_by_l4.items():
        row = search_by_l4.get(l4_id)
        placement = placement_by_l4[l4_id]
        if (
            row is None
            or row.get("l3_id") != placement.get("primary_l3_id")
            or row.get("assignment_status") != placement.get("assignment_status")
            or row.get("label") != registry_card.get("label_en")
            or row.get("label_ko") != registry_card.get("label_ko")
            or not isinstance(row.get("keywords"), str)
        ):
            search_failures.append(l4_id)
    audit.add(
        "SITE-008",
        "Every search-index row matches canonical card identity and placement",
        0,
        len(search_failures),
        not search_failures and set(search_by_l4) == set(registry_by_l4),
        details=str(search_failures[:20]),
    )
    site_shell_path = PROJECT_ROOT / "index.html"
    site_css_path = PROJECT_ROOT / "assets" / "site.css"
    site_js_path = PROJECT_ROOT / "assets" / "site.js"
    site_shell = site_shell_path.read_text(encoding="utf-8") if site_shell_path.is_file() else ""
    site_js = site_js_path.read_text(encoding="utf-8") if site_js_path.is_file() else ""
    site_contract_failures = []
    if 'href="assets/site.css"' not in site_shell:
        site_contract_failures.append("css_link")
    if 'src="assets/site.js"' not in site_shell:
        site_contract_failures.append("js_link")
    if 'const DATA_ROOT = "public/data/releases/v1.0.0"' not in site_js:
        site_contract_failures.append("release_data_root")
    if not site_css_path.is_file() or not site_js_path.is_file():
        site_contract_failures.append("site_assets")
    audit.add(
        "SITE-009",
        "Static HTML explorer targets the exact validated v1.0.0 public data bundle",
        0,
        len(site_contract_failures),
        not site_contract_failures,
        details=str(site_contract_failures),
    )

    proposed = [row for row in placements if row["assignment_status"] == "algorithm_proposed"]
    proposed_without_consensus = [
        row["l4_id"]
        for row in proposed
        if len(row.get("frontier_expert_reviews", [])) != 2
        or any(review.get("decision") != "APPROVE" for review in row.get("frontier_expert_reviews", []))
        or any(review.get("hierarchy_blind") is not True for review in row.get("frontier_expert_reviews", []))
    ]
    audit.add("ALG-001", "Algorithm proposals have two frontier-expert approvals", 0, len(proposed_without_consensus), not proposed_without_consensus)
    audit.add("ALG-002", "Confidence is not presented as calibrated", False, any(row.get("confidence_calibrated") is True for row in proposed), not any(row.get("confidence_calibrated") is True for row in proposed))
    audit.add("ALG-003", "50-L3 sufficiency is not claimed before human validation", "NOT_DEMONSTRATED", read_json(validation_dir / "coverage_summary.json").get("fifty_l3_sufficiency_status"), read_json(validation_dir / "coverage_summary.json").get("fifty_l3_sufficiency_status") == "NOT_DEMONSTRATED")
    recorded_revisions = {
        algorithm_config.get("model_revision"),
        algorithm_run.get("model_revision"),
        manifest.get("algorithm", {}).get("model_revision"),
    }
    audit.add(
        "ALG-004",
        "BGE-M3 revision is explicitly pinned and consistent",
        {PINNED_MODEL_REVISION},
        recorded_revisions,
        recorded_revisions == {PINNED_MODEL_REVISION}
        and algorithm_config.get("model_revision_pinned") is True
        and algorithm_run.get("model_revision_pinned") is True
        and manifest.get("algorithm", {}).get("model_revision_pinned") is True,
    )
    config_hash = canonical_sha256(algorithm_config)
    recorded_config_hashes = {
        algorithm_run.get("configuration_sha256"),
        manifest.get("algorithm", {}).get("configuration_sha256"),
    }
    audit.add(
        "ALG-005",
        "Immutable algorithm configuration hash matches run record and manifest",
        config_hash,
        recorded_config_hashes,
        recorded_config_hashes == {config_hash},
    )
    codebook_path = PROJECT_ROOT / "src" / "rai_taxonomy" / "codebook.py"
    audit.add(
        "ALG-006",
        "Algorithm configuration pins the active codebook hash",
        sha256_file(codebook_path),
        algorithm_config.get("codebook_sha256"),
        algorithm_config.get("codebook_sha256") == sha256_file(codebook_path),
    )
    snapshot = Path(algorithm_config.get("snapshot_path", ""))
    snapshot_entries = []
    if snapshot.is_dir():
        for path in sorted(item for item in snapshot.rglob("*") if item.is_file() or item.is_symlink()):
            resolved = path.resolve()
            snapshot_entries.append(
                {
                    "path": str(path.relative_to(snapshot)),
                    "blob": resolved.name,
                    "bytes": resolved.stat().st_size,
                }
            )
    snapshot_fingerprint = canonical_sha256(snapshot_entries) if snapshot_entries else None
    audit.add(
        "ALG-007",
        "Pinned local model snapshot inventory matches the recorded fingerprint",
        {
            "revision": PINNED_MODEL_REVISION,
            "files": algorithm_config.get("snapshot_file_count"),
            "fingerprint": algorithm_config.get("snapshot_tree_fingerprint"),
        },
        {
            "revision": snapshot.name if snapshot_entries else None,
            "files": len(snapshot_entries),
            "fingerprint": snapshot_fingerprint,
        },
        bool(snapshot_entries)
        and snapshot.name == PINNED_MODEL_REVISION
        and len(snapshot_entries) == algorithm_config.get("snapshot_file_count")
        and snapshot_fingerprint == algorithm_config.get("snapshot_tree_fingerprint"),
    )
    reproducibility_path = validation_dir / "model_revision_reproducibility.json"
    reproducibility = read_json(reproducibility_path) if reproducibility_path.is_file() else {}
    current_score_hash = sha256_file(release_dir / "algorithm_scores.json")
    current_packet_hash = sha256_file(
        validation_dir / "frontier_expert_reviews" / "review_packet.json"
    )
    audit.add(
        "ALG-008",
        "Explicit-revision rerun is byte-identical to the reviewed initial run",
        {
            "scores": reproducibility.get("before_pin", {}).get("algorithm_scores_sha256"),
            "packet": reproducibility.get("before_pin", {}).get("frontier_review_packet_sha256"),
        },
        {"scores": current_score_hash, "packet": current_packet_hash},
        reproducibility.get("byte_identical") is True
        and reproducibility.get("expert_review_reuse_valid") is True
        and current_score_hash
        == reproducibility.get("after_explicit_pin", {}).get("algorithm_scores_sha256")
        and current_packet_hash
        == reproducibility.get("after_explicit_pin", {}).get("frontier_review_packet_sha256"),
    )
    audit.add("WARN-001", "Non-Physical human gold-set validation", "required before automatic approval", "not yet performed", False, severity="warning", details="All non-Physical placements remain algorithm_proposed.")
    audit.add("WARN-002", "Unresolved cards remain explicit", 0, len(needs), len(needs) == 0, severity="warning", details="A nonzero queue is expected under open-set mapping and requires taxonomy decisions.")

    release_diff_rows = []
    previous_release = manifest.get("previous_release")
    if release_id == RELEASE_ID:
        audit.add(
            "REL-001",
            "Baseline release has no previous-release dependency",
            None,
            previous_release,
            previous_release is None,
        )
        audit.add(
            "REL-002",
            "Baseline migration ledger is empty",
            0,
            len(migrations),
            len(migrations) == 0,
        )
    else:
        previous_dir = PROJECT_ROOT / "data" / "releases" / str(previous_release)
        previous_source_dir = PROJECT_ROOT / "data" / "source_snapshots" / str(previous_release)
        previous_placements_path = previous_dir / "placements.json"
        audit.add(
            "REL-001",
            "Remap release declares an existing previous release",
            "existing previous release",
            previous_release,
            isinstance(previous_release, str) and previous_placements_path.is_file(),
        )
        previous_placements = read_json(previous_placements_path) if previous_placements_path.is_file() else []
        previous_by_l4 = {row["l4_id"]: row for row in previous_placements}
        current_by_l4 = {row["l4_id"]: row for row in placements}
        for l4_id in sorted(set(previous_by_l4) & set(current_by_l4)):
            before = previous_by_l4[l4_id]
            after = current_by_l4[l4_id]
            if (
                before.get("primary_l3_id") != after.get("primary_l3_id")
                or before.get("assignment_status") != after.get("assignment_status")
            ):
                release_diff_rows.append(
                    {
                        "l4_id": l4_id,
                        "from_release": previous_release,
                        "to_release": release_id,
                        "from_l3_id": before.get("primary_l3_id"),
                        "to_l3_id": after.get("primary_l3_id"),
                        "from_status": before.get("assignment_status"),
                        "to_status": after.get("assignment_status"),
                    }
                )
        migrations_for_release = [row for row in migrations if row.get("to_release") == release_id]
        migration_by_l4 = {row["l4_id"]: row for row in migrations_for_release}
        migration_failures = []
        for diff in release_diff_rows:
            migration = migration_by_l4.get(diff["l4_id"])
            if (
                migration is None
                or migration.get("from_release") != diff["from_release"]
                or migration.get("to_release") != diff["to_release"]
                or migration.get("from_l3_id") != diff["from_l3_id"]
                or migration.get("to_l3_id") != diff["to_l3_id"]
                or migration.get("from_status") != diff["from_status"]
                or migration.get("to_status") != diff["to_status"]
            ):
                migration_failures.append(diff["l4_id"])
        migration_failures.extend(sorted(set(migration_by_l4) - {row["l4_id"] for row in release_diff_rows}))
        audit.add(
            "REL-002",
            "Placement diff and migration ledger are complete in both directions",
            {"diffs": len(release_diff_rows), "failures": 0},
            {"migrations": len(migrations_for_release), "failures": len(migration_failures)},
            len(release_diff_rows) == len(migrations_for_release) and not migration_failures,
            details=str(migration_failures[:20]),
        )
        immutable_filenames = [
            "taxonomy_nodes.json",
            "l4_registry.json",
            "source_crosswalk.json",
            "physical_lock.json",
            "algorithm_config.json",
            "algorithm_run.json",
            "algorithm_scores.json",
        ]
        immutable_failures = [
            filename
            for filename in immutable_filenames
            if not (previous_dir / filename).is_file()
            or not (release_dir / filename).is_file()
            or sha256_file(previous_dir / filename) != sha256_file(release_dir / filename)
        ]
        previous_snapshot_files = {
            str(path.relative_to(previous_source_dir)): sha256_file(path)
            for path in previous_source_dir.rglob("*")
            if path.is_file()
        } if previous_source_dir.is_dir() else {}
        current_snapshot_files = {
            str(path.relative_to(source_dir)): sha256_file(path)
            for path in source_dir.rglob("*")
            if path.is_file()
        }
        if not previous_snapshot_files or previous_snapshot_files != current_snapshot_files:
            immutable_failures.append("source_snapshots")
        audit.add(
            "REL-004",
            "Remap-only successor preserves immutable taxonomy, registry, crosswalk, locks, algorithm evidence, and frozen snapshots",
            0,
            len(immutable_failures),
            not immutable_failures,
            details=str(immutable_failures),
        )
        previous_migrations_path = previous_dir / "placement_migrations.json"
        previous_migrations = (
            read_json(previous_migrations_path) if previous_migrations_path.is_file() else []
        )
        migration_ids = [row.get("migration_id") for row in migrations]
        prior_prefix_preserved = (
            migrations[: len(previous_migrations)] == previous_migrations
            and len(migration_ids) == len(set(migration_ids))
        )
        audit.add(
            "REL-005",
            "Prior migration ledger is an exact prefix and all migration IDs remain unique",
            {"prior_rows": len(previous_migrations), "duplicate_ids": 0},
            {
                "prior_rows_preserved": len(previous_migrations)
                if migrations[: len(previous_migrations)] == previous_migrations
                else 0,
                "duplicate_ids": len(migration_ids) - len(set(migration_ids)),
            },
            prior_prefix_preserved,
        )
        changed_l4_ids = {row["l4_id"] for row in release_diff_rows}
        decision_id_failures = [
            l4_id
            for l4_id in sorted(set(previous_by_l4) & set(current_by_l4) - changed_l4_ids)
            if previous_by_l4[l4_id].get("decision_id")
            != current_by_l4[l4_id].get("decision_id")
        ]
        audit.add(
            "REL-006",
            "Unchanged cards preserve stable taxonomy-decision queue IDs",
            0,
            len(decision_id_failures),
            not decision_id_failures,
            details=str(decision_id_failures[:20]),
        )
    release_id_failures = [row["l4_id"] for row in placements if row.get("release_id") != release_id]
    audit.add(
        "REL-003",
        "Every placement carries the validated release ID",
        0,
        len(release_id_failures),
        not release_id_failures,
        details=str(release_id_failures[:20]),
    )

    lock_audit_rows = []
    placement_by_l4 = {row["l4_id"]: row for row in placements}
    for lock in locks:
        placement = placement_by_l4[lock["l4_id"]]
        lock_audit_rows.append(
            {
                **lock,
                "actual_l3_id": placement["primary_l3_id"],
                "lock_status": "PASS" if placement["primary_l3_id"] == lock["new_l3_id"] else "FAIL",
            }
        )
    write_csv(validation_dir / "physical_lock_audit.csv", lock_audit_rows)

    xw_audit_rows = [
        {
            **row,
            "l4_exists": row["l4_id"] in set(actual_l4_ids),
            "audit_status": "PASS" if row["l4_id"] in set(actual_l4_ids) else "FAIL",
        }
        for row in crosswalk
    ]
    write_csv(validation_dir / "source_crosswalk_audit.csv", xw_audit_rows)
    migration_id_by_l4 = {
        row["l4_id"]: row["migration_id"]
        for row in migrations
        if row.get("to_release") == release_id
    }
    write_csv(
        validation_dir / "release_diff.csv",
        [
            {**row, "migration_id": migration_id_by_l4.get(row["l4_id"])}
            for row in release_diff_rows
        ],
        [
            "l4_id",
            "from_release",
            "to_release",
            "from_l3_id",
            "to_l3_id",
            "from_status",
            "to_status",
            "migration_id",
        ],
    )

    failed = [check for check in audit.checks if check["status"] == "FAIL"]
    warnings = [check for check in audit.checks if check["status"] == "WARN"]
    validation_status = "PASS_WITH_WARNINGS" if not failed else "FAIL"
    summary = {
        "release_id": release_id,
        "status": validation_status,
        "failed_checks": len(failed),
        "warning_checks": len(warnings),
        "passed_checks": sum(check["status"] == "PASS" for check in audit.checks),
        "checks": audit.checks,
    }
    write_json(validation_dir / "validation_summary.json", summary)

    all_artifact_paths = project_integrity_paths(
        release_dir, source_dir, public_dir, validation_dir, schemas_dir
    )
    manifest_path = release_dir / "manifest.json"
    manifest = read_json(manifest_path)
    manifest["counts"].update(
        {
            "algorithm_proposed": len(proposed),
            "human_approved": sum(row["assignment_status"] == "human_approved" for row in placements),
            "needs_taxonomy_decision": len(needs),
        }
    )
    manifest["artifacts"] = artifacts_for_manifest(all_artifact_paths)
    manifest["validation"] = {
        "status": validation_status,
        "failed_checks": len(failed),
        "warning_checks": len(warnings),
        "report": str((validation_dir / "validation_summary.json").relative_to(PROJECT_ROOT)),
    }
    manifest_errors = list(
        jsonschema.Draft202012Validator(read_json(schemas_dir / "release-manifest.schema.json")).iter_errors(manifest)
    )
    if manifest_errors:
        raise ValueError("Manifest schema failed: " + "; ".join(error.message for error in manifest_errors[:5]))
    write_json(manifest_path, manifest)
    write_json(public_dir / "manifest.json", manifest)

    checksum_paths = project_integrity_paths(
        release_dir, source_dir, public_dir, validation_dir, schemas_dir
    )
    checksum_lines = [
        f"{sha256_file(path)}  {path.relative_to(PROJECT_ROOT)}" for path in sorted(set(checksum_paths))
    ]
    (validation_dir / "checksums.sha256").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "status": validation_status,
                "passed": summary["passed_checks"],
                "failed": len(failed),
                "warnings": len(warnings),
                "algorithm_proposed": len(proposed),
                "needs_taxonomy_decision": len(needs),
            },
            ensure_ascii=False,
        )
    )
    if failed:
        for check in failed:
            print(json.dumps(check, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
