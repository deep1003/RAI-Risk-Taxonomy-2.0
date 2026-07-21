#!/usr/bin/env python3
"""Run one independent, hierarchy-blind local expert-model review.

The model never receives legacy global L1-L3 or the BGE candidate ranking. The
candidate pool is preselected only to control compute; every reviewed card is
presented with the full 26-L3 codebook.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rai_taxonomy.codebook import L3_NODES, NON_PHYSICAL_L3_IDS, RELEASE_ID  # noqa: E402

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
SEED = 1726


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, choices=["gemma3:4b", "qwen3:4b"])
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mechanism_only(value: str | None) -> str:
    text = (value or "").strip()
    for marker in ["This L4 risk card treats", "This risk card treats", "This L4 card treats"]:
        if marker in text:
            text = text.split(marker, 1)[0].strip(" .")
    return " ".join(text.split())


def codebook_text() -> str:
    nodes = {node["node_id"]: node for node in L3_NODES}
    return "\n".join(
        f"[{l3_id}] {nodes[l3_id]['label_en']}: {nodes[l3_id]['definition_en']}"
        for l3_id in NON_PHYSICAL_L3_IDS
    )


def review_prompt(cards: list[dict]) -> str:
    card_text = "\n".join(
        " | ".join(
            [
                f"KEY={card['_l4_id']}",
                f"LABEL={card.get('l4_label') or card.get('phrase')}",
                f"DEFINITION={mechanism_only(card.get('definition'))}",
                f"EVIDENCE={card.get('evidence_title') or card.get('ref_title') or ''}",
            ]
        )
        for card in cards
    )
    return f"""You are an independent AI-risk taxonomy reviewer.

Use only each card's label, mechanism definition, and evidence title. The legacy hierarchy is hidden. Select exactly one listed L3 only when the card's direct mechanism is fully included in that exact definition. Otherwise select NEEDS. Names are not broad themes.

Mandatory boundaries:
- Deliberate disinformation or influence operations are not the nonintentional misinformation category.
- Governance, audit, environmental, labor, inequality, power-concentration, general transparency, model-security, allocative-bias, dependency/manipulation, general robustness, reward-hacking, deception, control, and unlisted physical/robot risks normally require NEEDS.
- Hate/Unfairness requires hateful or discriminatory content, not mere group performance disparity.
- Anthropomorphism requires humanlike self-representation, not attachment or overreliance alone.
- Policy Exposure requires protected prompts, policies, weights, data, or internals to be obtained, exposed, or bypassed.
- Context Misalignment requires material cross-jurisdiction legal-order substitution.
- Goal Misalignment requires a user-intent or delegated-objective mechanism, not broad alignment failure.
- Each Agentic category requires its exact permission, traceability, propagation, feedback, competition, or covert-coordination mechanism.
- If two categories could fit, return NEEDS.

Return every key exactly once. Keep evidence_phrase to at most 12 words copied or closely paraphrased from the card.

CODEBOOK
{codebook_text()}

