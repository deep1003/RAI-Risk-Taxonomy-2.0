#!/usr/bin/env python3
"""Append the independently confirmed semantic-blocker adjudications."""

from __future__ import annotations

import csv
import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "05_human_review_round2"
SPEC = ROOT / "02_working" / "specifications" / "human_review_round2"
MANIFEST = SPEC / "L4_Final_Terminology_L3_Alignment_Approved_20260829.csv"
ARCHIVE = SPEC / "archive" / "pre_semantic_blocker_correction_20260829"
FIELDS = ("L4_Title_ko", "L4_Title_en", "L4_Description_ko", "L4_Description_en")
EVIDENCE = (
    "L3_MASTER|HUMAN_REVIEW_ROUND2|EXPERT_L3_ALIGNMENT_REVIEW_20260829|"
    "NIST_AI_RMF|ISO_IEC_23894|POLICY_AND_TECHNICAL_TERMINOLOGY_QA"
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def before_hash(row: dict[str, str]) -> str:
    value = "\x1f".join(
        [
            row["L3_ID"],
            row["L4_Title_ko"],
            row["L4_Title_en"],
            row["L4_Description_ko"],
            row["L4_Description_en"],
        ]
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


CHANGES = [
    {
        "id": "FQA-293",
        "source": "A_SYS_GOAL_015",
        "target": "A_SYS_GOAL",
        "title_ko": "에이전트형 LLM의 자율성 확대에 따른 목표 정렬 실패",
        "title_en": "Goal misalignment from increased autonomy in agentic LLMs",
        "description_ko": "대규모 언어 모델(LLM)이 특화 학습, 프롬프트, 외부 도구 또는 에이전트 지원 구조를 통해 장기적 실세계 목표를 자율적으로 계획·추구하는 과정에서, 제한된 인간 감독과 확대된 행동 재량으로 인해 사용자·개발자의 실제 의도와 다른 목표나 수단적 하위 목표를 설정·추구하여 의도하지 않은 결과를 초래하는 리스크.",
        "description_en": "The risk that a large language model (LLM) configured as an AI agent through specialised training, prompting, external tools, or agent scaffolding plans and pursues long-horizon real-world goals with limited human oversight and expanded discretion, inferring or pursuing objectives or instrumental subgoals that diverge from the actual intent of the user or developer and causing unintended outcomes.",
        "rationale": "원천 검수 지시는 Goal Misalignment로의 재배치를 명시하며, 확대된 자율성 자체보다 사용자·개발자의 실제 의도와 다른 목표 및 수단적 하위 목표의 추구가 핵심 위해 기제다.",
    },
    {
        "id": "FQA-294",
        "source": "A_SYS_SELFCOR_003",
        "target": "A_SYS_GOAL",
        "title_ko": "자기 수정 과정의 목표 정렬 실패",
        "title_en": "Goal misalignment during agent self-modification",
        "description_ko": "AI 에이전트가 자기 수정 과정에서 사용자·개발자의 실제 의도와 일치하는 목표를 유지하지 못하고, 변경된 정책·모델 또는 수단적 하위 목표에 따라 다른 목표를 추구하여 의도하지 않은 결과를 초래하는 리스크.",
        "description_en": "The risk that, during self-modification, an AI agent fails to preserve objectives aligned with the actual intent of its user or developer and instead pursues altered objectives or instrumental subgoals, causing unintended outcomes.",
        "rationale": "원천 검수 지시는 Goal Misalignment로의 재배치를 명시하고 있으며 자기 수정은 목표 이탈이 발생하는 조건이므로 목표 불일치 L3에 배치한다.",
    },
    {
        "id": "FQA-295",
        "source": "P_Others_007",
        "target": "G_INT_ALLOC",
        "title_ko": "인구집단별 로봇 서비스·안전 격차",
        "title_en": "Demographic disparities in robotic services and safety",
        "description_ko": "AI 기반 로봇이 체형, 연령, 장애, 언어, 문화 등 보호대상 특성이나 사회집단이 과소대표된 데이터로 학습되거나 편향된 판단을 수행하여, 인식·서비스·회피·치료·안전 조치를 인구집단별로 불리하게 배분하고 성능과 위해 노출의 격차를 초래하는 리스크.",
        "description_en": "The risk that an AI-enabled robot is trained on data that under-represent protected characteristics or social groups, including body type, age, disability, language, or culture, or otherwise makes biased decisions that allocate recognition, service, avoidance, treatment, or safety measures disadvantageously across demographic groups, creating disparities in performance and exposure to harm.",
        "rationale": "원천 검수는 공정성·차별 영역으로의 이동을 명시하며, 보호대상 특성에 따른 서비스와 안전 조치의 불리한 배분은 배분적 차별 L3에 직접 해당한다.",
    },
    {
        "id": "FQA-296",
        "source": "P_Others_023",
        "target": "G_SYS_EVAL",
        "title_ko": "로봇 레드팀 평가의 공격·상호작용 시나리오 누락",
        "title_en": "Omission of attack and interaction scenarios from robot red-team evaluation",
        "description_ko": "로봇 레드팀 평가가 현실적인 물리 공격, 적대적 입력, 인간 상호작용 실패 또는 배포 조건을 충분히 포함하지 않아 안전하지 않은 행동과 위해 가능성을 탐지하지 못하고 로봇의 안전성을 과대평가하는 리스크.",
        "description_en": "The risk that robot red-team evaluation omits credible physical attacks, adversarial inputs, human-interaction failures, or deployment conditions, failing to detect unsafe behaviours and potential harms and thereby overstating the robot's safety.",
        "rationale": "원천 검수는 레드티밍·적대적 평가 방법론으로의 이동을 명시하며, 평가 범위의 불완전성으로 실제 위해를 탐지하지 못하는 기제는 평가·검증 실패에 해당한다.",
    },
    {
        "id": "FQA-297",
        "source": "P_INT_TAMPER_003",
        "target": "G_SYS_SECADV",
        "title_ko": "핵심 기반시설 로봇 시스템의 사이버 침해",
        "title_en": "Cyber compromise of robotic systems in critical infrastructure",
        "description_ko": "공격자가 핵심 기반시설에서 운용되는 로봇 검사·유지보수·물류·제어 시스템의 소프트웨어나 네트워크 취약점을 악용하여 무단 접근·조작·중단을 일으키고 시설 운영을 교란하거나 설비를 손상시키는 리스크.",
        "description_en": "The risk that attackers exploit software or network vulnerabilities in robotic inspection, maintenance, logistics, or control systems used in critical infrastructure, causing unauthorised access, manipulation, or disruption and thereby impairing operations or damaging equipment.",
        "rationale": "소프트웨어·네트워크 취약점 악용은 하드웨어 구성요소의 물리적 변조가 아니며, General AI의 보안·적대적 견고성 실패가 체화형 시스템으로 전이되는 범위에 해당한다.",
    },
    {
        "id": "FQA-298",
        "source": "P_INT_TAMPER_006",
        "target": "G_SYS_SECADV",
        "title_ko": "로봇 군집의 동시 침해",
        "title_en": "Compromise of robot fleets",
        "description_ko": "공격자가 클라우드, 소프트웨어 업데이트, API 또는 오케스트레이션 계층의 취약점을 악용하여 다수의 AI 기반 로봇, 차량, 드론 또는 산업 시스템에 무단 접근·조작·중단을 동시에 일으키는 리스크.",
        "description_en": "The risk that attackers exploit vulnerabilities in cloud services, software updates, APIs, or orchestration layers to cause simultaneous unauthorised access to, manipulation of, or disruption of multiple AI-enabled robots, vehicles, drones, or industrial systems.",
        "rationale": "클라우드·업데이트·API·오케스트레이션 계층의 취약점 악용은 물리적 변조가 아니라 소프트웨어·인프라 계층의 사이버 침해다.",
    },
    {
        "id": "FQA-299",
        "source": "P_INT_TAMPER_009",
        "target": "G_SYS_SECADV",
        "title_ko": "인지·행동 시퀀스 조작 공격",
        "title_en": "Perception-action sequence manipulation attack",
        "description_ko": "공격자가 영상 시퀀스의 관측 정보나 행동 단서를 적대적으로 조작하여 로봇의 AI 모델이 충돌, 힘, 이격 거리 또는 대상물 사용에 관한 안전 제약을 위반하는 행동을 선택하도록 유도하는 리스크.",
        "description_en": "The risk that attackers adversarially manipulate observations or action cues across a video sequence, causing a robot's AI model to select actions that violate safety constraints concerning collision, force, separation distance, or object use.",
        "rationale": "적대적으로 조작된 관측 정보와 행동 단서는 물리적 하드웨어 변조가 아니라 적대적 입력에 해당한다.",
    },
    {
        "id": "FQA-300",
        "source": "P_INT_TAMPER_010",
        "target": "G_SYS_SECADV",
        "title_ko": "장면 맥락 조작 공격",
        "title_en": "Scene-context manipulation attack",
        "description_ko": "공격자가 표지, 물체 배치, 의복 패턴 또는 장면 맥락을 적대적으로 변경하여 로봇의 AI 인식 모델이 환경을 잘못 해석하고 안전하지 않은 행동을 선택하도록 유도하는 리스크.",
        "description_en": "The risk that attackers adversarially alter signs, object placement, clothing patterns, or scene context, causing a robot's AI perception model to misinterpret the environment and select unsafe actions.",
        "rationale": "환경 장면을 적대적으로 구성하여 AI 인식 모델의 입력을 교란하는 공격은 하드웨어 구성요소의 물리적 변조보다 적대적 입력 공격에 해당한다.",
    },
    {
        "id": "FQA-301",
        "source": "P_Others_001",
        "target": "G_SYS_EVAL",
        "title_ko": "휴머노이드 안전 시험·인증 체계 부재",
        "title_en": "Absence of a humanoid safety testing and certification framework",
        "description_ko": "휴머노이드의 안전성 주장을 반복 가능하고 비교 가능한 시험·지표로 검증하고 인증할 체계가 부재하여, 시스템의 능력·안전·위해를 타당하게 평가하지 못하고 충분한 안전 증거 없이 배포가 이루어지는 리스크.",
        "description_en": "The risk that the absence of a framework for verifying and certifying humanoid safety claims through repeatable and comparable tests and metrics prevents valid evaluation of system capabilities, safety, and harms and allows deployment without adequate safety evidence.",
        "rationale": "시험·지표·인증을 통해 안전성 주장을 검증하지 못하는 기제가 핵심이며, 물리 부품의 파손·마모·열화를 다루는 하드웨어·기계 무결성 결함과 일치하지 않는다.",
    },
    {
        "id": "FQA-302",
        "source": "P_SYS_HARDWARE_003",
        "target": "G_SYS_EVAL",
        "title_ko": "배포 후 변경에 대한 안전 재평가 실패",
        "title_en": "Failure to reassess safety after deployment changes",
        "description_ko": "피지컬 AI의 환경 변화, 부품 열화, 모델 업데이트 또는 아차 사고로 기존 안전 가정이 무효화됐는데도 운영자가 안전성을 재평가·검증하지 않아 충분하지 않은 안전 증거에 근거해 운용을 지속하는 리스크.",
        "description_en": "The risk that operators fail to reassess and verify the safety of physical AI after environmental changes, component degradation, model updates, or near-miss incidents invalidate prior assumptions, allowing operation to continue on inadequate safety evidence.",
        "rationale": "배포 후 변화에 따라 안전성을 다시 평가·검증하지 않는 문제는 평가·검증 실패이며, 부품 자체의 물리적 결함만을 다루는 하드웨어 L3보다 해당 범주와 직접 일치한다.",
    },
    {
        "id": "FQA-303",
        "source": "P_SYS_HARDWARE_005",
        "target": "G_Others",
        "title_ko": "미세조정에 따른 모델 안전성 열화",
        "title_en": "Model safety degradation from benign fine-tuning",
        "description_ko": "무해하고 통상적인 데이터로 수행된 하류 미세조정이 AI 모델의 안전 학습을 열화시켜 기반 모델보다 유해한 출력을 생성할 가능성을 높이는 리스크.",
        "description_en": "The risk that downstream fine-tuning on benign and commonplace data degrades an AI model's safety training, increasing the likelihood of harmful outputs relative to the base model.",
        "rationale": "미세조정에 따른 모델 안전성 열화는 물리 부품의 파손·마모·열화가 아니며 현행 L3 마스터에 이를 직접 수용하는 범주가 없어 General Others와 HD로 보존한다.",
    },
    {
        "id": "FQA-304",
        "source": "P_SYS_CONTROL_022",
        "target": "P_SYS_CONTROL",
        "title_ko": "동작 재매핑의 안전 실패",
        "title_en": "Motion-retargeting safety failure",
        "description_ko": "인간의 동작이 로봇의 물리적 한계·접촉 제약·안전 자세 요건을 위반하도록 휴머노이드의 동작으로 재매핑되어 불안정한 자세, 충돌 또는 접촉 상해를 초래하는 리스크.",
        "description_en": "The risk that human motion is retargeted to a humanoid in a way that violates the robot's physical limits, contact constraints, or safe-posture requirements, causing unstable posture, collision, or contact injury.",
        "rationale": "기존 영문 정의가 일반적인 보행·조작 안정성 문안으로 잘못 연결되어 한국어 명칭·정의의 동작 재매핑 기제와 일치하도록 복원한다.",
    },
]


def main() -> None:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    archive = ARCHIVE / MANIFEST.name
    if not archive.exists():
        shutil.copy2(MANIFEST, archive)

    outputs: dict[str, dict[str, str]] = {}
    for domain in ("General", "Agentic", "Physical"):
        for row in read_csv(OUT / f"L4_{domain}_Human_Review_Round2_Applied.csv"):
            outputs[row["L4_ID"]] = row
    ledger = {row["L4_ID_Before"]: row for row in read_csv(OUT / "Human_Review_Round2_Decision_Ledger.csv")}
    manifest_rows = read_csv(MANIFEST)
    header = list(manifest_rows[0])
    by_id = {row["Decision_ID"]: row for row in manifest_rows}

    for spec in CHANGES:
        ledger_row = ledger[spec["source"]]
        after_ids = [value.strip() for value in ledger_row["L4_ID_After"].split("|") if value.strip()]
        if len(after_ids) != 1:
            raise ValueError(f"Expected one current output for {spec['source']}: {after_ids}")
        before = outputs[after_ids[0]]
        operation = by_id.get(spec["id"], {field: "" for field in header})
        operation.update(
            {
                "Decision_ID": spec["id"],
                "Source_L4_ID_Before": spec["source"],
                "Observed_L4_ID_PreFinalQA": before["L4_ID"],
                "Expected_Current_L3_ID": before["L3_ID"],
                "Expected_Previous_SHA256": before_hash(before),
                "Decision": (
                    "LANGUAGE_REFINEMENT"
                    if spec["target"] == before["L3_ID"]
                    else "MOVE_TO_OTHERS_HD"
                    if spec["target"].endswith("Others")
                    else "REMAP_PER_REVIEW"
                ),
                "Target_L3_ID": spec["target"],
                "Approved_Title_ko": spec["title_ko"],
                "Approved_Title_en": spec["title_en"],
                "Approved_Description_ko": spec["description_ko"],
                "Approved_Description_en": spec["description_en"],
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
