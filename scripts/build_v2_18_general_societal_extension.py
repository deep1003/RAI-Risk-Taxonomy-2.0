#!/usr/bin/env python3
"""Build the sealed v2.18.0-rc General AI hierarchy extension.

The builder never modifies the source release. It creates a new release,
records the old-to-new hierarchy mapping, and optionally writes a sealed
archive of the complete source release.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import tarfile
from collections import Counter
from copy import deepcopy
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/data/releases/v2.17.2"
CONFIG = ROOT / "config/v2.18.0-rc_general_societal_extension.json"
DEFAULT_OUT = ROOT / "public/data/releases/v2.18.0-rc"
DEFAULT_REPORT = ROOT / "reports/validation/v2.18.0-rc/general_societal_extension"
EMBEDDING_ROOT = (
    ROOT
    / "reports/validation/v2.17.2"
    / "full_mapping_sensitivity_bge_m3_20260724"
)
MODEL_SNAPSHOT = Path(
    "/Users/deep1003/.cache/huggingface/hub/"
    "models--BAAI--bge-m3/snapshots/"
    "5617a9f61b028005a4858fdac845db406aefb181"
)
SEED = 20260725
MAX_ITER = 30


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def current_semantic_l3(card: dict) -> str:
    primary = card.get("primary_l3_id") or ""
    if "HLD" in primary:
        semantic = card.get("hold_semantic_path") or {}
        return semantic.get("l3_id") or card.get("forced_candidate_l3_id") or ""
    return primary


def card_text(card: dict) -> str:
    return " ".join(
        value.strip()
        for value in (
            card.get("label_en", ""),
            card.get("definition_en", ""),
            card.get("label_ko", ""),
            card.get("definition_ko", ""),
        )
        if value and value.strip()
    )


def seed_text(node: dict) -> str:
    return " ".join(
        value.strip()
        for value in (
            node.get("label_en", ""),
            node.get("definition_en", ""),
            node.get("label_ko", ""),
            node.get("definition_ko", ""),
        )
        if value and value.strip()
    )


def load_card_embeddings(cards: list[dict]) -> np.ndarray:
    index_path = EMBEDDING_ROOT / "index.json"
    embeddings_path = EMBEDDING_ROOT / "card_embeddings.npy"
    if index_path.exists() and embeddings_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
        positions = {l4_id: i for i, l4_id in enumerate(index["l4_ids"])}
        if all(card["l4_id"] in positions for card in cards):
            embeddings = np.load(embeddings_path)
            return embeddings[
                [positions[card["l4_id"]] for card in cards]
            ].astype("float32")
    model = SentenceTransformer(str(MODEL_SNAPSHOT), device="mps")
    return model.encode(
        [card_text(card) for card in cards],
        batch_size=24,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).astype("float32")


def encode_seeds(nodes: list[dict]) -> np.ndarray:
    model = SentenceTransformer(str(MODEL_SNAPSHOT), device="mps")
    return model.encode(
        [seed_text(node) for node in nodes],
        batch_size=24,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).astype("float32")


def migrated_hierarchy(
    source_payload: dict, config: dict
) -> tuple[dict, dict[str, str], list[dict]]:
    payload = deepcopy(source_payload)
    nodes = payload["nodes"]
    spec_reference = {
        "title": "General AI L2 and L3 Extension Specification",
        "type": "User-provided taxonomy specification",
        "source_system": "taxonomy_extension_20260725",
        "url": config["source_spec"],
    }
    migration = {
        f"RAI3-P-SOC-{sequence:02d}": f"RAI3-G-SOC-{sequence:02d}"
        for sequence in range(1, 10)
    }
    retired_nodes = [
        deepcopy(node)
        for node in nodes
        if node["node_id"] == "RAI2-P-SOC"
        or node["node_id"] in migration
    ]
    kept = [
        node
        for node in nodes
        if node["node_id"] != "RAI2-P-SOC"
        and node["node_id"] not in migration
    ]
    new_l2 = deepcopy(config["new_l2"])
    new_l2.update(
        {
            "status": "active",
            "canonical_l2_id": "RAI2-SOC",
            "references": [spec_reference],
        }
    )
    kept.append(new_l2)
    for node in kept:
        if node["node_id"] == "RAI2-G-HLD":
            node["sequence"] = 4
    old_by_id = {node["node_id"]: node for node in retired_nodes}
    for old_id, new_id in migration.items():
        old = deepcopy(old_by_id[old_id])
        old["node_id"] = new_id
        old["parent_id"] = "RAI2-G-SOC"
        old["introduced_in"] = config["release_id"]
        old["migrated_from_node_id"] = old_id
        old["scope_origin"] = "Physical AI Societal Safety"
        old["legacy_ids"] = list(
            dict.fromkeys([*(old.get("legacy_ids") or []), old_id])
        )
        old["references"] = [
            *(old.get("references") or []),
            spec_reference,
        ]
        kept.append(old)
    for node in config["new_l3"]:
        created = deepcopy(node)
        created.update(
            {
                "status": "active",
                "three_h_source": {
                    "Harmlessness": "무해성",
                    "Honesty": "사실성",
                }.get(created.pop("three_h_attribute"), "무해성"),
                "three_h_property": {
                    "Harmlessness": "harmlessness",
                    "Honesty": "honesty",
                }.get(node["three_h_attribute"], "harmlessness"),
                "evaluation_types": ["impact"],
                "mitigation_policy": None,
                "legacy_ids": [],
                "deprecated_in": None,
                "superseded_by": None,
                "l4_count": 0,
                "references": [spec_reference],
            }
        )
        kept.append(created)
    kept.sort(
        key=lambda node: (
            node["level"],
            node.get("parent_id") or "",
            node.get("sequence", 0),
            node["node_id"],
        )
    )
    payload["release_id"] = config["release_id"]
    payload["nodes"] = kept
    for category in payload.get("canonical_l2_categories", []):
        if category.get("category_id") == "RAI2-SOC":
            category["label_en"] = "Societal Impact"
            category["label_ko"] = "사회적 파급"
            category["path_node_ids"] = ["RAI2-G-SOC"]
    retired_l3 = payload.setdefault("retired_l3_archive", [])
    for old_id, new_id in migration.items():
        old = deepcopy(old_by_id[old_id])
        old.update(
            {
                "status": "retired",
                "retired_in": config["release_id"],
                "retirement_reason": (
                    "migrated from Physical AI Societal Safety to "
                    "General AI Societal Impact"
                ),
                "superseded_by": new_id,
                "id_reuse_prohibited": True,
            }
        )
        retired_l3.append(old)
    old_l2 = deepcopy(old_by_id["RAI2-P-SOC"])
    old_l2.update(
        {
            "status": "retired",
            "retired_in": config["release_id"],
            "retirement_reason": (
                "child families migrated to General AI Societal Impact"
            ),
            "superseded_by": "RAI2-G-SOC",
            "id_reuse_prohibited": True,
        }
    )
    payload.setdefault("retired_l2_archive", []).append(old_l2)
    return payload, migration, retired_nodes


def semantic_nodes(hierarchy: dict) -> list[dict]:
    return [
        node
        for node in hierarchy["nodes"]
        if node["level"] == 3
        and node.get("status") == "active"
        and "HLD" not in node["node_id"]
    ]


def compute_centers(
    embeddings: np.ndarray,
    assignment: np.ndarray,
    seeds: np.ndarray,
    prior_members: dict[int, np.ndarray],
) -> np.ndarray:
    centers = np.zeros_like(seeds, dtype="float32")
    for family in range(len(seeds)):
        members = embeddings[assignment == family]
        prior = prior_members.get(family)
        if len(members):
            mean = normalize(members.mean(axis=0, keepdims=True))[0]
            if prior is not None and len(prior):
                prior_mean = normalize(prior.mean(axis=0, keepdims=True))[0]
                center = 0.75 * mean + 0.15 * seeds[family] + 0.10 * prior_mean
            else:
                center = 0.85 * mean + 0.15 * seeds[family]
        elif prior is not None and len(prior):
            prior_mean = normalize(prior.mean(axis=0, keepdims=True))[0]
            center = 0.60 * prior_mean + 0.40 * seeds[family]
        else:
            center = seeds[family]
        centers[family] = center / np.linalg.norm(center)
    return centers


def allowed_mask(
    card: dict,
    family_ids: list[str],
    source_semantic: str,
    agentic_text: bool,
) -> np.ndarray:
    if (
        source_semantic.startswith("RAI3-P-SYS")
        or source_semantic.startswith("RAI3-P-INT")
    ):
        return np.array(
            [family_id == source_semantic for family_id in family_ids],
            dtype=bool,
        )
    mask = np.array(
        [not family_id.startswith("RAI3-P-") for family_id in family_ids],
        dtype=bool,
    )
    if not agentic_text and not source_semantic.startswith("RAI3-A-"):
        mask &= np.array(
            [not family_id.startswith("RAI3-A-") for family_id in family_ids],
            dtype=bool,
        )
    return mask


def run_winner_assignment(
    cards: list[dict],
    nodes: list[dict],
    migration: dict[str, str],
    candidate_priors: dict[str, list[str]],
    embeddings: np.ndarray,
    seed_embeddings: np.ndarray,
    epsilon: float,
) -> tuple[np.ndarray, np.ndarray, list[dict], np.ndarray, np.ndarray]:
    family_ids = [node["node_id"] for node in nodes]
    family_index = {family_id: i for i, family_id in enumerate(family_ids)}
    source_semantic = [
        migration.get(current_semantic_l3(card), current_semantic_l3(card))
        for card in cards
    ]
    missing = sorted(set(source_semantic) - set(family_ids))
    if missing:
        raise ValueError(f"Unknown semantic L3 IDs after migration: {missing}")
    source_assignment = np.array(
        [family_index[family_id] for family_id in source_semantic], dtype=int
    )
    assignment = source_assignment.copy()
    texts_en = [
        f"{card.get('label_en', '')}. {card.get('definition_en', '')}"
        for card in cards
    ]
    seed_texts_en = [
        f"{node.get('label_en', '')}. {node.get('definition_en', '')}"
        for node in nodes
    ]
    vectorizer = TfidfVectorizer(
        lowercase=True, stop_words="english", max_features=25000
    )
    tfidf = vectorizer.fit_transform(texts_en + seed_texts_en)
    keyword = (
        normalize(tfidf[: len(cards)])
        @ normalize(tfidf[len(cards) :]).T
    ).toarray()
    direct = embeddings @ seed_embeddings.T
    positions = {card["l4_id"]: i for i, card in enumerate(cards)}
    prior_members: dict[int, np.ndarray] = {}
    explicit_ids: set[str] = set()
    for family_id, l4_ids in candidate_priors.items():
        family = family_index[family_id]
        rows = [
            positions[l4_id]
            for l4_id in l4_ids
            if l4_id in positions
        ]
        explicit_ids.update(l4_ids)
        if rows:
            prior_members[family] = embeddings[rows]
    agentic_pattern = re.compile(
        r"\b(agent|agentic|autonomous|multi-agent|tool call|planning|"
        r"memory|orchestrat|collusion|agent chain)\b",
        re.I,
    )
    agentic_ok = [
        bool(agentic_pattern.search(text)) for text in texts_en
    ]
    events: list[dict] = []
    final_score = np.zeros((len(cards), len(nodes)), dtype="float32")
    for iteration in range(1, MAX_ITER + 1):
        centers = compute_centers(
            embeddings, assignment, seed_embeddings, prior_members
        )
        score = (
            0.60 * (embeddings @ centers.T)
            + 0.30 * direct
            + 0.10 * keyword
        )
        next_assignment = assignment.copy()
        changed = 0
        for row, card in enumerate(cards):
            mask = allowed_mask(
                card, family_ids, source_semantic[row], agentic_ok[row]
            )
            allowed = np.flatnonzero(mask)
            winner = allowed[np.argmax(score[row, allowed])]
            current = assignment[row]
            if score[row, winner] <= score[row, current] + epsilon:
                continue
            source_id = family_ids[source_assignment[row]]
            winner_id = family_ids[winner]
            in_explicit_scope = card["l4_id"] in explicit_ids
            is_structural_scope = source_id in migration.values()
            if in_explicit_scope or is_structural_scope:
                next_assignment[row] = winner
                changed += int(winner != current)
        events.append(
            {
                "iteration": iteration,
                "changed_cards": changed,
            }
        )
        assignment = next_assignment
        final_score = score
        if changed == 0:
            break
    centers = compute_centers(
        embeddings, assignment, seed_embeddings, prior_members
    )
    final_score = (
        0.60 * (embeddings @ centers.T)
        + 0.30 * direct
        + 0.10 * keyword
    )
    return assignment, source_assignment, events, final_score, direct


def node_path(node_id: str, nodes_by_id: dict[str, dict]) -> list[dict]:
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


def update_cards(
    cards_payload: dict,
    hierarchy: dict,
    active_cards: list[dict],
    nodes: list[dict],
    migration: dict[str, str],
    assignment: np.ndarray,
    source_assignment: np.ndarray,
    scores: np.ndarray,
    direct: np.ndarray,
    config: dict,
) -> tuple[dict, list[dict], list[dict]]:
    payload = deepcopy(cards_payload)
    payload["release_id"] = config["release_id"]
    payload["source_release"] = config["source_release"]
    family_ids = [node["node_id"] for node in nodes]
    nodes_by_id = {
        node["node_id"]: node for node in hierarchy["nodes"]
    }
    active_position = {
        card["l4_id"]: position
        for position, card in enumerate(active_cards)
    }
    thresholds = config["hold_release_thresholds"]
    explicit_ids = {
        l4_id
        for ids in config["candidate_priors"].values()
        for l4_id in ids
    }
    changes: list[dict] = []
    remaining_hold: list[dict] = []
    for card in payload["cards"]:
        card["release_id"] = config["release_id"]
        old_primary = card.get("primary_l3_id") or ""
        if card.get("status") != "active":
            if old_primary in migration:
                new_primary = migration[old_primary]
                card["previous_primary_l3_id"] = old_primary
                card["primary_l3_id"] = new_primary
                card["breadcrumb"] = node_path(new_primary, nodes_by_id)
                card["v2_18_reclassification"] = {
                    "type": "structural_l3_migration",
                    "from_l3_id": old_primary,
                    "to_l3_id": new_primary,
                }
            continue
        row = active_position[card["l4_id"]]
        winner = int(assignment[row])
        source = int(source_assignment[row])
        winner_id = family_ids[winner]
        source_id = family_ids[source]
        order = np.argsort(-scores[row])
        second = next(
            int(candidate) for candidate in order if int(candidate) != winner
        )
        margin = float(scores[row, winner] - scores[row, second])
        direct_fit = float(direct[row, winner])
        was_hold = bool(card.get("decision_required"))
        in_explicit_scope = card["l4_id"] in explicit_ids
        release_hold = (
            was_hold
            and in_explicit_scope
            and direct_fit
            >= thresholds["direct_seed_cosine_min"]
            and margin >= thresholds["composite_margin_min"]
        )
        structural_move = current_semantic_l3(card) in migration
        direct_move = (
            not was_hold
            and (in_explicit_scope or structural_move)
            and winner_id != source_id
        )
        if was_hold and not in_explicit_scope:
            remaining_hold.append(
                {
                    "l4_id": card["l4_id"],
                    "reason": "outside_extension_scope",
                    "winner_l3_id": current_semantic_l3(card),
                    "direct_seed_cosine": None,
                    "composite_margin": None,
                }
            )
            continue
        if was_hold and not release_hold:
            hold_l1 = (
                "A" if winner_id.startswith("RAI3-A-") else "G"
            )
            hold_l2 = f"RAI2-{hold_l1}-HLD"
            hold_l3 = f"RAI3-{hold_l1}-HLD-01"
            target = nodes_by_id[winner_id]
            parent = nodes_by_id[target["parent_id"]]
            card["primary_l3_id"] = hold_l3
            card["breadcrumb"] = node_path(hold_l3, nodes_by_id)
            card["hold_semantic_path"] = {
                "l2_id": parent["node_id"],
                "l3_id": target["node_id"],
                "l2_label_en": parent["label_en"],
                "l2_label_ko": parent["label_ko"],
                "l3_label_en": target["label_en"],
                "l3_label_ko": target["label_ko"],
            }
            card["hold_review_l2_id"] = hold_l2
            card["hold_review_l3_id"] = hold_l3
            card["stage2_suitability_score"] = round(direct_fit, 6)
            card["decision_reason"] = (
                "Review retained: winner does not meet both the "
                "direct-fit and margin release criteria."
            )
            card["v2_18_reclassification"] = {
                "type": "hold_retained",
                "semantic_winner_l3_id": winner_id,
                "direct_seed_cosine": round(direct_fit, 6),
                "composite_margin": round(margin, 6),
            }
            remaining_hold.append(
                {
                    "l4_id": card["l4_id"],
                    "reason": "release_threshold_not_met",
                    "winner_l3_id": winner_id,
                    "direct_seed_cosine": round(direct_fit, 6),
                    "composite_margin": round(margin, 6),
                }
            )
            continue
        if release_hold or direct_move or structural_move:
            card["previous_primary_l3_id"] = old_primary
            card["primary_l3_id"] = winner_id
            card["breadcrumb"] = node_path(winner_id, nodes_by_id)
            card["decision_required"] = False
            card["human_approved"] = False
            card["review_status"] = (
                "algorithmically_reclassified_pending_human_validation"
            )
            card["assignment_status"] = (
                "winner_takes_all_v2_18_rc"
            )
            for key in (
                "hold_semantic_path",
                "hold_review_l2_id",
                "hold_review_l3_id",
            ):
                card.pop(key, None)
            card["decision_reason"] = None
            card["v2_18_reclassification"] = {
                "type": (
                    "hold_released"
                    if release_hold
                    else "structural_or_competitive_move"
                ),
                "from_l3_id": source_id,
                "to_l3_id": winner_id,
                "direct_seed_cosine": round(direct_fit, 6),
                "composite_score": round(float(scores[row, winner]), 6),
                "composite_margin": round(margin, 6),
            }
            changes.append(
                {
                    "l4_id": card["l4_id"],
                    "label_en": card.get("label_en", ""),
                    "old_primary_l3_id": old_primary,
                    "old_semantic_l3_id": source_id,
                    "new_primary_l3_id": winner_id,
                    "change_type": card["v2_18_reclassification"]["type"],
                    "direct_seed_cosine": round(direct_fit, 6),
                    "composite_margin": round(margin, 6),
                }
            )
    for card in payload["cards"]:
        if (
            card.get("status") == "active"
            and card.get("primary_l3_id") in nodes_by_id
        ):
            card["breadcrumb"] = node_path(
                card["primary_l3_id"], nodes_by_id
            )
    counts = Counter(
        card["primary_l3_id"]
        for card in payload["cards"]
        if card.get("status") == "active"
    )
    for node in hierarchy["nodes"]:
        if node["level"] == 3:
            node["l4_count"] = counts.get(node["node_id"], 0)
    return payload, changes, remaining_hold


def seal_source_release(config: dict) -> dict:
    archive_root = ROOT / "archives/sealed"
    archive_root.mkdir(parents=True, exist_ok=True)
    stem = "v2.17.2_pre_general_societal_extension_20260725"
    archive = archive_root / f"{stem}.tar.gz"
    manifest_path = archive_root / f"{stem}.manifest.json"
    if archive.exists() or manifest_path.exists():
        raise FileExistsError(
            f"Sealed archive already exists: {archive}"
        )
    with tarfile.open(archive, "w:gz") as handle:
        handle.add(SOURCE, arcname="public/data/releases/v2.17.2")
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except subprocess.CalledProcessError:
        commit = None
    files = {
        path.name: {
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(SOURCE.iterdir())
        if path.is_file()
    }
    manifest = {
        "sealed": True,
        "sealed_on": "2026-07-25",
        "source_release": config["source_release"],
        "source_path": str(SOURCE.relative_to(ROOT)),
        "source_git_commit": commit,
        "archive": str(archive.relative_to(ROOT)),
        "archive_sha256": sha256(archive),
        "archive_bytes": archive.stat().st_size,
        "source_files": files,
        "restore_command": (
            "tar -xzf "
            f"{archive.relative_to(ROOT)} "
            "-C <empty-restore-directory>"
        ),
        "policy": (
            "Immutable rollback snapshot. Do not edit or replace. "
            "The live v2.17.2 directory remains unchanged."
        ),
    }
    write_json(manifest_path, manifest)
    return manifest


def build(args: argparse.Namespace) -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    source_cards = json.loads(
        (SOURCE / "cards.json").read_text(encoding="utf-8")
    )
    source_hierarchy = json.loads(
        (SOURCE / "hierarchy.json").read_text(encoding="utf-8")
    )
    hierarchy, migration, _ = migrated_hierarchy(
        source_hierarchy, config
    )
    nodes = semantic_nodes(hierarchy)
    cards = [
        card
        for card in source_cards["cards"]
        if card.get("status") == "active"
    ]
    if len(source_cards["cards"]) != 1711 or len(cards) != 1660:
        raise ValueError("Source registry or active-card count changed")
    if len(nodes) != 54:
        raise ValueError(f"Expected 54 semantic L3 nodes, got {len(nodes)}")
    embeddings = load_card_embeddings(cards)
    seed_embeddings = encode_seeds(nodes)
    assignment, source_assignment, events, scores, direct = (
        run_winner_assignment(
            cards,
            nodes,
            migration,
            config["candidate_priors"],
            embeddings,
            seed_embeddings,
            config["winner_takes_all_epsilon"],
        )
    )
    cards_payload, changes, remaining_hold = update_cards(
        source_cards,
        hierarchy,
        cards,
        nodes,
        migration,
        assignment,
        source_assignment,
        scores,
        direct,
        config,
    )
    out = Path(args.out_dir).resolve()
    report = Path(args.report_dir).resolve()
    if out.exists() or report.exists():
        raise FileExistsError(
            f"Output already exists: {out} or {report}"
        )
    out.mkdir(parents=True)
    report.mkdir(parents=True)
    active_out = [
        card
        for card in cards_payload["cards"]
        if card.get("status") == "active"
    ]
    counts_by_domain = Counter(
        card["primary_l3_id"].split("-")[1]
        for card in active_out
    )
    hold_count = sum(
        bool(card.get("decision_required")) for card in active_out
    )
    source_hold = sum(
        bool(card.get("decision_required")) for card in cards
    )
    structural = sum(
        change["old_primary_l3_id"].startswith("RAI3-P-SOC")
        for change in changes
    )
    candidate_by_id: dict[str, list[str]] = {}
    for family_id, l4_ids in config["candidate_priors"].items():
        for l4_id in l4_ids:
            candidate_by_id.setdefault(l4_id, []).append(family_id)
    active_position = {
        card["l4_id"]: position
        for position, card in enumerate(cards)
    }
    family_ids = [node["node_id"] for node in nodes]
    candidate_competition: list[dict] = []
    registry_by_id = {
        card["l4_id"]: card for card in source_cards["cards"]
    }
    output_by_id = {
        card["l4_id"]: card for card in cards_payload["cards"]
    }
    for l4_id, listed in sorted(candidate_by_id.items()):
        source_card = registry_by_id[l4_id]
        row = active_position.get(l4_id)
        if row is None:
            candidate_competition.append(
                {
                    "l4_id": l4_id,
                    "status": source_card["status"],
                    "listed_candidate_l3_ids": "|".join(sorted(listed)),
                    "winner_l3_id": "",
                    "output_primary_l3_id": output_by_id[l4_id][
                        "primary_l3_id"
                    ],
                    "direct_seed_cosine": "",
                    "composite_margin": "",
                }
            )
            continue
        winner = int(assignment[row])
        order = np.argsort(-scores[row])
        second = next(
            int(candidate) for candidate in order
            if int(candidate) != winner
        )
        candidate_competition.append(
            {
                "l4_id": l4_id,
                "status": source_card["status"],
                "listed_candidate_l3_ids": "|".join(sorted(listed)),
                "winner_l3_id": family_ids[winner],
                "output_primary_l3_id": output_by_id[l4_id][
                    "primary_l3_id"
                ],
                "direct_seed_cosine": round(
                    float(direct[row, winner]), 6
                ),
                "composite_margin": round(
                    float(scores[row, winner] - scores[row, second]), 6
                ),
            }
        )
    summary = {
        "release_id": config["release_id"],
        "source_release": config["source_release"],
        "method": {
            "encoder": "BAAI/bge-m3",
            "score": (
                "0.60 centroid cosine + 0.30 L3 definition cosine "
                "+ 0.10 TF-IDF keyword cosine"
            ),
            "assignment": "winner takes all within domain constraints",
            "physical_lock": (
                "Physical System Safety and Interaction Safety retained"
            ),
            "hold_release": config["hold_release_thresholds"],
            "iterations": events,
        },
        "counts": {
            "registered_ids": len(cards_payload["cards"]),
            "active_cards": len(active_out),
            "retired_cards": sum(
                card.get("status") == "retired"
                for card in cards_payload["cards"]
            ),
            "semantic_l3": len(nodes),
            "all_active_l3_including_hold": sum(
                node["level"] == 3
                and str(node.get("status", "")).startswith("active")
                for node in hierarchy["nodes"]
            ),
            "source_hold": source_hold,
            "remaining_hold": hold_count,
            "hold_released": source_hold - hold_count,
            "changed_active_cards": len(changes),
            "physical_societal_structural_moves": structural,
            "listed_candidate_ids": len(candidate_by_id),
            "listed_candidate_active": sum(
                registry_by_id[l4_id]["status"] == "active"
                for l4_id in candidate_by_id
            ),
            "listed_candidate_retired": sum(
                registry_by_id[l4_id]["status"] == "retired"
                for l4_id in candidate_by_id
            ),
            "by_primary_domain_code": dict(sorted(counts_by_domain.items())),
        },
        "l3_migration": migration,
        "source_hashes": {
            "cards_json": sha256(SOURCE / "cards.json"),
            "hierarchy_json": sha256(SOURCE / "hierarchy.json"),
        },
    }
    manifest = {
        "release_id": config["release_id"],
        "source_release": config["source_release"],
        "status": "release_candidate_pending_human_validation",
        "method": summary["method"],
        "counts": summary["counts"],
        "policy": (
            "All 1,711 IDs are preserved. Overlapping L3 families are "
            "retained. Algorithmic changes are pending human validation."
        ),
    }
    changelog = {
        "release_id": config["release_id"],
        "source_release": config["source_release"],
        "hierarchy_changes": {
            "added_l2": [config["new_l2"]["node_id"]],
            "added_l3": [
                node["node_id"] for node in config["new_l3"]
            ],
            "migrated_l3": migration,
            "retired_l2": ["RAI2-P-SOC"],
        },
        "card_changes": changes,
        "remaining_hold": remaining_hold,
    }
    write_json(out / "hierarchy.json", hierarchy)
    write_json(out / "cards.json", cards_payload)
    write_json(out / "manifest.json", manifest)
    write_json(out / "revision_changelog.json", changelog)
    np.save(report / "l3_seed_embeddings.npy", seed_embeddings)
    np.save(report / "final_assignment.npy", assignment)
    write_json(report / "reclassification_summary.json", summary)
    write_json(report / "l3_id_migration.json", migration)
    write_json(report / "iteration_log.json", events)
    with (report / "reclassification_changes.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(changes[0])
            if changes
            else ["l4_id"],
        )
        writer.writeheader()
        writer.writerows(changes)
    with (report / "remaining_hold.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(remaining_hold[0])
            if remaining_hold
            else ["l4_id"],
        )
        writer.writeheader()
        writer.writerows(remaining_hold)
    with (report / "candidate_competition.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(candidate_competition[0]),
        )
        writer.writeheader()
        writer.writerows(candidate_competition)
    if args.seal:
        summary["sealed_source"] = seal_source_release(config)
        write_json(report / "reclassification_summary.json", summary)
    print(json.dumps(summary["counts"], ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT))
    parser.add_argument("--seal", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
