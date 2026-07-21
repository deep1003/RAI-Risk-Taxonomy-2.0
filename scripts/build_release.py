#!/usr/bin/env python3
"""Build the site-ready provisional RAI taxonomy data release.

The script is intentionally hierarchy-blind during non-Physical placement. It
uses only a cleaned L4 label/definition/evidence title. Legacy global L1-L3
fields are retained strictly for post-hoc diagnostics.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from rai_taxonomy.codebook import (  # noqa: E402
    CLASSIFICATION_RULES,
    CODEBOOK_VERSION,
    GAP_RULES,
    L3_NODES,
    NON_PHYSICAL_L3_IDS,
    PHYSICAL_ALIAS_TO_GLOBAL,
    PHYSICAL_LEGACY_TO_NEW,
    RELEASE_ID,
    UPPER_NODES,
)

RUN_ID = "RUN-20260721-BGE-M3-01"
SEED = 1726
MODEL_ID = "BAAI/bge-m3"
PINNED_MODEL_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
SNAPSHOT_DATE = "2026-07-21"
CREATED_AT = "2026-07-21T00:00:00+09:00"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--global-source",
        type=Path,
        default=Path("/Users/deep1003/data3/AI_Topic_Space.github.io/data/global_ai_risk_l4_overlay_nodes.json"),
    )
    parser.add_argument(
        "--physical-source",
        type=Path,
        default=Path("/Users/deep1003/data3/Physical-AI-Risk-Taxonomy/data/l4_cards.json"),
    )
    parser.add_argument(
        "--physical-migrations",
        type=Path,
        default=Path("/Users/deep1003/data3/Physical-AI-Risk-Taxonomy/data/taxonomy_migrations.json"),
    )
    parser.add_argument(
        "--physical-references",
        type=Path,
        default=Path("/Users/deep1003/data3/Physical-AI-Risk-Taxonomy/data/l4_references.json"),
    )
    parser.add_argument(
        "--definition-source",
        type=Path,
        default=Path("/Users/deep1003/.codex/attachments/fc1a2b59-ea93-4897-9234-7cb110f0e408/pasted-text.txt"),
    )
    parser.add_argument("--release-id", default=RELEASE_ID)
    parser.add_argument("--semantic-threshold", type=float, default=0.55)
    parser.add_argument("--semantic-margin", type=float, default=0.035)
    parser.add_argument("--composite-threshold", type=float, default=0.54)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--model-revision", default=PINNED_MODEL_REVISION)
    parser.add_argument(
        "--overwrite-draft",
        action="store_true",
        help="Allow regeneration of an existing prepublication draft. Published releases are never overwritten.",
    )
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


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def git_commit(repo: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def normalize_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def mechanism_only_definition(value: str | None) -> str:
    text = normalize_text(value)
    template_markers = [
        r"\bThis L4 risk card treats\b",
        r"\bThis risk card treats\b",
        r"\bThis L4 card treats\b",
    ]
    for marker in template_markers:
        match = re.search(marker, text, flags=re.IGNORECASE)
        if match:
            text = text[: match.start()].strip(" .")
            break
    return text


def classification_text(card: dict) -> str:
    parts = [
        normalize_text(card.get("l4_label") or card.get("phrase")),
        mechanism_only_definition(card.get("definition")),
        normalize_text(card.get("evidence_title") or card.get("ref_title")),
    ]
    return ". ".join(part for part in parts if part)


def regex_hits(patterns: list[str], text: str) -> list[str]:
    return [pattern for pattern in patterns if re.search(pattern, text, flags=re.IGNORECASE)]


def model_snapshot_inventory(revision: str) -> dict:
    snapshot = Path.home() / ".cache/huggingface/hub/models--BAAI--bge-m3/snapshots" / revision
    if not snapshot.is_dir():
        raise FileNotFoundError(f"Pinned model snapshot is not cached: {snapshot}")
    entries = []
    for path in sorted(item for item in snapshot.rglob("*") if item.is_file() or item.is_symlink()):
        resolved = path.resolve()
        entries.append(
            {
                "path": str(path.relative_to(snapshot)),
                "blob": resolved.name,
                "bytes": resolved.stat().st_size,
            }
        )
    if not entries:
        raise ValueError(f"Pinned model snapshot is empty: {snapshot}")
    fingerprint = sha256_text(json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return {
        "snapshot_path": str(snapshot),
        "snapshot_file_count": len(entries),
        "snapshot_tree_fingerprint": fingerprint,
    }


def encode_texts(
    texts: list[str],
    batch_size: int,
    device: str,
    model_revision: str = PINNED_MODEL_REVISION,
) -> tuple[np.ndarray, str]:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    from sentence_transformers import SentenceTransformer
    from transformers.utils import logging as transformers_logging

    transformers_logging.set_verbosity_error()
    transformers_logging.disable_progress_bar()
    model_snapshot_inventory(model_revision)
    model = SentenceTransformer(
        MODEL_ID,
        revision=model_revision,
        local_files_only=True,
        device=device,
    )
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(vectors, dtype=np.float32), model_revision


def build_anchor_texts() -> tuple[list[str], list[tuple[str, int]]]:
    nodes = {node["node_id"]: node for node in L3_NODES}
    texts: list[str] = []
    index: list[tuple[str, int]] = []
    for l3_id in NON_PHYSICAL_L3_IDS:
        node = nodes[l3_id]
        rule = CLASSIFICATION_RULES[l3_id]
        anchors = [
            node["definition_en"],
            f"{node['label_en']}. {node['definition_ko']} {node['definition_en']}",
            rule["prototype"],
        ]
        for view, anchor in enumerate(anchors):
            texts.append(anchor)
            index.append((l3_id, view))
    return texts, index


def evaluate_rules(text: str) -> tuple[dict[str, dict], list[str]]:
    evaluations: dict[str, dict] = {}
    for l3_id in NON_PHYSICAL_L3_IDS:
        rules = CLASSIFICATION_RULES[l3_id]
        decisive = regex_hits(rules["decisive"], text)
        supporting = regex_hits(rules["supporting"], text)
        exclusions = regex_hits(rules["exclusions"], text)
        is_agentic = l3_id.startswith("RAI3-A-")
        if is_agentic:
            eligible = bool(decisive and supporting and not exclusions)
        else:
            eligible = bool((decisive or len(supporting) >= 2) and not exclusions)
        if decisive:
            rule_score = min(1.0, 0.8 + 0.1 * min(2, len(supporting)))
        elif len(supporting) >= 2:
            rule_score = min(0.7, 0.45 + 0.1 * len(supporting))
        else:
            rule_score = 0.0
        evaluations[l3_id] = {
            "eligible": eligible,
            "decisive_cues": decisive,
            "supporting_cues": supporting,
            "hard_exclusions": exclusions,
            "rule_score": round(rule_score, 6),
        }
    gap_hits = [family for family, patterns in GAP_RULES.items() if regex_hits(patterns, text)]
    return evaluations, gap_hits


def confidence_score(semantic: float, margin: float, rule_score: float, anchor_votes: int) -> float:
    # This is a transparent ranking score, not a calibrated probability.
    sem_component = max(0.0, min(1.0, (semantic - 0.35) / 0.4))
    margin_component = max(0.0, min(1.0, margin / 0.15))
    vote_component = anchor_votes / 3.0
    value = 0.5 * sem_component + 0.2 * margin_component + 0.2 * rule_score + 0.1 * vote_component
    return round(max(0.0, min(0.99, value)), 6)


def classify_nonphysical(
    cards: list[dict],
    card_vectors: np.ndarray,
    anchor_vectors: np.ndarray,
    semantic_threshold: float,
    semantic_margin_threshold: float,
    composite_threshold: float,
) -> tuple[list[dict], list[dict]]:
    n_cards = len(cards)
    n_l3 = len(NON_PHYSICAL_L3_IDS)
    anchor_tensor = anchor_vectors.reshape(n_l3, 3, -1)
    similarity = np.einsum("nd,kvd->nkv", card_vectors, anchor_tensor)
    semantic_scores = np.median(similarity, axis=2)
    view_winners = np.argmax(similarity, axis=1)
    decisions: list[dict] = []
    score_rows: list[dict] = []

    for row_index, card in enumerate(cards):
        text = card["_classification_text"]
        rule_evaluations, gap_hits = evaluate_rules(text)
        rule_scores = np.array(
            [rule_evaluations[l3_id]["rule_score"] for l3_id in NON_PHYSICAL_L3_IDS],
            dtype=np.float32,
        )
        eligible_flags = np.array(
            [rule_evaluations[l3_id]["eligible"] for l3_id in NON_PHYSICAL_L3_IDS],
            dtype=bool,
        )
        composite_scores = 0.75 * semantic_scores[row_index] + 0.20 * rule_scores + 0.05 * eligible_flags.astype(float)
        order = np.argsort(-composite_scores)
        semantic_order = np.argsort(-semantic_scores[row_index])
        top_candidates = []
        for idx in order[:5]:
            l3_id = NON_PHYSICAL_L3_IDS[int(idx)]
            top_candidates.append(
                {
                    "l3_id": l3_id,
                    "composite_score": round(float(composite_scores[idx]), 6),
                    "semantic_score": round(float(semantic_scores[row_index, idx]), 6),
                    "rule_score": round(float(rule_scores[idx]), 6),
                    "eligible": bool(eligible_flags[idx]),
                    "anchor_top1_votes": int(np.sum(view_winners[row_index] == idx)),
                }
            )

        eligible_indices = np.flatnonzero(eligible_flags)
        top_idx = int(order[0])
        top_l3_id = NON_PHYSICAL_L3_IDS[top_idx]
        top_semantic_idx = int(semantic_order[0])
        semantic_margin = float(
            semantic_scores[row_index, top_semantic_idx] - semantic_scores[row_index, semantic_order[1]]
        )
        composite_margin = float(composite_scores[order[0]] - composite_scores[order[1]])
        votes = int(np.sum(view_winners[row_index] == top_idx))
        top_rule = rule_evaluations[top_l3_id]
        text_too_short = len(mechanism_only_definition(card.get("definition"))) < 20

        reason_code: str | None = None
        if text_too_short:
            reason_code = "INSUFFICIENT_TEXT"
        elif gap_hits:
            reason_code = "PHYSICAL_OUTSIDE_LOCK" if "PHYSICAL_OUTSIDE_LOCK" in gap_hits else "GAP_SENTINEL"
        elif len(eligible_indices) == 0:
            reason_code = "NO_VALID_L3"
        elif len(eligible_indices) > 1:
            reason_code = "MULTI_MECHANISM"
        elif int(eligible_indices[0]) != top_idx or top_idx != top_semantic_idx:
            reason_code = "RULE_SEMANTIC_DISAGREEMENT"
        elif float(semantic_scores[row_index, top_idx]) < semantic_threshold:
            reason_code = "LOW_ABSOLUTE_FIT"
        elif float(composite_scores[top_idx]) < composite_threshold:
            reason_code = "LOW_ABSOLUTE_FIT"
        elif semantic_margin < semantic_margin_threshold or composite_margin < semantic_margin_threshold:
            reason_code = "LOW_MARGIN"
        elif votes < 2:
            reason_code = "ANCHOR_VIEW_DISAGREEMENT"

        accepted = reason_code is None
        confidence = confidence_score(
            float(semantic_scores[row_index, top_idx]),
            min(semantic_margin, composite_margin),
            float(rule_scores[top_idx]),
            votes,
        )
        decision = {
            "primary_l3_id": top_l3_id if accepted else None,
            "assignment_status": "algorithm_proposed" if accepted else "needs_taxonomy_decision",
            "assignment_method": "hierarchy_blind_bge_m3_rules_v1" if accepted else "open_set_abstention",
            "algorithm_run_id": RUN_ID,
            "confidence": confidence,
            "confidence_calibrated": False,
            "top_candidates": top_candidates[:3],
            "semantic_margin": round(semantic_margin, 6),
            "composite_margin": round(composite_margin, 6),
            "positive_cues_triggered": {
                l3_id: {
                    "decisive": rule_evaluations[l3_id]["decisive_cues"],
                    "supporting": rule_evaluations[l3_id]["supporting_cues"],
                }
                for l3_id in NON_PHYSICAL_L3_IDS
                if rule_evaluations[l3_id]["decisive_cues"] or rule_evaluations[l3_id]["supporting_cues"]
            },
            "hard_exclusions_triggered": {
                l3_id: rule_evaluations[l3_id]["hard_exclusions"]
                for l3_id in NON_PHYSICAL_L3_IDS
                if rule_evaluations[l3_id]["hard_exclusions"]
            },
            "gap_sentinels_triggered": gap_hits,
            "abstention_reason": reason_code,
            "rationale": (
                f"Strict rule and semantic agreement for {top_l3_id}; provisional pending human validation."
                if accepted
                else f"Open-set abstention: {reason_code}; no forced L3 placement."
            ),
            "review_status": "provisional_unreviewed" if accepted else "pending_taxonomy_decision",
            "approved_by": None,
            "approved_at": None,
            "input_text_hash": sha256_text(text),
            "input_fields": ["l4_label", "mechanism_only_definition", "evidence_title"],
            "legacy_hierarchy_used_as_feature": False,
        }
        decisions.append(decision)
        score_rows.append(
            {
                "l4_id": card["_l4_id"],
                "global_source_id": card["id"],
                "input_text_hash": sha256_text(text),
                "top1_l3_id": top_l3_id,
                "top1_semantic_score": round(float(semantic_scores[row_index, top_idx]), 6),
                "top1_composite_score": round(float(composite_scores[top_idx]), 6),
                "semantic_margin": round(semantic_margin, 6),
                "composite_margin": round(composite_margin, 6),
                "anchor_top1_votes": votes,
                "eligible_l3_ids": [NON_PHYSICAL_L3_IDS[int(i)] for i in eligible_indices],
                "gap_sentinels": gap_hits,
                "decision": decision["assignment_status"],
                "abstention_reason": reason_code,
            }
        )
    return decisions, score_rows


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


def build_registry(
    global_cards: list[dict],
    physical_by_global: dict[str, dict],
    physical_references_by_card: dict[str, list[dict]],
) -> list[dict]:
    registry: list[dict] = []
    for card in global_cards:
        physical = physical_by_global.get(card["id"])
        label_ko, physical_label_en = split_bilingual_label(physical["label"]) if physical else (None, None)
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
            for reference in physical_references_by_card.get(physical["card_id"], []):
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
        registry.append(
            {
                "l4_id": card["_l4_id"],
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
                "three_h_one_r": parse_three_h_one_r(physical.get("three_h_one_r") if physical else None),
                "references": references,
                "status": "active",
                "introduced_in": RELEASE_ID,
                "retired_in": None,
                "merged_into": None,
                "allocation_basis": "ASCII lexicographic order of frozen global source ID",
            }
        )
    return registry


def build_crosswalk_and_locks(
    global_cards: list[dict], physical_cards: list[dict]
) -> tuple[list[dict], list[dict], dict[str, dict]]:
    global_by_id = {card["id"]: card for card in global_cards}
    crosswalk: list[dict] = []
    for card in global_cards:
        crosswalk.append(
            {
                "l4_id": card["_l4_id"],
                "source_system": "global_1726",
                "source_snapshot_id": "global-20260721",
                "source_id": card["id"],
                "relationship": "canonical_source",
                "canonical_source_id": card["id"],
                "match_basis": "frozen global source record",
                "approved": True,
                "approved_by": "source_snapshot",
                "approved_at": SNAPSHOT_DATE,
            }
        )

    locks: list[dict] = []
    physical_by_global: dict[str, dict] = {}
    seen_global: set[str] = set()
    for physical in physical_cards:
        physical_id = physical["card_id"]
        canonical_id = physical_id if physical_id in global_by_id else PHYSICAL_ALIAS_TO_GLOBAL.get(physical_id)
        if canonical_id is None or canonical_id not in global_by_id:
            raise ValueError(f"Physical card has no approved global crosswalk: {physical_id}")
        if canonical_id in seen_global:
            raise ValueError(f"Multiple Physical cards map to one global card: {canonical_id}")
        seen_global.add(canonical_id)
        global_card = global_by_id[canonical_id]
        relationship = "exact_id" if physical_id == canonical_id else "explicit_alias"
        crosswalk.append(
            {
                "l4_id": global_card["_l4_id"],
                "source_system": "physical_182",
                "source_snapshot_id": "physical-20260721",
                "source_id": physical_id,
                "relationship": relationship,
                "canonical_source_id": canonical_id,
                "match_basis": (
                    "identical source ID"
                    if relationship == "exact_id"
                    else "approved bilingual label and definition equivalence; fixed alias table"
                ),
                "approved": True,
                "approved_by": "physical_taxonomy_gold",
                "approved_at": SNAPSHOT_DATE,
            }
        )
        new_l3_id = PHYSICAL_LEGACY_TO_NEW[physical["l3_id"]]
        locks.append(
            {
                "physical_card_id": physical_id,
                "global_source_id": canonical_id,
                "l4_id": global_card["_l4_id"],
                "legacy_l2_id": physical["l2_id"],
                "legacy_l2_name": physical["l2_name"],
                "legacy_l3_id": physical["l3_id"],
                "legacy_l3_name": physical["l3_name"],
                "new_l3_id": new_l3_id,
                "locked": True,
                "lock_basis": "Physical AI taxonomy gold assignment preserved",
            }
        )
        physical_by_global[canonical_id] = physical
    return crosswalk, locks, physical_by_global


def placement_for_lock(lock: dict) -> dict:
    return {
        "release_id": RELEASE_ID,
        "l4_id": lock["l4_id"],
        "primary_l3_id": lock["new_l3_id"],
        "assignment_status": "locked_physical",
        "assignment_method": "physical_gold",
        "algorithm_run_id": None,
        "confidence": None,
        "confidence_calibrated": None,
        "top_candidates": [],
        "semantic_margin": None,
        "composite_margin": None,
        "positive_cues_triggered": {},
        "hard_exclusions_triggered": {},
        "gap_sentinels_triggered": [],
        "abstention_reason": None,
        "rationale": f"Physical AI gold taxonomy {lock['legacy_l3_id']} preserved as {lock['new_l3_id']}.",
        "review_status": "approved_locked",
        "reviewers": ["physical_taxonomy_gold"],
        "decision_id": None,
        "approved_by": "physical_taxonomy_gold",
        "approved_at": SNAPSHOT_DATE,
        "input_text_hash": None,
        "input_fields": [],
        "legacy_hierarchy_used_as_feature": False,
    }


def csv_value(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return value


def write_csv(path: Path, rows: list[dict], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = columns or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key)) for key in fieldnames})


def hierarchy_path(node_id: str | None, nodes_by_id: dict[str, dict]) -> list[dict]:
    if node_id is None:
        return []
    path: list[dict] = []
    current = nodes_by_id[node_id]
    while current:
        path.append(
            {
                "node_id": current["node_id"],
                "label_en": current["label_en"],
                "label_ko": current["label_ko"],
            }
        )
        parent_id = current.get("parent_id")
        current = nodes_by_id.get(parent_id) if parent_id else None
    return list(reversed(path))


def build_site_bundle(
    release_dir: Path,
    public_dir: Path,
    nodes: list[dict],
    registry: list[dict],
    placements: list[dict],
    release_id: str = RELEASE_ID,
) -> tuple[list[dict], list[dict]]:
    nodes_by_id = {node["node_id"]: node for node in nodes}
    placement_by_l4 = {row["l4_id"]: row for row in placements}
    counts = Counter(
        row["primary_l3_id"] for row in placements if row["primary_l3_id"] is not None
    )
    hierarchy = []
    for node in nodes:
        item = dict(node)
        if node["level"] == 3:
            item["l4_count"] = counts[node["node_id"]]
        hierarchy.append(item)

    cards = []
    search_index = []
    for card in registry:
        placement = placement_by_l4[card["l4_id"]]
        site_card = {
            **card,
            "release_id": release_id,
            "primary_l3_id": placement["primary_l3_id"],
            "assignment_status": placement["assignment_status"],
            "review_status": placement["review_status"],
            "breadcrumb": hierarchy_path(placement["primary_l3_id"], nodes_by_id),
        }
        cards.append(site_card)
        search_index.append(
            {
                "l4_id": card["l4_id"],
                "l3_id": placement["primary_l3_id"],
                "assignment_status": placement["assignment_status"],
                "label": card["label_en"],
                "label_ko": card["label_ko"],
                "keywords": normalize_text(
                    f"{card['label_en']} {card.get('label_ko') or ''} {mechanism_only_definition(card.get('definition_en'))}"
                )[:1500],
            }
        )

    write_json(public_dir / "hierarchy.json", {"release_id": release_id, "nodes": hierarchy})
    write_json(public_dir / "cards.json", {"release_id": release_id, "cards": cards})
    write_json(public_dir / "search-index.json", search_index)
    write_json(release_dir / "site_cards.json", cards)
    return hierarchy, cards


def posthoc_coverage(
    global_cards: list[dict],
    placements: list[dict],
    nodes: list[dict],
    release_id: str = RELEASE_ID,
) -> tuple[dict, list[dict], list[dict], list[dict]]:
    placement_by_l4 = {row["l4_id"]: row for row in placements}
    nodes_by_id = {node["node_id"]: node for node in nodes}
    status_counts = Counter(row["assignment_status"] for row in placements)
    nonphysical_rows = [row for row in placements if row["assignment_status"] != "locked_physical"]
    nonphysical_status = Counter(row["assignment_status"] for row in nonphysical_rows)
    l3_rows = []
    for node in [item for item in nodes if item["level"] == 3]:
        relevant = [row for row in placements if row["primary_l3_id"] == node["node_id"]]
        l3_rows.append(
            {
                "l3_id": node["node_id"],
                "l2_id": node["parent_id"],
                "label_en": node["label_en"],
                "label_ko": node["label_ko"],
                "card_count": len(relevant),
                "locked_physical": sum(row["assignment_status"] == "locked_physical" for row in relevant),
                "algorithm_proposed": sum(row["assignment_status"] == "algorithm_proposed" for row in relevant),
                "human_approved": sum(row["assignment_status"] == "human_approved" for row in relevant),
            }
        )

    legacy_transition = Counter()
    unresolved_rows = []
    gap_counts = Counter()
    for card in global_cards:
        placement = placement_by_l4[card["_l4_id"]]
        target = placement["primary_l3_id"] or "needs_taxonomy_decision"
        legacy_transition[(card.get("l1"), card.get("l2"), card.get("l3"), target)] += 1
        if placement["assignment_status"] == "needs_taxonomy_decision":
            for family in placement["gap_sentinels_triggered"]:
                gap_counts[family] += 1
            unresolved_rows.append(
                {
                    "decision_id": placement["decision_id"],
                    "l4_id": card["_l4_id"],
                    "global_source_id": card["id"],
                    "label": card.get("l4_label"),
                    "mechanism_definition": mechanism_only_definition(card.get("definition")),
                    "abstention_reason": placement["abstention_reason"],
                    "gap_sentinels": placement["gap_sentinels_triggered"],
                    "top_candidates": placement["top_candidates"],
                    "confidence": placement["confidence"],
                    "legacy_l1_reference_only": card.get("l1"),
                    "legacy_l2_reference_only": card.get("l2"),
                    "legacy_l3_reference_only": card.get("l3"),
                }
            )

    transition_rows = [
        {
            "legacy_l1_reference_only": key[0],
            "legacy_l2_reference_only": key[1],
            "legacy_l3_reference_only": key[2],
            "new_l3_or_state": key[3],
            "card_count": count,
        }
        for key, count in sorted(legacy_transition.items(), key=lambda item: (-item[1], str(item[0])))
    ]
    summary = {
        "release_id": release_id,
        "total_l4": len(placements),
        "physical_locked": status_counts["locked_physical"],
        "nonphysical_total": len(nonphysical_rows),
        "algorithm_proposed": status_counts["algorithm_proposed"],
        "human_approved": status_counts["human_approved"],
        "needs_taxonomy_decision": status_counts["needs_taxonomy_decision"],
        "provisional_hard_coverage_rate": round(
            (status_counts["locked_physical"] + status_counts["algorithm_proposed"] + status_counts["human_approved"])
            / len(placements),
            6,
        ),
        "nonphysical_provisional_coverage_rate": round(
            nonphysical_status["algorithm_proposed"] / max(1, len(nonphysical_rows)), 6
        ),
        "nonphysical_abstention_rate": round(
            nonphysical_status["needs_taxonomy_decision"] / max(1, len(nonphysical_rows)), 6
        ),
        "strict_human_validated_coverage_rate": round(status_counts["locked_physical"] / len(placements), 6),
        "confidence_is_calibrated": False,
        "fifty_l3_sufficiency_status": (
            "NOT_DEMONSTRATED" if status_counts["needs_taxonomy_decision"] else "PENDING_HUMAN_VALIDATION"
        ),
        "gap_sentinel_counts": dict(sorted(gap_counts.items())),
        "notes": [
            "Algorithm-proposed placements are provisional and are not human-approved.",
            "Legacy global hierarchy is used only in the transition audit after placement.",
            "Any unresolved card remains outside the 50 L3 until a taxonomy decision is approved.",
        ],
    }
    return summary, l3_rows, transition_rows, unresolved_rows


def unresolved_clusters(
    unresolved_rows: list[dict],
    unresolved_vectors: np.ndarray,
    global_by_l4: dict[str, dict],
) -> tuple[list[dict], list[dict], dict]:
    if len(unresolved_rows) < 4:
        return [], [], {"cluster_count": 0, "reason": "fewer than four unresolved cards"}
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics import adjusted_rand_score

    n_clusters = min(20, max(4, int(round(math.sqrt(len(unresolved_rows) / 2)))))
    seeds = [SEED, SEED + 1, SEED + 2]
    bge_labels = []
    models = []
    for seed in seeds:
        model = KMeans(n_clusters=n_clusters, random_state=seed, n_init=20)
        bge_labels.append(model.fit_predict(unresolved_vectors))
        models.append(model)
    base_labels = bge_labels[0]
    stability = [adjusted_rand_score(base_labels, labels) for labels in bge_labels[1:]]

    texts = [
        normalize_text(f"{row['label']} {row['mechanism_definition']}") for row in unresolved_rows
    ]
    tfidf = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=2, max_features=15000)
    tfidf_matrix = tfidf.fit_transform(texts)
    tfidf_labels = KMeans(n_clusters=n_clusters, random_state=SEED, n_init=20).fit_predict(tfidf_matrix)
    cross_view_ari = adjusted_rand_score(base_labels, tfidf_labels)

    centers = models[0].cluster_centers_
    cluster_rows: list[dict] = []
    card_rows: list[dict] = []
    for cluster_id in range(n_clusters):
        positions = np.flatnonzero(base_labels == cluster_id)
        if not len(positions):
            continue
        center = centers[cluster_id]
        distances = np.linalg.norm(unresolved_vectors[positions] - center, axis=1)
        representative_positions = positions[np.argsort(distances)[:5]]
        representatives = [
            {
                "l4_id": unresolved_rows[int(pos)]["l4_id"],
                "label": unresolved_rows[int(pos)]["label"],
            }
            for pos in representative_positions
        ]
        gap_counter = Counter(
            gap
            for pos in positions
            for gap in unresolved_rows[int(pos)]["gap_sentinels"]
        )
        legacy_counter = Counter(
            global_by_l4[unresolved_rows[int(pos)]["l4_id"]].get("l3") for pos in positions
        )
        reason_counter = Counter(unresolved_rows[int(pos)]["abstention_reason"] for pos in positions)
        cluster_rows.append(
            {
                "cluster_id": f"UC-{cluster_id + 1:02d}",
                "card_count": int(len(positions)),
                "representative_cards": representatives,
                "dominant_gap_sentinels": gap_counter.most_common(5),
                "dominant_abstention_reasons": reason_counter.most_common(5),
                "dominant_legacy_l3_reference_only": legacy_counter.most_common(5),
                "taxonomy_decision_candidate": bool(len(positions) >= 3),
            }
        )
        for pos in positions:
            row = unresolved_rows[int(pos)]
            card_rows.append(
                {
                    "cluster_id": f"UC-{cluster_id + 1:02d}",
                    "tfidf_cluster_id": f"TC-{int(tfidf_labels[int(pos)]) + 1:02d}",
                    "l4_id": row["l4_id"],
                    "global_source_id": row["global_source_id"],
                    "label": row["label"],
                    "abstention_reason": row["abstention_reason"],
                    "gap_sentinels": row["gap_sentinels"],
                }
            )
    diagnostics = {
        "cluster_count": n_clusters,
        "method_primary": "BGE-M3 normalized embeddings with KMeans",
        "method_secondary": "word/bigram TF-IDF with KMeans",
        "seeds": seeds,
        "bge_bootstrap_adjusted_rand_index": [round(value, 6) for value in stability],
        "bge_tfidf_adjusted_rand_index": round(cross_view_ari, 6),
        "interpretation": "Clusters are discovery aids, not approved new L3 categories.",
    }
    return cluster_rows, card_rows, diagnostics


def artifact_rows(base: Path, paths: list[Path]) -> list[dict]:
    rows = []
    for path in sorted(paths):
        if not path.is_file():
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
            except (json.JSONDecodeError, OSError):
                pass
        rows.append(
            {
                "path": str(path.relative_to(base)),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "rows": row_count,
            }
        )
    return rows


def main() -> None:
    args = parse_args()
    if args.release_id != RELEASE_ID:
        raise ValueError(f"Codebook release is frozen to {RELEASE_ID}; got {args.release_id}")
    if args.model_revision != PINNED_MODEL_REVISION:
        raise ValueError(
            f"Model revision is frozen to {PINNED_MODEL_REVISION}; got {args.model_revision}"
        )
    for path in [
        args.global_source,
        args.physical_source,
        args.physical_references,
        args.definition_source,
    ]:
        if not path.is_file():
            raise FileNotFoundError(path)

    release_dir = PROJECT_ROOT / "data" / "releases" / RELEASE_ID
    source_dir = PROJECT_ROOT / "data" / "source_snapshots" / RELEASE_ID
    public_dir = PROJECT_ROOT / "public" / "data" / "releases" / RELEASE_ID
    validation_dir = PROJECT_ROOT / "reports" / "validation" / RELEASE_ID
    if release_dir.exists() and any(release_dir.iterdir()):
        manifest_path = release_dir / "manifest.json"
        existing_status = read_json(manifest_path).get("release_status") if manifest_path.is_file() else None
        if existing_status == "published":
            raise FileExistsError(f"Published release is immutable: {release_dir}")
        if not args.overwrite_draft:
            raise FileExistsError(
                f"Draft release already exists: {release_dir}. Use --overwrite-draft only for deliberate regeneration."
            )
    for path in [release_dir, source_dir, public_dir, validation_dir]:
        path.mkdir(parents=True, exist_ok=True)

    snapshot_targets = {
        args.global_source: source_dir / "global_ai_risk_l4_overlay_nodes.json",
        args.physical_source: source_dir / "physical_l4_cards.json",
        args.physical_references: source_dir / "physical_l4_references.json",
        args.definition_source: source_dir / "l0_l3_definition_source.txt",
    }
    if args.physical_migrations.is_file():
        snapshot_targets[args.physical_migrations] = source_dir / "physical_taxonomy_migrations.json"
    for source, destination in snapshot_targets.items():
        shutil.copy2(source, destination)

    global_cards = read_json(args.global_source)
    physical_cards = read_json(args.physical_source)
    physical_references = read_json(args.physical_references)
    if len(global_cards) != 1726 or len({row["id"] for row in global_cards}) != 1726:
        raise ValueError("Global source must contain 1,726 unique IDs")
    if len(physical_cards) != 182 or len({row["card_id"] for row in physical_cards}) != 182:
        raise ValueError("Physical source must contain 182 unique IDs")
    physical_ids = {row["card_id"] for row in physical_cards}
    if {row["card_id"] for row in physical_references} != physical_ids:
        raise ValueError("Physical references must cover the same 182 Physical card IDs")
    physical_references_by_card: dict[str, list[dict]] = defaultdict(list)
    for reference in physical_references:
        physical_references_by_card[reference["card_id"]].append(reference)

    sorted_global = sorted(global_cards, key=lambda row: row["id"])
    for number, card in enumerate(sorted_global, start=1):
        card["_l4_id"] = f"RAI4-{number:04d}"
        card["_classification_text"] = classification_text(card)

    crosswalk, physical_locks, physical_by_global = build_crosswalk_and_locks(
        sorted_global, physical_cards
    )
    locked_global_ids = {row["global_source_id"] for row in physical_locks}
    nonphysical_cards = [row for row in sorted_global if row["id"] not in locked_global_ids]

    anchor_texts, anchor_index = build_anchor_texts()
    texts_to_encode = [row["_classification_text"] for row in nonphysical_cards] + anchor_texts
    vectors, model_revision = encode_texts(
        texts_to_encode,
        args.batch_size,
        args.device,
        model_revision=args.model_revision,
    )
    card_vectors = vectors[: len(nonphysical_cards)]
    anchor_vectors = vectors[len(nonphysical_cards) :]
    decisions, score_rows = classify_nonphysical(
        nonphysical_cards,
        card_vectors,
        anchor_vectors,
        args.semantic_threshold,
        args.semantic_margin,
        args.composite_threshold,
    )

    placement_by_l4 = {
        lock["l4_id"]: placement_for_lock(lock) for lock in physical_locks
    }
    decision_number = 0
    for card, decision in zip(nonphysical_cards, decisions, strict=True):
        placement = {
            "release_id": RELEASE_ID,
            "l4_id": card["_l4_id"],
            **decision,
            "reviewers": [],
            "decision_id": None,
        }
        if placement["assignment_status"] == "needs_taxonomy_decision":
            decision_number += 1
            placement["decision_id"] = f"TD-{decision_number:04d}"
        placement_by_l4[card["_l4_id"]] = placement
    placements = [placement_by_l4[row["_l4_id"]] for row in sorted_global]

    nodes = UPPER_NODES + L3_NODES
    registry = build_registry(sorted_global, physical_by_global, physical_references_by_card)
    write_json(release_dir / "taxonomy_nodes.json", nodes)
    write_json(release_dir / "l4_registry.json", registry)
    write_json(release_dir / "source_crosswalk.json", crosswalk)
    write_json(release_dir / "physical_lock.json", physical_locks)
    write_json(release_dir / "placements.json", placements)
    write_json(release_dir / "placement_migrations.json", [])
    write_json(release_dir / "algorithm_scores.json", score_rows)

    write_csv(release_dir / "taxonomy_nodes.csv", nodes)
    write_csv(release_dir / "l4_registry.csv", registry)
    write_csv(release_dir / "source_crosswalk.csv", crosswalk)
    write_csv(release_dir / "physical_lock.csv", physical_locks)
    write_csv(release_dir / "placements.csv", placements)
    write_csv(release_dir / "algorithm_scores.csv", score_rows)

    _, site_cards = build_site_bundle(release_dir, public_dir, nodes, registry, placements)
    coverage_summary, l3_rows, transition_rows, unresolved_rows = posthoc_coverage(
        sorted_global, placements, nodes
    )
    write_json(validation_dir / "coverage_summary.json", coverage_summary)
    write_csv(validation_dir / "l3_distribution.csv", l3_rows)
    write_csv(validation_dir / "legacy_to_new_transition_reference_only.csv", transition_rows)
    write_json(validation_dir / "unresolved_cards.json", unresolved_rows)
    write_csv(validation_dir / "unresolved_cards.csv", unresolved_rows)

    unresolved_l4_ids = {row["l4_id"] for row in unresolved_rows}
    unresolved_positions = [
        index
        for index, card in enumerate(nonphysical_cards)
        if card["_l4_id"] in unresolved_l4_ids
    ]
    global_by_l4 = {row["_l4_id"]: row for row in sorted_global}
    cluster_rows, cluster_card_rows, cluster_diagnostics = unresolved_clusters(
        unresolved_rows,
        card_vectors[unresolved_positions],
        global_by_l4,
    )
    write_json(validation_dir / "unresolved_clusters.json", cluster_rows)
    write_csv(validation_dir / "unresolved_cluster_cards.csv", cluster_card_rows)
    write_json(validation_dir / "unresolved_cluster_diagnostics.json", cluster_diagnostics)

    codebook_path = PROJECT_ROOT / "src" / "rai_taxonomy" / "codebook.py"
    snapshot_inventory = model_snapshot_inventory(model_revision)
    algorithm_config = {
        "configuration_version": "1.0.0",
        "release_id": RELEASE_ID,
        "model_id": MODEL_ID,
        "model_revision": model_revision,
        "model_revision_pinned": True,
        **snapshot_inventory,
        "seed": SEED,
        "codebook_version": CODEBOOK_VERSION,
        "codebook_sha256": sha256_file(codebook_path),
        "input_fields": ["l4_label", "mechanism_only_definition", "evidence_title"],
        "excluded_predictive_fields": [
            "global l0",
            "global l1",
            "global l2",
            "global l3",
            "source family",
            "source ID prefix",
        ],
        "thresholds": {
            "semantic": args.semantic_threshold,
            "semantic_margin": args.semantic_margin,
            "composite": args.composite_threshold,
            "anchor_top1_votes": 2,
        },
        "ranking_weights": {"semantic": 0.75, "rule": 0.20, "eligibility": 0.05},
        "normalize_embeddings": True,
        "semantic_aggregation": "median cosine across definition, bilingual definition, and prototype anchors",
        "rule_eligibility": "one decisive cue or two supporting cues; Agentic requires decisive plus supporting; hard exclusions override",
    }
    configuration_sha256 = sha256_text(
        json.dumps(algorithm_config, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    write_json(release_dir / "algorithm_config.json", algorithm_config)
    run_record = {
        "algorithm_run_id": RUN_ID,
        "release_id": RELEASE_ID,
        "created_at": CREATED_AT,
        "classification_scope": "1,544 non-Physical global cards",
        "physical_cards": "182 locked before classification",
        "input_fields": ["l4_label", "mechanism_only_definition", "evidence_title"],
        "excluded_predictive_fields": ["global l0", "global l1", "global l2", "global l3", "source family", "source ID prefix"],
        "legacy_hierarchy_used_as_feature": False,
        "model_id": MODEL_ID,
        "model_revision": model_revision,
        "model_revision_pinned": True,
        **snapshot_inventory,
        "configuration_file": f"data/releases/{RELEASE_ID}/algorithm_config.json",
        "configuration_sha256": configuration_sha256,
        "embedding_dimension": int(card_vectors.shape[1]),
        "normalize_embeddings": True,
        "semantic_aggregation": "median cosine across definition, bilingual definition, and prototype anchors",
        "rule_eligibility": "one decisive cue or two supporting cues; Agentic requires decisive plus supporting; hard exclusions override",
        "thresholds": {
            "semantic": args.semantic_threshold,
            "semantic_margin": args.semantic_margin,
            "composite": args.composite_threshold,
            "anchor_top1_votes": 2,
        },
        "ranking_weights": {"semantic": 0.75, "rule": 0.20, "eligibility": 0.05},
        "confidence_calibrated": False,
        "seed": SEED,
        "codebook_version": CODEBOOK_VERSION,
        "codebook_sha256": sha256_file(codebook_path),
        "anchor_index": [{"l3_id": l3_id, "view": view} for l3_id, view in anchor_index],
        "acceptance_policy": "algorithm_proposed only; human validation required",
    }
    write_json(release_dir / "algorithm_run.json", run_record)

    write_json(
        PROJECT_ROOT / "data" / "current.json",
        {
            "current_release": RELEASE_ID,
            "release_status": "prepublication_draft",
            "manifest": f"data/releases/{RELEASE_ID}/manifest.json",
        },
    )

    source_manifest = [
        {
            "name": "global_1726",
            "path": str(snapshot_targets[args.global_source].relative_to(PROJECT_ROOT)),
            "sha256": sha256_file(args.global_source),
            "record_count": len(global_cards),
            "source_git_commit": git_commit(args.global_source.parents[1]),
        },
        {
            "name": "physical_182",
            "path": str(snapshot_targets[args.physical_source].relative_to(PROJECT_ROOT)),
            "sha256": sha256_file(args.physical_source),
            "record_count": len(physical_cards),
            "source_git_commit": git_commit(args.physical_source.parents[1]),
        },
        {
            "name": "physical_l4_references",
            "path": str(snapshot_targets[args.physical_references].relative_to(PROJECT_ROOT)),
            "sha256": sha256_file(args.physical_references),
            "record_count": len(physical_references),
            "source_git_commit": git_commit(args.physical_references.parents[1]),
        },
        {
            "name": "l0_l3_definition_source",
            "path": str(snapshot_targets[args.definition_source].relative_to(PROJECT_ROOT)),
            "sha256": sha256_file(args.definition_source),
            "record_count": 50,
            "source_git_commit": None,
        },
    ]
    if args.physical_migrations.is_file():
        source_manifest.append(
            {
                "name": "physical_taxonomy_migrations",
                "path": str(snapshot_targets[args.physical_migrations].relative_to(PROJECT_ROOT)),
                "sha256": sha256_file(args.physical_migrations),
                "record_count": len(read_json(args.physical_migrations)),
                "source_git_commit": git_commit(args.physical_migrations.parents[1]),
            }
        )

    artifact_paths = [
        path
        for root in [release_dir, public_dir, validation_dir]
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"manifest.json", "checksums.sha256"}
    ]
    artifacts = artifact_rows(PROJECT_ROOT, artifact_paths)
    status_counts = Counter(row["assignment_status"] for row in placements)
    manifest = {
        "release_id": RELEASE_ID,
        "release_status": "prepublication_draft",
        "provisional": True,
        "schema_version": "1.0.0",
        "created_at": CREATED_AT,
        "git_commit": None,
        "sources": source_manifest,
        "id_allocation": {
            "l4_pattern": "RAI4-####",
            "ordering": "ASCII lexicographic sort of frozen global source ID",
            "first_id": "RAI4-0001",
            "last_id": "RAI4-1726",
            "never_reuse": True,
        },
        "counts": {
            "l0": 1,
            "l1": 3,
            "l2": 6,
            "l3": 50,
            "l4": len(registry),
            "physical_locked": status_counts["locked_physical"],
            "source_exact_matches": sum(row["relationship"] == "exact_id" for row in crosswalk),
            "source_explicit_aliases": sum(row["relationship"] == "explicit_alias" for row in crosswalk),
            "algorithm_proposed": status_counts["algorithm_proposed"],
            "human_approved": status_counts["human_approved"],
            "needs_taxonomy_decision": status_counts["needs_taxonomy_decision"],
        },
        "algorithm": {
            "run_id": RUN_ID,
            "model": MODEL_ID,
            "model_revision": model_revision,
            "model_revision_pinned": True,
            "seed": SEED,
            "configuration_file": f"data/releases/{RELEASE_ID}/algorithm_config.json",
            "configuration_sha256": configuration_sha256,
            "confidence_calibrated": False,
        },
        "artifacts": artifacts,
        "validation": {
            "status": "PENDING_VALIDATOR",
            "report": f"reports/validation/{RELEASE_ID}/validation_summary.json",
        },
        "approvals": [
            {"scope": "Physical 182 lock", "status": "approved_source_gold"},
            {"scope": "Non-Physical algorithm proposals", "status": "pending_human_validation"},
        ],
    }
    write_json(release_dir / "manifest.json", manifest)
    write_json(public_dir / "manifest.json", manifest)

    checksums_path = validation_dir / "checksums.sha256"
    checksum_lines = [
        f"{row['sha256']}  {row['path']}" for row in artifact_rows(PROJECT_ROOT, artifact_paths + [release_dir / "manifest.json", public_dir / "manifest.json"])
    ]
    checksums_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "release": RELEASE_ID,
                "l4": len(registry),
                "physical_locked": status_counts["locked_physical"],
                "algorithm_proposed": status_counts["algorithm_proposed"],
                "needs_taxonomy_decision": status_counts["needs_taxonomy_decision"],
                "site_cards": len(site_cards),
                "output": str(release_dir),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
