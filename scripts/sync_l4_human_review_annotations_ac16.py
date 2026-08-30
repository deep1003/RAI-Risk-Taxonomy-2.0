#!/usr/bin/env python3
"""Synchronise current-card human-review results without changing taxonomy cards."""

from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_CARDS = ROOT / "public/data/releases/RAI-Risk-Taxonomy-2.0-master/cards.json"
HANDOVER_CARDS = ROOT / "handover/RAI-Risk-Taxonomy-2.0-master_20260829/04_web/cards.json"
HANDOVER_ROOT = ROOT / "handover/RAI-Risk-Taxonomy-2.0-master_20260829"

CSV_DIRS = (
    ROOT / "projects/rai_risk_taxonomy_2_0_rebuild_20260826/03_outputs/release",
    ROOT / "projects/rai_risk_taxonomy_2_0_rebuild_20260826/07_human_review_recovery_applied",
    ROOT / "handover/RAI-Risk-Taxonomy-2.0-master_20260829/01_data",
)

CURRENT_ID_PATTERN = re.compile(r"\b(?:G|A|P)_(?:INT|SYS|SOC)_[A-Z]+_\d{3}\b")

CONFLICT_RESULTS = {
    ("P_SYS_CONTROL_023", "SRC-P-0152"): (
        "유지와 삭제 제안을 함께 검토한 결과, 장면 변화에 따른 안전하지 않은 모방 제어라는 "
        "측정 가능한 기제가 있어 P_SYS_CONTROL_023(장면 변화 시 인간 행동 모방 실패)으로 유지함."
    ),
    ("G_SYS_EVAL_044", "SRC-P-0016"): (
        "유지와 삭제 제안을 함께 검토한 결과, 배포 전 물리적 안전 시험의 누락은 독립적으로 "
        "검증 가능한 평가·보증 실패이므로 G_SYS_EVAL_044(배포 전 물리적 안전 시험 미흡)로 이관·유지함."
    ),
    ("P_SYS_CONTROL_042", "SRC-P-0123"): (
        "유지와 L3 부적합·삭제 제안을 함께 검토한 결과, 런타임 안전 모니터의 제약 감지·집행 실패는 "
        "안전하지 않은 물리 제어·구동과 직접 관련되므로 P_SYS_CONTROL_042(런타임 안전 모니터 실패)로 유지함."
    ),
    ("P_SYS_CONTROL_043", "SRC-G-0014"): (
        "유지와 General AI 이관 제안을 함께 검토한 결과, 충돌 회피와 물리적 안전 제약을 희생하는 "
        "로봇 조작 정책의 문제이므로 P_SYS_CONTROL_043(안전-성능 균형 실패)으로 유지함."
    ),
}


def load_cards(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def card_result(card: dict, comment: str) -> str:
    l4_id = card["l4_id"]
    title = card["label_ko"]
    if "분할" in comment or "분해" in comment:
        return (
            f"휴먼검수에서 분리하도록 지적한 의미 중 현행 카드에 해당하는 축은 "
            f"{l4_id}({title})에 반영됨. 후속 통합·분해·재배정으로 퇴역한 카드 ID는 현행 결과에서 제외함."
        )
    if any(token in comment for token in ("이관", "이동", "분류", "재매핑")):
        return (
            f"이관 의견을 현행 L3 마스터와 후속 큐레이션 결과에 대조하여 "
            f"{l4_id}({title})에 최종 귀속함."
        )
    return f"휴먼검수 의견의 유지·문안 수정 취지가 현행 {l4_id}({title})에 반영됨."


def build_corrections(payload: dict) -> dict[tuple[str, str], tuple[str, str]]:
    cards = payload["cards"]
    current_ids = {card["l4_id"] for card in cards}
    corrections: dict[tuple[str, str], tuple[str, str]] = {}

    for card in cards:
        for review in card.get("human_reviews", []):
            key = (card["l4_id"], review["source_row_id"])
            old = review.get("result", "")
            referenced = CURRENT_ID_PATTERN.findall(old)
            if any(l4_id not in current_ids for l4_id in referenced):
                corrections[key] = (old, card_result(card, review.get("comment", "")))

    for key, new in CONFLICT_RESULTS.items():
        card = next(card for card in cards if card["l4_id"] == key[0])
        review = next(review for review in card["human_reviews"] if review["source_row_id"] == key[1])
        if review["result"] != new:
            corrections[key] = (review["result"], new)

    return corrections


def apply_to_cards(path: Path, corrections: dict[tuple[str, str], tuple[str, str]]) -> int:
    payload = load_cards(path)
    changed = 0
    for card in payload["cards"]:
        for review in card.get("human_reviews", []):
            key = (card["l4_id"], review["source_row_id"])
            if key not in corrections:
                continue
            old, new = corrections[key]
            if review["result"] != old:
                raise AssertionError(f"Unexpected prior result for {key} in {path}")
            review["result"] = new
            changed += 1
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return changed


def refresh_handover_checksums() -> int:
    checksum_path = HANDOVER_ROOT / "SHA256SUMS.txt"
    files = sorted(
        path for path in HANDOVER_ROOT.rglob("*")
        if path.is_file() and path != checksum_path
    )
    lines = []
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(HANDOVER_ROOT)}")
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(files)


def csv_path(directory: Path, domain: str) -> Path:
    direct = directory / f"L4_{domain}.csv"
    if direct.exists():
        return direct
    applied = directory / f"L4_{domain}_Human_Review_Recovery_Applied.csv"
    if applied.exists():
        return applied
    raise FileNotFoundError(f"No current {domain} CSV in {directory}")


def apply_to_csv(path: Path, corrections: dict[tuple[str, str], tuple[str, str]]) -> int:
    frame = pd.read_csv(path, dtype=str).fillna("")
    changed = 0
    for (l4_id, _source_row_id), (old, new) in corrections.items():
        mask = frame["L4_ID"].eq(l4_id)
        if not mask.any():
            continue
        index = frame.index[mask][0]
        value = frame.at[index, "Human_Review_Result"]
        if old not in value:
            if new in value:
                continue
            raise AssertionError(f"Missing prior result for {l4_id} in {path}")
        frame.at[index, "Human_Review_Result"] = value.replace(old, new)
        changed += 1
    frame.to_csv(path, index=False, lineterminator="\r\n")
    return changed


def main() -> None:
    source_payload = load_cards(PUBLIC_CARDS)
    corrections = build_corrections(source_payload)
    if len(corrections) not in (0, 35):
        raise AssertionError(f"Expected 0 or 35 annotation corrections, found {len(corrections)}")

    for path in (PUBLIC_CARDS, HANDOVER_CARDS):
        changed = apply_to_cards(path, corrections)
        if changed != len(corrections):
            raise AssertionError(
                f"Expected {len(corrections)} JSON changes in {path}, found {changed}"
            )

    csv_changes = 0
    for directory in CSV_DIRS:
        for domain in ("General", "Agentic", "Physical"):
            csv_changes += apply_to_csv(csv_path(directory, domain), corrections)

    checksum_count = refresh_handover_checksums()
    print(f"human-review JSON entries corrected: {len(corrections)} x 2 copies")
    print(f"full-column CSV result fields corrected: {csv_changes} replacements")
    print(f"handover checksums refreshed: {checksum_count} files")
    print("L4 cards created: 0")


if __name__ == "__main__":
    main()
