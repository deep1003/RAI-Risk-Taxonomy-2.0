#!/usr/bin/env python3
"""Create concise Korean labels/definitions for all non-Physical L4 cards."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/data/releases/v2.4.0"
OUT = ROOT / "public/data/releases/v2.5.0"
LOCALIZATION = ROOT / "reports/localization/nonphysical_l4_ko_v2.5.json"
ATTACHMENT = Path("/Users/deep1003/.codex/attachments/111df932-a33d-4168-8863-fe3f0cb671cc/pasted-text.txt")


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def concise_source_definition(value: str) -> str:
    core = value.split("This L4 risk card treats", 1)[0].strip()
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", core)
    first = sentences[0].strip()
    return first if first.endswith((".", "!", "?")) else first + "."


def translate_pair(label: str, definition: str) -> tuple[str, str]:
    payload = f"{label}\n|||\n{definition}"
    query = urllib.parse.urlencode({
        "client": "gtx", "sl": "en", "tl": "ko", "dt": "t", "q": payload
    })
    url = "https://translate.googleapis.com/translate_a/single?" + query
    last_error = None
    for attempt in range(5):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.load(response)
            translated = "".join(part[0] for part in data[0])
            pieces = re.split(r"\s*\|\|\|\s*", translated, maxsplit=1)
            if len(pieces) != 2:
                raise ValueError("translation delimiter was not preserved")
            return normalize_korean_label(pieces[0]), normalize_korean_definition(pieces[1])
        except Exception as error:  # network retry with bounded backoff
            last_error = error
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Translation failed after retries: {last_error}")


def normalize_korean_label(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip().rstrip(".")
    replacements = {
        "일반 목적 AI": "범용 AI",
        "대리인": "에이전트",
        "의인화주의": "의인화",
    }
    for before, after in replacements.items():
        value = value.replace(before, after)
    return value


def normalize_korean_definition(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    replacements = {
        "대리인": "에이전트",
        "사용자 의도": "사용자의 의도",
        "인공 지능": "AI",
    }
    for before, after in replacements.items():
        value = value.replace(before, after)
    if value and value[-1] not in ".!?다요음임함됨됨":
        value += "."
    return value


def refine_taxonomy_terminology(row: dict) -> dict:
    """Apply context-sensitive risk-taxonomy terminology after translation."""
    row = dict(row)
    label_en = row["label_en"]
    label_ko = row["label_ko"].replace("상담원", "에이전트")
    definition_ko = row["definition_ko"].replace("상담원", "에이전트")
    definition_ko = definition_ko.replace("에이전트은", "에이전트는").replace("에이전트이", "에이전트가")
    definition_ko = definition_ko.replace("작업의 사용자의 의도", "사용자의 작업 의도")

    if "poison" in label_en.casefold():
        label_ko = label_ko.replace("중독", "오염")
        definition_ko = definition_ko.replace("중독", "오염")
    overrides = {
        "Absent supervisor autonomy risk": "감독자 부재 시 자율행동 위험",
        "AI ethics washing": "AI 윤리 준수 위장",
        "Compliance washing": "규정 준수 위장",
        "Human oversight accountability washing": "인간 감독·책임성 위장",
        "Human-in-the-loop rubber stamping": "인간 참여형 형식적 승인",
        "Dialect and register exclusion": "방언·언어 사용역 배제",
        "Association in LLMs": "LLM의 정보 연계",
        "Griefbot dependency": "고인 모사 챗봇 의존",
        "Sockpuppet-account creation": "위장 계정 생성",
    }
    label_ko = overrides.get(label_en, label_ko)
    if label_en == "Dialect and register exclusion":
        definition_ko = definition_ko.replace("등록", "언어 사용역")
    if label_en == "Absent supervisor autonomy risk":
        definition_ko = "예정된 감독자가 부재하거나 개입할 수 없는 상황에서도 에이전트가 중대한 행동을 계속하는 위험."
    row["label_ko"] = label_ko
    row["definition_ko"] = definition_ko
    return row


def build_localization(cards: list[dict], workers: int) -> dict:
    targets = [card for card in cards if card["assignment_status"] != "locked_physical"]
    rows = {}
    if LOCALIZATION.is_file():
        existing = read(LOCALIZATION)
        rows = {row["l4_id"]: row for row in existing.get("rows", [])}

    pending = []
    for card in targets:
        source_definition = concise_source_definition(card["definition_en"])
        source_sha = hashlib.sha256(f"{card['label_en']}\n{source_definition}".encode()).hexdigest()
        if rows.get(card["l4_id"], {}).get("source_sha256") != source_sha:
            pending.append((card, source_definition, source_sha))

    completed = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(translate_pair, card["label_en"], source_definition):
            (card, source_definition, source_sha)
            for card, source_definition, source_sha in pending
        }
        for future in as_completed(futures):
            card, source_definition, source_sha = futures[future]
            label_ko, definition_ko = future.result()
            rows[card["l4_id"]] = {
                "l4_id": card["l4_id"],
                "label_en": card["label_en"],
                "label_ko": label_ko,
                "source_definition_en": source_definition,
                "definition_ko": definition_ko,
                "source_sha256": source_sha,
                "method": "concise_first-mechanism_sentence_then_en-ko_translation_and_terminology_normalization",
                "human_review_status": "pending",
            }
            completed += 1
            if completed % 100 == 0:
                print(f"localized {completed}/{len(pending)} new rows", flush=True)

    ordered = [refine_taxonomy_terminology(rows[card["l4_id"]]) for card in targets]
    artifact = {
        "release_id": "v2.5.0",
        "grain": "one localization row per non-Physical L4 card",
        "source_release": "v2.4.0",
        "source_attachment": str(ATTACHMENT),
        "source_attachment_sha256": sha256(ATTACHMENT),
        "policy": "Translate only the first core failure-mechanism sentence, omit provenance boilerplate, normalize taxonomy terminology, and retain human-review metadata.",
        "rows": ordered,
    }
    write(LOCALIZATION, artifact)
    return artifact


def validate_localization(artifact: dict, cards: list[dict]) -> dict:
    rows = artifact["rows"]
    expected = [card for card in cards if card["assignment_status"] != "locked_physical"]
    ids = [row["l4_id"] for row in rows]
    checks = {
        "expected_rows": len(rows) == len(expected) == 1529,
        "unique_ids": len(ids) == len(set(ids)),
        "all_labels_have_korean": all(re.search(r"[가-힣]", row["label_ko"]) for row in rows),
        "all_definitions_have_korean": all(re.search(r"[가-힣]", row["definition_ko"]) for row in rows),
        "no_empty_fields": all(row["label_ko"].strip() and row["definition_ko"].strip() for row in rows),
        "definition_length_max": max(len(row["definition_ko"]) for row in rows) <= 500,
    }
    if not all(checks.values()):
        raise ValueError(f"Localization quality checks failed: {checks}")
    return checks


def build_release(cards: list[dict], hierarchy: dict, artifact: dict, checks: dict) -> None:
    localization = {row["l4_id"]: row for row in artifact["rows"]}
    output = []
    for source in cards:
        card = dict(source)
        card["release_id"] = "v2.5.0"
        if card["assignment_status"] != "locked_physical":
            row = localization[card["l4_id"]]
            card.update({
                "label_ko": row["label_ko"],
                "definition_ko": row["definition_ko"],
                "localization_method": row["method"],
                "localization_review_status": row["human_review_status"],
            })
        output.append(card)

    hierarchy["release_id"] = "v2.5.0"
    cards_path, hierarchy_path = OUT / "cards.json", OUT / "hierarchy.json"
    write(cards_path, {"release_id": "v2.5.0", "cards": output})
    write(hierarchy_path, hierarchy)
    manifest = {
        "release_id": "v2.5.0",
        "source_release": "v2.4.0",
        "release_status": "complete_english_korean_bilingual_display",
        "counts": {
            "l4": len(output),
            "classified": len(output),
            "physical_locked": 182,
            "physical_total": 182,
            "nonphysical_cards_localized": len(localization),
            "cards_with_korean_label": sum(bool(card.get("label_ko")) for card in output),
            "cards_with_korean_definition": sum(bool(card.get("definition_ko")) for card in output),
            "decision_required": sum(card["decision_required"] for card in output),
            "l3_nodes": sum(node["level"] == 3 for node in hierarchy["nodes"]),
        },
        "localization_quality_checks": checks,
        "artifacts": [
            {"path": "cards.json", "sha256": sha256(cards_path)},
            {"path": "hierarchy.json", "sha256": sha256(hierarchy_path)},
            {"path": str(LOCALIZATION.relative_to(ROOT)), "sha256": sha256(LOCALIZATION)},
        ],
    }
    write(OUT / "manifest.json", manifest)
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    cards = read(SOURCE / "cards.json")["cards"]
    hierarchy = read(SOURCE / "hierarchy.json")
    artifact = build_localization(cards, args.workers)
    checks = validate_localization(artifact, cards)
    build_release(cards, hierarchy, artifact, checks)


if __name__ == "__main__":
    main()
