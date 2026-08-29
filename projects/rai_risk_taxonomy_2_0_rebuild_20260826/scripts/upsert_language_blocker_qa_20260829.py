#!/usr/bin/env python3
"""Append independently confirmed language and L3-boundary blocker fixes."""

from __future__ import annotations

import csv
import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "05_human_review_round2"
SPEC = ROOT / "02_working" / "specifications" / "human_review_round2"
MANIFEST = SPEC / "L4_Final_Terminology_L3_Alignment_Approved_20260829.csv"
ARCHIVE = SPEC / "archive" / "pre_language_blocker_correction_20260829"
EVIDENCE = (
    "L3_MASTER|HUMAN_REVIEW_ROUND2|KOREAN_LANGUAGE_QA_20260829|"
    "BRITISH_ENGLISH_QA_20260829|EXPERT_TERMINOLOGY_REVIEW_20260829|"
    "POLICY_AND_TECHNICAL_TERMINOLOGY_QA"
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def before_hash(row: dict[str, str]) -> str:
    value = "\x1f".join(
        [
            row["L3_ID"], row["L4_Title_ko"], row["L4_Title_en"],
            row["L4_Description_ko"], row["L4_Description_en"],
        ]
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


CHANGES = [
    {
        "id": "FQA-305", "source": "G_SYS_MISINFO_005", "target": "A_SYS_DECEPT",
        "description_en": "The risk that an AI system misleads humans or other systems through strategic deception, misconduct learned from human-authored data, an inaccurate world model, or representations of human-like understanding or care that it does not possess; conceals its goals, capabilities, or intentions; or complies only when monitored, thereby enabling unauthorised actions and causing harm.",
        "rationale": "영문 정의가 한국어 정의의 전략적 기만, 학습된 부정행위, 부정확한 월드 모델, 허위 돌봄 표상 및 감독 회피 기제를 누락해 한영 의미를 일치시킨다.",
    },
    {
        "id": "FQA-306", "source": "P_INT_SAFETY_014", "target": "P_INT_SAFETY",
        "description_ko": "비전-언어 모델이 장면을 올바르게 관찰했음에도 제안된 행동의 물리적 결과, 물체 어포던스 또는 사람이 위해에 노출될 가능성을 잘못 추론하는 리스크.",
        "rationale": "원천 영문은 장면 관찰 후 물리적 결과·어포던스·사람 노출 위험의 추론 오류를 다루므로 다른 기제인 안전성 분류기 위음성 문안을 제거한다.",
    },
    {
        "id": "FQA-307", "source": "P_SYS_CONTROL_022", "target": "P_SYS_CONTROL",
        "description_en": "The risk that human motion is retargeted to a humanoid body in a way that violates the robot's physical limits, contact constraints, or safe-posture requirements, causing unstable posture, collision, or contact injury.",
        "rationale": "동작 재매핑의 대상을 휴머노이드 신체로 명시하여 한국어 정의와 영문 기제를 정확히 일치시킨다.",
    },
    {
        "id": "FQA-308", "source": "G_INT_REL_004", "target": "G_INT_REL",
        "description_en": "The risk that users form one-sided parasocial bonds with AI agents and those bonds are exploited or undermine users' emotional stability.",
        "rationale": "병렬 관계절의 문법을 바로잡아 유대의 악용과 사용자의 정서적 불안정이라는 두 결과를 분명히 한다.",
    },
    {
        "id": "FQA-309", "source": "G_INT_UNETH_010", "target": "G_INT_UNETH",
        "description_en": "The risk that an AI system is intentionally designed to harm animals in ways that either reflect and amplify prevailing social values or are legally permitted.",
        "rationale": "AI system을 행위 주체로 명시하고 의도적 설계, 사회 가치의 반영·증폭, 법적 허용이라는 한국어 기제를 영문에 맞춘다.",
    },
    {
        "id": "FQA-310", "source": "A_SYS_SELFCOR_002", "target": "G_SYS_CONTEXT",
        "description_en": "The risk that an AI agent or evaluator fails to identify a safety risk that is contextually present in a multi-turn interaction record.",
        "rationale": "중복된 범용 에이전트 문구를 제거하고 다중 턴 기록에서 맥락상 존재하는 안전 위험을 식별하지 못하는 기제를 직접 서술한다.",
    },
    {
        "id": "FQA-311", "source": "G_SYS_OEXT_007", "target": "G_Others",
        "description_en": "The risk that malicious actors gain unrestricted or unmonitored access to general-purpose AI systems and exploit their broad capabilities to cause large-scale harm.",
        "rationale": "악의적 행위자의 무제한 접근과 오용은 검증된 역량·권한·전문성·범위를 넘어 수행하는 G_SYS_OEXT의 기제와 다르며, 피해 기제가 특정되지 않아 General Others와 HD로 보존한다.",
    },
    {
        "id": "FQA-312", "source": "G_SOC_ECON_005", "target": "G_SOC_ECON",
        "description_ko": "인공 에이전트가 더 빠른 작업 수행과 변화 적응, 방대한 지식 기반으로 인간을 직접 능가하여 인간 노동이 상대적으로 비싸고 비효율적인 선택이 되고, 조직이 속도를 맞추기 위해 통제권을 넘기는 리스크. 노동자는 일자리에서 밀려나 자동화된 산업에 재진입하기 어려워지고, 인간의 기여는 경제적으로 주변화되는 리스크.",
        "rationale": "조사와 문장 호응을 바로잡아 노동자가 일자리에서 밀려나고 인간의 기여가 주변화되는 경제적 결과를 자연스럽게 서술한다.",
    },
    {
        "id": "FQA-313", "source": "G_SOC_ENV_008", "target": "G_SOC_ENV",
        "description_ko": "모델의 개발과 배포가 막대한 에너지를 소비하고 모델 대형화 추세가 이를 심화시키는 리스크. 그에 따른 과도한 에너지 사용과 배출이 환경에 부정적 영향을 미치고, 후속 세대의 모델이 개발·배포될수록 그 부담이 누적되는 리스크.",
        "rationale": "번역투인 환경에 영향을 남긴다는 표현을 바로잡고 후속 모델 세대의 개발·배포에 따른 누적 부담을 명확히 한다.",
    },
    {
        "id": "FQA-314", "source": "G_Others_027", "target": "G_Others",
        "title_ko": "AI 시스템 사고로 인한 사망",
        "title_en": "Deaths caused by AI incidents",
        "description_ko": "AI 시스템이 사고를 유발·지원·증폭하여 한 명 이상의 사망을 초래하는 리스크.",
        "description_en": "The risk that an AI system causes, enables, or contributes to an incident resulting in one or more deaths.",
        "rationale": "인명 피해라는 완곡하고 모호한 표현을 사망 결과로 구체화하고 한영의 단수·복수 범위를 일치시킨다.",
    },
    {
        "id": "FQA-315", "source": "G_Others_065", "target": "G_Others",
        "title_ko": "인류 멸종",
        "rationale": "human extinction의 표준적 한국어 표현을 사용하고 인간 멸종이라는 부자연스러운 결합을 바로잡는다.",
    },
    {
        "id": "FQA-316", "source": "G_SYS_SECADV_009", "target": "G_SYS_SECADV",
        "title_ko": "취약점 탐지·악용 코드 작성 역량을 통한 사이버 공격 지원",
        "rationale": "역량 자체의 악용보다 해당 역량이 사이버공격 수행·지원을 가능하게 한다는 인과관계를 명확히 한다.",
    },
    {
        "id": "FQA-317", "source": "G_SYS_MISINFO_020", "target": "G_INT_ILLEGAL",
        "title_ko": "맞춤형 괴롭힘·갈취·협박 콘텐츠의 저비용 대량 생성",
        "title_en": "Low-cost mass generation of personalised harassment, extortion, and intimidation content",
        "description_ko": "범용 AI 시스템이 특정 개인이나 집단의 약점에 맞춘 괴롭힘·갈취·협박 콘텐츠를 낮은 비용으로 대량 생성하여 불법 행위를 조력하고 표적별 효율성과 성공 가능성을 높이는 리스크.",
        "description_en": "The risk that a general-purpose AI system generates at low cost and scale content tailored to the vulnerabilities of particular individuals or groups for harassment, extortion, or intimidation, facilitating unlawful conduct and increasing its effectiveness and likelihood of success against each target.",
        "rationale": "고의적 괴롭힘·갈취·협박을 위한 콘텐츠 생성은 허위정보 L3가 명시적으로 제외하는 의도적 오용이며 불법 행위의 직접적 조력에 해당한다.",
    },
    {
        "id": "FQA-318", "source": "G_Others_144", "target": "G_INT_WEAP",
        "description_ko": "정보 종합·지휘 통제 권고·자율 교전에 사용되는 AI 시스템이 인간의 실질적 검토 없이 오경보나 취약한 가정에 따라 행동하여 우발적 교전, 전쟁 범죄 또는 핵 충돌로 이어지는 급속한 비의도적 군사 확전을 초래하는 리스크.",
        "description_en": "The risk that AI systems used for intelligence synthesis, command-and-control recommendations, or autonomous engagement act on faulty warnings or brittle assumptions without effective human review, causing rapid and unintended military escalation through accidental engagements, war crimes, or nuclear conflict.",
        "rationale": "자동화 무기체계, 자율 교전 및 핵 충돌을 포함한 군사 확전은 무기의 운용과 대규모 물리 피해를 직접 다루므로 G_INT_WEAP에 해당한다.",
    },
]


def main() -> None:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    archive = ARCHIVE / MANIFEST.name
    if not archive.exists():
        shutil.copy2(MANIFEST, archive)
    outputs = {}
    for domain in ("General", "Agentic", "Physical"):
        for row in read_csv(OUT / f"L4_{domain}_Human_Review_Round2_Applied.csv"):
            outputs[row["L4_ID"]] = row
    ledger = {row["L4_ID_Before"]: row for row in read_csv(OUT / "Human_Review_Round2_Decision_Ledger.csv")}
    manifest_rows = read_csv(MANIFEST)
    header = list(manifest_rows[0])
    by_id = {row["Decision_ID"]: row for row in manifest_rows}

    for spec in CHANGES:
        after_ids = [value.strip() for value in ledger[spec["source"]]["L4_ID_After"].split("|") if value.strip()]
        if len(after_ids) != 1:
            raise ValueError(f"Expected one current output for {spec['source']}: {after_ids}")
        before = outputs[after_ids[0]]
        operation = by_id.get(spec["id"], {field: "" for field in header})
        approved = {
            "title_ko": before["L4_Title_ko"], "title_en": before["L4_Title_en"],
            "description_ko": before["L4_Description_ko"], "description_en": before["L4_Description_en"],
        }
        approved.update({key: value for key, value in spec.items() if key in approved})
        target = spec["target"]
        operation.update(
            {
                "Decision_ID": spec["id"],
                "Source_L4_ID_Before": spec["source"],
                "Observed_L4_ID_PreFinalQA": before["L4_ID"],
                "Expected_Current_L3_ID": before["L3_ID"],
                "Expected_Previous_SHA256": before_hash(before),
                "Decision": (
                    "LANGUAGE_REFINEMENT" if target == before["L3_ID"]
                    else "MOVE_TO_OTHERS_HD" if target.endswith("Others")
                    else "REMAP_PER_REVIEW"
                ),
                "Target_L3_ID": target,
                "Approved_Title_ko": approved["title_ko"],
                "Approved_Title_en": approved["title_en"],
                "Approved_Description_ko": approved["description_ko"],
                "Approved_Description_en": approved["description_en"],
                "Decision_Rationale": spec["rationale"],
                "Terminology_Evidence": EVIDENCE,
                "Approval_Status": "APPROVED_FINAL_QA_20260829",
            }
        )
        if spec["id"] not in by_id:
            manifest_rows.append(operation)
            by_id[spec["id"]] = operation

    manifest_rows.sort(key=lambda row: int(row["Decision_ID"].rsplit("-", 1)[1]))
    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(
        f"upserted={len(CHANGES)} total={len(manifest_rows)} "
        f"sha256={hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}"
    )


if __name__ == "__main__":
    main()
