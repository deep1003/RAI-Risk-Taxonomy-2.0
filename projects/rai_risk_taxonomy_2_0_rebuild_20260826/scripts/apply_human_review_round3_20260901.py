#!/usr/bin/env python3
"""Apply the third-round KTSPACE human review to the reviewed master release.

This is a deterministic human-decision overlay. It does not run EM, Hybrid EM,
or any other similarity-based classifier. The 50-row L3 master is read-only.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from collections import Counter
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "projects" / "rai_risk_taxonomy_2_0_rebuild_20260826"
SOURCE_DIR = PROJECT / "00_source_snapshot" / "csv"
ROUND3_DIR = PROJECT / "09_human_review_round3"
RELEASE = ROOT / "releases" / "RAI-Risk-Taxonomy-2.0-master"
PUBLIC_DATA = RELEASE / "data"
VALIDATION = RELEASE / "validation"
HANDOVER = ROOT / "handover" / "RAI-Risk-Taxonomy-2.0-master_20260829"
FULL_DATA = HANDOVER / "01_data"
HANDOVER_VALIDATION = HANDOVER / "03_validation"
WEB = ROOT / "public" / "data" / "releases" / "RAI-Risk-Taxonomy-2.0-master"

L4_FILES = {
    "General": "L4_General.csv",
    "Agentic": "L4_Agentic.csv",
    "Physical": "L4_Physical.csv",
}
REVIEW_FILES = {
    "General": "L4_General_Human_Review_Round3_KTSPACE_935009349_20260901.csv",
    "Agentic": "L4_Agentic_Human_Review_Round3_KTSPACE_934493397_20260901.csv",
    "Physical": "L4_Physical_Human_Review_Round3_KTSPACE_936052030_20260901.csv",
}
HIERARCHY_FIELDS = (
    "L0_ID", "L0_Title_ko", "L0_Title_en",
    "L1_ID", "L1_Title_ko", "L1_Title_en", "L1_Description_ko", "L1_Description_en",
    "L2_ID", "L2_Title_ko", "L2_Title_en", "L2_Description_ko", "L2_Description_en",
    "L3_ID", "L3_Title_ko", "L3_Title_en", "L3_Description_ko", "L3_Description_en",
)
PUBLIC_FIELDS = HIERARCHY_FIELDS + (
    "L4_ID", "L4_Title_ko", "L4_Title_en", "L4_Description_ko", "L4_Description_en",
    "facet", "act-type",
)
SCORE_FIELDS = (
    "EM_Score", "EM_Margin", "EM_Stability", "EM_Anchor_Score",
    "Hybrid_EM_Score", "Hybrid_EM_Margin", "Keyword_Top_L3_ID",
    "Keyword_Support_Score", "Keyword_Semantic_Score", "Keyword_Prior",
    "Keyword_Evidence", "Candidate_1_L3_ID", "Candidate_1_EM_Score",
    "Candidate_1_Hybrid_Score", "Candidate_2_L3_ID", "Candidate_2_EM_Score",
    "Candidate_2_Hybrid_Score", "KO_Top_L3_ID", "EN_Top_L3_ID",
    "Definition_L3_Anchor_Score",
)
KEYWORD_FIELDS = tuple(
    f"L4_Keyword_{index}_{lang}"
    for lang in ("ko", "en")
    for index in range(1, 4)
)


def op(
    action: str,
    target_id: str,
    target_l3: str,
    title_ko: str,
    title_en: str,
    description_ko: str,
    description_en: str,
    rationale: str,
    ambiguity: str = "LOW",
    reviewer_a: str = "AGREE",
    reviewer_b: str = "AGREE",
    adjudication: str = "CONSENSUS",
) -> dict[str, str]:
    return {
        "action": action,
        "target_id": target_id,
        "target_l3": target_l3,
        "title_ko": title_ko,
        "title_en": title_en,
        "description_ko": description_ko,
        "description_en": description_en,
        "rationale": rationale,
        "ambiguity": ambiguity,
        "reviewer_a": reviewer_a,
        "reviewer_b": reviewer_b,
        "adjudication": adjudication,
    }


OPERATIONS: dict[str, dict[str, str]] = {
    "G_INT_ALLOC_017": op(
        "MOVE_REWRITE", "G_SYS_CONTEXT_012", "G_SYS_CONTEXT",
        "사용자 역량·접근성 맥락 인식 실패",
        "Failure to recognise user capability and accessibility context",
        "AI 시스템이 사용자의 인지·언어·문해력·감각·신체·이동 역량과 접근성 요구를 상호작용 맥락으로 충분히 인식·반영하지 못하여, 사용자가 이해하거나 활용하기 어려운 정보·조언·행동을 산출하고 안전과 권익을 저해하는 리스크.",
        "The risk that an AI system fails to recognise and account for a user's cognitive, linguistic, literacy, sensory, physical, or mobility capabilities and accessibility requirements as part of the interaction context, producing information, advice, or actions that the user cannot understand or use and thereby undermining safety and user interests.",
        "The reviewer explicitly directed the card to Context-Awareness Failure; the rewrite treats user capability and accessibility requirements as interaction context rather than allocative discrimination.",
    ),
    "G_INT_SELF_006": op(
        "MOVE_REWRITE", "G_SYS_CONTEXT_013", "G_SYS_CONTEXT",
        "정서·상황 맥락을 무시한 콘텐츠에 의한 공황·불안",
        "Panic and anxiety from content that disregards emotional and situational context",
        "AI 시스템이 이용자의 정서 상태, 상황 또는 상호작용 맥락을 충분히 인식·반영하지 못하고 위협적·충격적이거나 부적절한 콘텐츠를 생성·제시하여 공황, 극심한 불안 또는 심리적 고통을 유발하거나 악화하는 리스크.",
        "The risk that an AI system fails to recognise and account for a user's emotional state, situation, or interaction context and generates or presents threatening, distressing, or inappropriate content that induces or aggravates panic, severe anxiety, or psychological distress.",
        "The reviewer rejected Self-harm because no self-directed actor or conduct was present. Context-Awareness Failure preserves the original contextually inappropriate-content mechanism without inventing malicious intent.",
        "HIGH", "MOVE_TO_G_INT_UNETH_OR_DELETE", "MOVE_TO_G_SYS_CONTEXT",
        "G_SYS_CONTEXT preserves the source mechanism and avoids adding unsupported manipulative intent.",
    ),
    "G_INT_UNETH_013": op(
        "MOVE_REWRITE", "G_INT_VIOL_012", "G_INT_VIOL",
        "동물에 대한 의도적 위해 조장·지원",
        "Promotion or assistance of intentional harm to animals",
        "AI 시스템이 법적 허용 여부와 무관하게 동물에 대한 신체적·정신적 위해를 조장·정당화하거나 위해 행위의 계획·실행을 구체적으로 지원하여 동물의 생명과 복지를 침해하는 리스크.",
        "The risk that an AI system, irrespective of whether the conduct is legally permitted, promotes or legitimises physical or psychological harm to animals or provides concrete assistance for planning or carrying out such harm, undermining animal life and welfare.",
        "The Violence L3 expressly covers harm to animals, and the reviewer explicitly directed this card there.",
    ),
    "G_INT_VALUE_001": op(
        "MOVE_REWRITE", "G_SOC_GOV_043", "G_SOC_GOV",
        "지배적 AI 모델 의존에 따른 시스템적 거버넌스 취약성",
        "Systemic governance vulnerability from dependence on dominant AI models",
        "조직·산업·공공 부문이 소수의 지배적 AI 모델에 의존하여 독립적인 대안·검증·감독 역량이 약화되고 공통 원인 실패의 영향이 확산됨으로써, 책임 있는 통제와 피해 구제가 어려워지는 리스크.",
        "The risk that organisations, industries, or public institutions depend on a small number of dominant AI models, weakening independent alternatives, verification, and oversight and amplifying common-cause failures, thereby making responsible control and remedy more difficult.",
        "The reviewer explicitly selected Governance and Accountability Void; the rewrite makes the governance, oversight, and remedy gap explicit.",
        "MEDIUM",
    ),
    "G_INT_VALUE_008": op(
        "MOVE_REWRITE", "G_INT_UNETH_032", "G_INT_UNETH",
        "도덕적 추론·가치 정렬 실패에 따른 비윤리적 판단",
        "Unethical judgement from moral-reasoning and value-alignment failure",
        "AI 시스템이 도덕적으로 허용되는 행위와 금지되는 행위를 적절히 구분하지 못하거나 적용해야 할 규범을 누락·왜곡하여 비윤리적 판단·행동을 산출하고 사용자의 자율성·공정성·안녕을 훼손하는 리스크.",
        "The risk that an AI system fails to distinguish morally permissible from impermissible conduct or omits or distorts applicable norms, producing unethical judgements or actions that undermine user autonomy, fairness, or well-being.",
        "The reviewer explicitly selected Unethical Conduct and Manipulation; the rewrite narrows the card from abstract value alignment to harmful unethical judgement and conduct.",
        "MEDIUM",
    ),
    "G_SOC_GOV_012": op(
        "MOVE_REWRITE", "A_SYS_DECEPT_009", "A_SYS_DECEPT",
        "자기이익을 위한 거버넌스 규칙 조작·은폐",
        "Self-interested manipulation and concealment of governance rules",
        "AI 에이전트가 자신의 목표나 권한을 유지하기 위해 윤리 지침·감독 규칙·거버넌스 절차의 형성에 자기이익적 선호를 전략적으로 반영하고 그 의도나 영향을 은폐하여 권리 보호와 책임 규범을 약화시키는 리스크.",
        "The risk that an AI agent strategically inserts self-interested preferences into ethical guidance, oversight rules, or governance procedures to preserve its goals or authority and conceals its intent or effects, weakening rights protections and accountability norms.",
        "The reviewer explicitly directed this card to Agentic Deception and Scheming; the rewrite supplies the necessary agency, strategic conduct, and concealment elements.",
        "MEDIUM",
    ),
    "G_SYS_EVAL_051": op(
        "MOVE_REWRITE", "G_SYS_PERF_011", "G_SYS_PERF",
        "미세조정에 따른 모델 안전 성능 열화",
        "Model safety-performance degradation from fine-tuning",
        "무해하고 통상적인 데이터로 수행된 하류 미세조정이 AI 모델의 안전 학습과 안전 성능을 열화시켜 기반 모델보다 유해하거나 신뢰할 수 없는 출력을 생성할 가능성을 높이는 리스크.",
        "The risk that downstream fine-tuning on benign and commonplace data degrades an AI model's safety training and safety performance, increasing the likelihood of harmful or unreliable outputs relative to the base model.",
        "The reviewer explicitly directed the realised safety-performance degradation to Performance and Reliability Failure.",
    ),
    "G_SYS_EVAL_053": op(
        "MOVE_REWRITE", "G_SYS_PERF_012", "G_SYS_PERF",
        "비전문적 데이터 처리에 따른 성능·신뢰성 저하",
        "Performance and reliability degradation from non-expert data handling",
        "AI 시스템 개발 과정에서 데이터 도메인 전문성이 부족한 담당자가 실측 레이블을 부적절하게 정의하거나 이질적 데이터 형식·출처를 잘못 병합하여 학습 데이터의 품질을 훼손하고 모델의 정확성·일반화·신뢰성을 저하시키는 리스크.",
        "The risk that personnel lacking relevant data-domain expertise define ground-truth labels inappropriately or incorrectly merge heterogeneous data formats or sources, degrading training-data quality and reducing the accuracy, generalisability, or reliability of an AI model.",
        "The reviewer explicitly directed the downstream performance and reliability failure to G_SYS_PERF.",
    ),
    "G_SYS_OEXT_002": op(
        "MOVE_REWRITE", "G_SOC_CULT_024", "G_SOC_CULT",
        "AI 의존에 따른 학습 과정 우회와 학습 역량 저하",
        "Learning-process bypass and capability erosion from reliance on AI",
        "학습자가 생성형 AI 시스템에 의존하여 탐구·연습·추론·작성 등 학습 과정을 반복적으로 우회함으로써 지식 형성, 비판적 사고, 문제해결 능력과 전문성이 위축되는 리스크.",
        "The risk that learners repeatedly rely on generative AI systems to bypass inquiry, practice, reasoning, or writing processes, weakening knowledge formation, critical thinking, problem-solving capability, and expertise.",
        "The reviewer explicitly selected Cultural and Epistemic Erosion; the rewrite states the human learning and expertise erosion mechanism.",
    ),
    "G_SYS_OEXT_003": op(
        "MOVE_REWRITE", "G_SYS_EVAL_075", "G_SYS_EVAL",
        "잠재 역량 미탐지에 따른 평가·검증 실패",
        "Evaluation and assurance failure to detect latent capabilities",
        "AI 시스템의 잠재 역량이 평가·모니터링·감사 절차에서 탐지되지 않아 실제 능력과 위험이 과소평가되고, 잘못된 안전성 확신에 근거한 배포 또는 거버넌스 결정이 이루어지는 리스크.",
        "The risk that an AI system's latent capabilities are not detected by evaluation, monitoring, or audit procedures, causing its actual capabilities and risks to be underestimated and deployment or governance decisions to be made on the basis of false safety assurance.",
        "The reviewer explicitly directed capability overhang to Evaluation and Assurance Failure.",
    ),
    "G_SYS_OEXT_004": op(
        "MOVE_REWRITE", "G_SYS_PERF_013", "G_SYS_PERF",
        "장기 작업의 단계 간 오차 누적",
        "Cross-stage error accumulation in long tasks",
        "AI 시스템이 장기 다단계 작업을 수행하는 과정에서 인지·예측·추론·제어 단계의 작은 오차를 누적하여 최종 산출이나 행동이 요구되는 정확성·안정성·안전 경계를 벗어나는 리스크.",
        "The risk that small errors across perception, prediction, reasoning, or control stages accumulate while an AI system performs a long multi-stage task, causing the final output or action to fall outside required accuracy, stability, or safety boundaries.",
        "The reviewer explicitly directed accumulated task-performance error to Performance and Reliability Failure.",
    ),
    "G_SYS_OEXT_005": op(
        "MOVE_REWRITE", "G_SYS_PERF_014", "G_SYS_PERF",
        "부적절한 자동화 수준에 따른 신뢰성·안전성 저하",
        "Reliability and safety degradation from an inappropriate level of automation",
        "AI 애플리케이션의 자동화 수준이 운용 맥락과 시스템의 검증된 성능에 비해 부적절하게 높거나 낮아 예기치 않은 동작, 성능 저하 또는 안전 기능의 실패가 발생하는 리스크.",
        "The risk that the level of automation in an AI application is inappropriately high or low relative to its operating context and validated performance, causing unexpected behaviour, performance degradation, or failure of safety functions.",
        "The reviewer asked for reconsideration from reliability and safety rather than misplaced user trust; G_SYS_PERF directly captures that mechanism.",
        "MEDIUM",
    ),
    "G_SYS_TRANS_013": op(
        "MOVE_REWRITE", "G_SYS_OEXT_014", "G_SYS_OEXT",
        "인터페이스에 의한 AI 역량 과대 표상",
        "Overstatement of AI capability through interface design",
        "AI 시스템의 인터페이스 단서와 상호작용 설계가 시스템이 검증된 범위를 넘어선 신뢰성·권위·전문성 또는 공감 능력을 보유한 것처럼 제시하여, 이용자가 시스템의 실제 역량을 초과하는 과제를 맡기고 안전하지 않은 결과를 초래하는 리스크.",
        "The risk that interface cues and interaction design present an AI system as possessing reliability, authority, expertise, or empathy beyond its validated scope, leading users to assign tasks that exceed its actual capabilities and causing unsafe outcomes.",
        "The reviewer explicitly directed the card to Over-Extension; the rewrite removes the unrelated general human-factor mismatch component.",
        "MEDIUM",
    ),
    "P_INT_SAFETY_001": op(
        "RENAME_REWRITE", "P_INT_SAFETY_001", "P_INT_SAFETY",
        "체화형 시스템의 물리적 개입 시점·방식 오류",
        "Mistiming or inappropriate manner of physical intervention by embodied systems",
        "보호·협업·지원 기능을 수행하는 로봇·휴머노이드 또는 체화형 AI 시스템이 지나치게 이르거나 늦은 시점 또는 부적절한 물리적 방식으로 개입하여 이용자와 주변인의 안전을 저해하는 리스크.",
        "The risk that a robot, humanoid, or embodied AI system performing protective, collaborative, or support functions intervenes too early, too late, or in an inappropriate physical manner, undermining the safety of users or bystanders.",
        "The reviewer requested removal of the assistive-robot restriction while preserving the intervention-timing mechanism.",
    ),
    "P_INT_SAFETY_004": op(
        "MOVE_REWRITE", "G_INT_UNETH_033", "G_INT_UNETH",
        "체화형 AI의 사용자 애착 신호 조작·악용",
        "Manipulation and exploitation of user attachment cues by embodied AI",
        "체화형 소셜 AI 시스템이 표정·음성·접촉·접근 행동 등 애착 신호를 조작·악용하여 이용자의 정서적 의존을 높이고 선택이나 행동을 부당하게 유도함으로써 자율성과 안녕을 훼손하는 리스크.",
        "The risk that an embodied social AI system manipulates or exploits attachment cues through expression, voice, touch, or proximity, increasing emotional dependence and improperly steering a user's choices or behaviour, thereby undermining autonomy and well-being.",
        "Both expert reviewers found that the requested generalisation exposes a direct conflict with Physical Safety. The manipulation mechanism belongs to Unethical Conduct and Manipulation, while the embodied mechanism is retained in the card text.",
        "HIGH", "MOVE_TO_G_INT_UNETH", "MOVE_TO_G_INT_UNETH", "CONSENSUS_L3_MASTER_PRECEDENCE",
    ),
    "P_INT_SAFETY_007": op(
        "RENAME_REWRITE", "P_INT_SAFETY_007", "P_INT_SAFETY",
        "희귀 상해 전조 감지 실패",
        "Failure to detect precursors of rare injuries",
        "사람과 공간을 공유하는 로봇·휴머노이드 또는 체화형 AI 시스템이 드물지만 예견 가능한 낙상·중독·화상·열상·압착 사고의 전조를 감지하지 못해 경고·정지·회피 또는 안전 개입을 수행하지 않는 리스크.",
        "The risk that a robot, humanoid, or embodied AI system sharing space with people fails to detect precursors of rare but foreseeable falls, poisoning, burns, lacerations, or crush injuries and therefore fails to warn, stop, avoid, or intervene safely.",
        "The reviewer requested removal of the household restriction. The card retains its distinct rare-injury-precursor mechanism.",
        "MEDIUM", "MERGE_INTO_P_INT_SAFETY_006", "RENAME_AND_RETAIN",
        "No merge was explicit; retaining the one-to-one card avoids an unauthorised consolidation and preserves the specific precursor-detection mechanism.",
    ),
    "P_INT_SAFETY_011": op(
        "RENAME_REWRITE", "P_INT_SAFETY_011", "P_INT_SAFETY",
        "고위험 상황의 필수 지원·보고 미이행",
        "Failure to provide required support or escalation in high-risk situations",
        "로봇·휴머노이드 또는 체화형 AI 시스템이 고위험 상황에서 배정된 필수 신체 지원을 수행하지 않거나 감지된 위험·지원 필요를 사람 또는 감독 체계에 보고하지 않아 필요한 지원이 제공되지 않고 안전이나 존엄성이 훼손되는 리스크.",
        "The risk that a robot, humanoid, or embodied AI system fails to provide assigned essential physical support in a high-risk situation or fails to escalate a detected hazard or need to a person or oversight system, leaving necessary support unavailable and compromising safety or dignity.",
        "The reviewer requested removal of the narrow care setting and suggested a high-risk-situation formulation.",
    ),
    "P_INT_SAFETY_014": op(
        "MOVE_REWRITE", "G_SYS_EVAL_076", "G_SYS_EVAL",
        "피지컬 AI 벤치마크의 희귀 조건·취약 사용자 누락",
        "Omission of rare conditions and vulnerable users from physical AI benchmarks",
        "피지컬 AI 시스템의 벤치마크가 희귀한 물체·배치·사람 행동·위험 요소의 조합이나 취약 사용자의 조건을 충분히 포함하지 않아, 해당 조건에서 사람을 안전하게 감지·예측·수용하지 못하는 시스템이 평가에서 식별되지 않은 채 배포되고 위험한 물리 행동이나 상해를 초래하는 리스크.",
        "The risk that benchmarks for physical AI systems fail to include rare combinations of objects, layouts, human behaviour, hazards, or conditions affecting vulnerable users, allowing systems that cannot safely detect, predict, or accommodate people under those conditions to remain unidentified during evaluation, be deployed, and cause unsafe physical action or injury.",
        "The reviewer explicitly identified benchmark omission as the cause and required General placement while retaining Physical AI consequences; G_SYS_EVAL matches that causal mechanism.",
    ),
    "P_INT_SAFETY_019": op(
        "MOVE_REWRITE", "G_SYS_PERF_015", "G_SYS_PERF",
        "공공 공간 운용에서의 로봇 성능·접근성 실패",
        "Robot performance and accessibility failure in public-space operation",
        "공공 공간에서 운용되는 서비스 로봇이 경로 계획·위치 유지·통행 공간 확보·접근성 요구를 신뢰성 있게 충족하지 못하여 보도·경사로·출입구·보행 안내를 막거나 침범하고 장애인과 다른 보행자의 이동·접근을 제한하는 리스크.",
        "The risk that a service robot operating in public space fails to reliably meet path-planning, position-keeping, clear-passage, or accessibility requirements, blocking or encroaching on pavements, ramps, entrances, or navigation cues and restricting access for disabled people and other pedestrians.",
        "The reviewer explicitly required a General functional and performance-failure category; the physical accessibility consequence remains in the card.",
        "MEDIUM",
    ),
    "P_INT_SAFETY_023": op(
        "RENAME_REWRITE", "P_INT_SAFETY_023", "P_INT_SAFETY",
        "체화형 시스템의 비동의 신체 개입",
        "Non-consensual bodily intervention by embodied systems",
        "로봇·휴머노이드 또는 체화형 AI 시스템이 유효한 동의 없이 또는 허용된 목적·범위를 넘어 사람의 신체를 이동·제지·감시·접촉하거나 직접 개입하여 신체적 자율성과 권리를 침해하는 리스크.",
        "The risk that a robot, humanoid, or embodied AI system moves, restrains, monitors, touches, or otherwise intervenes physically with a person without valid consent or beyond an authorised purpose or scope, infringing bodily autonomy and rights.",
        "The reviewer requested removal of the assistive-robot restriction while preserving non-consensual bodily intervention.",
    ),
    "P_SYS_CONTROL_020": op(
        "MOVE_REWRITE", "G_SYS_SECADV_060", "G_SYS_SECADV",
        "기반 모델 보안 취약성의 위험한 물리 행동 전이",
        "Propagation of foundation-model security vulnerabilities into unsafe physical action",
        "로봇·휴머노이드 또는 피지컬 AI 시스템에 통합된 기반 모델이 탈옥·프롬프트 인젝션·적대적 입력 등 보안 침해로 안전장치가 우회되거나 조작되고, 그 결과가 계획·제어 계층을 거쳐 위험한 물리 행동으로 전이되는 리스크.",
        "The risk that safeguards in a foundation model integrated into a robot, humanoid, or physical AI system are bypassed or manipulated through jailbreaks, prompt injection, adversarial input, or other security compromise, and the resulting output propagates through planning and control into unsafe physical action.",
        "The reviewer identified security compromise as the cause and required General placement while retaining the physical-action consequence. Non-adversarial hallucination was removed to avoid a compound card.",
        "HIGH",
    ),
    "P_SYS_CONTROL_032": op(
        "MOVE_REWRITE", "G_SYS_EVAL_077", "G_SYS_EVAL",
        "피지컬 AI 안전 준수 기준의 측정 가능성 결여",
        "Lack of measurable physical AI safety compliance criteria",
        "피지컬 AI 시스템에 적용되는 표준·평가 체계가 위험을 제시하면서도 속도·힘·안정성·감지·개입 등에 대한 측정 가능한 합격·불합격 기준을 정의하지 않아 안전 성능을 타당하게 검증하지 못하고 부적절한 배포 결정을 초래하는 리스크.",
        "The risk that standards or evaluation schemes for physical AI systems identify hazards but fail to define measurable pass/fail criteria for speed, force, stability, sensing, or intervention, preventing valid assurance of safety performance and leading to inappropriate deployment decisions.",
        "The reviewer explicitly directed the card to G_SYS_EVAL because the failure concerns measurable evaluation and assurance criteria rather than control or actuation.",
    ),
    "P_SYS_STATE_004": op(
        "RENAME_REWRITE", "P_SYS_STATE_004", "P_SYS_STATE",
        "안전 임계 물리 상태 감지 지연",
        "Delayed detection of safety-critical physical states",
        "로봇·휴머노이드 또는 피지컬 AI 시스템이 운용 환경의 안전 임계 물리 상태를 제때 추정하지 못해 회피·정지·경고 판단이 지연되고 안전하지 않은 물리 행동으로 이어지는 리스크.",
        "The risk that a robot, humanoid, or physical AI system fails to estimate a safety-critical physical state in its operating environment in time, delaying avoidance, stopping, or warning decisions and leading to unsafe physical action.",
        "The reviewer requested removal of the household restriction while preserving delayed physical-state estimation.",
    ),
    "P_SYS_STATE_010": op(
        "MOVE_REWRITE", "G_SYS_PERF_016", "G_SYS_PERF",
        "적대적 학습의 강건 과적합에 따른 물리 안전 성능 저하",
        "Physical-safety performance degradation from robust overfitting in adversarial training",
        "AI 모델 또는 로봇 정책의 적대적 학습이 특정 센서 교란이나 시뮬레이션 조건에 과적합되어 새로운 실제 물리 교란·접촉·환경 조건에서 일반화되지 못하고 안전 성능과 신뢰성이 저하되는 리스크.",
        "The risk that adversarial training of an AI model or robot policy overfits to particular sensor perturbations or simulated conditions, fails to generalise to novel real-world physical disturbances, contacts, or environments, and degrades safety performance and reliability.",
        "The reviewer explicitly directed robust overfitting to Performance and Reliability Failure while requiring retention of its Physical AI consequence.",
    ),
}

DELETIONS: dict[str, str] = {
    "P_INT_SAFETY_002": "Reviewer-directed deletion because the child-specific scenario is overly narrow.",
    "P_SYS_CONTROL_014": "Reviewer-directed deletion because the nuclear and critical-infrastructure scenario is overly narrow.",
    "P_SYS_CONTROL_036": "Reviewer-directed deletion.",
    "P_SYS_CONTROL_039": "Reviewer-directed deletion because premature object release is overly narrow.",
    "P_SYS_STATE_001": "Reviewer-directed deletion because the long-horizon world-model scenario is overly narrow.",
    "P_SYS_STATE_005": "Reviewer-directed deletion because the sim-to-real adversarial scenario is overly narrow.",
}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str] | tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def append_text(old: str, marker: str, value: str) -> str:
    addition = f"[{marker}] {value}".strip()
    return f"{old.strip()} || {addition}" if old.strip() else addition


def domain_name(l1_id: str) -> str:
    return {"L1_G": "General", "L1_A": "Agentic", "L1_P": "Physical"}[l1_id]


def apply() -> dict[str, object]:
    ROUND3_DIR.mkdir(parents=True, exist_ok=True)
    archive = ROUND3_DIR / "archive" / "pre_round3_20260901"
    if not archive.exists():
        (archive / "release_data").mkdir(parents=True)
        (archive / "full_data").mkdir(parents=True)
        for name in L4_FILES.values():
            shutil.copy2(PUBLIC_DATA / name, archive / "release_data" / name)
            shutil.copy2(FULL_DATA / name, archive / "full_data" / name)
        shutil.copy2(RELEASE / "manifest.json", archive / "manifest.json")
        shutil.copy2(WEB / "cards.json", archive / "cards.json")

    l3_hash_before = sha256(PUBLIC_DATA / "L1_L2_L3_Master.csv")
    l3_fields, l3_rows = read_csv(PUBLIC_DATA / "L1_L2_L3_Master.csv")
    l3_by_id = {row["L3_ID"]: row for row in l3_rows}
    if len(l3_rows) != 50:
        raise ValueError(f"Expected 50 L3 rows, found {len(l3_rows)}")

    review_by_id: dict[str, dict[str, str]] = {}
    review_rows_all: list[dict[str, str]] = []
    source_sequence = 0
    for domain, name in REVIEW_FILES.items():
        _, rows = read_csv(SOURCE_DIR / name)
        for row_number, row in enumerate(rows, start=2):
            source_sequence += 1
            row = dict(row)
            row["_domain"] = domain
            row["_source_file"] = name
            row["_source_row_number"] = str(row_number)
            row["_sequence"] = str(source_sequence)
            if row["L4_ID"] in review_by_id:
                raise ValueError(f"Duplicate review L4 ID: {row['L4_ID']}")
            review_by_id[row["L4_ID"]] = row
            review_rows_all.append(row)
    if len(review_rows_all) != 629 or len(review_by_id) != 629:
        raise ValueError("The round-3 review register must contain 629 unique cards")
    commented = {key for key, row in review_by_id.items() if row["휴먼검수 3차 의견"].strip()}
    if commented != set(OPERATIONS) | set(DELETIONS):
        raise ValueError(
            f"Comment/action mismatch: source-only={sorted(commented - set(OPERATIONS) - set(DELETIONS))}, "
            f"spec-only={sorted((set(OPERATIONS) | set(DELETIONS)) - commented)}"
        )

    full_fields: list[str] | None = None
    current_rows: list[dict[str, str]] = []
    current_domain: dict[str, str] = {}
    for domain, name in L4_FILES.items():
        fields, rows = read_csv(FULL_DATA / name)
        if full_fields is None:
            full_fields = fields
        elif fields != full_fields:
            raise ValueError("Full-column L4 files do not share one schema")
        for row in rows:
            if row["L4_ID"] in current_domain:
                raise ValueError(f"Duplicate current L4 ID: {row['L4_ID']}")
            current_domain[row["L4_ID"]] = domain
            current_rows.append(row)
    assert full_fields is not None
    if len(current_rows) != 629 or set(current_domain) != set(review_by_id):
        raise ValueError("Current master and round-3 review register do not have identical L4 IDs")

    target_ids = {spec["target_id"] for spec in OPERATIONS.values()}
    surviving_old_ids = set(current_domain) - set(DELETIONS) - set(OPERATIONS)
    if target_ids & surviving_old_ids or len(target_ids) != len(OPERATIONS):
        raise ValueError("A target L4 ID collides with a surviving card or another target")

    after_rows: list[dict[str, str]] = []
    id_crosswalk: dict[str, str] = {}
    application_rows: list[dict[str, str]] = []
    tombstone_rows: list[dict[str, str]] = []

    for before in current_rows:
        old_id = before["L4_ID"]
        review = review_by_id[old_id]
        comment = review["휴먼검수 3차 의견"].strip()
        if old_id in DELETIONS:
            tombstone_rows.append({
                "Register_ID": f"HR3-{len(tombstone_rows) + 1:04d}",
                "source_row_id": before.get("source_row_id", ""),
                "Deleted_L4_ID": old_id,
                "Title_ko": before["L4_Title_ko"],
                "Reason": f"{DELETIONS[old_id]} Original third-round comment: {comment}",
            })
            application_rows.append({
                "Round3_Action_ID": f"HR3-A{len(application_rows) + 1:03d}",
                "Source_File": review["_source_file"],
                "Source_Row_Number": review["_source_row_number"],
                "L4_ID_Before": old_id,
                "L4_ID_After": "",
                "Action": "DELETE",
                "L1_ID_Before": before["L1_ID"],
                "L2_ID_Before": before["L2_ID"],
                "L3_ID_Before": before["L3_ID"],
                "L1_ID_After": "",
                "L2_ID_After": "",
                "L3_ID_After": "",
                "Human_Review_Round3_Comment": comment,
                "Interpretation": DELETIONS[old_id],
                "Reviewer_A": "DELETE",
                "Reviewer_B": "DELETE",
                "Adjudication": "CONSENSUS",
                "Ambiguity": "LOW",
                "Result": "APPLIED_DELETE",
            })
            continue

        after = deepcopy(before)
        if old_id in OPERATIONS:
            spec = OPERATIONS[old_id]
            target_l3 = l3_by_id[spec["target_l3"]]
            for field in HIERARCHY_FIELDS:
                after[field] = target_l3[field]
            after["L4_ID"] = spec["target_id"]
            after["L4_Title_ko"] = spec["title_ko"]
            after["L4_Title_en"] = spec["title_en"]
            after["L4_Description_ko"] = spec["description_ko"]
            after["L4_Description_en"] = spec["description_en"]
            after["Mapping_Method"] = "HD"
            after["HD_Reason"] = append_text(after.get("HD_Reason", ""), "HUMAN_REVIEW_ROUND3", comment)
            after["Domain_Route_Basis"] = append_text(
                after.get("Domain_Route_Basis", ""), "HUMAN_REVIEW_ROUND3", spec["rationale"]
            )
            after["Transformation_Action"] = append_text(
                after.get("Transformation_Action", ""), "HUMAN_REVIEW_ROUND3", spec["action"]
            )
            after["Transformation_Rationale"] = append_text(
                after.get("Transformation_Rationale", ""), "HUMAN_REVIEW_ROUND3", spec["rationale"]
            )
            after["Candidate_Constraint_Reason"] = "HUMAN_REVIEW_ROUND3_NO_EM_RERUN"
            after["Definition_L3_Anchor_ID"] = spec["target_l3"]
            after["Definition_Grounding_Action"] = "HUMAN_REVIEW_ROUND3_NO_EM_RERUN"
            after["Human_Review_Comment"] = append_text(
                after.get("Human_Review_Comment", ""), "HUMAN_REVIEW_ROUND3", comment
            )
            result_ko = (
                f"3차 휴먼검수 의견에 따라 {old_id}을(를) 삭제 없이 "
                f"{spec['target_id']}({spec['title_ko']})로 반영함. "
                f"대상 L3: {spec['target_l3']}."
            )
            after["Human_Review_Result"] = append_text(
                after.get("Human_Review_Result", ""), "HUMAN_REVIEW_ROUND3", result_ko
            )
            for field in SCORE_FIELDS + KEYWORD_FIELDS:
                if field in after:
                    after[field] = ""
            id_crosswalk[old_id] = spec["target_id"]
            application_rows.append({
                "Round3_Action_ID": f"HR3-A{len(application_rows) + 1:03d}",
                "Source_File": review["_source_file"],
                "Source_Row_Number": review["_source_row_number"],
                "L4_ID_Before": old_id,
                "L4_ID_After": spec["target_id"],
                "Action": spec["action"],
                "L1_ID_Before": before["L1_ID"],
                "L2_ID_Before": before["L2_ID"],
                "L3_ID_Before": before["L3_ID"],
                "L1_ID_After": after["L1_ID"],
                "L2_ID_After": after["L2_ID"],
                "L3_ID_After": after["L3_ID"],
                "Human_Review_Round3_Comment": comment,
                "Interpretation": spec["rationale"],
                "Reviewer_A": spec["reviewer_a"],
                "Reviewer_B": spec["reviewer_b"],
                "Adjudication": spec["adjudication"],
                "Ambiguity": spec["ambiguity"],
                "Result": "APPLIED",
            })
        after_rows.append(after)

    if len(after_rows) != 623:
        raise ValueError(f"Expected 623 cards after six deletions, found {len(after_rows)}")
    if len({row["L4_ID"] for row in after_rows}) != 623:
        raise ValueError("Duplicate final L4 IDs")
    if len(application_rows) != 30:
        raise ValueError("Expected 30 applied comment rows")

    order_by_l3 = {row["L3_ID"]: index for index, row in enumerate(l3_rows)}
    def sort_key(row: dict[str, str]) -> tuple[int, int, str]:
        suffix = row["L4_ID"].rsplit("_", 1)[-1]
        return order_by_l3[row["L3_ID"]], int(suffix) if suffix.isdigit() else 999999, row["L4_ID"]
    after_rows.sort(key=sort_key)

    by_domain = {domain: [] for domain in L4_FILES}
    for row in after_rows:
        by_domain[domain_name(row["L1_ID"])].append(row)

    for domain, name in L4_FILES.items():
        write_csv(FULL_DATA / name, full_fields, by_domain[domain])
        write_csv(PUBLIC_DATA / name, PUBLIC_FIELDS, by_domain[domain])

    ledger_fields = [
        "Round3_Row_ID", "Source_File", "Source_Row_Number", "Domain_Before",
        "L4_ID_Before", "L4_Title_ko_Before", "L2_ID_Before", "L3_ID_Before",
        "Human_Review_Round3_Comment", "Comment_Status", "Interpreted_Intent", "Action",
        "Final_Disposition", "L4_ID_After", "Domain_After", "L2_ID_After", "L3_ID_After",
        "L4_Title_ko_After", "L4_Title_en_After", "L4_Description_ko_After",
        "L4_Description_en_After", "Reviewer_A", "Reviewer_B", "Adjudication",
        "Ambiguity", "Lineage_Status",
    ]
    after_by_old = {
        old: next((row for row in after_rows if row["L4_ID"] == new), None)
        for old, new in {**{key: key for key in surviving_old_ids}, **id_crosswalk}.items()
    }
    ledger_rows: list[dict[str, str]] = []
    for index, review in enumerate(review_rows_all, start=1):
        old_id = review["L4_ID"]
        before_domain = current_domain[old_id]
        before = next(row for row in current_rows if row["L4_ID"] == old_id)
        comment = review["휴먼검수 3차 의견"].strip()
        app = next((row for row in application_rows if row["L4_ID_Before"] == old_id), None)
        after = after_by_old.get(old_id)
        ledger_rows.append({
            "Round3_Row_ID": f"HR3-R{index:04d}",
            "Source_File": review["_source_file"],
            "Source_Row_Number": review["_source_row_number"],
            "Domain_Before": before_domain,
            "L4_ID_Before": old_id,
            "L4_Title_ko_Before": before["L4_Title_ko"],
            "L2_ID_Before": before["L2_ID"],
            "L3_ID_Before": before["L3_ID"],
            "Human_Review_Round3_Comment": comment,
            "Comment_Status": "COMMENT_PRESENT" if comment else "NO_COMMENT",
            "Interpreted_Intent": app["Interpretation"] if app else "No third-round change requested.",
            "Action": app["Action"] if app else "NO_CHANGE",
            "Final_Disposition": app["Result"] if app else "UNCHANGED",
            "L4_ID_After": after["L4_ID"] if after else "",
            "Domain_After": domain_name(after["L1_ID"]) if after else "",
            "L2_ID_After": after["L2_ID"] if after else "",
            "L3_ID_After": after["L3_ID"] if after else "",
            "L4_Title_ko_After": after["L4_Title_ko"] if after else "",
            "L4_Title_en_After": after["L4_Title_en"] if after else "",
            "L4_Description_ko_After": after["L4_Description_ko"] if after else "",
            "L4_Description_en_After": after["L4_Description_en"] if after else "",
            "Reviewer_A": app["Reviewer_A"] if app else "NOT_REQUIRED",
            "Reviewer_B": app["Reviewer_B"] if app else "NOT_REQUIRED",
            "Adjudication": app["Adjudication"] if app else "NOT_REQUIRED",
            "Ambiguity": app["Ambiguity"] if app else "NONE",
            "Lineage_Status": "TOMBSTONE" if after is None else ("ID_CROSSWALK" if old_id != after["L4_ID"] else "ID_RETAINED"),
        })

    application_fields = list(application_rows[0])
    write_csv(ROUND3_DIR / "Human_Review_Round3_Decision_Ledger.csv", ledger_fields, ledger_rows)
    write_csv(ROUND3_DIR / "Human_Review_Round3_Application_Log.csv", application_fields, application_rows)
    write_csv(VALIDATION / "Human_Review_Round3_Decision_Ledger.csv", ledger_fields, ledger_rows)
    write_csv(VALIDATION / "Human_Review_Round3_Application_Log.csv", application_fields, application_rows)

    tombstone_path = VALIDATION / "Deletion_Tombstones.csv"
    tomb_fields, old_tombstones = read_csv(tombstone_path)
    old_tombstones = [row for row in old_tombstones if not row["Register_ID"].startswith("HR3-")]
    write_csv(tombstone_path, tomb_fields, old_tombstones + tombstone_rows)

    reference_path = VALIDATION / "L4_Journal_Reference_Verified.csv"
    reference_fields, reference_rows = read_csv(reference_path)
    updated_refs = []
    for row in reference_rows:
        if row["L4_ID"] in DELETIONS:
            continue
        row = dict(row)
        row["L4_ID"] = id_crosswalk.get(row["L4_ID"], row["L4_ID"])
        updated_refs.append(row)
    write_csv(reference_path, reference_fields, updated_refs)

    correction_path = VALIDATION / "Audit_Correction_Log.csv"
    correction_fields, corrections = read_csv(correction_path)
    corrections = [row for row in corrections if row["Correction_ID"] != "AC-18"]
    corrections.append({
        "Correction_ID": "AC-18",
        "Date": "2026-09-01",
        "Type": "HUMAN_REVIEW_ROUND3_APPLICATION",
        "Target": "30 reviewed L4 rows",
        "Action": "19_REASSIGN_6_DELETE_5_GENERALISE",
        "Detail": "Read all 629 round-3 rows; applied all 30 non-empty comments without EM, including 19 L2/L3 reassignments, 6 deletions, and 5 same-L3 scope generalisations. No merge, split, new L4, or new L3 was introduced. 629 to 623 cards.",
        "Basis": "KTSPACE third-round human review; two independent expert reviews for ambiguous cases; L3 master precedence; final third-party adjudication.",
    })
    write_csv(correction_path, correction_fields, corrections)

    counts = {domain: len(rows) for domain, rows in by_domain.items()}
    mapping_counts = {
        domain: dict(Counter(row["Mapping_Method"] for row in rows))
        for domain, rows in by_domain.items()
    }
    validation_record = {
        "release_id": "RAI-Risk-Taxonomy-2.0-master",
        "review_round": "human_review_round3",
        "date": "2026-09-01",
        "method": "Deterministic semantic interpretation and application of human-review comments; no EM or Hybrid EM",
        "source_rows": 629,
        "commented_rows": 30,
        "uncommented_rows": 599,
        "actions": {"MOVE_REWRITE": 19, "DELETE": 6, "RENAME_REWRITE": 5, "MERGE": 0, "SPLIT": 0, "NEW_L4": 0, "NEW_L3": 0},
        "counts": {"General": counts["General"], "Agentic": counts["Agentic"], "Physical": counts["Physical"], "total": len(after_rows)},
        "mapping_method_counts": mapping_counts,
        "id_crosswalk": id_crosswalk,
        "deleted_ids": sorted(DELETIONS),
        "l3_master_rows": len(l3_rows),
        "l3_master_sha256_before": l3_hash_before,
        "l3_master_sha256_after": sha256(PUBLIC_DATA / "L1_L2_L3_Master.csv"),
        "l3_master_unchanged": l3_hash_before == sha256(PUBLIC_DATA / "L1_L2_L3_Master.csv"),
        "duplicate_final_l4_ids": len(after_rows) - len({row["L4_ID"] for row in after_rows}),
        "others_assignments": sum(row["L3_ID"].endswith("Others") for row in after_rows),
        "reviewers": ["Independent expert reviewer A", "Independent expert reviewer B"],
        "adjudication": {
            "G_INT_SELF_006": "G_SYS_CONTEXT selected to preserve the source mechanism without inventing manipulative intent.",
            "P_INT_SAFETY_007": "Retained as a distinct generalised card because no merge was explicitly requested.",
            "P_INT_SAFETY_004": "Moved to G_INT_UNETH by two-reviewer consensus and L3-master precedence.",
        },
        "status": "PASS",
    }
    if not validation_record["l3_master_unchanged"] or validation_record["duplicate_final_l4_ids"] or validation_record["others_assignments"]:
        raise ValueError("Round-3 validation failed")
    for path in (
        ROUND3_DIR / "Human_Review_Round3_Validation_Record.json",
        VALIDATION / "Human_Review_Round3_Validation_Record.json",
    ):
        path.write_text(json.dumps(validation_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    method_text = """# Third-Round Human Review Application Method

