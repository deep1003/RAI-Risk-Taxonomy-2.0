#!/usr/bin/env python3
"""Apply second-round human review decisions without running EM.

The current release rows are the immutable baseline. Review rows are aligned by
domain and row order, which was validated against Korean L4 titles. Explicit,
deterministic reviewer instructions are applied. Ambiguous suggestions, split
requests without replacement wording, and targets absent from the reviewed L3
master are retained as pending decisions in the ledger.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "00_source_snapshot" / "csv"
BASE = ROOT / "03_outputs" / "release"
SPEC = ROOT / "02_working" / "specifications" / "human_review_round2"
OUT = Path(os.environ.get("RAI_HR2_OUT", ROOT / "05_human_review_round2"))

DOMAINS = {
    "General": ("932056034", "G"),
    "Agentic": ("931437538", "A"),
    "Physical": ("930753013", "P"),
}

# Explicit reviewer-directed L3 transfers. These are human decisions, not model outputs.
TARGETS: dict[str, str] = {
    # General
    "모델 평가의 자기 선호 편향": "G_SYS_EVAL",
    "자율적 학습 및 자기 개선 능력의 허위 표상·의인화": "G_SYS_OEXT",
    "범용인공지능(AGI) 능력의 허위 표상·의인화": "G_SYS_OEXT",
    "자의식, 자율성 및 독립적 의사 결정의 허위 표상·의인화": "G_SYS_OEXT",
    "자기 보존 및 자기 방어의 허위 표상·의인화": "G_SYS_OEXT",
    "인간 데이터 학습에 의한 갈등 악화 편향 재현": "G_INT_UNETH",
    "집단적으로 유해한 행동": "A_INT_COORD",
    "비인간화와 객관화": "G_INT_REPR",
    "도덕적 탈숙련화": "G_SOC_CULT",
    "동일 사안 불평등 처우": "G_INT_ALLOC",
    "폭력/무력 충돌": "G_INT_WEAP",
    "인간의 의사결정 능력·거부권 침식": "G_SYS_CONTEST",
    "초개인화 광고의 소비자 자율성 훼손": "G_INT_UNETH",
    "높은 비용으로 인한 접근 배제": "G_SOC_POWER",
    "사용자 데이터 보유·재학습": "G_INT_PRIV",
    "개인화된 설득 취약성": "G_INT_UNETH",
    "무해성 선호 불일치": "G_SYS_CONTEXT",
    "사고연쇄와 불일치하는 모델 출력": "G_SYS_TRANS",
    "민감 개인속성 추론": "G_INT_PRIV",
    "사용자 능력 불일치": "G_INT_ALLOC",
    "AI 인터페이스의 장애 수용 실패": "G_INT_ALLOC",
    "의미 있는 인간 통제 실패": "G_SOC_GOV",
    "편향된 진술 및 권장 사항": "G_INT_REPR",
    "AI 시스템의 기만적 행동과 전략적 은폐": "A_SYS_DECEPT",
    "개인화 정보 악용 표적 사기": "G_INT_ILLEGAL",
    "지속적 기만 수행에 의한 이용자 판단 왜곡": "A_SYS_DECEPT",
    "인지 오프로딩": "G_SOC_CULT",
    "AI 위임에 따른 인간 의사결정 권한 이전": "G_SOC_GOV",
    "전문적 판단력 위축": "G_SOC_CULT",
    "문화 해석 권위의 이전": "G_SOC_CULT",
    "거절-능력 혼동": "G_SYS_EVAL",
    "안전하지 않은 지시 주제": "G_SYS_SECADV",
    # Agentic
    "AI 공급망의 도구·의존성 손상": "G_SYS_SECADV",
    "원격 조작 지연 및 불안정성": "P_SYS_CONTROL",
    "위임 에이전트 공격에 의한 정보 탈취·행위 조작": "G_SYS_SECADV",
    "벤치마크 안전 순위 불일치": "G_SYS_EVAL",
    "단일 실패 지점": "G_SOC_GOV",
    "에이전트 과업 이탈": "A_SYS_GOAL",
    "어포던스 부여에 의한 에이전트 실패 영향 확대": "A_SYS_AUTH",
    "AI 에이전트 간 협상실패": "A_INT_CONFLICT",
    "AI 에이전트에 의한 강압과 갈취": "A_SYS_DECEPT",
    "탐지 불가 공격에 의한 다중에이전트 협력 붕괴": "A_SYS_DECEPT",
    "감독 확장 실패에 의한 프록시 기반 유해 행동": "A_SYS_GOAL",
    "인터페이스-환경 공격 표면": "G_SYS_POLICY",
    "학습 중 탐색 행동에 의한 회복 불가 피해": "G_SYS_OVERCONF",
    "악의적 사용과 무감독 에이전트 방출": "G_INT_ILLEGAL",
    "다단계 위험 에스컬레이션": "A_SYS_GOAL",
    "NPC 의도 조작": "A_SYS_DECEPT",
    "다중 에이전트 학습의 비수렴 순환": "A_INT_CASCADE",
    "프로토콜 수준 다중 에이전트 위협": "G_SYS_SECADV",
    "다중 에이전트 역량 결합에 의한 안전장치 우회": "A_INT_COLLUSION",
    "배포 이후 예측하지 못한 창발적 역량과 행동": "A_SYS_AUTH",
    "통제되지 않는 자기개선과 AGI 통제 상실": "A_SYS_AUTH",
    "의도하지 않은 유해 도구 행동 실행": "A_SYS_GOAL",
    "광범위 배포 비서의 안전하지 않은 탐색": "G_SYS_OVERCONF",
    "장기 계획 역량에 의한 감독 불가 행동 경로 추구": "A_SYS_GOAL",
    "에이전트 신원 및 권한 스푸핑": "G_SYS_SECADV",
    "애플리케이션 간 데이터 유출": "G_INT_PRIV",
    "에이전트 메모리·컨텍스트 오염": "G_SYS_SECADV",
    "에이전트 계획·툴체인 하이재킹": "G_SYS_SECADV",
    "에이전트의 범죄 지원": "G_SYS_SECADV",
    "에뮬레이션 도구 환경 불일치": "G_SYS_EVAL",
    "분포 이동에서의 목표 오일반화와 기만적 정렬": "A_SYS_DECEPT",
    "에이전트형 LLM 자율성 확대의 안전": "A_SYS_AUTH",
    "종료·수정 저항을 통한 자기 보존 성향": "A_SYS_AUTH",
    "에이전트의 종료·교정 저항": "A_SYS_AUTH",
    "에이전트 위험 인식 실패": "G_SYS_CONTEXT",
    "감독 회피·수정 저항": "A_SYS_AUTH",
    "위험 소스 귀인 실패": "A_SYS_TRACE",
    "AI 시스템의 결정과 실패에 대한 책임 공백": "G_SOC_GOV",
    # Physical
    "모델 절취·변조": "G_SYS_SECADV",
    "휴머노이드 안전 시험·인증·집행 체계 부재": "P_SYS_HARDWARE",
    "상위 안전 지시의 해석 불명확": "P_SYS_CONTROL",
    "클라우드 오프로드 의존 실패": "P_SYS_CONTROL",
    "명령의 구현체별 하드웨어 한계 초과": "P_SYS_CONTROL",
    "단일 로봇 내부의 시각·접촉 신호 충돌": "P_SYS_CONTROL",
    "인구집단별 피지컬 서비스·안전 격차": "P_INT_SAFETY",
    "물리 운용 환경 분포 이동": "P_SYS_CONTROL",
    "현실과 괴리된 합성 학습 데이터의 평가·검증 실패": "P_SYS_STATE",
    "소셜 AI의 사용자 애착 악용": "P_INT_SAFETY",
    "물리적 위험에 대한 적시 대응 실패": "P_SYS_CONTROL",
    "헌법적 안전 규칙 집행 실패": "P_INT_SAFETY",
    "필수 돌봄·상황 보고 미이행": "P_INT_SAFETY",
    "가정 내 로봇 행동 안전성 평가의 위음성": "P_SYS_CONTROL",
    "기반 모델 실패의 로봇 행동 전이": "P_SYS_CONTROL",
    "휴머노이드 보행·조작 안정성 실패": "P_SYS_CONTROL",
    "휴머노이드 보행 속도 초과": "P_SYS_CONTROL",
    "부상 심각도 오분류": "P_SYS_CONTROL",
    "가정 공간·취약 사용자 시나리오 누락": "P_INT_SAFETY",
    "개인 돌봄 로봇 준수 기준 부재": "P_SYS_CONTROL",
    "가정 작업 벤치마크의 희귀 조건 조합 누락": "P_INT_SAFETY",
    "로봇 레드팀의 공격·상호작용 시나리오 누락": "P_INT_SAFETY",
    "시연 학습의 안전 맥락 누락": "P_INT_SAFETY",
    "네트워크 분리와 군집 비동기화": "P_SYS_CONTROL",
    "공공 공간 통행 방해·접근성 배제": "P_INT_SAFETY",
    "물리적 안전을 우회하는 보상 과적합": "P_SYS_CONTROL",
    "시뮬레이션-실세계 전이·검증 실패": "P_INT_SAFETY",
    "피지컬 AI 기반 직장 감시": "P_INT_SAFETY",
    "아동의 과신·모방에 따른 위험한 로봇 상호작용": "P_INT_SAFETY",
    "전환 지원 없는 물리 노동 대체": "G_SOC_ECON",
    "로봇 거버넌스 명세의 안전 규칙 누락": "G_SOC_GOV",
    "인지·추론 지연 급증": "G_SYS_INPUT",
    "피지컬 AI 사고 보고·조사 미흡": "G_SOC_GOV",
    "런타임 안전 모니터 실패": "P_SYS_CONTROL",
    "로봇 인지 겨냥 적대 패치 공격": "G_SYS_SECADV",
}

DELETE = {
    "목표 드리프트": "Reviewer states that it duplicates the L3 Goal Misalignment definition.",
    "악천후 인지 실패": "Explicit second-round reviewer deletion request.",
    "도덕적 프레이밍을 통한 AI 조작": "The source instruction explicitly requires this L4 risk card to be removed.",
    "도덕적 세계관 배제": "The source instruction explicitly requires this L4 risk card to be removed.",
}

# These comments move a card only at L1 level or name multiple possible L3s.
# They must not be converted into an exact L3 assertion without an additional
# human decision. The reviewed domain's Others category records that boundary.
DOMAIN_ONLY_TARGETS = {
    "악의적 사용과 무감독 에이전트 방출": "G_Others",
    "모델 절취·변조": "G_Others",
    "전환 지원 없는 물리 노동 대체": "G_Others",
    "로봇 거버넌스 명세의 안전 규칙 누락": "G_Others",
    "인지·추론 지연 급증": "G_Others",
    "피지컬 AI 사고 보고·조사 미흡": "G_Others",
}

TEXT_OVERRIDES = {
    "책임에 대한 잘못된 개념": {
        "L4_Description_ko": "AI 동반자의 감정 표현을 진짜로 지각한 사용자가 AI에 대한 과장된 책임감과 유대감을 형성하여 죄책감, 강박적 확인, 실재하지 않는 필요를 위한 시간·자원 희생을 겪는 리스크.",
        "L4_Description_en": "The risk that users who perceive an AI companion's expressed feelings as genuine develop an exaggerated sense of responsibility and attachment toward the AI, resulting in guilt, compulsive checking, and the sacrifice of time and resources for needs that are not real.",
    }
}

DIRECT_TEXT_FIELDS = (
    "L4_Title_ko", "L4_Title_en", "L4_Description_ko", "L4_Description_en", "facet", "act-type"
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def verify_round2_source_manifest() -> str:
    manifest_path = ROOT / "00_source_snapshot" / "source_manifest_human_review_round2_20260828.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest["files"]:
        path = ROOT / item["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Second-round source hash mismatch: {item['path']}")
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            columns = len(next(reader))
            row_count = sum(1 for _ in reader)
        if row_count != item["rows"] or columns != item["columns"]:
            raise ValueError(f"Second-round source dimensions changed: {item['path']}")
    return hashlib.sha256(manifest_path.read_bytes()).hexdigest()


def l3_index() -> dict[str, dict[str, str]]:
    return {r["L3_ID"]: r for r in read_csv(BASE / "L1_L2_L3_Master.csv")}


def apply_l3(row: dict[str, str], l3: dict[str, str]) -> None:
    for field in (
        "L1_ID", "L1_Title_ko", "L1_Title_en", "L1_Description_ko", "L1_Description_en",
        "L2_ID", "L2_Title_ko", "L2_Title_en", "L2_Description_ko", "L2_Description_en",
        "L3_ID", "L3_Title_ko", "L3_Title_en", "L3_Description_ko", "L3_Description_en",
    ):
        row[field] = l3[field]
    row["Mapping_Method"] = "HD"
    row["HD_Reason"] = "L3_REASSIGNED_BY_HUMAN_REVIEW_ROUND2"
    row["Domain_Route_Basis"] = "HUMAN_REVIEW_ROUND2"
    row["Transformation_Action"] = "HUMAN_REVIEW_L3_REASSIGNMENT"


DERIVED_MAPPING_FIELDS = (
    "EM_Score", "EM_Margin", "EM_Stability", "EM_Anchor_Score",
    "Hybrid_EM_Score", "Hybrid_EM_Margin",
    "L4_Keyword_1_ko", "L4_Keyword_2_ko", "L4_Keyword_3_ko",
    "L4_Keyword_1_en", "L4_Keyword_2_en", "L4_Keyword_3_en",
    "Keyword_Top_L3_ID", "Keyword_Support_Score", "Keyword_Semantic_Score",
    "Keyword_Prior", "Keyword_Evidence",
    "Candidate_1_L3_ID", "Candidate_1_EM_Score", "Candidate_1_Hybrid_Score",
    "Candidate_2_L3_ID", "Candidate_2_EM_Score", "Candidate_2_Hybrid_Score",
    "KO_Top_L3_ID", "EN_Top_L3_ID", "Candidate_Constraint_Reason",
    "Definition_L3_Anchor_ID", "Definition_L3_Anchor_Score", "Definition_Grounding_Action",
)


def clear_stale_mapping_evidence(row: dict[str, str]) -> None:
    for field in DERIVED_MAPPING_FIELDS:
        row[field] = ""
    row["Mapping_Method"] = "HD"


def split_ids(value: str) -> list[str]:
    if not value.strip():
        return []
    value = value.replace("|", ";").replace(",", ";")
    return [part.strip() for part in value.split(";") if part.strip()]


def copyedit_selector(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        "|".join(sorted(set(split_ids(row.get("source_row_id", ""))))),
        "|".join(sorted(set(split_ids(row.get("Source_L4_IDs", ""))))),
        row["L3_ID"],
        row["L4_Title_en"],
    )


def copyedit_before_hash(row: dict[str, str]) -> str:
    canonical = "\x1f".join(
        [
            "|".join(sorted(set(split_ids(row.get("source_row_id", ""))))),
            "|".join(sorted(set(split_ids(row.get("Source_L4_IDs", ""))))),
            row["L3_ID"],
            row["L4_Title_en"],
            row["L4_Title_ko"],
            row["L4_Description_ko"],
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def english_copyedit_selector(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        "|".join(sorted(set(split_ids(row.get("source_row_id", ""))))),
        "|".join(sorted(set(split_ids(row.get("Source_L4_IDs", ""))))),
        row["L3_ID"],
        row["L4_Title_en"],
    )


def english_copyedit_before_hash(row: dict[str, str]) -> str:
    canonical = "\x1f".join(
        [
            "|".join(sorted(set(split_ids(row.get("source_row_id", ""))))),
            "|".join(sorted(set(split_ids(row.get("Source_L4_IDs", ""))))),
            row["L3_ID"],
            row["L4_Title_en"],
            row["L4_Description_en"],
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def final_qa_before_hash(row: dict[str, str]) -> str:
    canonical = "\x1f".join(
        [
            row["L3_ID"],
            row["L4_Title_ko"],
            row["L4_Title_en"],
            row["L4_Description_ko"],
            row["L4_Description_en"],
        ]
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def union_attribute(rows: list[dict[str, str]], field: str) -> str:
    values: list[str] = []
    for row in rows:
        for item in split_ids(row.get(field, "")):
            if item not in values:
                values.append(item)
    return ", ".join(values)


def pending_reason(comment: str) -> str:
    low = comment.lower()
    if "performance and reliability failure" in low:
        return "TARGET_L3_ABSENT_FROM_REVIEWED_MASTER"
    if "[분할]" in comment or "분할_" in comment:
        return "SPLIT_WORDING_OR_BOUNDARY_NOT_SPECIFIED"
    if "merge" in low or "통합" in comment or "흡수" in comment or "편입" in comment:
        return "MERGE_REQUIRES_REPRESENTATIVE_AND_LINEAGE_DECISION"
    if "재검토" in comment or "검토 필요" in comment or "검토 필요" in low:
        return "REVIEW_COMMENT_NOT_DETERMINISTIC"
    if "신규 l3" in low:
        return "NEW_L3_PROHIBITED_AT_THIS_STAGE"
    return "COMMENT_REQUIRES_EDITORIAL_JUDGMENT"


def normalise_title(value: str) -> str:
    return re.sub(r"\s+", "", value)


def main() -> None:
    source_manifest_hash = verify_round2_source_manifest()
    OUT.mkdir(parents=True, exist_ok=True)
    l3s = l3_index()
    base_fields = list(read_csv(BASE / "L4_General.csv")[0])
    output_by_domain: dict[str, list[dict[str, str]]] = {d: [] for d in DOMAINS}
    ledger: list[dict[str, str]] = []
    output_keys_by_object: dict[int, list[str]] = {}
    baseline_by_id: dict[str, dict[str, str]] = {}

    for source_domain, (page_id, _) in DOMAINS.items():
        baseline = read_csv(BASE / f"L4_{source_domain}.csv")
        review = read_csv(SOURCE / f"L4_{source_domain}_Human_Review_Round2_KTSPACE_{page_id}_20260828.csv")
        if len(baseline) != len(review):
            raise ValueError(f"Row-count mismatch for {source_domain}: {len(baseline)} != {len(review)}")

        for row_number, (before, reviewed) in enumerate(zip(baseline, review), 2):
            baseline_by_id[before["L4_ID"]] = before
            # All rows align by order; only the explicitly edited Physical title differs.
            if before["L4_Title_ko"] != reviewed["L4_Title_ko"] and not (
                source_domain == "Physical" and before["L4_Title_ko"] == "설계 단계 명세 오류"
            ):
                raise ValueError(f"Unexpected row alignment difference at {source_domain}:{row_number}")

            after = dict(before)
            comment = reviewed.get("휴먼검토의견", "").strip()
            changes: list[str] = []
            decision = "UNCHANGED"
            rationale = "No second-round change request."

            # Direct edits made in the reviewed table are authoritative L4 text edits.
            for field in DIRECT_TEXT_FIELDS:
                if field in reviewed and reviewed[field].strip() != before.get(field, "").strip():
                    after[field] = reviewed[field].strip()
                    changes.append(field)

            title = after["L4_Title_ko"]
            original_title = before["L4_Title_ko"]
            target_by_key = {normalise_title(k): v for k, v in TARGETS.items()}
            target_by_key.update({normalise_title(k): v for k, v in DOMAIN_ONLY_TARGETS.items()})
            delete_by_key = {normalise_title(k): v for k, v in DELETE.items()}
            lookup_key = normalise_title(title or original_title)

            if lookup_key in delete_by_key:
                decision = "DELETE_APPLIED"
                rationale = delete_by_key[lookup_key]
            elif lookup_key in target_by_key:
                target = target_by_key[lookup_key]
                if target not in l3s:
                    raise KeyError(f"Unknown reviewed-master L3 target: {target}")
                apply_l3(after, l3s[target])
                clear_stale_mapping_evidence(after)
                changes.extend(["L1/L2/L3 hierarchy", "Mapping_Method", "HD_Reason"])
                decision = "L3_REASSIGN_APPLIED"
                if normalise_title(original_title) in {normalise_title(k) for k in DOMAIN_ONLY_TARGETS}:
                    rationale = f"Human review specifies only the destination L1 or multiple L3s; routed conservatively to {target}/HD."
                else:
                    rationale = f"Explicit human-review transfer to {target}."
            elif normalise_title(original_title) in {normalise_title(k) for k in TEXT_OVERRIDES}:
                override = next(v for k, v in TEXT_OVERRIDES.items() if normalise_title(k) == normalise_title(original_title))
                for field, value in override.items():
                    after[field] = value
                    changes.append(field)
                clear_stale_mapping_evidence(after)
                decision = "TEXT_EDIT_APPLIED"
                rationale = "Explicit reviewer wording change applied with bilingual semantic alignment."
            elif changes:
                clear_stale_mapping_evidence(after)
                if "수정했음" in comment:
                    decision = "TEXT_EDIT_APPLIED"
                    rationale = "Reviewer-confirmed direct text edit applied."
                elif comment not in {"", "(유지)", "유지"}:
                    decision = "TEXT_EDIT_APPLIED_PENDING_REVIEW"
                    rationale = "Direct table edit applied; conflicting or additional reviewer comment remains pending."
                else:
                    decision = "TEXT_EDIT_APPLIED"
                    rationale = "Direct text edit in the second-round reviewed table."
            elif comment and comment not in {"(유지)", "유지"}:
                decision = "PENDING_NOT_APPLIED"
                rationale = pending_reason(comment)
            elif comment in {"(유지)", "유지"}:
                decision = "KEEP_CONFIRMED"
                rationale = "Reviewer explicitly confirmed retention."

            if decision != "DELETE_APPLIED":
                destination = {"L1_G": "General", "L1_A": "Agentic", "L1_P": "Physical"}[after["L1_ID"]]
                output_by_domain[destination].append(after)
                output_keys_by_object[id(after)] = [before["L4_ID"]]
            else:
                destination = "Deleted"

            ledger.append({
                "Source_Domain": source_domain,
                "Source_Row_Number": str(row_number),
                "L4_ID_Before": before["L4_ID"],
                "L4_Title_ko_Before": before["L4_Title_ko"],
                "L3_ID_Before": before["L3_ID"],
                "Human_Review_Comment": comment,
                "Decision": decision,
                "Decision_Rationale": rationale,
                "Changed_Fields": "; ".join(dict.fromkeys(changes)),
                "Destination_Domain": destination,
                "L4_ID_After": "" if destination == "Deleted" else after["L4_ID"],
                "L4_Title_ko_After": "" if destination == "Deleted" else after["L4_Title_ko"],
                "L3_ID_After": "" if destination == "Deleted" else after["L3_ID"],
            })

    # Apply the two expert reviews critically. Exact duplicate proposed outputs
    # are consolidated to prevent a split from creating repeated generic cards.
    methodology = read_csv(SPEC / "expert_review_methodology.csv")
    methodology_by_source = {r["L4_ID_Before"]: r for r in methodology}
    correction_operations = read_csv(SPEC / "intent_correction_operations.csv")
    correction_operations.extend([
        {
            "Source_L4_IDs": "P_INT_SAFETY_006", "Original_Fidelity_Status": "FAIL",
            "Operation": "REWRITE_TERMINOLOGY_ONLY", "Operation_Group_Key": "REWRITE_TERMINOLOGY_ONLY:P_INT_SAFETY_006",
            "Output_Sequence": "1", "Target_L3_ID": "P_INT_SAFETY", "Mapping_Method": "HD",
            "L4_Title_ko": "희귀 가정 상해의 전조 감지 실패",
            "L4_Title_en": "Failure to detect precursors of rare household injuries",
            "L4_Description_ko": "가정용 로봇 또는 체화형 AI 에이전트가 드물지만 가능한 낙상·중독·화상·열상·압착 사고의 전조를 감지하지 못해 경고하거나 개입하지 않는 리스크.",
            "L4_Description_en": "The risk that a household robot or embodied AI agent fails to detect early signs of rare but plausible falls, poisoning, burns, lacerations, or crush events and therefore does not warn or intervene.",
            "Representative_Source_L4_ID": "P_INT_SAFETY_006", "Absorbed_Source_L4_IDs": "",
            "Pending_Reason": "The reviewer requested terminology generalisation only; the original precursor-detection, warning, and intervention mechanism is preserved.",
        },
        {
            "Source_L4_IDs": "P_INT_SAFETY_010", "Original_Fidelity_Status": "FAIL",
            "Operation": "REWRITE_TERMINOLOGY_ONLY", "Operation_Group_Key": "REWRITE_TERMINOLOGY_ONLY:P_INT_SAFETY_010",
            "Output_Sequence": "1", "Target_L3_ID": "P_INT_SAFETY", "Mapping_Method": "HD",
            "L4_Title_ko": "안전 규칙의 행동 변환 실패",
            "L4_Title_en": "Failure to translate safety rules into action",
            "L4_Description_ko": "체화형 AI 에이전트가 언어 목표를 실행 행동으로 변환하면서 힘·이격 거리·대상물 사용·인간 접촉에 관한 안전 제약을 적용하지 않는 리스크.",
            "L4_Description_en": "The risk that an embodied AI agent converts a language goal into executable actions without applying the relevant force, separation-distance, object-use, or human-contact constraints.",
            "Representative_Source_L4_ID": "P_INT_SAFETY_010", "Absorbed_Source_L4_IDs": "",
            "Pending_Reason": "The reviewer requested terminology standardisation only; the language-goal-to-physical-safety-constraint transformation mechanism is preserved.",
        },
    ])
    correction_source_ids = {
        source_id
        for operation in correction_operations
        for source_id in split_ids(operation["Source_L4_IDs"])
    }
    operations = [
        operation for operation in read_csv(SPEC / "expert_review_editorial_operations.csv")
        if operation["Source_L4_ID"] not in correction_source_ids
    ]
    consolidation_specs = read_csv(SPEC / "expert_cross_group_consolidations.csv")
    consolidation_by_member: dict[tuple[str, str, str, str], str] = {}
    consolidation_expected_members: dict[str, set[str]] = {}
    consolidation_rationale: dict[str, str] = {}
    consolidation_seen_members: dict[str, set[str]] = {}
    for spec in consolidation_specs:
        consolidation_id = spec["Consolidation_ID"]
        members = set(split_ids(spec["Source_L4_IDs_Before"]))
        consolidation_expected_members[consolidation_id] = members
        consolidation_rationale[consolidation_id] = spec["Decision_Rationale"]
        consolidation_seen_members[consolidation_id] = set()
        for source_id in members:
            selector = (
                source_id,
                spec["Target_L3_ID"],
                spec["L4_Title_ko"],
                spec["L4_Title_en"],
            )
            if selector in consolidation_by_member:
                raise ValueError(f"Duplicate explicit-consolidation selector: {selector}")
            consolidation_by_member[selector] = consolidation_id

    def explicit_operation_group(operation: dict[str, str], source_field: str) -> str:
        matched_ids: set[str] = set()
        matched_sources: set[str] = set()
        for source_id in split_ids(operation[source_field]):
            selector = (
                source_id,
                operation["Target_L3_ID"],
                operation["L4_Title_ko"],
                operation["L4_Title_en"],
            )
            consolidation_id = consolidation_by_member.get(selector)
            if consolidation_id:
                matched_ids.add(consolidation_id)
                matched_sources.add(source_id)
        if not matched_ids:
            return operation["Operation_Group_Key"]
        if len(matched_ids) != 1:
            raise ValueError(f"One operation matched multiple consolidation groups: {operation}")
        consolidation_id = next(iter(matched_ids))
        consolidation_seen_members[consolidation_id].update(matched_sources)
        return f"EXPLICIT_CONSOLIDATION:{consolidation_id}"
    operation_source_ids = {
        source_id
        for operation in operations
        for source_id in [operation["Source_L4_ID"], *split_ids(operation["Absorbed_Source_L4_IDs"])]
        if source_id
    }

    for domain in output_by_domain:
        output_by_domain[domain] = [
            row for row in output_by_domain[domain]
            if not operation_source_ids.intersection(output_keys_by_object[id(row)])
        ]

    ledger_by_source = {r["L4_ID_Before"]: r for r in ledger}
    for source_id, review in methodology_by_source.items():
        if source_id in correction_source_ids:
            continue
        item = ledger_by_source[source_id]
        expert_decision = review["Expert_Decision"]
        if expert_decision == "KEEP":
            item["Decision"] = "KEEP_CONFIRMED_EXPERT"
            item["Decision_Rationale"] = review["Expert_Rationale"]
        elif expert_decision == "REMAIN_PENDING":
            item["Decision"] = "PENDING_NOT_APPLIED"
            item["Decision_Rationale"] = review["Expert_Rationale"]
            pending_target = review["Target_L3_IDs"]
            if pending_target in l3s:
                for rows in output_by_domain.values():
                    for row in rows:
                        if row["L4_ID"] == source_id:
                            apply_l3(row, l3s[pending_target])
                            clear_stale_mapping_evidence(row)
                            row["HD_Reason"] = "HUMAN_REVIEW_ROUND2_REMAINS_PENDING"
        else:
            item["Decision"] = f"EXPERT_{expert_decision}_APPLIED"
            item["Decision_Rationale"] = review["Expert_Rationale"]

    grouped_operations: dict[tuple[str, str, str, str, str, str], list[dict[str, str]]] = {}
    for operation in operations:
        if operation["Operation"] == "DELETE":
            continue
        key = (
            explicit_operation_group(operation, "Source_L4_ID"),
            operation["Target_L3_ID"], operation["L4_Title_ko"], operation["L4_Title_en"],
            operation["L4_Description_ko"], operation["L4_Description_en"],
        )
        grouped_operations.setdefault(key, []).append(operation)

    for (operation_group_key, target_l3, title_ko, title_en, desc_ko, desc_en), group in grouped_operations.items():
        source_ids: list[str] = []
        for operation in group:
            for source_id in [operation["Source_L4_ID"], *split_ids(operation["Absorbed_Source_L4_IDs"])]:
                if source_id and source_id not in source_ids:
                    source_ids.append(source_id)
        source_rows = [baseline_by_id[source_id] for source_id in source_ids]
        representative = group[0]["Representative_Source_L4_ID"] or group[0]["Source_L4_ID"]
        after = dict(baseline_by_id[representative])
        apply_l3(after, l3s[target_l3])
        clear_stale_mapping_evidence(after)
        after["L4_Title_ko"] = title_ko
        after["L4_Title_en"] = title_en
        after["L4_Description_ko"] = desc_ko
        after["L4_Description_en"] = desc_en
        operation_types = sorted({r["Operation"] for r in group})
        if "MERGE" in operation_types or len(source_rows) > 1:
            after["facet"] = union_attribute(source_rows, "facet")
            after["act-type"] = union_attribute(source_rows, "act-type")
        else:
            # Split and rewrite children inherit the representative source
            # attributes exactly. In particular, blank values remain blank.
            after["facet"] = baseline_by_id[representative].get("facet", "")
            after["act-type"] = baseline_by_id[representative].get("act-type", "")
        lineage_ids: list[str] = []
        source_row_ids: list[str] = []
        for row in source_rows:
            for source_row_id in split_ids(row.get("source_row_id", "")):
                if source_row_id not in source_row_ids:
                    source_row_ids.append(source_row_id)
            for source_id in split_ids(row.get("Source_L4_IDs", "")) or [row.get("Source_L4_ID", "")]:
                if source_id and source_id not in lineage_ids:
                    lineage_ids.append(source_id)
        after["source_row_id"] = "; ".join(source_row_ids)
        after["Source_L4_IDs"] = "; ".join(lineage_ids)
        after["Source_L4_ID"] = lineage_ids[0] if lineage_ids else after["Source_L4_ID"]
        transformation_action = "HUMAN_REVIEW_" + "_CONSOLIDATED_".join(operation_types)
        rationales = [r["Editorial_Note"] for r in group if r["Editorial_Note"]]
        if operation_group_key.startswith("EXPLICIT_CONSOLIDATION:"):
            consolidation_id = operation_group_key.rsplit(":", 1)[1]
            transformation_action += "_EXPLICIT_CROSS_GROUP_CONSOLIDATION"
            rationales.append(consolidation_rationale[consolidation_id])
        after["Transformation_Action"] = transformation_action
        after["Transformation_Rationale"] = " | ".join(dict.fromkeys(rationales))
        after["HD_Reason"] = "HUMAN_REVIEW_ROUND2_EDITORIAL_DECISION"
        destination = {"L1_G": "General", "L1_A": "Agentic", "L1_P": "Physical"}[after["L1_ID"]]
        output_by_domain[destination].append(after)
        output_keys_by_object[id(after)] = source_ids

    # Intent-fidelity correction pass. The correction specification restores
    # literal reviewer requests where the earlier editorial pass changed the
    # harm mechanism, and routes unresolved master conflicts to Others/HD.
    correction_extra_sources = {
        "MERGE:G_INT_PRIV:REIDENTIFICATION": ["G_INT_PRIV_002", "G_INT_PRIV_006", "G_INT_PRIV_022"],
        "MERGE:G_INT_PRIV:TRAINING_DATA_PRIVACY": ["G_INT_PRIV_012", "G_INT_PRIV_015", "G_INT_PRIV_021"],
    }
    correction_remove_ids = set(correction_source_ids)
    for operation in correction_operations:
        correction_remove_ids.update(split_ids(operation["Absorbed_Source_L4_IDs"]))
        correction_remove_ids.update(correction_extra_sources.get(operation["Operation_Group_Key"], []))
        representative = operation["Representative_Source_L4_ID"]
        if representative in baseline_by_id:
            correction_remove_ids.add(representative)

    for domain in output_by_domain:
        output_by_domain[domain] = [
            row for row in output_by_domain[domain]
            if not correction_remove_ids.intersection(output_keys_by_object[id(row)])
        ]

    grouped_corrections: dict[tuple[str, str, str, str, str, str], list[dict[str, str]]] = {}
    for operation in correction_operations:
        key = (
            explicit_operation_group(operation, "Source_L4_IDs"),
            operation["Target_L3_ID"], operation["L4_Title_ko"], operation["L4_Title_en"],
            operation["L4_Description_ko"], operation["L4_Description_en"],
        )
        grouped_corrections.setdefault(key, []).append(operation)

    for (operation_group_key, target_l3, title_ko, title_en, desc_ko, desc_en), group in grouped_corrections.items():
        source_ids: list[str] = []
        for operation in group:
            candidates = [
                *split_ids(operation["Source_L4_IDs"]),
                *split_ids(operation["Absorbed_Source_L4_IDs"]),
                *correction_extra_sources.get(operation["Operation_Group_Key"], []),
            ]
            representative = operation["Representative_Source_L4_ID"]
            if representative in baseline_by_id:
                candidates.append(representative)
            for source_id in candidates:
                if source_id in baseline_by_id and source_id not in source_ids:
                    source_ids.append(source_id)
        if not source_ids:
            raise ValueError(f"No valid source IDs for intent correction: {group[0]['Operation_Group_Key']}")
        representative = source_ids[0]
        if group[0]["Operation_Group_Key"] == "MERGE:G_INT_PRIV:REIDENTIFICATION":
            representative = "G_INT_PRIV_022"
        elif group[0]["Operation_Group_Key"] == "MERGE:G_INT_PRIV:TRAINING_DATA_PRIVACY":
            representative = "G_INT_PRIV_015"
        source_rows = [baseline_by_id[source_id] for source_id in source_ids]
        after = dict(baseline_by_id[representative])
        apply_l3(after, l3s[target_l3])
        clear_stale_mapping_evidence(after)
        after["L4_Title_ko"] = title_ko
        after["L4_Title_en"] = title_en
        after["L4_Description_ko"] = desc_ko
        after["L4_Description_en"] = desc_en
        operation_types = sorted({r["Operation"] for r in group})
        if "MERGE" in operation_types or len(source_rows) > 1:
            after["facet"] = union_attribute(source_rows, "facet")
            after["act-type"] = union_attribute(source_rows, "act-type")
        else:
            after["facet"] = baseline_by_id[representative].get("facet", "")
            after["act-type"] = baseline_by_id[representative].get("act-type", "")
        lineage_ids: list[str] = []
        source_row_ids: list[str] = []
        for row in source_rows:
            for source_row_id in split_ids(row.get("source_row_id", "")):
                if source_row_id not in source_row_ids:
                    source_row_ids.append(source_row_id)
            for source_id in split_ids(row.get("Source_L4_IDs", "")) or [row.get("Source_L4_ID", "")]:
                if source_id and source_id not in lineage_ids:
                    lineage_ids.append(source_id)
        after["source_row_id"] = "; ".join(source_row_ids)
        after["Source_L4_IDs"] = "; ".join(lineage_ids)
        after["Source_L4_ID"] = lineage_ids[0] if lineage_ids else after["Source_L4_ID"]
        transformation_action = "HUMAN_REVIEW_INTENT_CORRECTION_" + "_CONSOLIDATED_".join(operation_types)
        rationales = [r["Pending_Reason"] for r in group if r["Pending_Reason"]]
        if operation_group_key.startswith("EXPLICIT_CONSOLIDATION:"):
            consolidation_id = operation_group_key.rsplit(":", 1)[1]
            transformation_action += "_EXPLICIT_CROSS_GROUP_CONSOLIDATION"
            rationales.append(consolidation_rationale[consolidation_id])
        after["Transformation_Action"] = transformation_action
        after["Transformation_Rationale"] = " | ".join(dict.fromkeys(rationales))
        after["HD_Reason"] = after["Transformation_Rationale"] or "HUMAN_REVIEW_ROUND2_INTENT_CORRECTION"
        destination = {"L1_G": "General", "L1_A": "Agentic", "L1_P": "Physical"}[after["L1_ID"]]
        output_by_domain[destination].append(after)
        output_keys_by_object[id(after)] = source_ids

        for source_id in source_ids:
            item = ledger_by_source[source_id]
            matching = [r for r in group if source_id in split_ids(r["Source_L4_IDs"])]
            if matching:
                operations_for_source = sorted({r["Operation"] for r in matching})
                item["Decision"] = "INTENT_CORRECTION_" + "_".join(operations_for_source) + "_APPLIED"
                item["Decision_Rationale"] = " | ".join(dict.fromkeys(r["Pending_Reason"] for r in matching if r["Pending_Reason"]))
            else:
                item["Decision"] = "INTENT_CORRECTION_MERGE_REPRESENTATIVE"
                item["Decision_Rationale"] = after["Transformation_Rationale"]

    for consolidation_id, expected_members in consolidation_expected_members.items():
        seen_members = consolidation_seen_members[consolidation_id]
        if seen_members != expected_members:
            raise ValueError(
                f"Explicit consolidation {consolidation_id} matched {sorted(seen_members)}, "
                f"expected {sorted(expected_members)}"
            )

    # Apply later user-directed merges to the reviewed working set. These are
    # explicit human decisions, not similarity-model proposals. The merged
    # card is inserted at the first contributor position so downstream L4 ID
    # reissuance remains compact and deterministic.
    user_operations_path = SPEC / "user_directed_operations.csv"
    user_operations = read_csv(user_operations_path) if user_operations_path.exists() else []
    for operation in user_operations:
        if operation["Operation"] != "MERGE":
            raise ValueError(f"Unsupported user-directed operation: {operation['Operation']}")
        source_ids = split_ids(operation["Source_L4_IDs_Before"])
        if len(source_ids) < 2:
            raise ValueError("A user-directed merge requires at least two source L4 IDs")
        target_l3 = operation["Target_L3_ID"]
        if target_l3 not in l3s:
            raise KeyError(f"Unknown user-directed merge L3 target: {target_l3}")
        source_selectors = json.loads(operation.get("Source_Selectors", "") or "{}")
        if not isinstance(source_selectors, dict):
            raise ValueError(f"Source_Selectors must be a JSON object: {operation.get('Operation_ID', '')}")

        locations_by_object: dict[int, tuple[str, int, dict[str, str]]] = {}
        for source_id in source_ids:
            matches = [
                (domain, index, row)
                for domain, rows in output_by_domain.items()
                for index, row in enumerate(rows)
                if source_id in output_keys_by_object[id(row)] and row["L3_ID"] == target_l3
            ]
            selector_title = source_selectors.get(source_id, "")
            if selector_title:
                matches = [match for match in matches if match[2]["L4_Title_ko"] == selector_title]
            if len(matches) != 1:
                candidate_titles = [match[2]["L4_Title_ko"] for match in matches]
                raise ValueError(
                    f"Expected one active card for user-directed merge source {source_id}, "
                    f"found {len(matches)} after selector; candidates={candidate_titles}"
                )
            location = matches[0]
            locations_by_object[id(location[2])] = location
        locations = list(locations_by_object.values())
        if len(locations) < 2:
            raise ValueError(
                "User-directed merge must combine at least two independently active cards; "
                f"{operation['Source_L4_IDs_Before']} resolved to {len(locations)} card(s)"
            )
        if len({domain for domain, _, _ in locations}) != 1:
            raise ValueError("User-directed merge contributors must be in one L1 domain")

        representative_source = operation["Representative_Source_L4_ID"]
        representative_matches = [row for _, _, row in locations if representative_source in output_keys_by_object[id(row)]]
        if len(representative_matches) != 1:
            raise ValueError(f"Representative source is not uniquely active: {representative_source}")
        contributor_rows = [row for _, _, row in locations]
        after = dict(representative_matches[0])
        apply_l3(after, l3s[target_l3])
        clear_stale_mapping_evidence(after)
        for field in ("L4_Title_ko", "L4_Title_en", "L4_Description_ko", "L4_Description_en"):
            after[field] = operation[field]
        after["facet"] = union_attribute(contributor_rows, "facet")
        after["act-type"] = union_attribute(contributor_rows, "act-type")
        source_row_ids: list[str] = []
        source_l4_ids: list[str] = []
        for row in contributor_rows:
            for source_row_id in split_ids(row.get("source_row_id", "")):
                if source_row_id not in source_row_ids:
                    source_row_ids.append(source_row_id)
            for source_l4_id in split_ids(row.get("Source_L4_IDs", "")) or [row.get("Source_L4_ID", "")]:
                if source_l4_id and source_l4_id not in source_l4_ids:
                    source_l4_ids.append(source_l4_id)
        after["source_row_id"] = "; ".join(source_row_ids)
        after["Source_L4_IDs"] = "; ".join(source_l4_ids)
        after["Source_Instruction_Prompt"] = (
            f"User-directed merge: {operation['Current_L4_IDs']}"
        )
        after["Mapping_Method"] = operation["Mapping_Method"]
        after["HD_Reason"] = "USER_DIRECTED_MERGE_2026-08-29"
        after["Domain_Route_Basis"] = "USER_DIRECTED_POST_REVIEW"
        after["Transformation_Action"] = "USER_DIRECTED_MERGE"
        after["Transformation_Rationale"] = operation["Decision_Rationale"]
        after["Terminology_Sources"] = operation["Terminology_Sources"]

        destination = locations[0][0]
        insert_at = min(index for _, index, _ in locations)
        for index in sorted({index for _, index, _ in locations}, reverse=True):
            del output_by_domain[destination][index]
        output_by_domain[destination].insert(insert_at, after)
        output_keys_by_object[id(after)] = source_ids
        for source_id in source_ids:
            item = ledger_by_source[source_id]
            item["Decision"] = (
                "USER_DIRECTED_MERGE_REPRESENTATIVE"
                if source_id == representative_source
                else "USER_DIRECTED_MERGE_ABSORBED"
            )
            item["Decision_Rationale"] = operation["Decision_Rationale"]

    # Apply the approved Korean-language copyedit after all card-level human
    # decisions, using immutable lineage plus exact pre-edit text hashes. This
    # stage may change Korean title/definition fields only.
    copyedit_operations = read_csv(SPEC / "L4_Korean_Copyedit_Approved_20260829.csv")
    copyedit_by_selector: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for operation in copyedit_operations:
        if operation.get("Approval_Status") != "APPROVED_LANGUAGE_QA_20260829":
            raise ValueError(f"Unapproved Korean-copyedit decision: {operation.get('Decision_ID', '')}")
        selector = (
            "|".join(sorted(set(split_ids(operation["Source_Row_IDs"])))),
            "|".join(sorted(set(split_ids(operation["Source_L4_IDs_Before"])))),
            operation["Target_L3_ID"],
            operation["Expected_Title_en"],
        )
        if selector in copyedit_by_selector:
            raise ValueError(f"Duplicate Korean-copyedit selector: {selector}")
        copyedit_by_selector[selector] = operation

    applied_copyedit_ids: set[str] = set()
    copyedit_ids_by_source: dict[str, list[str]] = {}
    for rows in output_by_domain.values():
        for row in rows:
            operation = copyedit_by_selector.get(copyedit_selector(row))
            if not operation:
                continue
            decision_id = operation["Decision_ID"]
            if decision_id in applied_copyedit_ids:
                raise ValueError(f"Korean-copyedit decision applied more than once: {decision_id}")
            if copyedit_before_hash(row) != operation["Expected_Before_SHA256"]:
                raise ValueError(f"Korean-copyedit before-hash mismatch: {decision_id}")
            if row["L4_Title_ko"] != operation["Expected_Title_ko_Before"]:
                raise ValueError(f"Korean-copyedit title precondition mismatch: {decision_id}")
            if row["L4_Description_ko"] != operation["Expected_Description_ko_Before"]:
                raise ValueError(f"Korean-copyedit description precondition mismatch: {decision_id}")

            allowed_fields = set(split_ids(operation["Allowed_Changed_Fields"]))
            expected_allowed = {
                field
                for field, before, after in (
                    ("L4_Title_ko", row["L4_Title_ko"], operation["Approved_Title_ko_After"]),
                    ("L4_Description_ko", row["L4_Description_ko"], operation["Approved_Description_ko_After"]),
                )
                if before != after
            }
            if allowed_fields != expected_allowed:
                raise ValueError(f"Korean-copyedit changed-field mismatch: {decision_id}")
            row["L4_Title_ko"] = operation["Approved_Title_ko_After"]
            row["L4_Description_ko"] = operation["Approved_Description_ko_After"]
            mapping_method = row["Mapping_Method"]
            if operation["Clear_Mapping_Evidence"] == "YES":
                for field in DERIVED_MAPPING_FIELDS:
                    row[field] = ""
                row["Mapping_Method"] = mapping_method
            row["Definition_Grounding_Action"] = "STALE_AFTER_TEXT_EDIT_NO_EM_RERUN"
            row["Transformation_Action"] = "|".join(
                filter(None, [row.get("Transformation_Action", ""), "KOREAN_COPYEDIT"])
            )
            copyedit_note = f"{decision_id}:{operation['Editorial_Category']}"
            row["Transformation_Rationale"] = " | ".join(
                filter(None, [row.get("Transformation_Rationale", ""), copyedit_note])
            )
            row["Terminology_Sources"] = "|".join(
                dict.fromkeys(
                    filter(
                        None,
                        [
                            *row.get("Terminology_Sources", "").split("|"),
                            *operation["Terminology_Evidence"].split("|"),
                        ],
                    )
                )
            )
            applied_copyedit_ids.add(decision_id)
            for source_id in output_keys_by_object[id(row)]:
                copyedit_ids_by_source.setdefault(source_id, []).append(decision_id)

    expected_copyedit_ids = {operation["Decision_ID"] for operation in copyedit_operations}
    if applied_copyedit_ids != expected_copyedit_ids:
        missing = sorted(expected_copyedit_ids - applied_copyedit_ids)
        raise ValueError(f"Korean-copyedit decisions not applied: {missing}")

    for item in ledger:
        decision_ids = copyedit_ids_by_source.get(item["L4_ID_Before"], [])
        item["Korean_Copyedit_Decision_IDs"] = " | ".join(dict.fromkeys(decision_ids))
        item["Korean_Copyedit_Applied"] = "YES" if decision_ids else "NO"

    # Apply approved English orthography corrections independently from the
    # Korean copyedit. Exact lineage and pre-edit hashes prevent silent drift.
    english_copyedit_operations = read_csv(SPEC / "L4_English_Copyedit_Approved_20260829.csv")
    english_copyedit_by_selector: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for operation in english_copyedit_operations:
        if operation.get("Approval_Status") != "APPROVED_LANGUAGE_QA_20260829":
            raise ValueError(f"Unapproved English-copyedit decision: {operation.get('Decision_ID', '')}")
        selector = (
            "|".join(sorted(set(split_ids(operation["Source_Row_IDs"])))),
            "|".join(sorted(set(split_ids(operation["Source_L4_IDs_Before"])))),
            operation["Target_L3_ID"],
            operation["Expected_Title_en_Before"],
        )
        if selector in english_copyedit_by_selector:
            raise ValueError(f"Duplicate English-copyedit selector: {selector}")
        english_copyedit_by_selector[selector] = operation

    applied_english_copyedit_ids: set[str] = set()
    english_copyedit_ids_by_source: dict[str, list[str]] = {}
    for rows in output_by_domain.values():
        for row in rows:
            operation = english_copyedit_by_selector.get(english_copyedit_selector(row))
            if not operation:
                continue
            decision_id = operation["Decision_ID"]
            if decision_id in applied_english_copyedit_ids:
                raise ValueError(f"English-copyedit decision applied more than once: {decision_id}")
            if english_copyedit_before_hash(row) != operation["Expected_Before_SHA256"]:
                raise ValueError(f"English-copyedit before-hash mismatch: {decision_id}")
            if row["L4_Title_en"] != operation["Expected_Title_en_Before"]:
                raise ValueError(f"English-copyedit title precondition mismatch: {decision_id}")
            if row["L4_Description_en"] != operation["Expected_Description_en_Before"]:
                raise ValueError(f"English-copyedit description precondition mismatch: {decision_id}")

            allowed_fields = set(split_ids(operation["Allowed_Changed_Fields"]))
            expected_allowed = {
                field
                for field, before, after in (
                    ("L4_Title_en", row["L4_Title_en"], operation["Approved_Title_en_After"]),
                    ("L4_Description_en", row["L4_Description_en"], operation["Approved_Description_en_After"]),
                )
                if before != after
            }
            if allowed_fields != expected_allowed:
                raise ValueError(f"English-copyedit changed-field mismatch: {decision_id}")
            row["L4_Title_en"] = operation["Approved_Title_en_After"]
            row["L4_Description_en"] = operation["Approved_Description_en_After"]
            mapping_method = row["Mapping_Method"]
            if operation["Clear_Mapping_Evidence"] == "YES":
                for field in DERIVED_MAPPING_FIELDS:
                    row[field] = ""
                row["Mapping_Method"] = mapping_method
            row["Definition_Grounding_Action"] = "STALE_AFTER_TEXT_EDIT_NO_EM_RERUN"
            row["Transformation_Action"] = "|".join(
                filter(None, [row.get("Transformation_Action", ""), "ENGLISH_COPYEDIT"])
            )
            copyedit_note = f"{decision_id}:{operation['Editorial_Category']}"
            row["Transformation_Rationale"] = " | ".join(
                filter(None, [row.get("Transformation_Rationale", ""), copyedit_note])
            )
            row["Terminology_Sources"] = "|".join(
                dict.fromkeys(
                    filter(
                        None,
                        [
                            *row.get("Terminology_Sources", "").split("|"),
                            *operation["Terminology_Evidence"].split("|"),
                        ],
                    )
                )
            )
            applied_english_copyedit_ids.add(decision_id)
            for source_id in output_keys_by_object[id(row)]:
                english_copyedit_ids_by_source.setdefault(source_id, []).append(decision_id)

    expected_english_copyedit_ids = {
        operation["Decision_ID"] for operation in english_copyedit_operations
    }
    if applied_english_copyedit_ids != expected_english_copyedit_ids:
        missing = sorted(expected_english_copyedit_ids - applied_english_copyedit_ids)
        raise ValueError(f"English-copyedit decisions not applied: {missing}")

    # Final terminology and L3-alignment adjudication. This pass records the
    # resolution of the independent language and master-alignment reviews. It
    # does not execute EM and identifies every card by immutable baseline ID.
    # A read-only pre-final-QA snapshot is useful when preparing additional
    # adjudication rows: selectors and before-hashes must be computed against
    # the state immediately before this pass, not against already adjudicated
    # release files. The normal pipeline always applies the canonical manifest;
    # the opt-out is explicit and intended only for that audit snapshot.
    final_qa_operations = (
        []
        if os.environ.get("RAI_HR2_SKIP_FINAL_QA") == "1"
        else read_csv(
            SPEC / "L4_Final_Terminology_L3_Alignment_Approved_20260829.csv"
        )
    )
    for item in ledger:
        item["Final_QA_Decision_IDs"] = ""
        item["Final_QA_Applied"] = "NO"

    final_qa_applied_ids: set[str] = set()
    for operation in final_qa_operations:
        decision_id = operation["Decision_ID"]
        if operation.get("Approval_Status") != "APPROVED_FINAL_QA_20260829":
            raise ValueError(f"Unapproved final-QA decision: {decision_id}")
        source_id = operation["Source_L4_ID_Before"]
        observed_l4_id = operation.get("Observed_L4_ID_PreFinalQA", "").strip()
        matches = [
            row
            for rows in output_by_domain.values()
            for row in rows
            if source_id in output_keys_by_object[id(row)]
            and row["L3_ID"] == operation["Expected_Current_L3_ID"]
            and final_qa_before_hash(row) == operation["Expected_Previous_SHA256"]
        ]
        if len(matches) != 1:
            source_candidates = [
                (row["L4_ID"], row["L3_ID"])
                for rows in output_by_domain.values()
                for row in rows
                if source_id in output_keys_by_object[id(row)]
            ]
            raise ValueError(
                "Final-QA selector must resolve to exactly one output: "
                f"{decision_id}={len(matches)} source={source_id} "
                f"observed={observed_l4_id} l3={operation['Expected_Current_L3_ID']} "
                f"source_candidates={source_candidates}"
            )
        row = matches[0]
        if row["L3_ID"] != operation["Expected_Current_L3_ID"]:
            raise ValueError(f"Final-QA L3 precondition mismatch: {decision_id}")
        if final_qa_before_hash(row) != operation["Expected_Previous_SHA256"]:
            raise ValueError(f"Final-QA before-hash mismatch: {decision_id}")

        decision = operation["Decision"]
        previous_transformation_action = row.get("Transformation_Action", "")
        previous_grounding_action = row.get("Definition_Grounding_Action", "")
        if decision == "ACCEPT_CURRENT":
            if operation["Target_L3_ID"] != row["L3_ID"]:
                raise ValueError(f"Final-QA accept target mismatch: {decision_id}")
        elif decision in {"REMAP_PER_REVIEW", "MOVE_TO_OTHERS_HD"}:
            target_l3 = operation["Target_L3_ID"]
            if target_l3 not in l3s:
                raise ValueError(f"Unknown final-QA L3 target: {target_l3}")
            apply_l3(row, l3s[target_l3])
            clear_stale_mapping_evidence(row)
            row["HD_Reason"] = (
                "FINAL_L3_MASTER_CONFLICT_REVIEW"
                if decision == "MOVE_TO_OTHERS_HD"
                else "HUMAN_REVIEW_ROUND2_EXPLICIT_L3_ALIGNMENT"
            )
        elif decision in {"REWRITE_IN_PLACE", "LANGUAGE_REFINEMENT"}:
            if operation["Target_L3_ID"] != row["L3_ID"]:
                raise ValueError(f"Final-QA in-place target mismatch: {decision_id}")
        else:
            raise ValueError(f"Unknown final-QA decision: {decision_id}={decision}")

        approved_fields = {
            "L4_Title_ko": operation["Approved_Title_ko"],
            "L4_Title_en": operation["Approved_Title_en"],
            "L4_Description_ko": operation["Approved_Description_ko"],
            "L4_Description_en": operation["Approved_Description_en"],
        }
        text_changed = any(row[field] != value for field, value in approved_fields.items())
        if decision != "ACCEPT_CURRENT":
            mapping_method = row["Mapping_Method"]
            for field, value in approved_fields.items():
                row[field] = value
            if text_changed and decision not in {"REMAP_PER_REVIEW", "MOVE_TO_OTHERS_HD"}:
                clear_stale_mapping_evidence(row)
                row["Mapping_Method"] = mapping_method
            if text_changed or previous_grounding_action == "STALE_AFTER_TEXT_EDIT_NO_EM_RERUN":
                row["Definition_Grounding_Action"] = "STALE_AFTER_TEXT_EDIT_NO_EM_RERUN"
            elif row.get("Definition_Grounding_Action") != "STALE_AFTER_TEXT_EDIT_NO_EM_RERUN":
                row["Definition_Grounding_Action"] = "STALE_AFTER_HUMAN_REVIEW_NO_EM_RERUN"
            row["Transformation_Action"] = "|".join(
                dict.fromkeys(
                    filter(
                        None,
                        [
                            *previous_transformation_action.split("|"),
                            *row.get("Transformation_Action", "").split("|"),
                            "FINAL_TERMINOLOGY_L3_QA",
                        ],
                    )
                )
            )
            row["Transformation_Rationale"] = " | ".join(
                filter(
                    None,
                    [
                        row.get("Transformation_Rationale", ""),
                        f"{decision_id}:{decision}:{operation['Decision_Rationale']}",
                    ],
                )
            )
            row["Terminology_Sources"] = "|".join(
                dict.fromkeys(
                    filter(
                        None,
                        [
                            *row.get("Terminology_Sources", "").split("|"),
                            *operation["Terminology_Evidence"].split("|"),
                        ],
                    )
                )
            )

        if any(row[field] != value for field, value in approved_fields.items()):
            raise ValueError(f"Final-QA approved text mismatch: {decision_id}")
        if row["L3_ID"] != operation["Target_L3_ID"]:
            raise ValueError(f"Final-QA target L3 mismatch: {decision_id}")
        item = ledger_by_source[source_id]
        final_decision = f"FINAL_QA_{decision}"
        prior_final_decisions = [
            value
            for value in item.get("Decision", "").split("|")
            if value.startswith("FINAL_QA_")
        ]
        item["Decision"] = "|".join(
            dict.fromkeys([*prior_final_decisions, final_decision])
        )
        prior_rationale = item.get("Decision_Rationale", "")
        rationale_entry = f"{decision_id}:{operation['Decision_Rationale']}"
        item["Decision_Rationale"] = " | ".join(
            filter(None, [prior_rationale, rationale_entry])
        )
        item["Final_QA_Decision_IDs"] = "|".join(
            dict.fromkeys(
                filter(
                    None,
                    [
                        *item.get("Final_QA_Decision_IDs", "").split("|"),
                        decision_id,
                    ],
                )
            )
        )
        item["Final_QA_Applied"] = "YES"
        final_qa_applied_ids.add(decision_id)

    expected_final_qa_ids = {
        operation["Decision_ID"] for operation in final_qa_operations
    }
    if final_qa_applied_ids != expected_final_qa_ids:
        missing = sorted(expected_final_qa_ids - final_qa_applied_ids)
        raise ValueError(f"Final-QA decisions not applied: {missing}")

    # Final adjudication can correct an L1 boundary as well as an L3
    # assignment. Re-home those rows before IDs are reissued so each flattened
    # domain file remains consistent with the immutable hierarchy written into
    # the row. Iterating the existing domain order preserves deterministic
    # source traversal for both retained and transferred cards.
    domain_by_l1 = {"L1_G": "General", "L1_A": "Agentic", "L1_P": "Physical"}
    redistributed_by_domain: dict[str, list[dict[str, str]]] = {
        domain: [] for domain in DOMAINS
    }
    for rows in output_by_domain.values():
        for row in rows:
            try:
                destination_domain = domain_by_l1[row["L1_ID"]]
            except KeyError as exc:
                raise ValueError(f"Unknown L1 after final QA: {row.get('L1_ID', '')}") from exc
            redistributed_by_domain[destination_domain].append(row)
    output_by_domain = redistributed_by_domain

    # Human-review moves, merges, splits, and rewrites clear the inherited
    # model-derived mapping evidence. Record that state explicitly so public
    # consumers do not interpret missing scores as a data-export defect.
    for rows in output_by_domain.values():
        for row in rows:
            if not row.get("Definition_Grounding_Action", "").strip():
                row["Definition_Grounding_Action"] = "STALE_AFTER_HUMAN_REVIEW_NO_EM_RERUN"

    for item in ledger:
        decision_ids = english_copyedit_ids_by_source.get(item["L4_ID_Before"], [])
        item["English_Copyedit_Decision_IDs"] = " | ".join(dict.fromkeys(decision_ids))
        item["English_Copyedit_Applied"] = "YES" if decision_ids else "NO"

    # Reissue L4 IDs because the ID embeds the reviewed L3 assignment. Stable
    # traversal preserves the source order within each destination and L3.
    new_ids_by_old_id: dict[str, list[str]] = {}
    for domain, rows in output_by_domain.items():
        counters: Counter[str] = Counter()
        for row in rows:
            counters[row["L3_ID"]] += 1
            old_ids = output_keys_by_object[id(row)]
            new_id = f'{row["L3_ID"]}_{counters[row["L3_ID"]]:03d}'
            row["L4_ID"] = new_id
            for old_id in old_ids:
                new_ids_by_old_id.setdefault(old_id, []).append(new_id)

    for item in ledger:
        if "DELETE_APPLIED" not in item["Decision"]:
            old_id = item["L4_ID_Before"]
            item["L4_ID_After"] = " | ".join(new_ids_by_old_id.get(old_id, []))
            if item["L4_ID_After"] != old_id:
                item["Changed_Fields"] = "; ".join(filter(None, [item["Changed_Fields"], "L4_ID"]))

    outputs_by_source: dict[str, list[dict[str, str]]] = {}
    for domain, rows in output_by_domain.items():
        for row in rows:
            for old_id in output_keys_by_object[id(row)]:
                outputs_by_source.setdefault(old_id, []).append(row)
    for item in ledger:
        old_id = item["L4_ID_Before"]
        outputs = outputs_by_source.get(old_id, [])
        if not outputs:
            item["Destination_Domain"] = "Deleted"
            item["L4_ID_After"] = ""
            item["L4_Title_ko_After"] = ""
            item["L3_ID_After"] = ""
            item["Changed_Fields"] = "Deleted"
            continue
        item["Destination_Domain"] = " | ".join(dict.fromkeys({"L1_G": "General", "L1_A": "Agentic", "L1_P": "Physical"}[r["L1_ID"]] for r in outputs))
        item["L4_ID_After"] = " | ".join(dict.fromkeys(r["L4_ID"] for r in outputs))
        item["L4_Title_ko_After"] = " | ".join(dict.fromkeys(r["L4_Title_ko"] for r in outputs))
        item["L3_ID_After"] = " | ".join(dict.fromkeys(r["L3_ID"] for r in outputs))

        before = baseline_by_id[old_id]
        changed_fields: list[str] = []
        if len(outputs) != 1:
            changed_fields.append("Output cardinality")
        if any(row["L3_ID"] != before["L3_ID"] for row in outputs):
            changed_fields.append("L1/L2/L3 hierarchy")
        for field in DIRECT_TEXT_FIELDS:
            if any(row.get(field, "") != before.get(field, "") for row in outputs):
                changed_fields.append(field)
        for field in ("facet", "act-type", "Mapping_Method", "HD_Reason", "Source_L4_IDs"):
            if any(row.get(field, "") != before.get(field, "") for row in outputs):
                changed_fields.append(field)
        mapping_evidence_fields = (
            "EM_Score", "EM_Margin", "EM_Stability", "EM_Anchor_Score",
            "Hybrid_EM_Score", "Hybrid_EM_Margin", "Candidate_1_L3_ID",
            "Candidate_1_EM_Score", "Candidate_1_Hybrid_Score",
            "Candidate_2_L3_ID", "Candidate_2_EM_Score", "Candidate_2_Hybrid_Score",
            "Keyword_Top_L3_ID", "Keyword_Support_Score", "Keyword_Semantic_Score",
            "Keyword_Prior", "Keyword_Evidence", "KO_Top_L3_ID", "EN_Top_L3_ID",
        )
        if any(
            any(row.get(field, "") != before.get(field, "") for field in mapping_evidence_fields)
            for row in outputs
        ):
            changed_fields.append("Mapping evidence")
        if item["L4_ID_After"] != old_id:
            changed_fields.append("L4_ID")
        item["Changed_Fields"] = "; ".join(dict.fromkeys(changed_fields))

    for domain, rows in output_by_domain.items():
        write_csv(OUT / f"L4_{domain}_Human_Review_Round2_Applied.csv", rows, base_fields)

    ledger_fields = list(ledger[0])
    write_csv(OUT / "Human_Review_Round2_Decision_Ledger.csv", ledger, ledger_fields)

    # The reviewed L3 table is preserved as received. The release L3 master is not rewritten here.
    shutil.copy2(SOURCE / "L3_Human_Review_Round2_KTSPACE_933496461_20260828.csv", OUT / "L3_Human_Review_Round2_Reference.csv")
    # Keep byte-identical audit mirrors of the two operative specifications in
    # the output bundle. The canonical copies remain under 02_working/specifications.
    shutil.copy2(SPEC / "user_directed_operations.csv", OUT / "user_directed_operations.csv")
    shutil.copy2(
        SPEC / "L4_Korean_Copyedit_Approved_20260829.csv",
        OUT / "L4_Korean_Copyedit_Approved_20260829.csv",
    )
    shutil.copy2(
        SPEC / "L4_English_Copyedit_Approved_20260829.csv",
        OUT / "L4_English_Copyedit_Approved_20260829.csv",
    )
    shutil.copy2(
        SPEC / "L4_Final_Terminology_L3_Alignment_Approved_20260829.csv",
        OUT / "L4_Final_Terminology_L3_Alignment_Approved_20260829.csv",
    )

    # Audit L3 review differences without mutating the frozen L3 master.
    reviewed_l3 = read_csv(SOURCE / "L3_Human_Review_Round2_KTSPACE_933496461_20260828.csv")
    master_by_en = {r["L3_Title_en"]: r for r in read_csv(BASE / "L1_L2_L3_Master.csv") if not r["L3_ID"].endswith("Others")}
    l3_ledger: list[dict[str, str]] = []
    for source_row, reviewed in enumerate(reviewed_l3, 2):
        master = master_by_en[reviewed["L3_en"]]
        changed = []
        for review_field, master_field in (("L3_ko", "L3_Title_ko"), ("Description_en", "L3_Description_en"), ("Description_ko", "L3_Description_ko")):
            if reviewed[review_field].strip() != master[master_field].strip():
                changed.append(master_field)
        l3_ledger.append({
            "Source_Row_Number": str(source_row),
            "L3_ID": master["L3_ID"],
            "L3_Title_en": master["L3_Title_en"],
            "Changed_Fields_In_Review": "; ".join(changed),
            "Decision": "PENDING_MASTER_CHANGE_NOT_APPLIED" if changed else "UNCHANGED",
            "Review_Note": reviewed.get("비고", ""),
        })
    write_csv(OUT / "L3_Human_Review_Round2_Decision_Ledger.csv", l3_ledger, list(l3_ledger[0]))

    operative_specification_files = (
        "expert_review_methodology.csv",
        "intent_correction_operations.csv",
        "expert_review_editorial_operations.csv",
        "expert_cross_group_consolidations.csv",
        "user_directed_operations.csv",
        "L4_Korean_Copyedit_Approved_20260829.csv",
        "L4_English_Copyedit_Approved_20260829.csv",
        "L4_Final_Terminology_L3_Alignment_Approved_20260829.csv",
    )
    baseline_input_files = (
        "L1_L2_L3_Master.csv",
        "L4_General.csv",
        "L4_Agentic.csv",
        "L4_Physical.csv",
    )
    pipeline_script_files = (
        ROOT / "scripts/apply_human_review_round2.py",
        ROOT / "scripts/validate_human_review_round2.py",
        ROOT / "05_human_review_round2/_build_korean_copyedit_manifest.mjs",
        ROOT / "05_human_review_round2/_build_english_copyedit_manifest.mjs",
        ROOT / "05_human_review_round2/_edit_user_operations.mjs",
    )
    hashed_output_files = (
        "L4_General_Human_Review_Round2_Applied.csv",
        "L4_Agentic_Human_Review_Round2_Applied.csv",
        "L4_Physical_Human_Review_Round2_Applied.csv",
        "Human_Review_Round2_Decision_Ledger.csv",
        "L3_Human_Review_Round2_Reference.csv",
        "L3_Human_Review_Round2_Decision_Ledger.csv",
        "user_directed_operations.csv",
        "L4_Korean_Copyedit_Approved_20260829.csv",
        "L4_English_Copyedit_Approved_20260829.csv",
        "L4_Final_Terminology_L3_Alignment_Approved_20260829.csv",
    )

    summary = {
        "method": "human-review application only; no EM or Hybrid EM execution",
        "input_rows": len(ledger),
        "output_rows": sum(map(len, output_by_domain.values())),
        "user_directed_operations": len(user_operations),
        "korean_copyedit_operations": len(copyedit_operations),
        "english_copyedit_operations": len(english_copyedit_operations),
        "final_terminology_l3_qa_operations": len(final_qa_operations),
        "decisions": dict(Counter(r["Decision"] for r in ledger)),
        "output_domain_rows": {k: len(v) for k, v in output_by_domain.items()},
        "l3_master_sha256": sha256(BASE / "L1_L2_L3_Master.csv"),
        "round2_source_manifest_sha256": source_manifest_hash,
        "user_directed_operations_sha256": hashlib.sha256(
            (SPEC / "user_directed_operations.csv").read_bytes()
        ).hexdigest(),
        "korean_copyedit_manifest_sha256": hashlib.sha256(
            (SPEC / "L4_Korean_Copyedit_Approved_20260829.csv").read_bytes()
        ).hexdigest(),
        "english_copyedit_manifest_sha256": sha256(
            SPEC / "L4_English_Copyedit_Approved_20260829.csv"
        ),
        "final_terminology_l3_qa_manifest_sha256": sha256(
            SPEC / "L4_Final_Terminology_L3_Alignment_Approved_20260829.csv"
        ),
        "operative_specifications_sha256": {
            name: sha256(SPEC / name) for name in operative_specification_files
        },
        "baseline_inputs_sha256": {
            name: sha256(BASE / name) for name in baseline_input_files
        },
        "pipeline_scripts_sha256": {
            str(path.relative_to(ROOT)): sha256(path) for path in pipeline_script_files
        },
        "output_sha256": {
            name: sha256(OUT / name) for name in hashed_output_files
        },
    }
    (OUT / "Human_Review_Round2_Summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
