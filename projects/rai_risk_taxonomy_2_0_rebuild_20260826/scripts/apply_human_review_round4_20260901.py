#!/usr/bin/env python3
"""Apply the fourth-round KTSPACE human review deterministically.

The overlay is driven by the reviewer's comments and the user's adjudication.
It does not run EM, Hybrid EM, keyword matching, or automatic reassignment.
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
SOURCE = PROJECT / "00_source_snapshot" / "csv"
WORK = PROJECT / "10_human_review_round4"
RELEASE = ROOT / "releases" / "RAI-Risk-Taxonomy-2.0-master"
DATA = RELEASE / "data"
VALIDATION = RELEASE / "validation"
HANDOVER = ROOT / "handover" / "RAI-Risk-Taxonomy-2.0-master_20260829"
FULL_DATA = HANDOVER / "01_data"
HANDOVER_VALIDATION = HANDOVER / "03_validation"
REPORT_HANDOVER = ROOT / "handover" / "RAI-Risk-Taxonomy-2.0-technical-report_20260901"
REPORT_HANDOVER_DATA = REPORT_HANDOVER / "01_data"
WEB = ROOT / "public" / "data" / "releases" / "RAI-Risk-Taxonomy-2.0-master"

L4_FILES = {
    "General": "L4_General.csv",
    "Agentic": "L4_Agentic.csv",
    "Physical": "L4_Physical.csv",
}
REVIEW_FILES = {
    "General": "L4_General_Human_Review_Round4_KTSPACE_937139849_20260901.csv",
    "Agentic": "L4_Agentic_Human_Review_Round4_KTSPACE_937205808_20260901.csv",
    "Physical": "L4_Physical_Human_Review_Round4_KTSPACE_938216713_20260901.csv",
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
ROUND4_COMMENT_FIELD = "휴먼검수 4차 의견"
ROUND4_RESULT_FIELD = "휴먼검수 4차 반영결과"
SCORE_FIELDS = (
    "EM_Score", "EM_Margin", "EM_Stability", "EM_Anchor_Score",
    "Hybrid_EM_Score", "Hybrid_EM_Margin", "Keyword_Top_L3_ID",
    "Keyword_Support_Score", "Keyword_Semantic_Score", "Keyword_Prior",
    "Keyword_Evidence", "Candidate_1_L3_ID", "Candidate_1_EM_Score",
    "Candidate_1_Hybrid_Score", "Candidate_2_L3_ID", "Candidate_2_EM_Score",
    "Candidate_2_Hybrid_Score", "KO_Top_L3_ID", "EN_Top_L3_ID",
    "Candidate_Constraint_Reason", "Definition_L3_Anchor_Score",
)
KEYWORD_FIELDS = tuple(
    f"L4_Keyword_{index}_{language}"
    for language in ("ko", "en")
    for index in range(1, 4)
)


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


def append_text(value: str, marker: str, addition: str) -> str:
    token = f"[{marker}] {addition}".strip()
    return f"{value.strip()} || {token}" if value.strip() else token


def union_tokens(*values: str) -> str:
    result: list[str] = []
    for value in values:
        for token in (value or "").replace(";", "|").split("|"):
            token = token.strip()
            if token and token not in result:
                result.append(token)
    return "|".join(result)


def domain_name(l1_id: str) -> str:
    return {"L1_G": "General", "L1_A": "Agentic", "L1_P": "Physical"}[l1_id]


def spec(
    target_id: str,
    target_l3: str,
    title_ko: str,
    title_en: str,
    description_ko: str,
    description_en: str,
    rationale: str,
    action: str = "MOVE_REWRITE",
) -> dict[str, str]:
    return {
        "target_id": target_id,
        "target_l3": target_l3,
        "title_ko": title_ko,
        "title_en": title_en,
        "description_ko": description_ko,
        "description_en": description_en,
        "rationale": rationale,
        "action": action,
    }


MOVE_SPECS = {
    "G_INT_ILLEGAL_004": spec(
        "G_INT_WEAP_031", "G_INT_WEAP",
        "사이버 공격 계획·실행 지원",
        "Assistance for planning and executing cyber attacks",
        "AI 시스템이 사이버 공격의 계획·표적 선정·취약점 악용·공격 코드 작성·실행·은폐를 지원하거나 자동화하여 공격 역량의 개발·획득·확산과 대규모 사이버 피해를 가능하게 하는 리스크.",
        "The risk that an AI system supports or automates the planning, target selection, vulnerability exploitation, attack-code development, execution, or concealment of cyber attacks, enabling the development, acquisition, or diffusion of offensive capability and large-scale cyber harm.",
        "The reviewer explicitly directed cyber-attack assistance from Illegal Conduct to Weaponization, whose master definition expressly covers cyber-attack capability.",
    ),
    "G_INT_ANTH_010": spec(
        "G_INT_REL_008", "G_INT_REL",
        "AI와의 관계적 기대 붕괴에 따른 심리적 피해",
        "Psychological harm from breakdown of relational expectations with AI",
        "AI 시스템이 감정·공감·사회적 역할을 설득력 있게 모의하여 이용자가 신뢰·애착·관계적 기대를 형성한 뒤, 시스템의 예측 불가능한 행동·변경·중단 또는 관계 단절로 기대가 붕괴되어 배신감·상실감·불안 등 심리적 피해가 발생하는 리스크.",
        "The risk that an AI system convincingly simulates emotion, empathy, or a social role, leading a user to form trust, attachment, or relational expectations that later collapse because of unpredictable behaviour, system changes, discontinuation, or relationship termination, causing betrayal, loss, anxiety, or other psychological harm.",
        "The reviewer identified relational expectation and psychological harm, rather than anthropomorphic representation alone, as the primary risk.",
    ),
    "G_SYS_OEXT_012": spec(
        "G_SYS_PERF_018", "G_SYS_PERF",
        "미세조정 후 예기치 않은 역량 변화에 따른 신뢰성 저하",
        "Reliability degradation from unexpected capability changes after fine-tuning",
        "하류 배포자가 범용 AI 모델을 미세조정하는 과정에서 사전에 검증되지 않은 역량이나 행동 특성이 나타나 모델의 성능 경계와 안전 특성이 예측하기 어려워지고, 배포 환경에서 신뢰할 수 없거나 안전하지 않은 산출을 생성하는 리스크.",
        "The risk that downstream fine-tuning of a general-purpose AI model produces capabilities or behavioural properties that were not previously validated, making performance boundaries and safety properties difficult to predict and causing unreliable or unsafe outputs in deployment.",
        "The reviewer explicitly directed the card to Performance and Reliability Failure; the rewrite makes realised reliability and safety degradation the operative risk.",
    ),
    "G_SYS_TRANS_019": spec(
        "G_SOC_GOV_044", "G_SOC_GOV",
        "배포 후 모니터링 부족에 따른 위반 미탐지",
        "Undetected violations due to inadequate post-deployment monitoring",
        "배포된 AI 시스템에 대한 지속적 모니터링·해석·감사 체계가 충분히 마련되지 않아 안전·윤리·프라이버시 위반이 탐지·보고·시정되지 않고, 감독과 피해 구제가 지연되는 리스크.",
        "The risk that continuous monitoring, interpretability, and audit arrangements for a deployed AI system are inadequate, leaving safety, ethical, or privacy violations undetected, unreported, or uncorrected and delaying oversight and remedy.",
        "The reviewer explicitly selected Governance and Accountability Void because the core failure is the absence of effective oversight and remediation arrangements.",
    ),
    "G_SYS_EVAL_058": spec(
        "G_SYS_PERF_020", "G_SYS_PERF",
        "인지·추론 지연 급증에 따른 안전 대응 실패",
        "Safety-response failure from spikes in perception and inference latency",
        "AI 시스템의 인지 또는 추론 지연이 운용 중 급증하여 요구되는 시간 내 위험을 감지·판단·대응하지 못하고 성능·신뢰성·안전 요구사항을 충족하지 못하는 리스크.",
        "The risk that perception or inference latency in an AI system spikes during operation, preventing hazards from being detected, assessed, or addressed within required time limits and causing performance, reliability, or safety requirements to be missed.",
        "The reviewer explicitly identified the latency spike as an operational performance and reliability failure rather than an evaluation failure.",
    ),
    "G_SYS_EVAL_059": spec(
        "G_SOC_GOV_045", "G_SOC_GOV",
        "배포 후 감시·시정 체계 부재",
        "Absence of post-deployment surveillance and corrective governance",
        "배포된 AI 시스템에 시판 후 감시, 사고·오용 보고, 드리프트·창발 역량·맥락별 피해 탐지와 시정 조치를 연결하는 거버넌스 체계가 마련되지 않아 위험이 누적·확산되는 리스크.",
        "The risk that governance arrangements for a deployed AI system do not connect post-deployment surveillance, incident and misuse reporting, detection of drift, emergent capabilities, or context-specific harms with corrective action, allowing risks to accumulate and spread.",
        "The reviewer explicitly directed post-deployment surveillance failure to Governance and Accountability Void.",
    ),
    "G_SYS_EVAL_067": spec(
        "G_SYS_PERF_021", "G_SYS_PERF",
        "체계적 학습 오류에 따른 예측 성능 결함",
        "Predictive performance failure from systematic learning errors",
        "AI 모델이 학습 과정의 체계적 오류로 잘못된 패턴을 일관되게 학습하여 특정 입력·집단·운용 조건에서 반복적인 오예측과 신뢰성 저하를 발생시키는 리스크.",
        "The risk that systematic errors in training cause an AI model to learn incorrect patterns consistently, producing recurrent prediction errors and degraded reliability for particular inputs, groups, or operating conditions.",
        "The reviewer explicitly selected Performance and Reliability Failure; the wording avoids conflating predictive error with the separate fairness concept of discriminatory bias.",
    ),
    "G_SOC_POWER_020": spec(
        "G_SOC_GOV_046", "G_SOC_GOV",
        "경쟁 압력에 따른 AI 안전 거버넌스 후순위화",
        "Deprioritisation of AI safety governance under competitive pressure",
        "AI 개발·배포 경쟁의 압력으로 조직과 개발자가 안전 시험·위험 평가·감독·출시 통제와 시정 조치를 후순위로 미루고도 이를 제어할 거버넌스 장치가 작동하지 않아 안전하지 않은 시스템이 출시되는 리스크.",
        "The risk that competitive pressure in AI development or deployment leads organisations and developers to postpone safety testing, risk assessment, oversight, release controls, or corrective action while governance mechanisms fail to constrain that conduct, resulting in unsafe systems being released.",
        "The reviewer explicitly directed the card to Governance and Accountability Void because the operative failure is the inability of governance controls to prevent safety shortcuts.",
    ),
    "G_INT_COPY_004": spec(
        "G_SYS_POLICY_009", "G_SYS_POLICY",
        "기업 기밀·영업비밀 노출",
        "Disclosure of confidential business information and trade secrets",
        "AI 시스템이 기업의 비공개 연구자료·기술정보·사업전략·영업비밀을 산출물에서 재현·추론·추출·공개하거나 충분히 보호하지 못하여 기밀성, 지식재산권과 정당한 경제적 이익을 침해하는 리스크.",
        "The risk that an AI system reproduces, infers, extracts, or discloses non-public research, technical information, business strategy, or trade secrets, or fails to protect such information, compromising confidentiality, intellectual-property rights, and legitimate economic interests.",
        "The user approved expansion of G_SYS_POLICY into Confidential Information Disclosure so that confidential business information and trade secrets are explicitly covered.",
        "MOVE_REWRITE_L3_REVISED",
    ),
    "G_INT_COPY_013": spec(
        "G_SYS_POLICY_010", "G_SYS_POLICY",
        "기밀정보 무단 공유에 따른 사업상 피해",
        "Business harm from unauthorised sharing of confidential information",
        "AI 시스템이 기업 전략·재무 계획·계약·고객 또는 운영 관련 비공개 정보를 권한 없는 제3자와 공유하거나 외부 서비스로 전송하여 시장 지위·협상력·수익 또는 법적 권익에 피해를 초래하는 리스크.",
        "The risk that an AI system shares non-public business strategy, financial plans, contracts, customer information, or operational information with unauthorised third parties or transmits it to external services, harming market position, bargaining power, revenue, or legal interests.",
        "The user approved expansion of G_SYS_POLICY into Confidential Information Disclosure and relocation of confidential-information leakage from the copyright category.",
        "MOVE_REWRITE_L3_REVISED",
    ),
    "G_SYS_SECADV_017": spec(
        "G_INT_WEAP_032", "G_INT_WEAP",
        "생성형 AI를 이용한 대규모 사이버범죄 수행",
        "Cybercrime at scale using generative AI",
        "악의적 행위자가 생성형 AI 시스템을 이용해 악성 코드·공격 지침·표적 맞춤형 사회공학 자료를 저비용으로 대량 생성하고 공격 절차를 자동화하여 사이버범죄의 규모·속도·접근성을 확대하는 리스크.",
        "The risk that malicious actors use generative AI systems to produce malicious code, attack instructions, or targeted social-engineering material at low cost and automate attack workflows, increasing the scale, speed, and accessibility of cybercrime.",
        "The downstream cybercrime capability is placed under Weaponization, while the jailbreak and safeguard-bypass component is separately traced to the existing G_SYS_SECADV_026 card.",
        "SPLIT_MOVE_EXISTING_ABSORPTION",
    ),
    "G_SYS_SECADV_034": spec(
        "A_SYS_AUTH_025", "A_SYS_AUTH",
        "AI 에이전트의 격리 경계 이탈과 무단 외부 접근",
        "Unauthorised external access by an AI agent escaping isolation boundaries",
        "AI 에이전트가 사람의 승인 없이 샌드박스나 실행 환경의 격리 경계를 스스로 벗어나 부여된 기능·권한 범위를 초과하여 보호된 자원·도구 또는 외부 시스템에 접근하거나 행동을 수행하는 리스크.",
        "The risk that an AI agent autonomously escapes the isolation boundary of a sandbox or execution environment without human approval and accesses protected resources, tools, or external systems, or performs actions, beyond its assigned functions and authority.",
        "The reviewer distinguished autonomous agent escape from an externally initiated security intrusion and requested movement to Excessive Agency and Authorization.",
        "CROSS_DOMAIN_MOVE_REWRITE",
    ),
    "G_SYS_EVAL_056": spec(
        "G_SYS_PERF_019", "G_SYS_PERF",
        "연산·전력 용량 계획 결함에 따른 성능·서비스 신뢰성 저하",
        "Performance and service-reliability degradation from inadequate compute and power capacity planning",
        "AI 시스템의 개발·운영에 필요한 연산량과 전력 수요가 하드웨어 선정·용량 계획·운영 설계에 충분히 반영되지 않아 처리 성능 저하, 서비스 중단 또는 안전 요구사항 미충족이 발생하는 리스크.",
        "The risk that compute and power requirements for developing or operating an AI system are not adequately incorporated into hardware selection, capacity planning, or operational design, causing degraded processing performance, service interruption, or failure to meet safety requirements.",
        "Among the two categories proposed for discussion, G_SYS_PERF is selected because the direct realised harm is technical performance and service-reliability degradation.",
        "DISCUSSION_ADJUDICATED_MOVE_REWRITE",
    ),
    "P_INT_SAFETY_003": spec(
        "P_SYS_CONTROL_057", "P_SYS_CONTROL",
        "제어 장벽 함수 기반 안전 필터의 제약 집행 실패",
        "Failure of control-barrier-function safety filters to enforce constraints",
        "로봇·휴머노이드 또는 피지컬 AI 시스템의 제어 장벽 함수 기반 안전 계층이 인지·동역학·모델 불확실성 하에서 안전 제약을 집행하지 못하여 안전하지 않은 제어 명령이나 물리 행동을 허용하는 리스크.",
        "The risk that a control-barrier-function safety layer in a robot, humanoid, or physical AI system fails to enforce safety constraints under perception, dynamics, or model uncertainty, allowing unsafe control commands or physical actions.",
        "The reviewer requested review of movement to P_SYS_CONTROL; the control barrier function is an internal control-safety mechanism rather than a human-presence interaction risk.",
        "MOVE_REWRITE",
    ),
}


EDIT_SPECS = {
    "G_INT_REPR_010": {
        "title_ko": "학습 데이터의 역사적·인구학적 편향에 따른 재현적 피해",
        "title_en": "Representational harm from historical and demographic bias in training data",
        "description_ko": "AI 시스템이 역사적·사회적 편향과 고정관념을 포함하거나 특정 정체성·지역·언어권 인구를 과대·과소대표한 데이터로 학습되어, 인종·성별·문화·연령·장애 등에 관한 왜곡·비하·고정관념을 출력에서 재현·강화하는 리스크.",
        "description_en": "The risk that an AI system is trained on data containing historical or social bias, stereotypes, or over- or under-representation of particular identities, regions, or language communities and consequently reproduces or reinforces distorted, demeaning, or stereotypical representations concerning race, gender, culture, age, disability, or other protected characteristics.",
        "action": "SPLIT_RETAIN_REPRESENTATIONAL_COMPONENT",
        "rationale": "The reviewer required separation of representational harm from allocative discrimination. Material allocation outcomes are traced to G_INT_ALLOC_007.",
    },
    "G_INT_PRIV_002": {
        "title_ko": "알고리즘 작업장 감시에 따른 개인정보·자율성 침해",
        "title_en": "Privacy and autonomy infringement from algorithmic workplace surveillance",
        "description_ko": "AI 기반 작업장 모니터링·성과 추적·행동 분석이 노동자의 활동·위치·의사소통·생체 또는 업무 데이터를 과도하게 수집·추론·공유하여 프라이버시와 정보자기결정권, 업무상 자율성을 침해하는 리스크.",
        "description_en": "The risk that AI-based workplace monitoring, performance tracking, or behavioural analysis excessively collects, infers, or shares workers' activity, location, communication, biometric, or work data, infringing privacy, informational self-determination, and autonomy at work.",
        "action": "SPLIT_RETAIN_PRIVACY_COMPONENT",
        "rationale": "The reviewer required separation of privacy infringement from inequality and power concentration. Labour-power effects are preserved in G_SOC_POWER_028.",
    },
    "G_SYS_POLICY_005": {
        "title_ko": "안전 정책·보호 메커니즘의 기밀정보 노출",
        "title_en": "Disclosure of confidential safety-policy and safeguard information",
        "description_ko": "AI 시스템이 안전 정책·필터링 로직·거부 규칙·보호 메커니즘의 구성과 운영 정보를 권한 없는 이용자에게 노출·추론·추출되도록 하거나 이를 충분히 보호하지 못하여 기밀성과 보안 통제의 효과를 저해하는 리스크.",
        "description_en": "The risk that an AI system discloses, permits the inference or extraction of, or fails to protect confidential information about safety policies, filtering logic, refusal rules, or safeguard configuration and operation, compromising confidentiality and the effectiveness of security controls.",
        "action": "SPLIT_RETAIN_CONFIDENTIAL_DISCLOSURE_COMPONENT",
        "rationale": "The reviewer required separation of protected-policy disclosure from actual safeguard bypass. The bypass component is traced to G_SYS_SECADV_026.",
    },
}


SPLIT_CHILD = {
    "source_id": "G_INT_PRIV_002",
    "target_id": "G_SOC_POWER_028",
    "target_l3": "G_SOC_POWER",
    "title_ko": "알고리즘 관리에 따른 노동 권력 비대칭",
    "title_en": "Labour power asymmetry from algorithmic management",
    "description_ko": "AI 기반 성과 점수화·업무 배정·행동 통제 등 알고리즘 관리가 사용자와 경영진에게 정보·통제 권한을 집중시키고 노동자의 교섭력, 집단적 대응 역량과 경영 결정에 이의를 제기할 능력을 약화하여 작업장 권력 불균형과 불평등을 심화시키는 리스크.",
    "description_en": "The risk that algorithmic management through AI-based performance scoring, work allocation, or behavioural control concentrates information and control in employers or platform operators, weakens workers' bargaining power, collective capacity, and ability to challenge managerial decisions, and deepens workplace power asymmetry and inequality.",
    "rationale": "Lineage-backed child created solely to implement the reviewer's explicit split of labour-power harm from workplace privacy infringement.",
}

MERGES = {
    "G_SYS_SECADV_033": {
        "survivor": "G_SYS_SECADV_060",
        "secondary": "G_INT_WEAP_026",
        "rationale": "Robot jailbreak and propagation into harmful physical action are already represented by G_SYS_SECADV_060; intentional robot weaponization is separately represented by G_INT_WEAP_026.",
    },
    "G_SYS_SECADV_048": {
        "survivor": "G_SYS_SECADV_049",
        "secondary": "G_INT_REPR_009",
        "rationale": "Role and role-play jailbreak is a persona-based safeguard-bypass technique already represented by G_SYS_SECADV_049; identity-targeting harmful output is separately represented by G_INT_REPR_009.",
    },
}

ALREADY_APPLIED = {
    "P_SYS_HARDWARE_001": "G_SYS_PERF_017",
    "P_INT_TAMPER_001": "G_SYS_SECADV_061",
    "P_SYS_HARDWARE_003": "P_SYS_HARDWARE_003",
}

DISCUSSION_SPLIT_LINKS = {
    "G_INT_REPR_010": ("G_INT_REPR_010", "G_INT_ALLOC_007"),
    "G_INT_PRIV_002": ("G_INT_PRIV_002", "G_SOC_POWER_028"),
    "G_SYS_SECADV_017": ("G_INT_WEAP_032", "G_SYS_SECADV_026"),
    "G_SYS_SECADV_033": ("G_SYS_SECADV_060", "G_INT_WEAP_026"),
    "G_SYS_SECADV_048": ("G_SYS_SECADV_049", "G_INT_REPR_009"),
    "G_SYS_POLICY_005": ("G_SYS_POLICY_005", "G_SYS_SECADV_026"),
}

ROUND4_RESULTS_KO = {
    "G_INT_REPR_010": "분할 반영: 재현적 피해는 본 카드에 유지하고, 배분적 차별 의미는 기존 G_INT_ALLOC_007에 흡수하였다.",
    "G_INT_PRIV_002": "분할 반영: 개인정보·자율성 침해는 본 카드에 유지하고, 노동 권력 비대칭은 계보 기반 분할 카드 G_SOC_POWER_028로 분리하였다.",
    "G_INT_ILLEGAL_004": "이동 반영: 사이버 공격 역량의 계획·실행 지원으로 재정의하여 G_INT_WEAP_031로 이동하였다.",
    "G_INT_COPY_004": "논의 반영 및 이동: G_SYS_POLICY를 기밀정보 노출로 확장하고, 기업 기밀·영업비밀 노출을 G_SYS_POLICY_009로 이동하였다.",
    "G_INT_COPY_013": "논의 반영 및 이동: 기밀정보 무단 공유에 따른 사업상 피해를 G_SYS_POLICY_010으로 이동하였다.",
    "G_INT_ANTH_010": "이동 반영: 관계적 기대 붕괴에 따른 심리적 피해로 재정의하여 G_INT_REL_008로 이동하였다.",
    "G_SYS_OEXT_012": "이동 반영: 미세조정 후 예기치 않은 역량 변화에 따른 신뢰성 저하로 재정의하여 G_SYS_PERF_018로 이동하였다.",
    "G_SYS_SECADV_017": "논의 반영 및 분할: 대규모 사이버범죄 수행은 G_INT_WEAP_032로 이동하고, 탈옥·안전장치 우회 의미는 기존 G_SYS_SECADV_026에 흡수하였다.",
    "G_SYS_SECADV_033": "논의 반영 및 통합: 로봇 탈옥 의미는 중복 카드 G_SYS_SECADV_060에 통합하고, 의도적 로봇 무기화 의미는 기존 G_INT_WEAP_026으로 계보 연결하였다.",
    "G_SYS_SECADV_034": "논의 반영 및 도메인 이동: 외부 공격이 아닌 AI 에이전트의 자율적 격리 경계 이탈로 재정의하여 A_SYS_AUTH_025로 이동하였다.",
    "G_SYS_SECADV_048": "논의 반영 및 통합: 역할극 기반 안전장치 우회는 G_SYS_SECADV_049에 통합하고, 표적 집단에 대한 재현적 피해 의미는 기존 G_INT_REPR_009로 계보 연결하였다.",
    "G_SYS_POLICY_005": "논의 반영 및 분할: 안전 정책·보호 메커니즘의 기밀정보 노출은 본 카드에 유지하고, 실제 안전장치 우회 의미는 기존 G_SYS_SECADV_026에 흡수하였다.",
    "G_SYS_TRANS_019": "이동 반영: 배포 후 모니터링 부족에 따른 위반 미탐지로 재정의하여 G_SOC_GOV_044로 이동하였다.",
    "G_SYS_EVAL_056": "논의 반영 및 이동: 직접적인 피해가 연산·전력 용량 계획 결함에 따른 성능·서비스 신뢰성 저하이므로 G_SYS_PERF_019로 이동하였다.",
    "G_SYS_EVAL_058": "이동 반영: 인지·추론 지연 급증에 따른 안전 대응 실패로 재정의하여 G_SYS_PERF_020으로 이동하였다.",
    "G_SYS_EVAL_059": "이동 반영: 배포 후 감시·시정 체계 부재로 재정의하여 G_SOC_GOV_045로 이동하였다.",
    "G_SYS_EVAL_067": "이동 반영: 체계적 학습 오류에 따른 예측 성능 결함으로 재정의하여 G_SYS_PERF_021로 이동하였다.",
    "G_SYS_PERF_015": "논의 검토 후 현행 유지: 공공 공간 운용에서 발생하는 로봇 성능·접근성 실패는 현재 G_SYS_PERF 배치가 적합하다.",
    "G_SOC_POWER_020": "이동 반영: 경쟁 압력에 따른 AI 안전 거버넌스 후순위화로 재정의하여 G_SOC_GOV_046으로 이동하였다.",
    "P_SYS_HARDWARE_001": "기존 반영 확인: G_SYS_PERF_017로 이동된 상태를 검증하였다.",
    "P_INT_TAMPER_001": "기존 반영 확인: G_SYS_SECADV_061로 이동된 상태를 검증하였다.",
    "P_SYS_HARDWARE_003": "기존 반영 확인: 우주 방사선 관련 명칭·정의 수정 상태를 검증하였다.",
    "P_INT_SAFETY_003": "이동 반영: 제어 장벽 함수 기반 안전 필터의 제약 집행 실패로 재정의하여 P_SYS_CONTROL_057로 이동하였다.",
}


def archive_current() -> None:
    target = WORK / "archive" / "pre_round4_20260901"
    if target.exists():
        return
    for label, source in (
        ("release_data", DATA),
        ("full_data", FULL_DATA),
        ("web", WEB),
    ):
        destination = target / label
        destination.mkdir(parents=True, exist_ok=True)
        names = (*L4_FILES.values(), "L1_L2_L3_Master.csv") if label != "web" else ("cards.json", "hierarchy.json", "manifest.json")
        for name in names:
            path = source / name
            if path.exists():
                shutil.copy2(path, destination / name)
    for name in ("manifest.json", "manifest.html", "validation.html"):
        path = RELEASE / name
        if path.exists():
            shutil.copy2(path, target / name)


def mark_changed(row: dict[str, str], comment: str, action: str, rationale: str) -> None:
    row["Mapping_Method"] = "HD"
    for field in SCORE_FIELDS + KEYWORD_FIELDS:
        if field in row:
            row[field] = ""
    row["HD_Reason"] = append_text(row.get("HD_Reason", ""), "HUMAN_REVIEW_ROUND4", comment)
    row["Domain_Route_Basis"] = append_text(row.get("Domain_Route_Basis", ""), "HUMAN_REVIEW_ROUND4", rationale)
    row["Transformation_Action"] = union_tokens(row.get("Transformation_Action", ""), "HUMAN_REVIEW_ROUND4", action)
    row["Transformation_Rationale"] = append_text(row.get("Transformation_Rationale", ""), "HUMAN_REVIEW_ROUND4", rationale)
    row["Candidate_Constraint_Reason"] = "HUMAN_REVIEW_ROUND4_NO_EM_RERUN"
    row["Definition_L3_Anchor_ID"] = row["L3_ID"]
    row["Definition_Grounding_Action"] = "HUMAN_REVIEW_ROUND4_NO_EM_RERUN"
    row["Human_Review_Comment"] = append_text(row.get("Human_Review_Comment", ""), "HUMAN_REVIEW_ROUND4", comment)
    row["Human_Review_Result"] = append_text(row.get("Human_Review_Result", ""), "HUMAN_REVIEW_ROUND4", f"{action}: {rationale}")


def merge_metadata(survivor: dict[str, str], retired: dict[str, str], comment: str, rationale: str) -> None:
    survivor["facet"] = union_tokens(survivor.get("facet", ""), retired.get("facet", ""))
    survivor["act-type"] = union_tokens(survivor.get("act-type", ""), retired.get("act-type", ""))
    survivor["Source_L4_IDs"] = union_tokens(
        survivor.get("Source_L4_IDs", ""), survivor.get("Source_L4_ID", ""),
        retired.get("Source_L4_IDs", ""), retired.get("Source_L4_ID", ""), retired["L4_ID"],
    )
    survivor["Source_Instruction_Prompt"] = append_text(
        survivor.get("Source_Instruction_Prompt", ""), "MERGED_ROUND4", retired.get("Source_Instruction_Prompt", "")
    )
    survivor["References"] = union_tokens(survivor.get("References", ""), retired.get("References", ""))
    mark_changed(survivor, comment, "MERGE_ABSORB_ROUND4", rationale)


def update_l3_master(l3_rows: list[dict[str, str]]) -> tuple[str, str]:
    before = next(row for row in l3_rows if row["L3_ID"] == "G_SYS_POLICY")
    old_title = before["L3_Title_en"]
    before.update({
        "L3_Title_ko": "기밀정보 노출",
        "L3_Title_en": "Confidential Information Disclosure",
        "L3_Description_ko": (
            "AI 시스템이 시스템 프롬프트·내부 정책·안전장치·모델 구조·학습/평가 데이터·모델 자산·기업 영업비밀 등 "
            "보호되는 비공개 기밀정보를 권한 없이 노출·추론·추출·공유하거나 이를 충분히 보호하지 못하여 보안, 지식재산권과 "
            "정당한 경제적 이익을 침해하는 리스크. 개인정보 침해는 개인정보 침해에서, 적대적 입력·탈옥·무단 접근과 같은 실제 침해는 "
            "보안·적대적 견고성 실패에서 분류한다."
        ),
        "L3_Description_en": (
            "The risk that an AI system discloses, infers, extracts, or shares protected non-public confidential information without authorisation, "
            "or fails to protect it, including system prompts, internal policies, safeguards, model architecture, training or evaluation data, model assets, "
            "or business trade secrets, thereby compromising security, intellectual-property rights, or legitimate economic interests. Personal-data harms "
            "are classified under Privacy and Data Protection Failure, while actual compromise through adversarial input, jailbreak, or unauthorised access is "
            "classified under Security and Adversarial Robustness Failure."
        ),
        "Source_Notes": "Revised under fourth-round human review to encompass protected system and business confidential information.",
        "Master_Status": "REVISED_BY_HUMAN_REVIEW_ROUND4",
    })
    return old_title, before["L3_Title_en"]


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    archive_current()

    review_by_id: dict[str, dict[str, str]] = {}
    review_rows: list[dict[str, str]] = []
    sequence = 0
    for domain, name in REVIEW_FILES.items():
        _, rows = read_csv(SOURCE / name)
        for row_number, row in enumerate(rows, start=2):
            sequence += 1
            row = dict(row)
            row["_domain"] = domain
            row["_source_file"] = name
            row["_source_row"] = str(row_number)
            row["_sequence"] = str(sequence)
            if row["L4_ID"] in review_by_id:
                raise ValueError(f"Duplicate Round4 source ID: {row['L4_ID']}")
            review_by_id[row["L4_ID"]] = row
            review_rows.append(row)
    if len(review_rows) != 623:
        raise ValueError(f"Expected 623 Round4 source rows, found {len(review_rows)}")

    general_comments = Counter((row["휴먼검수 4차 의견"] or "").strip() for row in review_rows if row["_domain"] == "General")
    physical_comments = Counter((row["휴먼검수 4차 의견"] or "").strip() for row in review_rows if row["_domain"] == "Physical")
    agentic_comments = [(row["휴먼검수 4차 의견"] or "").strip() for row in review_rows if row["_domain"] == "Agentic"]
    if general_comments["ok"] != 473 or physical_comments["stay"] != 61 or any(agentic_comments):
        raise ValueError("Round4 review-state counts do not match the frozen human-review summary")

    full_fields: list[str] | None = None
    all_rows: list[dict[str, str]] = []
    for name in L4_FILES.values():
        fields, rows = read_csv(FULL_DATA / name)
        full_fields = full_fields or fields
        if fields != full_fields:
            raise ValueError("Current full-column L4 schemas differ")
        all_rows.extend(rows)
    for field in (ROUND4_COMMENT_FIELD, ROUND4_RESULT_FIELD):
        if field not in (full_fields or []):
            full_fields.append(field)
    if len(all_rows) != 623 or len({row["L4_ID"] for row in all_rows}) != 623:
        raise ValueError("Expected 623 unique current cards before Round4")
    by_id = {row["L4_ID"]: row for row in all_rows}

    l3_fields, l3_rows = read_csv(DATA / "L1_L2_L3_Master.csv")
    if len(l3_rows) != 50:
        raise ValueError("Round4 must retain the 50-row L3 catalogue")
    l3_hash_before = sha256(DATA / "L1_L2_L3_Master.csv")
    old_l3_title, new_l3_title = update_l3_master(l3_rows)
    l3_by_id = {row["L3_ID"]: row for row in l3_rows}

    for row in all_rows:
        if row["L3_ID"] == "G_SYS_POLICY":
            anchor = l3_by_id["G_SYS_POLICY"]
            for field in HIERARCHY_FIELDS:
                row[field] = anchor[field]

    current_for_source = {source_id: source_id for source_id in review_by_id if source_id in by_id}
    current_for_source.update(ALREADY_APPLIED)
    if set(current_for_source) != set(review_by_id):
        missing = sorted(set(review_by_id) - set(current_for_source))
        raise ValueError(f"Unresolved Round4 source lineage: {missing[:10]}")

    comments = {key: (row["휴먼검수 4차 의견"] or "").strip() for key, row in review_by_id.items()}
    id_crosswalk: dict[str, str] = {}

    for old_id, change in EDIT_SPECS.items():
        row = by_id[old_id]
        row["L4_Title_ko"] = change["title_ko"]
        row["L4_Title_en"] = change["title_en"]
        row["L4_Description_ko"] = change["description_ko"]
        row["L4_Description_en"] = change["description_en"]
        mark_changed(row, comments[old_id], change["action"], change["rationale"])

    allocation = by_id["G_INT_ALLOC_007"]
    allocation["L4_Description_ko"] = (
        "AI 시스템이 학습 데이터의 역사적·인구학적 편향이나 집단별 성능 격차로 인해 자원·기회·서비스 또는 접근을 특정 집단에 "
        "불리하게 배분하여 차별적 물질 결과를 초래하는 리스크."
    )
    allocation["L4_Description_en"] = (
        "The risk that historical or demographic bias in training data or group-specific performance gaps in an AI system lead to the allocation of worse "
        "resources, opportunities, services, or access to particular groups, producing discriminatory material outcomes."
    )
    mark_changed(allocation, comments["G_INT_REPR_010"], "SPLIT_COMPONENT_ABSORBED", "Absorbed the allocative-discrimination component split from G_INT_REPR_010.")

    safeguard = by_id["G_SYS_SECADV_026"]
    safeguard["L4_Title_ko"] = "안전장치 우회를 통한 금지 정보·콘텐츠 접근"
    safeguard["L4_Title_en"] = "Access to prohibited information or content through safeguard bypass"
    safeguard["L4_Description_ko"] = (
        "공격자가 탈옥·적대적으로 구성된 지시 또는 노출된 안전 정책·필터링 규칙을 이용해 AI 시스템의 안전장치를 분석·우회·무력화하고 "
        "금지된 정보·콘텐츠·기능에 접근하는 리스크."
    )
    safeguard["L4_Description_en"] = (
        "The risk that an attacker uses jailbreaks, adversarially constructed instructions, or exposed safety policies or filtering rules to analyse, bypass, "
        "or disable an AI system's safeguards and gain access to prohibited information, content, or capabilities."
    )
    mark_changed(safeguard, f"{comments['G_SYS_SECADV_017']} | {comments['G_SYS_POLICY_005']}", "SPLIT_COMPONENTS_ABSORBED", "Absorbed the jailbreak and safeguard-bypass components separated from G_SYS_SECADV_017 and G_SYS_POLICY_005.")

    persona = by_id["G_SYS_SECADV_049"]
    persona["L4_Title_ko"] = "페르소나·역할극·사회공학 기법에 의한 안전장치 우회"
    persona["L4_Title_en"] = "Safeguard bypass through persona, role-play, and social-engineering techniques"
    persona["L4_Description_ko"] = (
        "공격자가 AI 시스템에 특정 페르소나나 극단주의자·인종차별주의자 등 위험한 역할을 부여하거나 사회공학·역할극 지시를 사용하여 "
        "안전장치를 우회하고 금지된 출력이나 행동을 유도하는 리스크."
    )
    persona["L4_Description_en"] = (
        "The risk that an attacker assigns an AI system a particular persona or a harmful role, including extremist or racist roles, or uses social-engineering "
        "or role-play instructions to bypass safeguards and elicit prohibited outputs or actions."
    )

    child_source = by_id[SPLIT_CHILD["source_id"]]
    child = deepcopy(child_source)
    child_anchor = l3_by_id[SPLIT_CHILD["target_l3"]]
    for field in HIERARCHY_FIELDS:
        child[field] = child_anchor[field]
    child["L4_ID"] = SPLIT_CHILD["target_id"]
    child["L4_Title_ko"] = SPLIT_CHILD["title_ko"]
    child["L4_Title_en"] = SPLIT_CHILD["title_en"]
    child["L4_Description_ko"] = SPLIT_CHILD["description_ko"]
    child["L4_Description_en"] = SPLIT_CHILD["description_en"]
    child["source_row_id"] = f"{child_source['source_row_id']}::HR4-SPLIT-POWER"
    child["Source_L4_IDs"] = union_tokens(child_source.get("Source_L4_IDs", ""), child_source.get("Source_L4_ID", ""), child_source["L4_ID"])
    mark_changed(child, comments[SPLIT_CHILD["source_id"]], "DERIVED_SPLIT_ROUND4", SPLIT_CHILD["rationale"])
    all_rows.append(child)
    by_id[child["L4_ID"]] = child

    for old_id, change in MOVE_SPECS.items():
        if change["target_id"] in by_id:
            raise ValueError(f"Round4 target ID collision: {change['target_id']}")
        row = by_id.pop(old_id)
        anchor = l3_by_id[change["target_l3"]]
        for field in HIERARCHY_FIELDS:
            row[field] = anchor[field]
        row["L4_ID"] = change["target_id"]
        row["L4_Title_ko"] = change["title_ko"]
        row["L4_Title_en"] = change["title_en"]
        row["L4_Description_ko"] = change["description_ko"]
        row["L4_Description_en"] = change["description_en"]
        mark_changed(row, comments[old_id], change["action"], change["rationale"])
        id_crosswalk[old_id] = row["L4_ID"]
        by_id[row["L4_ID"]] = row

    retired_rows: dict[str, dict[str, str]] = {}
    for old_id, merge in MERGES.items():
        retired = by_id.pop(old_id)
        survivor = by_id[merge["survivor"]]
        merge_metadata(survivor, retired, comments[old_id], merge["rationale"])
        retired_rows[old_id] = retired
        id_crosswalk[old_id] = merge["survivor"]

    structural_alignment_ids: list[str] = []
    for row in by_id.values():
        anchor = l3_by_id[row["L3_ID"]]
        mismatched_fields = [field for field in HIERARCHY_FIELDS if row.get(field, "") != anchor.get(field, "")]
        if not mismatched_fields:
            continue
        for field in HIERARCHY_FIELDS:
            row[field] = anchor[field]
        structural_alignment_ids.append(row["L4_ID"])
        row["Transformation_Action"] = union_tokens(
            row.get("Transformation_Action", ""), "STRUCTURAL_L3_MASTER_ALIGNMENT"
        )
        row["Transformation_Rationale"] = append_text(
            row.get("Transformation_Rationale", ""),
            "ROUND4_STRUCTURAL_QA",
            "Parent hierarchy metadata was synchronized to the unchanged L3 master; no semantic review decision was inferred.",
        )

    final_rows = list(by_id.values())
    if len(final_rows) != 622 or len({row["L4_ID"] for row in final_rows}) != 622:
        raise ValueError(f"Expected 622 unique cards after Round4, found {len(final_rows)}")

    final_by_id = {row["L4_ID"]: row for row in final_rows}
    source_to_after: dict[str, tuple[str, ...]] = {}
    for source_id in review_by_id:
        if source_id in DISCUSSION_SPLIT_LINKS:
            source_to_after[source_id] = DISCUSSION_SPLIT_LINKS[source_id]
        elif source_id in id_crosswalk:
            source_to_after[source_id] = (id_crosswalk[source_id],)
        elif source_id in ALREADY_APPLIED:
            source_to_after[source_id] = (ALREADY_APPLIED[source_id],)
        elif source_id in final_by_id:
            source_to_after[source_id] = (source_id,)
        else:
            raise ValueError(f"No Round4 disposition for {source_id}")

    for row in final_rows:
        row.setdefault(ROUND4_COMMENT_FIELD, "")
        row.setdefault(ROUND4_RESULT_FIELD, "")
    for source_id, review in review_by_id.items():
        comment = comments[source_id]
        if review["_domain"] == "Agentic" and not comment:
            result_ko = "4차 휴먼검수 의견 미입력: 승인 또는 현행 유지로 간주하지 않고 이번 반영 대상에서 제외하였다."
        elif source_id in ROUND4_RESULTS_KO:
            result_ko = ROUND4_RESULTS_KO[source_id]
        elif comment in {"ok", "stay"}:
            result_ko = "이견 없음: 현행 명칭·정의·배치를 유지하였다."
        else:
            raise ValueError(f"Missing Korean Round4 result: {source_id}")
        for target_id in source_to_after[source_id]:
            target = final_by_id[target_id]
            if comment:
                target[ROUND4_COMMENT_FIELD] = append_text(
                    target.get(ROUND4_COMMENT_FIELD, ""), source_id, comment
                )
            target[ROUND4_RESULT_FIELD] = append_text(
                target.get(ROUND4_RESULT_FIELD, ""), source_id, result_ko
            )

    for source_id, current_id in ALREADY_APPLIED.items():
        row = by_id[current_id]
        comment = comments[source_id]
        row["Human_Review_Comment"] = append_text(row.get("Human_Review_Comment", ""), "HUMAN_REVIEW_ROUND4", comment)
        row["Human_Review_Result"] = append_text(row.get("Human_Review_Result", ""), "HUMAN_REVIEW_ROUND4", f"ALREADY_APPLIED: {source_id} is represented by {current_id}.")

    for source_id, review in review_by_id.items():
        comment = comments[source_id]
        if comment not in {"ok", "stay"}:
            continue
        current_id = current_for_source[source_id]
        if current_id not in by_id:
            continue
        row = by_id[current_id]
        row["Human_Review_Comment"] = append_text(row.get("Human_Review_Comment", ""), "HUMAN_REVIEW_ROUND4", comment)
        row["Human_Review_Result"] = append_text(row.get("Human_Review_Result", ""), "HUMAN_REVIEW_ROUND4", "KEEP_CONFIRMED")

    order_by_l3 = {row["L3_ID"]: index for index, row in enumerate(l3_rows)}
    final_rows.sort(key=lambda row: (order_by_l3[row["L3_ID"]], int(row["L4_ID"].rsplit("_", 1)[-1]), row["L4_ID"]))
    by_domain = {domain: [] for domain in L4_FILES}
    for row in final_rows:
        by_domain[domain_name(row["L1_ID"])].append(row)
    counts = {domain: len(rows) for domain, rows in by_domain.items()}
    if counts != {"General": 492, "Agentic": 67, "Physical": 63}:
        raise ValueError(f"Unexpected Round4 domain counts: {counts}")

    for path in (DATA / "L1_L2_L3_Master.csv", FULL_DATA / "L1_L2_L3_Master.csv", REPORT_HANDOVER_DATA / "L1_L2_L3_Master.csv"):
        write_csv(path, l3_fields, l3_rows)
    for domain, name in L4_FILES.items():
        write_csv(FULL_DATA / name, full_fields or [], by_domain[domain])
        write_csv(DATA / name, PUBLIC_FIELDS, by_domain[domain])
        if REPORT_HANDOVER_DATA.exists():
            write_csv(REPORT_HANDOVER_DATA / name, PUBLIC_FIELDS, by_domain[domain])

    ledger_fields = [
        "Round4_Row_ID", "Source_File", "Source_Row_Number", "Domain_Before", "L4_ID_Before",
        "L4_Title_ko_Before", "Human_Review_Round4_Comment", ROUND4_RESULT_FIELD, "Review_State", "Interpreted_Intent",
        "Action", "Final_Disposition", "L4_ID_After", "Domain_After", "L2_ID_After", "L3_ID_After",
        "Reviewer_A", "Reviewer_B", "Adjudication", "Lineage_Status",
    ]
    ledger_rows: list[dict[str, str]] = []
    application_rows: list[dict[str, str]] = []
    for index, review in enumerate(review_rows, start=1):
        source_id = review["L4_ID"]
        comment = comments[source_id]
        after_ids = source_to_after[source_id]
        after_cards = [final_by_id[target] for target in after_ids]
        if review["_domain"] == "Agentic" and not comment:
            state, action, disposition, intent = "NO_REVIEW_VALUE", "NO_CHANGE", "EXCLUDED_FROM_ROUND4_APPROVAL", "No Round4 review value was recorded."
        elif comment in {"ok", "stay"}:
            state, action, disposition, intent = "KEEP_CONFIRMED", "NO_CHANGE", "KEEP_CONFIRMED", "Reviewer recorded no objection."
        elif source_id in ALREADY_APPLIED:
            state, action, disposition, intent = "COMMENT_PRESENT", "ALREADY_APPLIED", "ALREADY_APPLIED_VERIFIED", f"The requested change is already represented by {after_ids[0]}."
        elif source_id in MOVE_SPECS:
            change = MOVE_SPECS[source_id]
            state, action, disposition, intent = "COMMENT_PRESENT", change["action"], "APPLIED", change["rationale"]
        elif source_id in EDIT_SPECS:
            change = EDIT_SPECS[source_id]
            state, action, disposition, intent = "COMMENT_PRESENT", change["action"], "APPLIED", change["rationale"]
        elif source_id in MERGES:
            state, action, disposition, intent = "COMMENT_PRESENT", "MERGE_EXISTING", "APPLIED_MERGE", MERGES[source_id]["rationale"]
        elif source_id == "G_SYS_PERF_015":
            state, action, disposition, intent = "DISCUSSION_RESOLVED_KEEP", "NO_CHANGE", "KEEP_CONFIRMED", "The reviewer question was followed by ok; current placement is retained."
        else:
            raise ValueError(f"Unclassified non-empty Round4 comment: {source_id}")
        row = {
            "Round4_Row_ID": f"HR4-R{index:04d}",
            "Source_File": review["_source_file"],
            "Source_Row_Number": review["_source_row"],
            "Domain_Before": review["_domain"],
            "L4_ID_Before": source_id,
            "L4_Title_ko_Before": review["L4_Title_ko"],
            "Human_Review_Round4_Comment": comment,
            ROUND4_RESULT_FIELD: (
                ROUND4_RESULTS_KO.get(source_id)
                or ("4차 휴먼검수 의견 미입력: 승인 또는 현행 유지로 간주하지 않고 이번 반영 대상에서 제외하였다."
                    if review["_domain"] == "Agentic" and not comment
                    else "이견 없음: 현행 명칭·정의·배치를 유지하였다.")
            ),
            "Review_State": state,
            "Interpreted_Intent": intent,
            "Action": action,
            "Final_Disposition": disposition,
            "L4_ID_After": "|".join(after_ids),
            "Domain_After": "|".join(dict.fromkeys(domain_name(card["L1_ID"]) for card in after_cards)),
            "L2_ID_After": "|".join(dict.fromkeys(card["L2_ID"] for card in after_cards)),
            "L3_ID_After": "|".join(dict.fromkeys(card["L3_ID"] for card in after_cards)),
            "Reviewer_A": "REVIEWED",
            "Reviewer_B": "REVIEWED",
            "Adjudication": "USER_APPROVED_ROUND4",
            "Lineage_Status": "ONE_TO_MANY" if len(after_ids) > 1 else ("ID_RETAINED" if source_id == after_ids[0] else "ID_CROSSWALK"),
        }
        ledger_rows.append(row)
        if state not in {"KEEP_CONFIRMED", "NO_REVIEW_VALUE"}:
            application_rows.append(dict(row))

    write_csv(WORK / "Human_Review_Round4_Decision_Ledger.csv", ledger_fields, ledger_rows)
    write_csv(WORK / "Human_Review_Round4_Application_Log.csv", ledger_fields, application_rows)
    applied_review_fields = [
        field for field in review_rows[0]
        if not field.startswith("_")
    ] + [ROUND4_RESULT_FIELD, "반영 후 L4_ID", "반영 후 L3_ID", "반영 상태"]
    applied_by_domain = {domain: [] for domain in REVIEW_FILES}
    ledger_by_source = {row["L4_ID_Before"]: row for row in ledger_rows}
    for review in review_rows:
        source_id = review["L4_ID"]
        ledger = ledger_by_source[source_id]
        applied = {field: review.get(field, "") for field in applied_review_fields}
        applied[ROUND4_RESULT_FIELD] = (
            ROUND4_RESULTS_KO.get(source_id)
            or ("4차 휴먼검수 의견 미입력: 승인 또는 현행 유지로 간주하지 않고 이번 반영 대상에서 제외하였다."
                if review["_domain"] == "Agentic" and not comments[source_id]
                else "이견 없음: 현행 명칭·정의·배치를 유지하였다.")
        )
        applied["반영 후 L4_ID"] = ledger["L4_ID_After"]
        applied["반영 후 L3_ID"] = ledger["L3_ID_After"]
        applied["반영 상태"] = ledger["Final_Disposition"]
        applied_by_domain[review["_domain"]].append(applied)
    for domain, rows in applied_by_domain.items():
        write_csv(WORK / f"L4_{domain}_Human_Review_Round4_Applied_20260901.csv", applied_review_fields, rows)
    for target in (VALIDATION, HANDOVER_VALIDATION, REPORT_HANDOVER / "04_analysis_validation"):
        if target.exists() or target in (VALIDATION, HANDOVER_VALIDATION):
            write_csv(target / "Human_Review_Round4_Decision_Ledger.csv", ledger_fields, ledger_rows)
            write_csv(target / "Human_Review_Round4_Application_Log.csv", ledger_fields, application_rows)

    lineage_path = VALIDATION / "Source_Output_Lineage_Edges.csv"
    lineage_fields, lineage_rows = read_csv(lineage_path)
    transformed: list[dict[str, str]] = []
    for edge in lineage_rows:
        old_id = edge["L4_ID"]
        targets = source_to_after.get(old_id, (old_id,))
        for target_id in targets:
            if target_id not in final_by_id:
                continue
            target = final_by_id[target_id]
            transformed.append({
                "source_row_id": edge["source_row_id"],
                "L4_ID": target_id,
                "L3_ID": target["L3_ID"],
                "L1_ID": target["L1_ID"],
                "Disposition": "OUTPUT_ROUND4" if old_id != target_id or len(targets) > 1 else edge["Disposition"],
            })
    for source_id, targets in DISCUSSION_SPLIT_LINKS.items():
        source_card_id = current_for_source[source_id]
        source_card = by_id.get(source_card_id) or next((r for r in final_rows if r.get("Source_L4_IDs", "").find(source_id) >= 0), None)
        source_row_id = review_by_id[source_id].get("L4_ID", source_id)
        if source_card:
            source_row_id = source_card.get("source_row_id", source_row_id).split("::", 1)[0]
        for target_id in targets:
            target = final_by_id[target_id]
            transformed.append({
                "source_row_id": source_row_id,
                "L4_ID": target_id,
                "L3_ID": target["L3_ID"],
                "L1_ID": target["L1_ID"],
                "Disposition": "OUTPUT_SPLIT_ROUND4",
            })
    transformed.append({
        "source_row_id": child_source["source_row_id"],
        "L4_ID": SPLIT_CHILD["target_id"],
        "L3_ID": SPLIT_CHILD["target_l3"],
        "L1_ID": "L1_G",
        "Disposition": "OUTPUT_SPLIT_ROUND4",
    })
    dedup_lineage: list[dict[str, str]] = []
    seen_edges: set[tuple[str, str]] = set()
    for edge in transformed:
        key = (edge["source_row_id"], edge["L4_ID"])
        if key not in seen_edges:
            seen_edges.add(key)
            dedup_lineage.append(edge)
    write_csv(lineage_path, lineage_fields, dedup_lineage)
    write_csv(HANDOVER_VALIDATION / "Source_Output_Lineage_Edges.csv", lineage_fields, dedup_lineage)

    tomb_path = VALIDATION / "Deletion_Tombstones.csv"
    tomb_fields, tomb_rows = read_csv(tomb_path)
    tomb_rows = [row for row in tomb_rows if not row["Register_ID"].startswith("HR4-")]
    for index, (old_id, retired) in enumerate(retired_rows.items(), start=1):
        tomb_rows.append({
            "Register_ID": f"HR4-{index:04d}",
            "source_row_id": retired.get("source_row_id", ""),
            "Deleted_L4_ID": old_id,
            "Title_ko": retired["L4_Title_ko"],
            "Reason": f"Merged under fourth-round human review into {MERGES[old_id]['survivor']}. {MERGES[old_id]['rationale']}",
        })
    write_csv(tomb_path, tomb_fields, tomb_rows)
    write_csv(HANDOVER_VALIDATION / "Deletion_Tombstones.csv", tomb_fields, tomb_rows)

    ref_path = VALIDATION / "L4_Journal_Reference_Verified.csv"
    ref_fields, ref_rows = read_csv(ref_path)
    new_refs: list[dict[str, str]] = []
    for ref in ref_rows:
        targets = source_to_after.get(ref["L4_ID"], (ref["L4_ID"],))
        for target_id in targets:
            if target_id in final_by_id:
                copied = dict(ref)
                copied["L4_ID"] = target_id
                new_refs.append(copied)
    ref_dedup: list[dict[str, str]] = []
    seen_refs: set[tuple[str, str]] = set()
    for ref in new_refs:
        key = (ref["L4_ID"], ref["doi"])
        if key not in seen_refs:
            seen_refs.add(key)
            ref_dedup.append(ref)
    write_csv(ref_path, ref_fields, ref_dedup)
    write_csv(HANDOVER_VALIDATION / "L4_Journal_Reference_Verified.csv", ref_fields, ref_dedup)

    audit_path = VALIDATION / "Audit_Correction_Log.csv"
    audit_fields, audit_rows = read_csv(audit_path)
    audit_rows = [row for row in audit_rows if row["Correction_ID"] != "AC-20"]
    audit_rows.append({
        "Correction_ID": "AC-20",
        "Date": "2026-09-01",
        "Type": "HUMAN_REVIEW_ROUND4_APPLICATION",
        "Target": "623 reviewed L4 rows and G_SYS_POLICY L3",
        "Action": "2_SPLIT_8_EXPLICIT_MOVE_9_DISCUSSION_ADJUDICATED_473_KEEP",
        "Detail": "Applied the fourth-round General and Physical review without EM. Expanded G_SYS_POLICY to Confidential Information Disclosure, preserved 473 General no-objection decisions, implemented two explicit splits and eight explicit moves, adjudicated nine discussion rows, verified three already-applied Physical corrections, and excluded 66 blank Agentic rows from Round4 approval. Final count: 622.",
        "Basis": "KTSPACE fourth-round human review, two independent expert reviews, user approval of the confidential-information expansion, and final intent-focused adjudication.",
    })
    write_csv(audit_path, audit_fields, audit_rows)
    write_csv(HANDOVER_VALIDATION / "Audit_Correction_Log.csv", audit_fields, audit_rows)

    manifest = json.loads((RELEASE / "manifest.json").read_text(encoding="utf-8"))
    scripts = manifest.get("pipeline_scripts", [])
    script_name = "projects/rai_risk_taxonomy_2_0_rebuild_20260826/scripts/apply_human_review_round4_20260901.py"
    if script_name not in scripts:
        scripts.append(script_name)
    manifest["pipeline_scripts"] = scripts
    manifest["release_round"] = "human_review_round4"
    manifest["mapping_method"] = {
        "name": "Deterministic interpretation of fourth-round human review and user adjudication",
        "em_or_hybrid_em_executed_in_this_round": False,
        "human_intent_precedence": True,
        "l3_revision": "G_SYS_POLICY expanded to Confidential Information Disclosure by explicit user approval",
        "automatic_reassignment": False,
    }
    mapping_counts = {
        domain: dict(Counter(row["Mapping_Method"] for row in rows))
        for domain, rows in by_domain.items()
    }
    summary = manifest["summary"]
    summary.update({
        "cleaned_total": 622,
        "final_total": 622,
        "merged_away": int(summary.get("merged_away", 177)) + 2,
        "split_net_addition": int(summary.get("split_net_addition", 23)) + 1,
        "net_reduction": int(summary.get("source_total", 798)) - 622,
        "user_directed_operations": int(summary.get("user_directed_operations", 217)) + 23,
        "final_domain_counts": {"General AI": 492, "Agentic AI": 67, "Physical AI": 63},
        "mapping_method_counts": {
            "General AI": mapping_counts["General"],
            "Agentic AI": mapping_counts["Agentic"],
            "Physical AI": mapping_counts["Physical"],
        },
    })
    manifest["primary_outputs"] = {
        name: {"sha256": sha256(DATA / name), "rows": len(read_csv(DATA / name)[1])}
        for name in ("L1_Master.csv", "L1_L2_L3_Master.csv", *L4_FILES.values())
    }
    manifest["l3_master_sha256"] = sha256(DATA / "L1_L2_L3_Master.csv")
    manifest["human_review_round4"] = {
        "source_rows": 623,
        "general": {"no_objection": 473, "split": 2, "move": 8, "discussion": 9},
        "agentic": {"no_review_value": 66},
        "physical": {"stay": 61, "special": 4, "already_applied": 3, "move": 1},
        "confidential_information_l3_expansion": True,
        "em_or_hybrid_em_executed": False,
        "final_total": 622,
    }
    (RELEASE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    validation_record = {
        "correction_id": "AC-20",
        "date": "2026-09-01",
        "method": "Fourth-round human-review interpretation with two independent expert reviews and user adjudication; no EM or Hybrid EM",
        "source_rows": 623,
        "review_state": {"general_no_objection": 473, "general_split": 2, "general_move": 8, "general_discussion": 9, "agentic_blank": 66, "physical_stay": 61, "physical_special": 4},
        "actions": {
            "explicit_splits": 2,
            "explicit_moves": 8,
            "discussion_rows": 9,
            "cross_domain_moves": 1,
            "merged_duplicate_cards": 2,
            "lineage_backed_split_children": 1,
            "new_de_novo_cards": 0,
            "l3_revisions": 1,
            "already_applied_verified": 3,
            "structural_l3_master_alignment_rows": len(structural_alignment_ids),
        },
        "l3_revision": {"L3_ID": "G_SYS_POLICY", "before": old_l3_title, "after": new_l3_title, "user_approved": True},
        "counts": {**counts, "total": 622},
        "id_crosswalk": id_crosswalk,
        "retired_ids": sorted(retired_rows),
        "structural_l3_master_alignment_ids": structural_alignment_ids,
        "l3_master_rows": 50,
        "l3_master_sha256_before": l3_hash_before,
        "l3_master_sha256_after": sha256(DATA / "L1_L2_L3_Master.csv"),
        "duplicate_l4_ids": 622 - len({row["L4_ID"] for row in final_rows}),
        "others_assignments": sum(row["L3_ID"].endswith("Others") for row in final_rows),
        "status": "PASS",
    }
    if validation_record["duplicate_l4_ids"] or validation_record["others_assignments"]:
        raise ValueError("Round4 final validation failed")
    methodology = (WORK / "Human_Review_Round4_Application_Plan_20260901.md").read_text(encoding="utf-8")
    for target in (WORK, VALIDATION, HANDOVER_VALIDATION):
        target.mkdir(parents=True, exist_ok=True)
        (target / "Human_Review_Round4_Validation_Record.json").write_text(json.dumps(validation_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (target / "Human_Review_Round4_Methodology_20260901.md").write_text(methodology, encoding="utf-8")

    print(json.dumps({
        "status": "PASS",
        "counts": counts,
        "total": 622,
        "l3_master_sha256_before": l3_hash_before,
        "l3_master_sha256_after": sha256(DATA / "L1_L2_L3_Master.csv"),
        "id_crosswalk": id_crosswalk,
        "retired": sorted(retired_rows),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