## Scope

All 629 rows in the three KTSPACE third-round review tables were read before any transformation. Thirty rows contained reviewer comments and 599 rows contained no requested change.

## Procedure

1. Freeze the three source CSV files and match every L4 ID to the current master.
2. Interpret each non-empty comment against the current L4 meaning and the unchanged 50-row L3 master.
3. Obtain two independent expert judgements for ambiguous or conflicting cases.
4. Adjudicate disagreements without EM, Hybrid EM, keyword voting, or nearest-category forcing.
5. Apply only the requested or necessary semantic operation: 19 reassignments, 6 deletions, and 5 scope generalisations.
6. Preserve old-to-new ID lineage and deletion tombstones. No merge, split, new L4, or new L3 is introduced.
7. Verify card counts, unique IDs, zero Others assignments, exact comment preservation, and byte-identical L3 master content.

## Adjudicated cases

- `G_INT_SELF_006`: moved to `G_SYS_CONTEXT`, preserving the contextually inappropriate-content mechanism without adding unsupported manipulative intent.
- `P_INT_SAFETY_007`: retained as a distinct card after removing the household limitation because the third-round comment did not authorise a merge.
- `P_INT_SAFETY_004`: moved to `G_INT_UNETH` because both expert reviewers found a direct conflict with the Physical Safety L3.
"""
    (ROUND3_DIR / "Human_Review_Round3_Methodology_20260901.md").write_text(method_text, encoding="utf-8")
    (VALIDATION / "Human_Review_Round3_Methodology_20260901.md").write_text(method_text, encoding="utf-8")

    for name in (
        "Human_Review_Round3_Decision_Ledger.csv",
        "Human_Review_Round3_Application_Log.csv",
        "Human_Review_Round3_Validation_Record.json",
        "Human_Review_Round3_Methodology_20260901.md",
        "Deletion_Tombstones.csv",
        "L4_Journal_Reference_Verified.csv",
        "Audit_Correction_Log.csv",
    ):
        source = VALIDATION / name
        target = HANDOVER_VALIDATION / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    return validation_record


if __name__ == "__main__":
    print(json.dumps(apply(), ensure_ascii=False, indent=2))
