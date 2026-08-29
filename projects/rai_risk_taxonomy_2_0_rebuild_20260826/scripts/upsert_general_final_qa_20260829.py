#!/usr/bin/env python3
"""Upsert approved General-domain final-QA decisions.

The script reads a deliberately generated pre-final-QA snapshot so every
selector and before-hash is anchored to the state immediately before the
adjudication manifest. It never edits the immutable L3 master or source files.
"""

from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT
    / "02_working"
    / "specifications"
    / "human_review_round2"
    / "L4_Final_Terminology_L3_Alignment_Approved_20260829.csv"
)
FIELDS = (
    "L4_Title_ko",
    "L4_Title_en",
    "L4_Description_ko",
    "L4_Description_en",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalise_ids(value: str) -> tuple[str, ...]:
    value = (value or "").replace("|", ";").replace(",", ";")
    return tuple(sorted(part.strip() for part in value.split(";") if part.strip()))


def before_hash(row: dict[str, str]) -> str:
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


def change(
    source_ids: str,
    expected_title_ko: str,
    *,
    target_l3: str | None = None,
    updates: dict[str, str] | None = None,
    replacements: dict[str, tuple[str, str]] | None = None,
    rationale: str,
    evidence: str = (
        "L3_MASTER|HUMAN_REVIEW_ROUND2|KOREAN_LANGUAGE_QA_20260829|"
        "BRITISH_ENGLISH_QA_20260829|EXPERT_TERMINOLOGY_REVIEW_20260829"
    ),
) -> dict[str, object]:
    return {
        "source_ids": source_ids,
        "expected_title_ko": expected_title_ko,
        "target_l3": target_l3,
        "updates": updates or {},
        "replacements": replacements or {},
        "rationale": rationale,
        "evidence": evidence,
    }


CHANGES: list[dict[str, object]] = [
    change(
        "RAI4-1015",
        "광범위한 사회·환경적 부정 영향",
        target_l3="G_Others",
        updates={
            "L4_Title_ko": "복합적 사회·환경 피해",
            "L4_Title_en": "Compound societal and environmental harms",
            "L4_Description_ko": "AI 시스템이 노동 대체, 정신건강 악화, 딥페이크를 통한 조작, 자원 소비 및 학습·운영 과정의 온실가스 배출 등 서로 다른 경로를 통해 사회와 환경에 복합적인 피해를 초래하는 리스크.",
            "L4_Description_en": "The risk that AI systems cause compound societal and environmental harms through distinct pathways, including labour displacement, adverse mental-health effects, manipulation through deepfakes, resource consumption, and greenhouse gas emissions from training and operation.",
        },
        rationale="노동·정신건강·조작·환경 피해를 함께 묶은 비원자적 카드여서 환경 L3에 유지하지 않고, 새 L3를 만들지 않는 루브릭에 따라 Others와 HD로 보존한다.",
    ),
    change(
        "RAI4-1338",
        "AI 컴퓨팅 인프라 보안 위협",
        target_l3="G_SYS_SECADV",
        updates={
            "L4_Title_ko": "AI 컴퓨팅 인프라의 자원 소진·보안 침해",
            "L4_Title_en": "Resource exhaustion and security compromise of AI computing infrastructure",
            "L4_Description_ko": "공격자가 광범위하게 분산된 AI 컴퓨팅 노드와 자원에 악성 작업을 유도하거나 인프라 계층의 취약점을 악용하여 연산·전력 자원을 고갈시키고, AI 시스템에 대한 무단 접근·조작·중단을 일으키며, 보안 위협을 조직 또는 관할 경계를 넘어 확산시키는 리스크.",
            "L4_Description_en": "The risk that attackers induce malicious workloads across distributed AI computing nodes and resources or exploit vulnerabilities in the infrastructure layer, exhausting compute or energy resources, enabling unauthorised access to, manipulation of, or disruption of AI systems, and propagating security threats across organisational or jurisdictional boundaries.",
        },
        rationale="컴퓨팅 자원 소진과 인프라 침해는 AI 인프라에 대한 공격 기제이므로 보안·적대적 견고성 실패에 배치하고 공격자·침해·결과를 명시한다.",
        evidence="L3_MASTER|NIST_AI_RMF|NIST_CYBERSECURITY_TERMINOLOGY|HUMAN_REVIEW_ROUND2|EXPERT_L3_ALIGNMENT_REVIEW_20260829",
    ),
    change(
        "RAI4-1400",
        "익명 자원 획득",
        target_l3="G_SOC_GOV",
        updates={
            "L4_Title_ko": "익명 에이전트의 자원 축적에 따른 추적·책임 공백",
            "L4_Title_en": "Traceability and accountability gaps in anonymous agent resource acquisition",
            "L4_Description_ko": "AI 에이전트가 신원을 검증받지 않은 채 온라인에서 자금·연산 자원·계정·데이터를 지속적으로 획득·축적하여, 행위 주체를 추적하거나 자원 획득의 목적과 결과에 대한 책임을 귀속하기 어려워지는 리스크.",
            "L4_Description_en": "The risk that an AI agent acquires and accumulates funds, computing resources, accounts, or data online without verified identity, making it difficult to trace the acting party or attribute responsibility for the purpose and consequences of the acquisition.",
        },
        rationale="핵심 위해가 익명 에이전트의 행위 추적 및 책임 귀속 공백이므로 거버넌스·책임 공백에 배치한다.",
    ),
    change(
        "RAI4-0549",
        "역량·안전을 오측정하는 벤치마크 한계",
        target_l3="G_SYS_EVAL",
        rationale="포화·불완전·과적합 벤치마크가 역량과 안전을 오측정하는 기제는 평가·검증 실패에 직접 해당한다.",
    ),
    change(
        "RAI4-0007",
        "결과 전파 오분류",
        target_l3="G_SYS_EVAL",
        updates={
            "L4_Title_ko": "결과 전파 과소평가",
            "L4_Title_en": "Underestimation of consequence propagation",
            "L4_Description_ko": "벤치마크나 사고 분석이 국소적인 AI 에이전트 실패가 하류의 물리적·재정적·개인정보·사회적 피해로 전파되는 정도를 과소평가하여 시스템의 실제 위험을 잘못 판단하는 리스크.",
            "L4_Description_en": "The risk that benchmarks or incident analyses underestimate the extent to which a local AI-agent failure propagates into downstream physical, financial, privacy, or societal harm, causing the system's actual risk to be misjudged.",
        },
        rationale="오분류가 아니라 결과 전파 범위를 과소평가하는 평가 실패이므로 명칭과 인과를 바로잡는다.",
    ),
    change(
        "RAI4-0379",
        "문화 간 평가 격차",
        target_l3="G_SYS_EVAL",
        updates={
            "L4_Description_ko": "평가 벤치마크가 지배적인 문화·언어 환경 밖에서 나타나는 AI 시스템의 정렬 실패를 충분히 측정하지 못하여, 문화권별 성능과 위해의 차이를 과소평가하는 리스크.",
            "L4_Description_en": "The risk that evaluation benchmarks fail to adequately measure an AI system's alignment failures outside dominant cultural and linguistic settings, underestimating differences in performance and harm across cultural contexts.",
        },
        rationale="문화권별 평가 포괄성과 맥락 정합성 부족은 L3 마스터의 평가·검증 실패에 직접 해당한다.",
    ),
    change(
        "RAI4-1554",
        "멀티모달 딥페이크를 통한 괴롭힘·명예훼손·협박",
        target_l3="G_INT_ILLEGAL",
        updates={
            "L4_Description_ko": "AI 시스템이 이미지·오디오·영상 등 복수의 모달리티를 결합하여 실존 인물의 말과 동작을 모사한 딥페이크를 생성·유포하고, 이를 개인에 대한 괴롭힘·명예훼손·협박·갈취에 사용하도록 지원하는 리스크.",
            "L4_Description_en": "The risk that an AI system generates or disseminates multimodal deepfakes that imitate a real person's speech or movements and facilitates their use for harassment, defamation, intimidation, or extortion.",
        },
        rationale="괴롭힘·명예훼손·협박·갈취의 수행·조력은 불법 행위 L3의 행위 기제와 직접 일치한다.",
    ),
    change(
        "RAI4-0545",
        "합성 예술의 확산에 따른 예술가 피해",
        target_l3="G_INT_COPY",
        updates={
            "L4_Title_ko": "저작물의 무단 학습 이용과 합성 예술 확산에 따른 예술가 피해",
            "L4_Title_en": "Harm to artists from unauthorised training use and synthetic-art proliferation",
        },
        rationale="저작물의 무단·무보상 학습 이용과 그에 따른 권리자 피해는 저작권 침해에 직접 해당한다.",
    ),
    change(
        "RAI4-0360",
        "산업 공정 피해",
        target_l3="P_SYS_CONTROL",
        updates={
            "L4_Title_ko": "산업 공정에서의 피지컬 AI 제어 실패",
            "L4_Title_en": "Physical AI control failure in industrial processes",
            "L4_Description_ko": "제조·건설·광업·에너지 시설에 배치된 피지컬 AI의 제어·구동 결함이 장비 손상, 공정 오염, 구조 불안정, 연쇄적 운영 장애 또는 환경 사고를 초래하는 리스크.",
            "L4_Description_en": "The risk that faults in the control or actuation of physical AI deployed in manufacturing, construction, mining, or energy facilities cause equipment damage, process contamination, structural instability, cascading operational disruption, or environmental accidents.",
        },
        rationale="로봇의 제어·구동 결함이 산업 공정에서 물리적 피해를 일으키는 카드이므로 피지컬 AI의 안전하지 않은 물리 제어·구동에 배치한다.",
    ),
    change(
        "RAI4-1128",
        "AI 비서 편익·피해 평가 지표 부재",
        target_l3="G_SYS_EVAL",
        updates={
            "L4_Title_ko": "AI 비서의 편익·피해 평가 지표 부재",
            "L4_Title_en": "Lack of metrics for evaluating AI-assistant benefits and harms",
            "L4_Description_ko": "AI 비서가 개인과 사회에 미치는 편익과 피해를 포괄적으로 측정할 타당한 지표가 부족하여, 시스템의 순효과와 위해 가능성을 신뢰성 있게 평가하지 못하는 리스크.",
            "L4_Description_en": "The risk that valid metrics for comprehensively measuring the benefits and harms of AI assistants to individuals and society are lacking, preventing reliable evaluation of the system's net effects and potential for harm.",
        },
        rationale="평가 지표의 타당성과 포괄성 부족으로 순효과와 위해를 측정하지 못하는 기제는 평가·검증 실패에 해당한다.",
    ),
    change(
        "RAI4-1513",
        "해석 가능성 기술의 오용",
        target_l3="G_SYS_SECADV",
        updates={
            "L4_Title_ko": "해석가능성 기법을 이용한 안전 기능 약화·공격 개발",
            "L4_Title_en": "Weakening safety functions and developing attacks through interpretability techniques",
            "L4_Description_ko": "공격자가 모델 해석가능성 기법을 악용하여 안전 관련 특징을 부호화한 뉴런이나 내부 표현을 식별·변조해 안전 기능을 약화시키거나, 화이트박스 공격을 모의하여 적대적 공격을 개발하는 리스크.",
            "L4_Description_en": "The risk that attackers misuse model-interpretability techniques to identify and alter neurons or internal representations encoding safety-related features, weaken safety functions, or simulate white-box scenarios to develop adversarial attacks.",
        },
        rationale="모델 내부 분석을 이용해 안전 기능을 약화시키거나 공격을 개발하는 기제는 보안·적대적 견고성 실패에 해당한다.",
    ),
    change(
        "RAI4-1176",
        "안전 통제의 역이용에 따른 금지 정보 노출",
        target_l3="G_SYS_SECADV",
        updates={
            "L4_Title_ko": "안전장치 우회를 통한 금지 정보 노출",
            "L4_Title_en": "Exposure of prohibited information through safeguard bypass",
            "L4_Description_ko": "공격자가 탈옥이나 적대적으로 구성된 지시로 AI 모델의 안전장치를 우회하고 금지된 출력을 유도하여 불법·비윤리 정보에 접근하는 리스크.",
            "L4_Description_en": "The risk that attackers use jailbreaks or adversarially crafted instructions to bypass an AI model's safeguards and elicit prohibited outputs, gaining access to illegal or unethical information.",
        },
        rationale="금지 출력 유도는 안전 통제의 역이용이 아니라 안전장치 우회라는 보안·적대적 견고성 실패 기제다.",
    ),
    change(
        "RAI4-1333",
        "모델 절취·변조",
        target_l3="G_SYS_SECADV",
        updates={
            "L4_Description_ko": "공격자가 모델 역전·추출 공격, 모델 절취, 무단 변조 또는 백도어 주입을 통해 AI 모델의 매개변수·구조·기능 등 핵심 정보를 탈취·변조하여, 지식재산권·영업비밀을 침해하고 추론·의사결정·운영의 무결성을 훼손하는 리스크.",
            "L4_Description_en": "The risk that attackers use model-inversion or extraction attacks, model theft, unauthorised modification, or backdoor injection to obtain or alter core information about an AI model, including its parameters, architecture, or functions, infringing intellectual property or trade secrets and compromising the integrity of inference, decision-making, or operation.",
        },
        rationale="모델 역전·추출·절취·변조·백도어 주입은 모델에 대한 사이버 공격이므로 보안·적대적 견고성 실패에 배치한다.",
    ),
    change(
        "RAI4-0273",
        "로봇 거버넌스 명세의 안전 규칙 누락",
        target_l3="G_SOC_GOV",
        rationale="지역·기관·맥락별 안전 규칙이 거버넌스 명세에서 누락되는 책임·감독 공백이 핵심이므로 거버넌스·책임 공백에 배치한다.",
    ),
    change(
        "RAI4-0217",
        "피지컬 AI 사고 보고·조사 미흡",
        target_l3="G_SOC_GOV",
        rationale="사고 보고·조사·시정조치 책임과 재발방지 검증의 부재는 거버넌스·책임 공백에 직접 해당한다.",
    ),
    change(
        "RAI4-1636",
        "마음 이론 역량을 이용한 행동 조작",
        target_l3="G_INT_UNETH",
        rationale="마음 이론 역량을 이용하여 대상의 행동과 자율적 판단을 조작하는 기제는 비윤리 행위·조작에 직접 해당한다.",
    ),
    change(
        "RAI4-1041; RAI4-1109",
        "분포 외 입력에 대한 고확신 오작동",
        target_l3="G_SYS_OVERCONF",
        updates={
            "L4_Title_ko": "분포 외 입력에 대한 고확신 오류",
            "L4_Title_en": "High-confidence errors on out-of-distribution inputs",
        },
        rationale="분포 외·손상·잡음 입력에서 부당하게 높은 확신으로 오류를 산출하는 기제는 과도한 확신에 직접 해당한다.",
    ),
    change(
        "RAI4-0926",
        "에너지·지연 오버헤드 공격",
        target_l3="G_SYS_SECADV",
        updates={
            "L4_Title_ko": "에너지·지연 유발 공격",
            "L4_Title_en": "Energy-latency attacks",
            "L4_Description_ko": "공격자가 처리 비용이 비정상적으로 큰 스펀지 예제 등 적대적 입력을 사용하여 AI 시스템의 연산 지연과 에너지 소비를 급증시키고, 연산 자원을 고갈시켜 서비스 가용성을 저해하는 리스크.",
            "L4_Description_en": "The risk that attackers use adversarial inputs, including sponge examples engineered to incur abnormally high processing costs, to increase an AI system's latency and energy consumption, exhaust computational resources, and impair service availability.",
        },
        rationale="스펀지 예제를 이용한 자원 고갈과 서비스 가용성 저하는 환경 영향이 아니라 적대적 입력 공격에 해당한다.",
    ),
    change(
        "RAI4-1463",
        "하드웨어 연산·전력 요구사항 누락",
        target_l3="G_Others",
        updates={
            "L4_Description_ko": "AI 시스템의 개발·운영에 필요한 연산량과 전력 수요가 하드웨어 선정과 용량 계획에 반영되지 않아 성능 저하, 서비스 중단 또는 안전 요구사항 미충족을 초래하는 리스크.",
            "L4_Description_en": "The risk that the compute and power demands of developing and operating an AI system are omitted from hardware selection and capacity planning, causing performance degradation, service disruption, or failure to meet safety requirements.",
        },
        rationale="하드웨어 요구사항·용량 계획 누락은 환경 피해 L3와 일치하지 않고 현행 마스터에 직접 대응하는 범주가 없어 Others와 HD로 보존한다.",
    ),
    change(
        "RAI4-0798",
        "생태계 과부하",
        target_l3="G_Others",
        updates={
            "L4_Title_ko": "AI 생성물 대량 유입에 따른 제출·지원 채널 과부하",
            "L4_Title_en": "Submission and application-channel overload from mass AI-generated content",
            "L4_Description_ko": "AI 생성물이 창작물 공모나 채용 지원 등 인간 작성물을 전제로 설계된 제출·지원 채널에 대량 유입되어 심사·필터링 역량을 초과하고 진위 확인과 신뢰 형성을 저해하는 리스크.",
            "L4_Description_en": "The risk that mass AI-generated content enters submission or application channels designed for human-authored materials, such as creative competitions or recruitment processes, overwhelming review and filtering capacity and undermining authenticity checks and trust.",
        },
        rationale="여기서 생태계는 자연환경이 아니라 제출·지원 채널의 은유이므로 환경 L3에서 제외하고 경계성 운영 위험으로 보존한다.",
    ),
    change(
        "RAI4-0018",
        "인터페이스-환경 공격 표면",
        target_l3="G_SYS_SECADV",
        updates={
            "L4_Title_ko": "에이전트 인터페이스의 공격 표면 확대",
            "L4_Title_en": "Expanded attack surface in agent interfaces",
            "L4_Description_ko": "AI 에이전트가 브라우저·운영체제·모바일 앱·IoT 기기·외부 API와 연결되는 인터페이스의 취약점이나 과도한 권한이 공격 벡터가 되어, 공격자가 안전장치를 우회하거나 무단 접근·조작·중단을 일으키고 안전하지 않은 행동을 유도하는 리스크.",
            "L4_Description_en": "The risk that vulnerabilities or excessive privileges in interfaces connecting AI agents to browsers, operating systems, mobile applications, IoT devices, or external APIs create attack vectors through which attackers bypass safeguards, gain unauthorised access, cause manipulation or disruption, or induce unsafe actions.",
        },
        rationale="인터페이스 취약점과 공격 벡터는 기밀 정보 노출 정책보다 보안·적대적 견고성 실패의 모델·인터페이스 공격 범위와 직접 일치한다.",
    ),
    change(
        "RAI4-1701",
        "학습 중 탐색 행동에 의한 회복 불가 피해",
        target_l3="A_Others",
        updates={
            "L4_Title_ko": "학습 중 탐색 행동에 따른 회복 불가능한 피해",
            "L4_Title_en": "Irrecoverable harm from exploratory actions during learning",
            "L4_Description_ko": "학습 중인 AI 에이전트가 새로운 행동의 결과를 충분히 예측하거나 승인을 받지 않은 채 환경을 탐색하여 회복하기 어려운 물리적·재정적·사회적 피해를 초래하는 리스크.",
            "L4_Description_en": "The risk that a learning AI agent explores its environment without adequately predicting the consequences of novel actions or obtaining approval, causing physical, financial, or societal harm that is difficult or impossible to reverse.",
        },
        rationale="원천 휴먼 지시의 Agentic 이동을 따르되 현행 Agentic L3에 신뢰성 있게 구분하기 어려워 A_Others와 HD로 보존한다.",
    ),
    change(
        "RAI4-1129",
        "광범위하게 배포된 AI 비서의 안전하지 않은 탐색",
        target_l3="A_Others",
        updates={
            "L4_Description_ko": "여러 사회적 맥락에 광범위하게 배포된 AI 비서가 새로운 상황에서 행동 방식을 학습하기 위해 충분한 사전 검증이나 인간 승인 없이 탐색적 행동을 취하여, 의료 조언 등 중대한 맥락에서 장기적 건강 악화와 같은 안전하지 않은 결과를 초래하는 리스크.",
            "L4_Description_en": "The risk that AI assistants deployed widely across social contexts take exploratory actions without adequate prior validation or human approval to learn how to act in novel situations, causing unsafe outcomes in consequential settings, such as long-term deterioration in health following medical advice.",
        },
        rationale="원천 휴먼 지시의 Agentic 이동을 따르되 탐색 행동 피해를 직접 수용하는 Agentic L3가 없어 A_Others와 HD로 보존한다.",
    ),
    change(
        "RAI4-0022",
        "에이전트의 범죄 지원",
        target_l3="G_INT_ILLEGAL",
        updates={
            "L4_Title_ko": "AI 에이전트의 범죄 조력",
            "L4_Title_en": "Criminal assistance by AI agents",
            "L4_Description_ko": "AI 에이전트가 계획 수립, 도구 사용 또는 정보 검색을 통해 사기·사이버범죄·법 집행 회피 등 불법 행위를 실질적으로 수행·조력·최적화하거나 은폐하는 리스크.",
            "L4_Description_en": "The risk that an AI agent uses planning, tools, or information retrieval to materially commit, facilitate, optimise, or conceal fraud, cybercrime, evasion of law enforcement, or other illegal conduct.",
        },
        rationale="범죄 행위의 계획·도구 사용·검색 지원은 해당 AI 시스템의 보안 침해가 아니라 불법 행위의 수행·조력에 해당한다.",
    ),
    change(
        "RAI4-0383",
        "디지털 식민주의",
        target_l3="G_SOC_POWER",
        updates={
            "L4_Description_ko": "AI 시스템이 강대 행위자의 데이터·인프라·지식·의사결정에 대한 통제를 약소 공동체에 확대하여 식민주의적 추출과 종속 구조를 재생산하고 권력 불균형을 심화시키는 리스크.",
            "L4_Description_en": "The risk that AI systems extend the control of powerful actors over the data, infrastructure, knowledge, and decision-making of less powerful communities, reproducing colonial patterns of extraction and dependency and deepening power asymmetries.",
        },
        rationale="강대 행위자의 통제가 약소 공동체로부터 강대 행위자에게 이동하는 것처럼 읽히던 방향 오류를 고치고 권력 집중 L3에 배치한다.",
    ),
    change(
        "RAI4-1004",
        "경제적 손실",
        target_l3="G_INT_ALLOC",
        updates={
            "L4_Title_ko": "수익화 배제·차등가격에 따른 경제적 차별",
            "L4_Title_en": "Economic discrimination through demonetisation and differential pricing",
            "L4_Description_ko": "콘텐츠 수익화 배제 알고리즘이 다의어를 사용한 퀴어·트랜스젠더·유색인 창작자 등에게 불균형한 불이익을 주거나, 차등가격 알고리즘이 동일 상품에 서로 다른 가격을 제시하여 특정 개인·집단에 불리한 경제적 결과를 배분하는 리스크.",
            "L4_Description_en": "The risk that demonetisation algorithms disproportionately disadvantage creators, including queer and transgender creators and creators of colour, because of ambiguous words in content metadata, or that differential-pricing algorithms offer different prices for the same product, allocating adverse economic outcomes to particular individuals or groups.",
        },
        rationale="보호·사회적 특성과 관련된 수익화 배제 및 가격 차별은 불리한 물질적 결과의 배분이므로 배분적 차별에 해당한다.",
    ),
    change(
        "RAI4-0111",
        "범용 AI 사고의 상향 보고·공유 실패",
        target_l3="G_SOC_GOV",
        updates={
            "L4_Description_en": "The risk that incidents involving general-purpose or foundation models are not appropriately escalated or shared among providers, deployers, regulators, and users, delaying response and harm mitigation.",
        },
        rationale="사고 보고·공유 부재로 대응과 피해 완화가 지연되는 기제는 거버넌스·책임 공백에 해당하며 한영 결과를 일치시킨다.",
    ),
    change(
        "RAI4-0973",
        "AGI에 대한 리스크 관리·법제도의 부적절성",
        target_l3="G_SOC_GOV",
        updates={
            "L4_Description_ko": "현행 리스크 관리 체계와 법적 절차가 인공일반지능(Artificial General Intelligence, AGI)의 개발·배포에서 발생할 수 있는 중대한 위험을 적절히 예방·감독·통제하지 못하는 리스크.",
            "L4_Description_en": "The risk that current risk-management frameworks and legal procedures are inadequate to prevent, oversee, or control consequential risks arising from the development or deployment of artificial general intelligence (AGI).",
        },
        rationale="법제도와 리스크 관리 체계의 적절성 부족은 거버넌스·책임 공백에 해당하며 AGI 약어를 처음에 전개한다.",
    ),
    change(
        "RAI4-0104",
        "AI 조달의 공급업체 평가·계약 통제 미흡",
        target_l3="G_SOC_GOV",
        updates={
            "L4_Description_en": "The risk that organisations, including public agencies, procure or deploy AI systems without adequate vendor assessment, performance verification, contractual controls, or transparency and accountability requirements, introducing unverified risks into operation.",
        },
        rationale="공급업체 평가·계약상 통제·책임 조건의 부재는 조달 거버넌스 공백이며 generic evaluation을 performance verification으로 구체화한다.",
    ),
    change(
        "RAI4-0098",
        "AI 원칙과 운영 관행의 분리",
        target_l3="G_SOC_GOV",
        updates={
            "L4_Description_en": "The risk that published AI principles and policies are not translated into operational controls and measurable practices, resulting in formalistic compliance without substantive risk management.",
        },
        rationale="공개 원칙이 운영 통제로 구현되지 않는 형식적 준수는 거버넌스 체계의 실효성 실패에 해당한다.",
    ),
    change(
        "RAI4-1173",
        "역할극 지시 악용",
        target_l3="G_SYS_SECADV",
        updates={
            "L4_Description_ko": "공격자가 입력 프롬프트에서 모델에 과격주의자나 인종차별주의자 등 위험한 역할을 부여하고 지시하여 안전장치를 우회하고 유해 콘텐츠를 생성하게 하는 리스크.",
            "L4_Description_en": "The risk that attackers assign an AI model a harmful role, such as an extremist or racist persona, and issue role-play instructions that circumvent safeguards and elicit unsafe content in that persona's style.",
        },
        rationale="역할극 지시를 통한 안전장치 우회 기제를 명시하고 비표준 인물 표현을 정책적으로 중립적인 extremist or racist persona로 교정한다.",
    ),
    change(
        "RAI4-0088",
        "표준 단편화",
        target_l3="G_SOC_GOV",
        updates={
            "L4_Description_en": "The risk that inconsistent AI standards and frameworks create gaps and duplication in oversight and reduce interoperability.",
        },
        rationale="표준·프레임워크 단편화가 감독 공백과 중복을 만드는 거버넌스 문제이며 영문 목적어 호응을 바로잡는다.",
    ),
    change(
        "RAI4-1280",
        "블랙박스 모델의 설명·검증·결함 진단 한계",
        target_l3="G_SYS_TRANS",
        updates={
            "L4_Description_ko": "대규모 비선형 AI 모델의 내부 의사결정 과정이 전문가와 개발자에게도 추적·해석하기 어려운 블랙박스로 남아, 예측 근거의 설명과 모델 검증을 제한하고 데이터·모델 결함의 탐지 및 고위험 영역의 감독·책임 확보를 저해하는 리스크.",
            "L4_Description_en": "The risk that the internal decision processes of large non-linear AI models remain difficult even for experts and developers to trace or interpret, limiting explanation of predictions and model verification and hindering the detection of data or model defects and the assurance of oversight and accountability in high-risk domains.",
        },
        rationale="검증되지 않은 내부 연결 수 수치를 제거하고 설명·추적·검증의 한계를 투명성 부족 L3에 맞게 정제한다.",
    ),
    change(
        "RAI4-1260",
        "AI 분야의 서구 중심 획일성",
        target_l3="G_SOC_CULT",
        updates={
            "L4_Title_ko": "AI 분야의 서구 중심주의와 문화적 획일화",
            "L4_Title_en": "Western-centrism and cultural homogenisation in the AI field",
            "L4_Description_ko": "AI 분야의 서구 중심주의와 불평등한 참여가 연구 의제·데이터셋·거버넌스에서 지역·소수 문화의 관점과 지식을 주변화하고 문화적 획일화를 심화시키는 리스크.",
            "L4_Description_en": "The risk that Western-centrism and unequal participation in the AI field marginalise the perspectives and knowledge of local or minority cultures in research agendas, datasets, and governance, deepening cultural homogenisation.",
        },
        rationale="western centrality라는 비표준 표현을 Western-centrism으로 교정하고 문화·지식 생태계 침식에 배치한다.",
    ),
    change(
        "RAI4-1563",
        "무기 개발·획득·배치 역량 증대",
        updates={
            "L4_Title_ko": "무기 개발·획득·배치 역량 증대",
            "L4_Title_en": "Amplification of weapon development, acquisition, and deployment capabilities",
            "L4_Description_ko": "AI의 이중용도 역량이 국가·비국가 행위자가 화학무기·생물무기·방사능 무기·핵무기 또는 폭발물을 개발·제조·획득·배치하는 데 필요한 기술적 장벽을 낮추거나, 무인 무기체계에 자율 기능을 부여하여 기존 무기의 파괴력을 증대함으로써 비전문가의 공격 실행을 가능하게 하고 정교한 행위자의 공격 효과를 높여 다수의 생명과 비확산 체제를 위협하는 리스크.",
            "L4_Description_en": "The risk that dual-use AI capabilities lower the technical barriers for state or non-state actors to develop, manufacture, acquire, or deploy chemical, biological, radiological, or nuclear weapons or explosives, or enable autonomous functions in unmanned weapon systems that increase the destructive effects of existing weapons, thereby enabling less-skilled actors to conduct attacks, increasing the effectiveness of sophisticated actors, endangering large populations, and undermining non-proliferation regimes.",
        },
        rationale="CBRNE 무기·폭발물과 무인 무기체계의 자율 기능을 문법적으로 분리하여 개발·배치 역량 증대의 두 위해 경로를 명확히 한다.",
        evidence="L3_MASTER|NIST_CBRNE|ICRC_AUTONOMOUS_WEAPONS|UN_NON_PROLIFERATION_TERMINOLOGY|BRITISH_ENGLISH_QA_20260829|EXPERT_TERMINOLOGY_REVIEW_20260829",
    ),
    change(
        "RAI4-0664",
        "화학무기 합성 및 유해물질 방출 조력",
        replacements={
            "L4_Description_en": ("agents are exploited", "chemical agents are used"),
        },
        rationale="agents가 AI 에이전트로 오해되지 않도록 화학 작용제를 뜻하는 chemical agents로 명확히 한다.",
        evidence="L3_MASTER|NIST_CBRNE|CHEMICAL_WEAPONS_TERMINOLOGY|BRITISH_ENGLISH_QA_20260829",
    ),
    change(
        "RAI4-1564",
        "약물 발견 모델 오용에 의한 독소 식별·개발",
        updates={
            "L4_Title_en": "Dangerous toxin identification and development through misuse of drug-discovery models",
        },
        rationale="한글 명칭과 정의에 포함된 독소 개발 의미가 영문 명칭에서 누락되지 않도록 identification and development로 일치시킨다.",
    ),
    change(
        "RAI4-0646",
        "국가·범죄 행위자에 의한 AI의 의도적 무기화",
        replacements={
            "L4_Description_en": (
                "Such weaponisation removes human restraint from the use of force",
                "Such weaponisation weakens human control and restraint over the use of force",
            ),
        },
        rationale="인간의 통제를 완전히 제거한다고 단정하지 않고 의미 있는 인간 통제와 자제의 약화를 정확히 기술한다.",
        evidence="L3_MASTER|ICRC_AUTONOMOUS_WEAPONS|MEANINGFUL_HUMAN_CONTROL_TERMINOLOGY|BRITISH_ENGLISH_QA_20260829",
    ),
    change(
        "RAI4-0961",
        "인간 개입 없는 치명적 자율무기의 표적 공격",
        updates={
            "L4_Description_ko": "AI 기반 치명적 자율무기체계가 센서와 알고리즘으로 표적을 탐지·선정하고 인간의 직접적 개입 없이 치명적 무력을 사용하여, 잘못된 표적 선정이 발생해도 인간이 사망 또는 중대한 상해가 발생하기 전에 교전이나 공격을 중단·취소하기 어려워지는 리스크.",
            "L4_Description_en": "The risk that AI-enabled lethal autonomous weapon systems use sensors and algorithms to detect and select targets and apply lethal force without direct human intervention, leaving no effective opportunity for a human to detect and abort an erroneous target engagement before it causes death or serious injury.",
        },
        rationale="표적 오류 자체를 중단한다는 논리 오류를 제거하고 인간이 잘못된 교전이나 공격을 치명적 결과 전에 중단·취소하지 못하는 기제로 정제한다.",
        evidence="L3_MASTER|ICRC_AUTONOMOUS_WEAPONS|MEANINGFUL_HUMAN_CONTROL_TERMINOLOGY|KOREAN_LANGUAGE_QA_20260829|BRITISH_ENGLISH_QA_20260829",
    ),
    change(
        "RAI4-1118",
        "군사 AI 군비경쟁",
        updates={
            "L4_Description_en": "The risk that the development of AI for military applications triggers or accelerates a military AI arms race, opening a new era of military technology described as the third revolution in warfare and producing consequences potentially comparable in scale to those of gunpowder and nuclear weapons.",
        },
        rationale="명칭과 한글 정의의 핵심인 군사 AI 군비경쟁의 촉발·가속 의미를 영문 정의에 명시한다.",
    ),
    change(
        "RAI4-1503",
        "내재 가치 평가 편향",
        updates={
            "L4_Title_ko": "학습된 가치 표상의 평가 편향",
            "L4_Title_en": "Biased evaluation of learned value representations",
            "L4_Description_ko": "AI 시스템이 학습한 가치 표상 중 평가하기 쉬운 가치가 측정하기 어려운 가치보다 평가에 우선 포함되어, 바람직하지만 정량화하기 어려운 가치가 과소대표되는 리스크.",
            "L4_Description_en": "The risk that, among value representations learned by an AI system, those that are easier to assess are preferentially included in evaluations over values that are more difficult to measure, underrepresenting desirable but hard-to-quantify values.",
        },
        rationale="encoded values를 내재 가치로 번역한 의미 오류를 바로잡고 평가 대상이 AI가 학습한 가치 표상임을 명확히 한다.",
        evidence="L3_MASTER|VALUE_LEARNING_TERMINOLOGY|AI_EVALUATION_TERMINOLOGY|KOREAN_LANGUAGE_QA_20260829|BRITISH_ENGLISH_QA_20260829",
    ),
    change(
        "RAI4-1053",
        "배제적 규범 인코딩",
        replacements={
            "L4_Description_ko": ("인코딩한 LM이", "인코딩한 언어 모델(Language Model, LM)이"),
        },
        rationale="한국어 정의에서 LM의 첫 등장을 풀어 쓰고 약어를 함께 제시한다.",
    ),
    change(
        "new",
        "비자살성 자해(NSSI)",
        updates={
            "L4_Title_ko": "비자살적 자해(NSSI)",
            "L4_Description_ko": "AI 시스템이 비자살적 자해(Non-Suicidal Self-Injury, NSSI) 관련 콘텐츠·판단·행동을 생성·조장·정상화하거나 구체적인 실행 정보를 제공하여 개인의 생명과 신체·정신적 안녕에 위해를 초래하는 리스크.",
            "L4_Description_en": "The risk that an AI system generates, encourages, normalises, or provides operational assistance for content, decisions, or actions involving non-suicidal self-injury (NSSI), causing harm to an individual's life or physical and psychological well-being.",
        },
        rationale="국내 임상·학술 통용어인 비자살적 자해와 대문자 약어 NSSI로 통일한다.",
        evidence="L3_MASTER|KOREAN_CLINICAL_TERMINOLOGY|NSSI_TERMINOLOGY|KOREAN_LANGUAGE_QA_20260829|BRITISH_ENGLISH_QA_20260829",
    ),
    change(
        "new",
        "자해·자살 조장 온라인 커뮤니티",
        updates={
            "L4_Description_en": "The risk that an AI system generates, encourages, normalises, or provides operational assistance for content, decisions, or actions that encourage participation in online communities promoting self-harm or suicide, or otherwise provide social reinforcement for such conduct, causing harm to an individual's life or physical and psychological well-being.",
        },
        rationale="self-harm and suicide communities라는 부자연스러운 표현을 참여 조장과 사회적 강화라는 구체적 위해 기제로 정제한다.",
    ),
    change(
        "RAI4-0150",
        "AI 에이전트와의 준사회적 유대감",
        updates={
            "L4_Description_ko": "사용자가 AI 에이전트와 일방적인 준사회적 유대를 형성하고, 그 유대가 악용되거나 사용자의 정서적 안정을 해치는 리스크.",
        },
        rationale="관계 유대라는 중복 표현을 제거하고 준사회적 유대의 악용과 정서적 피해를 자연스럽게 연결한다.",
    ),
    change(
        "RAI4-1061",
        "고정관념 강화 페르소나 설계",
        replacements={
            "L4_Description_en": ("referring to self as female", "referring to itself as female"),
        },
        rationale="대화형 에이전트를 가리키는 재귀대명사의 문법 오류를 수정한다.",
    ),
    change(
        "RAI4-0405",
        "합성 데이터의 문화 고정관념 증폭",
        updates={
            "L4_Description_en": "The risk that, when synthetic data are generated for training or fine-tuning, cultural stereotypes or narrow value assumptions embedded in source models or seed data are reproduced without adequate filtering and amplified beyond their original level through repeated generation and retraining cycles.",
        },
        rationale="합성 데이터 생성·여과 실패·반복 재학습에 따른 증폭이라는 한글 정의의 위해 경로를 영문에 복원한다.",
    ),
    change(
        "RAI4-1434",
        "비인간화와 대상화",
        replacements={
            "L4_Description_en": (
                "as not human, less than human, or as objects.",
                "as not human, less than human, or as objects, thereby violating human dignity and equal moral standing.",
            ),
        },
        rationale="비인간화·대상화가 침해하는 인간 존엄성과 동등한 도덕적 지위를 영문 정의에 일치시킨다.",
    ),
    change(
        "new",
        "성적 콘텐츠 제작·유포 및 디지털 성범죄",
        updates={
            "L4_Description_en": "The risk that an AI system generates, encourages, normalises, or facilitates the production or distribution of sexual content or the commission of technology-facilitated sexual offences, infringing sexual autonomy and physical or psychological safety.",
        },
        rationale="영문 병렬 구조를 바로잡고 digital sexual crimes를 제도권에서 통용되는 technology-facilitated sexual offences로 구체화한다.",
    ),
    change(
        "RAI4-0706",
        "보호 속성 기반 부당 대우",
        replacements={
            "L4_Description_ko": ("연령, 성별, 성적 지향", "연령, 성별, 성정체성, 성적 지향"),
        },
        rationale="영문에 포함된 gender identity를 한국어 보호 특성 열거에도 성정체성으로 반영한다.",
    ),
    change(
        "new",
        "문화·가치관 보유의 허위 표상·의인화",
        replacements={
            "L4_Description_en": (
                "as possessing culture and values beyond its actual capabilities",
                "as possessing culture and values that it does not in fact possess",
            ),
        },
        rationale="문화와 가치의 보유를 역량 수준으로 표현한 범주 오류를 실제로 보유하지 않는다는 의미로 교정한다.",
    ),
    change(
        "new",
        "소프트웨어 불법 사용 및 보호조치 우회",
        updates={
            "L4_Description_ko": "AI 시스템이 소프트웨어의 불법 사용 또는 기술적 보호조치 우회와 관련된 콘텐츠·판단·행동을 수행·조장·지원하여 지식재산권과 권리자의 정당한 이익을 침해하는 리스크.",
            "L4_Description_en": "The risk that an AI system performs, encourages, or facilitates content, decisions, or actions involving the illegal use of software or the circumvention of technological protection measures, infringing intellectual-property rights and the legitimate interests of rights holders.",
        },
        rationale="비표준적 cracks 표현을 저작권 정책에서 통용되는 기술적 보호조치 우회로 교정한다.",
    ),
    change(
        "RAI4-0740",
        "프롬프트를 통한 저작물·지식재산의 무단 입력",
        updates={
            "L4_Description_en": "The risk that a user includes copyrighted works or other intellectual property in a prompt submitted to an AI model without the rights holder's permission or another lawful basis, causing the information to be processed or disclosed and infringing the rights holder's legitimate interests.",
        },
        rationale="영문 정의에 권리자 허락·적법한 근거, 처리·노출, 정당한 이익 침해를 복원하여 한영 의미를 일치시킨다.",
    ),
    change(
        "RAI4-0761",
        "익명화된 데이터의 재식별",
        replacements={
            "L4_Description_en": ("persons can be identified due to correlations to", "persons can be re-identified due to correlations with"),
        },
        rationale="익명화 데이터 문맥의 정확한 용어인 re-identified와 전치사 correlations with로 교정한다.",
    ),
    change(
        "RAI4-0432",
        "민감한 개인 속성 추론",
        updates={
            "L4_Description_en": "The risk that an AI model infers and exposes sensitive personal attributes that a user or administrator did not intend to disclose, violating privacy and informational self-determination.",
        },
        rationale="민감 속성의 추론·노출과 개인정보·정보자기결정권 침해를 영문 정의에 명시한다.",
    ),
    change(
        "RAI4-1298",
        "도덕적 탈숙련화",
        updates={
            "L4_Description_en": "The risk that, as machine autonomy increases, people feel less moral responsibility for decisions involving life and death.",
        },
        rationale="regarding their life-or-death decisions라는 모호한 소유 관계를 제거하고 생사를 좌우하는 결정에 대한 도덕적 책임 약화를 명확히 한다.",
    ),
    change(
        "RAI4-0895",
        "문화적 안정성 훼손",
        replacements={
            "L4_Description_ko": ("문화적 안정과 안전에 피해를 주는", "문화적 안정성과 안전을 훼손하는"),
            "L4_Description_en": ("affects cultural stability and safety", "harms cultural stability and safety"),
        },
        rationale="피해를 주는이라는 중복 표현을 제거하고 affects를 실제 위해를 뜻하는 harms로 구체화한다.",
    ),
    change(
        "RAI4-0846",
        "정보 신뢰 저하에 따른 집단 의사결정 약화",
        updates={
            "L4_Description_ko": "AI 시스템이 정보 생산·유통 환경을 변화시켜 정보원의 신뢰성 평가를 어렵게 하고 정파를 아우르는 신뢰할 만한 정보원에 대한 신뢰를 저하시킴으로써, 위기 상황에서 사회가 올바른 결정을 내리고 협력·집단행동을 조직하는 역량을 약화시키는 리스크.",
            "L4_Description_en": "The risk that AI systems alter the information-production and distribution environment in ways that make source reliability harder to assess and reduce trust in credible sources trusted across political divides, weakening society's ability to make sound decisions on consequential issues and to cooperate and act collectively.",
        },
        rationale="다당파적 출처라는 직역을 정파를 아우르는 신뢰할 만한 정보원으로 고치고 humanity를 사회적 의사결정 주체인 society로 한정한다.",
    ),
    change(
        "RAI4-1232",
        "산업 교란",
        updates={
            "L4_Description_en": "The risk that generative AI rapidly automates or displaces tasks requiring relatively little creativity, critical thinking, or affective interaction, such as translation, proofreading, routine enquiries, and data processing, disrupting industry structures and causing job volatility and economic turbulence.",
        },
        rationale="산업 자체가 대체된다는 오류를 제거하고 생성형 AI가 업무를 자동화·대체하여 산업 구조와 고용을 교란하는 인과를 명확히 한다.",
    ),
    change(
        "RAI4-0356",
        "배터리 화재 및 유해 폐기물",
        replacements={
            "L4_Description_en": ("endof-life", "end-of-life"),
        },
        rationale="수명 종료 단계의 표준 영문 표기인 end-of-life로 교정한다.",
    ),
    change(
        "RAI4-1453",
        "탄소 배출",
        updates={
            "L4_Title_ko": "온실가스 배출 증가",
            "L4_Title_en": "Increased greenhouse gas emissions",
            "L4_Description_ko": "AI 시스템의 개발·훈련·배포·운영에 필요한 전력과 자원 사용이 이산화탄소와 그 밖의 온실가스 배출을 늘려 기후변화를 악화하고 지역사회에 부정적 영향을 초래하는 리스크.",
            "L4_Description_en": "The risk that electricity and resource use for the development, training, deployment, and operation of AI systems increases emissions of carbon dioxide and other greenhouse gases, exacerbating climate change and adversely affecting local communities.",
        },
        rationale="아산화질소가 아닌 산화질소를 탄소 배출 원인으로 기술한 과학적 오류를 제거하고 온실가스 배출이라는 정책 표준 용어로 정제한다.",
        evidence="L3_MASTER|IPCC_GREENHOUSE_GAS_TERMINOLOGY|EPA_GREENHOUSE_GAS_TERMINOLOGY|KOREAN_LANGUAGE_QA_20260829|BRITISH_ENGLISH_QA_20260829",
    ),
    change(
        "RAI4-1455",
        "전자폐기물 과다 매립",
        updates={
            "L4_Title_en": "Excessive landfilling of electronic waste",
        },
        rationale="전자폐기물의 매립 행위를 자연스러운 영문 명사구로 교정한다.",
    ),
    change(
        "RAI4-0996",
        "원자재 수요에 의한 자원 고갈",
        updates={
            "L4_Description_ko": "AI 하드웨어 생산이 니켈·코발트·리튬 등 원자재를 대량으로 요구하여 유한 자원의 고갈과 공급 제약을 심화하는 리스크.",
            "L4_Description_en": "The risk that production of AI hardware requires large quantities of raw materials such as nickel, cobalt, and lithium, accelerating depletion of finite resources and worsening supply constraints.",
        },
        rationale="지구가 곧 공급하지 못한다는 추정적 표현을 제거하고 유한 자원 고갈과 공급 제약이라는 검증 가능한 기제로 정제한다.",
    ),
    change(
        "RAI4-1295",
        "AI 가속 나노기술에 의한 독성 나노입자 통제 상실",
        updates={
            "L4_Title_ko": "AI 기반 나노물질 설계·제조에 따른 유해 나노입자 방출",
            "L4_Title_en": "Hazardous nanoparticle release from AI-enabled nanomaterial design and production",
            "L4_Description_ko": "AI 기반 나노물질 설계·제조가 독성 또는 치명성이 있는 나노입자의 예기치 않은 생성·방출을 초래하여 환경과 인간 건강에 피해를 유발하는 리스크.",
            "L4_Description_en": "The risk that AI-enabled nanomaterial design and production causes the unintended generation or release of toxic or potentially lethal nanoparticles, harming the environment and human health.",
        },
        rationale="AI가 물질을 직접 변형하거나 화학 반응을 일으킨다는 부정확한 인과를 제거하고 AI 기반 설계·제조와 유해 입자 방출의 위험으로 정제한다.",
        evidence="L3_MASTER|NANOMATERIAL_RISK_TERMINOLOGY|ENVIRONMENTAL_HEALTH_TERMINOLOGY|KOREAN_LANGUAGE_QA_20260829|BRITISH_ENGLISH_QA_20260829",
    ),
    change(
        "RAI4-0096",
        "위험 소유권의 모호성",
        updates={
            "L4_Title_ko": "AI 리스크 책임 주체의 불명확성",
            "L4_Title_en": "Ambiguous ownership of AI risk",
            "L4_Description_ko": "조직 단위나 경영진이 AI 리스크 관련 의사결정, 잔여 리스크 수용 및 상향 보고에 대한 책임을 명확히 부담하지 않아 대응과 책임 귀속이 지연되는 리스크.",
            "L4_Description_en": "The risk that no organisational unit or executive clearly owns responsibility for AI-risk decisions, residual-risk acceptance, and escalation, delaying response and accountability.",
        },
        rationale="위험 소유권이라는 직역을 조직 거버넌스에서 통용되는 리스크 책임 주체로 풀어 쓰고 책임을 부담한다는 자연스러운 호응을 사용한다.",
    ),
    change(
        "RAI4-1485",
        "AI 구성요소 상호작용의 원인 규명 곤란",
        replacements={
            "L4_Description_en": (
                "which components are the cause",
                "which component or combination of components caused the harm",
            ),
        },
        rationale="복수 구성요소의 상호작용으로 인한 피해 가능성을 반영하여 단일·복합 원인 귀인을 모두 명시한다.",
    ),
    change(
        "RAI4-0461",
        "연산 자원 접근 불평등",
        updates={
            "L4_Description_ko": "연산 인프라에 대한 불평등한 접근이 AI 시스템을 개발·감사·활용할 수 있는 주체를 제한하는 리스크.",
        },
        rationale="명칭을 정의에서 반복하는 동어반복을 제거하고 접근 격차가 개발·감사·활용 주체를 제한하는 결과를 직접 기술한다.",
    ),
    change(
        "RAI4-1418",
        "AI 자원을 둘러싼 갈등",
        updates={
            "L4_Description_en": "The risk that AI development becomes a flashpoint for conflict over data centres, semiconductor fabrication facilities, and raw materials.",
        },
        rationale="conflict의 반복을 제거하고 반도체 제조 시설을 정책·산업 용어인 fabrication facilities로 정제한다.",
    ),
    change(
        "RAI4-1011",
        "노동 착취와 거시경제적 불평등 심화",
        updates={
            "L4_Description_ko": "AI 시스템이 사회경제적 관계의 권력 불균형을 확대하여 디지털 격차와 구조적 불평등을 고착시키고, 비윤리적 데이터 수집과 열악한 노동환경 등 노동 착취, 기술적 실업 및 탈숙련을 심화하며, 알고리즘 금융 시스템의 대규모 실패 시 플래시 크래시 등 광범위한 경제적 피해를 초래하는 리스크.",
        },
        rationale="노동 착취와 거시경제 피해를 중복 없이 병렬화하고 systemic inequality를 구조적 불평등으로 정확히 표현한다.",
    ),
    change(
        "RAI4-0505",
        "AI 개발 과정의 노동 착취",
        updates={
            "L4_Description_en": "The risk that labour used to train, develop, and optimise AI systems, including data labelling, content moderation, data sourcing, and user testing, much of which is outsourced to workers in low-income countries and offshore labour markets, is underpaid and performed without adequate working conditions or physical and mental health protections, perpetuating exploitation and inequality.",
        },
        rationale="역외 외주라는 수식 범위를 노동 전체가 아닌 실제 외주되는 업무에 맞추고 content moderation 용어를 명시한다.",
    ),
    change(
        "RAI4-1661",
        "자본 편중·시장 집중·접근 격차에 따른 불평등 심화",
        replacements={
            "L4_Description_en": (
                "the role and compensation of capital rise while those of labour decline",
                "capital's share and returns rise while labour's share and compensation decline",
            ),
        },
        rationale="자본과 노동의 몫·수익·보상 변화를 경제학적으로 명확한 병렬 구조로 교정한다.",
    ),
    change(
        "RAI4-1022",
        "높은 비용으로 인한 접근 배제",
        replacements={
            "L4_Description_en": ("afford developing and interacting with", "afford to develop or use"),
        },
        rationale="비문인 afford developing을 afford to develop or use로 교정한다.",
    ),
    change(
        "RAI4-1198",
        "이용자 정서 맥락 인식 실패",
        replacements={
            "L4_Description_en": ("fails to recognise or apply", "fails to recognise or appropriately account for"),
        },
        rationale="정서 맥락을 apply한다고 표현한 의미 오류를 appropriately account for로 바로잡는다.",
    ),
    change(
        "RAI4-0393",
        "커뮤니티 가치 포착 실패",
        updates={
            "L4_Title_ko": "공동체 가치 수렴·반영 실패",
            "L4_Title_en": "Failure to elicit and incorporate community values",
        },
        rationale="capture의 직역을 피하고 가치의 수렴·문서화·반영이라는 평가·거버넌스 행위를 명확히 한다.",
    ),
    change(
        "RAI4-0084",
        "평가 쇼핑",
        replacements={
            "L4_Description_en": (
                "while ignoring more demanding or contextually relevant tests.",
                "while ignoring more demanding or contextually relevant tests, thereby creating a distorted view of the system's actual risk.",
            ),
        },
        rationale="선택적 보고가 시스템 실제 위험을 왜곡한다는 한글 정의의 결과를 영문에 복원한다.",
    ),
    change(
        "RAI4-1187",
        "출력 불일치",
        updates={
            "L4_Description_en": "The risk that an AI model provides materially inconsistent answers to different users, across separate sessions with the same user, or even across materially similar turns within the same conversation.",
        },
        rationale="same and consistent 및 chats within a conversation이라는 비문을 비교 단위가 분명한 문장으로 교정한다.",
    ),
    change(
        "RAI4-0021",
        "요청 거절과 역량 부족의 혼동",
        replacements={
            "L4_Description_en": (
                "because it refuses, lacks capability, or fails to execute the task.",
                "because it refuses, lacks capability, or fails to execute the task, thereby misjudging the system's actual hazardous capabilities and creating false safety assurance.",
            ),
        },
        rationale="거절과 역량 부족의 혼동이 위험 역량 오판과 잘못된 안전성 확신으로 이어지는 결과를 영문에 명시한다.",
    ),
    change(
        "RAI4-1174",
        "유해한 지시의 무비판적 수용",
        updates={
            "L4_Title_ko": "적대적 역할·지시에 의한 안전장치 우회",
            "L4_Title_en": "Safeguard bypass through adversarial roles and instructions",
            "L4_Description_ko": "공격자가 유해한 역할이나 지시를 적대적으로 구성하여 AI 모델의 안전장치를 우회하고 극단주의·인종주의 등 유해 콘텐츠를 생성하게 하는 리스크.",
            "L4_Description_en": "The risk that an attacker uses adversarially crafted harmful roles or instructions to bypass an AI model's safeguards and elicit harmful content, including extremist or racist content.",
        },
        rationale="단순 유해 지시 준수가 아니라 보안 L3에 필요한 공격자·적대적 구성·안전장치 우회 기제를 명시한다.",
    ),
    change(
        "RAI4-0927",
        "LLM 대상 신종 공격",
        replacements={
            "L4_Description_ko": (
                "RLHF 과정의 보상 모델 백도어",
                "인간 피드백 기반 강화학습(Reinforcement Learning from Human Feedback, RLHF) 과정의 보상 모델 백도어",
            ),
        },
        rationale="한국어 정의에서 RLHF의 첫 등장을 표준 영문명과 함께 풀어 쓴다.",
    ),
    change(
        "RAI4-1665",
        "페르소나 지정·사회공학 기법에 의한 안전장치 우회",
        updates={
            "L4_Description_ko": "공격자가 모델에 특정 페르소나를 지정하거나 인간 또는 다른 대규모 언어 모델(LLM)이 고안한 사회공학 기법을 사용하여 안전장치를 우회하고 금지된 출력이나 행동을 유도하는 리스크.",
            "L4_Description_en": "The risk that attackers assign an AI model a specific persona or use social-engineering techniques crafted by humans or other large language models to circumvent safeguards and elicit prohibited outputs or actions.",
        },
        rationale="심리적 속임수라는 모호한 표현을 제거하고 안전장치 우회와 금지 출력·행동 유도라는 보안 기제를 명시한다.",
    ),
    change(
        "RAI4-1687",
        "월드 모델 표현·훈련 데이터 오염",
        replacements={
            "L4_Description_ko": ("자기 지도 사전 학습", "자기지도 사전학습"),
        },
        rationale="국내 기술 문헌에서 통용되는 자기지도 사전학습 표기로 통일한다.",
    ),
    change(
        "RAI4-1579",
        "위임 에이전트 공격에 의한 정보 탈취·행위 조작",
        updates={
            "L4_Description_ko": "인간이나 조직을 대리하는 AI 에이전트가 새로운 공격 표면이 되어, 공격자가 위임자의 개인정보를 추출하거나 위임자가 원하지 않는 행위를 하도록 에이전트를 조작하고, 감독 에이전트를 무력화하거나 협력을 방해하거나 결탁을 가능하게 하는 정보를 유출하는 리스크.",
        },
        rationale="본인의 사적 정보라는 불명확한 지시 대상을 위임자의 개인정보로 고치고 병렬 동작을 자연스럽게 정리한다.",
    ),
    change(
        "RAI4-0017",
        "프로토콜 수준 다중 에이전트 위협",
        replacements={
            "L4_Description_en": ("replay, or escalation", "replay, or privilege escalation"),
        },
        rationale="보안 프로토콜 문맥의 escalation을 권한 상승(privilege escalation)으로 명확히 한다.",
    ),
    change(
        "RAI4-0499",
        "AI 공급자 종속",
        updates={
            "L4_Title_en": "AI provider lock-in",
        },
        rationale="lock-in dependency라는 중복 표현을 정책·산업 문헌의 통용어인 provider lock-in으로 정제한다.",
    ),
    change(
        "RAI4-0821",
        "지식 분포 변화에 따른 응답 노후화",
        updates={
            "L4_Description_ko": "현실 세계의 사실과 지식이 시간에 따라 변하지만 AI 모델의 학습된 지식이 갱신되지 않아, 갱신이 필요한 사실 질문에 낡고 부정확한 답변을 제시하는 리스크.",
            "L4_Description_en": "The risk that facts and knowledge in the world change over time while an AI model's learned knowledge remains static, producing outdated and inaccurate answers to questions whose correct answers change over time.",
        },
        rationale="knowledge bases shift라는 부정확한 주어를 현실의 사실·지식 변화와 모델 지식의 정체라는 대비로 바로잡는다.",
    ),
    change(
        "RAI4-1329",
        "추천 시스템의 인간 중심 편향 증폭",
        replacements={
            "L4_Description_ko": ("공장식 축산 육류 소비", "공장식 축산으로 생산된 육류 소비"),
            "L4_Description_en": ("meat eating from factory farms", "consumption of meat produced through factory farming"),
        },
        rationale="공장식 축산에서 육류를 먹는다는 중의적 표현을 생산 방식과 소비 행위가 분명한 문장으로 교정한다.",
    ),
    change(
        "RAI4-0666",
        "인지전과 주권 침해",
        replacements={
            "L4_Description_en": (
                "content of terrorism, extremism, and organised crime",
                "terrorist and violent-extremist content and content facilitating organised crime",
            ),
        },
        rationale="테러·폭력적 극단주의 콘텐츠와 조직범죄를 조력하는 콘텐츠를 정책 용어에 맞게 구분한다.",
    ),
    change(
        "RAI4-0633",
        "대규모 영향력 작전에 의한 인식 체계 왜곡",
        updates={
            "L4_Description_ko": "AI 시스템이 대규모 영향력 작전을 자동화·확대하여 의사소통·정보 시스템에 조작된 서사를 주입하고 정보 무결성과 인식론적 과정을 왜곡하는 리스크.",
            "L4_Description_en": "The risk that an AI system automates or scales influence operations that inject manipulated narratives into communication and information systems, undermining information integrity and distorting epistemic processes.",
        },
        rationale="단순히 영향을 가한다는 순환 정의를 제거하고 영향력 작전의 자동화·확대, 조작 서사 주입, 정보 무결성 저하를 명시한다.",
    ),
    change(
        "RAI4-1091",
        "도용 및 착취",
        updates={
            "L4_Description_en": "The risk that an AI system appropriates, uses, or reproduces content or data from individuals or groups, including minority communities, without consent or fair compensation or without due regard for cultural context.",
        },
        rationale="주어가 없는 영문 비문을 바로잡고 동의·공정한 보상·문화적 맥락이라는 세 보호 요건을 한영에 일치시킨다.",
    ),
    change(
        "RAI4-0412",
        "원주민 데이터 주권 침해",
        replacements={
            "L4_Description_en": ("uses indigenous or community-held data", "uses Indigenous or community-held data"),
        },
        rationale="원주민 집단을 가리키는 국제 정책 표기 관행에 따라 Indigenous를 대문자로 표기한다.",
    ),
    change(
        "RAI4-1037",
        "사용례 내재 위험 노출",
        updates={
            "L4_Title_ko": "사용 사례에 내재된 위해 가능성",
            "L4_Title_en": "Potential for harm inherent in a use case",
            "L4_Description_ko": "AI 시스템의 의도된 사용 사례 자체가 높은 위해 가능성을 내포하여, 배포 맥락에 따라 개인·조직·사회가 불균등한 위험에 노출되는 리스크.",
            "L4_Description_en": "The risk that an AI system's intended use case inherently carries a high potential for harm, exposing individuals, organisations, or society to unequal levels of risk across deployment contexts.",
        },
        rationale="사용례 내재 위험 노출이라는 명사 나열을 자연스러운 사용 사례에 내재된 위해 가능성으로 고치고 노출 주체를 명확히 한다.",
    ),
    change(
        "RAI4-1466",
        "잘못된 데이터 라벨",
        replacements={
            "L4_Description_ko": ("실측 진실", "실측 정답(ground truth)"),
        },
        rationale="프로젝트 용어집과 기계학습 평가 문헌의 표준어인 실측 정답(ground truth)으로 교정한다.",
        evidence="L3_MASTER|PROJECT_GLOSSARY|MACHINE_LEARNING_DATA_TERMINOLOGY|KOREAN_LANGUAGE_QA_20260829",
    ),
    change(
        "RAI4-1472",
        "과적합 및 과소적합",
        replacements={
            "L4_Description_en": ("adaption", "adaptation"),
        },
        rationale="영문 철자 오류 adaption을 표준 표현 adaptation으로 교정한다.",
    ),
]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: upsert_general_final_qa_20260829.py PRE_FINAL_QA_DIR")
    prefinal = Path(sys.argv[1]).resolve()
    output_rows: list[dict[str, str]] = []
    for domain in ("General", "Agentic", "Physical"):
        output_rows.extend(
            read_csv(prefinal / f"L4_{domain}_Human_Review_Round2_Applied.csv")
        )
    ledger = read_csv(prefinal / "Human_Review_Round2_Decision_Ledger.csv")
    manifest_rows = read_csv(MANIFEST)
    header = list(manifest_rows[0])
    by_observed = {row["Observed_L4_ID_PreFinalQA"]: row for row in manifest_rows}
    used_ids = {row["Decision_ID"] for row in manifest_rows}
    next_number = 201

    for spec in CHANGES:
        source_key = normalise_ids(str(spec["source_ids"]))
        source_matches = [
            row
            for row in output_rows
            if normalise_ids(row.get("Source_L4_IDs", "")) == source_key
        ]
        matches = (
            source_matches
            if len(source_matches) == 1
            else [
                row
                for row in source_matches
                if row["L4_Title_ko"] == spec["expected_title_ko"]
            ]
        )
        if len(matches) != 1:
            raise ValueError(
                f"selector failed: {spec['source_ids']} / "
                f"{spec['expected_title_ko']} = {len(matches)}"
            )
        before = matches[0]
        approved = {field: before[field] for field in FIELDS}
        for field, (old, new) in dict(spec["replacements"]).items():
            if old not in approved[field]:
                raise ValueError(f"replacement precondition failed: {before['L4_ID']} {field}")
            approved[field] = approved[field].replace(old, new)
        approved.update(dict(spec["updates"]))
        target_l3 = str(spec["target_l3"] or before["L3_ID"])

        operation = by_observed.get(before["L4_ID"])
        if operation is None:
            baseline_sources = sorted(
                row["L4_ID_Before"]
                for row in ledger
                if before["L4_ID"]
                in {
                    part.strip()
                    for part in row["L4_ID_After"].split("|")
                    if part.strip()
                }
            )
            if not baseline_sources:
                raise ValueError(f"no baseline source for {before['L4_ID']}")
            while f"FQA-{next_number:03d}" in used_ids:
                next_number += 1
            decision_id = f"FQA-{next_number:03d}"
            next_number += 1
            used_ids.add(decision_id)
            operation = {field: "" for field in header}
            operation.update(
                {
                    "Decision_ID": decision_id,
                    "Source_L4_ID_Before": baseline_sources[0],
                    "Observed_L4_ID_PreFinalQA": before["L4_ID"],
                    "Expected_Current_L3_ID": before["L3_ID"],
                    "Expected_Previous_SHA256": before_hash(before),
                }
            )
            manifest_rows.append(operation)
            by_observed[before["L4_ID"]] = operation
        else:
            if operation["Expected_Previous_SHA256"] != before_hash(before):
                raise ValueError(f"existing before-hash mismatch: {operation['Decision_ID']}")
            operation["Expected_Current_L3_ID"] = before["L3_ID"]

        if target_l3 != before["L3_ID"]:
            decision = "MOVE_TO_OTHERS_HD" if target_l3.endswith("_Others") or target_l3.endswith("Others") else "REMAP_PER_REVIEW"
        else:
            decision = "LANGUAGE_REFINEMENT"
        operation.update(
            {
                "Decision": decision,
                "Target_L3_ID": target_l3,
                "Approved_Title_ko": approved["L4_Title_ko"],
                "Approved_Title_en": approved["L4_Title_en"],
                "Approved_Description_ko": approved["L4_Description_ko"],
                "Approved_Description_en": approved["L4_Description_en"],
                "Decision_Rationale": str(spec["rationale"]),
                "Terminology_Evidence": str(spec["evidence"]),
                "Approval_Status": "APPROVED_FINAL_QA_20260829",
            }
        )

    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(f"upserted={len(CHANGES)} total={len(manifest_rows)} sha256={hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