CARDS
{card_text}"""


def response_schema(keys: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "minItems": len(keys),
                "maxItems": len(keys),
                "items": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "enum": keys},
                        "decision": {
                            "type": "string",
                            "enum": NON_PHYSICAL_L3_IDS + ["NEEDS"],
                        },
                        "reason_code": {
                            "type": "string",
                            "enum": ["DIRECT_FIT", "NO_EXACT_FIT", "AMBIGUOUS", "INSUFFICIENT"],
                        },
                        "evidence_phrase": {"type": "string"},
                    },
                    "required": ["key", "decision", "reason_code", "evidence_phrase"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["results"],
        "additionalProperties": False,
    }


def call_ollama(model: str, cards: list[dict], timeout: int) -> list[dict]:
    keys = [card["_l4_id"] for card in cards]
    payload = {
        "model": model,
        "prompt": review_prompt(cards),
        "stream": False,
        "format": response_schema(keys),
        "think": False,
        "options": {
            "temperature": 0,
            "seed": SEED,
            "num_predict": max(1200, len(cards) * 110),
        },
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        envelope = json.load(response)
    parsed = json.loads(envelope["response"])
    results = parsed.get("results", [])
    result_keys = [row.get("key") for row in results]
    if len(results) != len(keys) or set(result_keys) != set(keys) or len(set(result_keys)) != len(keys):
        raise ValueError(f"Invalid key coverage: expected {keys}, got {result_keys}")
    allowed = set(NON_PHYSICAL_L3_IDS) | {"NEEDS"}
    for row in results:
        if row.get("decision") not in allowed:
            raise ValueError(f"Invalid decision: {row}")
        if row["decision"] == "NEEDS" and row.get("reason_code") == "DIRECT_FIT":
            row["reason_code"] = "NO_EXACT_FIT"
        if row["decision"] != "NEEDS":
            row["reason_code"] = "DIRECT_FIT"
    by_key = {row["key"]: row for row in results}
    return [by_key[key] for key in keys]


def review_batch_resilient(model: str, cards: list[dict], timeout: int) -> list[dict]:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            return call_ollama(model, cards, timeout)
        except (ValueError, json.JSONDecodeError, urllib.error.URLError, TimeoutError) as error:
            last_error = error
            time.sleep(1 + attempt)
    if len(cards) == 1:
        raise RuntimeError(f"Review failed for {cards[0]['_l4_id']}: {last_error}") from last_error
    midpoint = len(cards) // 2
    return review_batch_resilient(model, cards[:midpoint], timeout) + review_batch_resilient(
        model, cards[midpoint:], timeout
    )


def main() -> None:
    args = parse_args()
    release_dir = PROJECT_ROOT / "data" / "releases" / RELEASE_ID
    review_dir = PROJECT_ROOT / "reports" / "validation" / RELEASE_ID / "expert_model_reviews"
    safe_model_name = args.model.replace(":", "_")
    output_path = review_dir / f"{safe_model_name}.json"
    if output_path.exists() and not args.force:
        print(json.dumps({"status": "cached", "model": args.model, "path": str(output_path)}))
        return

    source_cards = read_json(
        PROJECT_ROOT / "data" / "source_snapshots" / RELEASE_ID / "global_ai_risk_l4_overlay_nodes.json"
    )
    source_cards = sorted(source_cards, key=lambda row: row["id"])
    for number, card in enumerate(source_cards, start=1):
        card["_l4_id"] = f"RAI4-{number:04d}"
    placements = {row["l4_id"]: row for row in read_json(release_dir / "placements.json")}
    pool = []
    for card in source_cards:
        placement = placements[card["_l4_id"]]
        if placement["assignment_status"] == "locked_physical":
            continue
        if placement["gap_sentinels_triggered"]:
            continue
        top = placement["top_candidates"][0]
        semantic_prefilter = top["semantic_score"] >= 0.58 and placement["semantic_margin"] >= 0.02
        rule_prefilter = any(candidate["eligible"] for candidate in placement["top_candidates"])
        if placement["assignment_status"] == "algorithm_proposed" or semantic_prefilter or rule_prefilter:
            pool.append(card)

    all_results = []
    total_batches = (len(pool) + args.batch_size - 1) // args.batch_size
    for batch_number, start in enumerate(range(0, len(pool), args.batch_size), start=1):
        batch = pool[start : start + args.batch_size]
        results = review_batch_resilient(args.model, batch, args.timeout)
        for card, result in zip(batch, results, strict=True):
            result["global_source_id"] = card["id"]
            result["model"] = args.model
            result["model_role"] = "independent_hierarchy_blind_expert"
            result["legacy_hierarchy_used_as_feature"] = False
        all_results.extend(results)
        print(
            json.dumps(
                {
                    "model": args.model,
                    "batch": batch_number,
                    "total_batches": total_batches,
                    "reviewed": len(all_results),
                    "pool": len(pool),
                }
            ),
            flush=True,
        )

    output = {
        "model": args.model,
        "run_id": f"LLM-REVIEW-{safe_model_name}-20260721",
        "release_id": RELEASE_ID,
        "seed": SEED,
        "temperature": 0,
        "hierarchy_blind": True,
        "legacy_hierarchy_used_as_feature": False,
        "reviewed_card_count": len(all_results),
        "selection_rule": "non-Physical; no gap sentinel; initial proposal or BGE semantic>=0.58 and margin>=0.02 or rule-eligible top candidate",
        "results": all_results,
    }
    write_json(output_path, output)
    print(json.dumps({"status": "complete", "model": args.model, "reviewed": len(all_results), "path": str(output_path)}))


if __name__ == "__main__":
    main()

