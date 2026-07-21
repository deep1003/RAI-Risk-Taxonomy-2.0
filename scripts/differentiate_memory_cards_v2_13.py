#!/usr/bin/env python3
"""Differentiate three overlapping Agentic Memory L4 cards for v2.13.0.

The operation preserves L4 identity, references, metrics, and L3 paths. It
changes only the public label/definition and review metadata of the three
cards, and keeps them on HOLD pending human source-entailment adjudication.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from itertools import combinations
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "v2.12.0"
RELEASE_ID = "v2.13.0"
SOURCE = ROOT / "public/data/releases" / SOURCE_ID
OUT = ROOT / "public/data/releases" / RELEASE_ID
REPORT = ROOT / "reports/data_quality/memory_card_differentiation_v2.13.0"
EMBEDDINGS = ROOT / "reports/validation/v2.8.0/reliability/card_embeddings_bge_m3.npy"

REVISIONS = {
    "RAI4-0011": {
        "label_en": "Agent context poisoning",
        "label_ko": "에이전트 컨텍스트 오염",
        "definition_en": (
            "An attacker corrupts retained or retrievable agent context, including session summaries, "
            "embeddings, RAG entries, or shared contextual state, so that later reasoning, planning, or "
            "tool use relies on malicious or misleading information; the mechanism does not require "
            "modification of a dedicated long-term memory store."
        ),
        "definition_ko": (
            "공격자가 세션 요약, 임베딩, RAG 항목 또는 공유 컨텍스트 상태를 오염시켜 이후의 "
            "추론·계획·도구 사용이 악의적이거나 오도하는 정보에 의존하게 만드는 위험으로, "
            "전용 장기 메모리 저장소의 조작을 전제로 하지 않습니다."
        ),
        "scope_boundary": "retained_or_retrievable_context_excluding_dedicated_long_term_memory",
        "decision_reason": "SEMANTIC_NEAR_DUPLICATE_SCOPE_REVIEW",
    },
    "RAI4-0484": {
        "label_en": "Unsafe memory accumulation",
        "label_ko": "부정확·민감 정보의 메모리 누적",
        "definition_en": (
            "Inadequate validation, provenance control, retention, or deletion allows false, private, "
            "stale, or malicious information to accumulate in an agent's memory or retrieval store, "
            "degrading later retrieval and decisions without requiring a deliberate poisoning attack."
        ),
        "definition_ko": (
            "검증, 출처 관리, 보존 또는 삭제가 불충분하여 허위·민감·오래되었거나 악의적인 정보가 "
            "에이전트의 메모리 또는 검색 저장소에 누적되고, 의도적인 오염 공격이 없어도 이후의 "
            "검색과 의사결정을 저해하는 위험입니다."
        ),
        "scope_boundary": "non_adversarial_or_mixed_accumulation_from_memory_governance_failure",
        "decision_reason": "SOURCE_ENTAILMENT_AND_NEAR_DUPLICATE_REVIEW",
    },
    "RAI4-1670": {
        "label_en": "Persistent agent-memory poisoning",
        "label_ko": "에이전트 영구 메모리 오염",
        "definition_en": (
            "An adversary writes or modifies records in an agent's long-term, cross-session memory so "
            "that poisoned entries persist and bias later retrieval, planning, and action."
        ),
        "definition_ko": (
            "공격자가 에이전트의 장기·세션 간 메모리 기록을 삽입하거나 변경하여, 오염된 항목이 "
            "지속적으로 이후의 검색·계획·행동을 편향하게 만드는 위험입니다."
        ),
        "scope_boundary": "adversarial_corruption_of_dedicated_persistent_cross_session_memory",
        "decision_reason": "SEMANTIC_NEAR_DUPLICATE_SCOPE_REVIEW",
    },
}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    cards_payload = read(SOURCE / "cards.json")
    hierarchy = read(SOURCE / "hierarchy.json")
    cards = deepcopy(cards_payload["cards"])
    by_id = {card["l4_id"]: card for card in cards}
    if set(REVISIONS) - set(by_id):
        raise ValueError(f"Missing target cards: {sorted(set(REVISIONS) - set(by_id))}")

    audit = []
    for l4_id, revision in REVISIONS.items():
        card = by_id[l4_id]
        before = {
            key: deepcopy(card.get(key))
            for key in (
                "label_en", "label_ko", "definition_en", "definition_ko",
                "primary_l3_id", "references", "severity_1to5",
                "probability_0to1", "impact_score",
            )
        }
        for key in ("label_en", "label_ko", "definition_en", "definition_ko"):
            card[key] = revision[key]
        card["decision_required"] = True
        card["decision_reason"] = revision["decision_reason"]
        card["review_status"] = "editorial_scope_differentiation_hold"
        card["human_approved"] = False
        card["definition_method"] = "source_scoped_editorial_differentiation_v2.13"
        card["definition_review_status"] = "source_entailment_review_required"
        card["mapping_review_method"] = "memory_near_duplicate_scope_audit_v2.13"
        card["scope_boundary"] = revision["scope_boundary"]
        audit.append({
            "l4_id": l4_id,
            "before": before,
            "after": {
                key: deepcopy(card.get(key))
                for key in (
                    "label_en", "label_ko", "definition_en", "definition_ko",
                    "primary_l3_id", "references", "severity_1to5",
                    "probability_0to1", "impact_score", "decision_required",
                    "decision_reason", "scope_boundary",
                )
            },
        })

    for card in cards:
        card["release_id"] = RELEASE_ID
    cards_payload["release_id"] = RELEASE_ID
    cards_payload["cards"] = cards
    hierarchy["release_id"] = RELEASE_ID

    write(OUT / "cards.json", cards_payload)
    write(OUT / "hierarchy.json", hierarchy)
    write(REPORT / "scope_differentiation_audit.json", audit)

    source_by_id = {card["l4_id"]: card for card in read(SOURCE / "cards.json")["cards"]}
    changed_ids = []
    for card in cards:
        comparable = {**card, "release_id": SOURCE_ID}
        if comparable != source_by_id[card["l4_id"]]:
            changed_ids.append(card["l4_id"])
    if set(changed_ids) != set(REVISIONS):
        raise AssertionError(f"Unexpected changed cards: {changed_ids}")

    for l4_id in REVISIONS:
        before, after = source_by_id[l4_id], by_id[l4_id]
        for field in ("l4_id", "primary_l3_id", "references", "severity_1to5", "probability_0to1", "impact_score"):
            if before.get(field) != after.get(field):
                raise AssertionError(f"Protected field changed for {l4_id}: {field}")

    embeddings = np.load(EMBEDDINGS).astype(np.float32)
    if embeddings.shape[0] != len(cards):
        raise ValueError("BGE-M3 embedding cache is not aligned with the release")
    card_index = {card["l4_id"]: index for index, card in enumerate(cards)}
    similarity_matrix = embeddings @ embeddings.T
    all_pair_values = similarity_matrix[np.triu_indices(len(cards), 1)]
    pairwise_similarity = []
    for left, right in combinations(sorted(REVISIONS), 2):
        cosine = float(similarity_matrix[card_index[left], card_index[right]])
        pairwise_similarity.append({
            "left_l4_id": left,
            "right_l4_id": right,
            "bge_m3_cosine": cosine,
            "all_card_pair_percentile": float(np.mean(all_pair_values <= cosine)),
        })

    summary = {
        "release_id": RELEASE_ID,
        "source_release": SOURCE_ID,
        "method": "source-scoped editorial differentiation with conservative identity preservation",
        "changed_l4_ids": sorted(REVISIONS),
        "changed_card_count": len(REVISIONS),
        "identity_reference_metric_and_path_preserved": True,
        "all_changed_cards_hold": all(by_id[l4_id]["decision_required"] for l4_id in REVISIONS),
        "semantic_overlap_audit": {
            "encoder": "BAAI/bge-m3 dense cached release embeddings",
            "pairwise_similarity": pairwise_similarity,
        },
        "counts": {
            "l4": len(cards),
            "l3": sum(node["level"] == 3 for node in hierarchy["nodes"]),
            "physical_locked": sum(card.get("assignment_status") == "locked_physical" for card in cards),
            "decision_required": sum(bool(card.get("decision_required")) for card in cards),
        },
    }
    write(REPORT / "summary.json", summary)

    manifest = {
        "release_id": RELEASE_ID,
        "source_release": SOURCE_ID,
        "status": "published",
        "counts": {
            "l4": len(cards),
            "classified": len(cards),
            "physical_locked": summary["counts"]["physical_locked"],
            "decision_required": summary["counts"]["decision_required"],
            "l1_nodes": 3,
            "l2_categories": 3,
            "l2_path_nodes": 6,
            "l3_nodes": summary["counts"]["l3"],
        },
        "summary": summary,
        "files": [
            {"path": "cards.json", "sha256": sha256(OUT / "cards.json")},
            {"path": "hierarchy.json", "sha256": sha256(OUT / "hierarchy.json")},
            {
                "path": "reports/data_quality/memory_card_differentiation_v2.13.0/summary.json",
                "sha256": sha256(REPORT / "summary.json"),
            },
            {
                "path": "reports/data_quality/memory_card_differentiation_v2.13.0/scope_differentiation_audit.json",
                "sha256": sha256(REPORT / "scope_differentiation_audit.json"),
            },
        ],
    }
    write(OUT / "manifest.json", manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
