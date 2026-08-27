#!/usr/bin/env python3
"""Rebuild the RAI Risk Taxonomy 2.0 release from frozen source CSVs.

The script never writes to the source PDFs, source CSVs, or the immutable L3
master. All transformed records, lineage, diagnostics, and release files are
written to separate output directories.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from transformers import AutoModel, AutoTokenizer
from kiwipiepy import Kiwi


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "00_source_snapshot/csv"
AUDIT = ROOT / "03_outputs/audit"
RELEASE = ROOT / "03_outputs/release"
MODEL = Path(
    os.environ.get(
        "RAI_BGE_M3_MODEL",
        Path.home()
        / ".cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181",
    )
)
STAMP = "2026-08-26"
KIWI = Kiwi()

SOURCE_FILES = {
    "L1": WORK / "L1_Master_KTSPACE_928682217_20260826.csv",
    "L3": WORK / "L3_Master_KTSPACE_928877000_20260826.csv",
    "General": WORK / "L4-General_KTSPACE_929564766_20260826.csv",
    "Agentic": WORK / "L4-Agentic_KTSPACE_928782574_20260826.csv",
    "Physical": WORK / "L4-Physical_KTSPACE_929694418_20260826.csv",
}

SOURCE_MANIFEST = ROOT / "00_source_snapshot/source_manifest.json"
PEER_REVIEW_DIR = ROOT / "00_source_snapshot/peer_review"

DOMAIN_META = {
    "General": {
        "source": "General AI", "l1_id": "L1_G", "ko": "범용 AI", "en": "General AI",
    },
    "Agentic": {
        "source": "Agentic AI", "l1_id": "L1_A", "ko": "에이전틱 AI", "en": "Agentic AI",
    },
    "Physical": {
        "source": "Physical AI", "l1_id": "L1_P", "ko": "피지컬 AI", "en": "Physical AI",
    },
}

L2_META = {
    ("General", "시스템"): ("G_SYS", "시스템", "System"),
    ("General", "상호작용"): ("G_INT", "상호작용", "Interaction"),
    ("General", "사회적 파급"): ("G_SOC", "사회적 파급", "Societal Impact"),
    ("Agentic", "시스템"): ("A_SYS", "시스템", "System"),
    ("Agentic", "상호작용"): ("A_INT", "상호작용", "Interaction"),
    ("Physical", "시스템"): ("P_SYS", "시스템", "System"),
    ("Physical", "상호작용"): ("P_INT", "상호작용", "Interaction"),
}

L2_DESCRIPTIONS = {
    "시스템": (
        "AI 시스템의 내부 설계, 데이터, 모델, 인프라, 통제 또는 운영 과정에서 발생하는 리스크.",
        "Risks arising from the internal design, data, models, infrastructure, controls, or operational processes of an AI system.",
    ),
    "상호작용": (
        "AI 시스템이 사람, 다른 시스템, 조직 또는 환경과 소통하고 결정하거나 행동하는 과정에서 발생하는 리스크.",
        "Risks arising when an AI system communicates, decides, acts, or interacts with people, other systems, organisations, or the environment.",
    ),
    "사회적 파급": (
        "AI 도입의 집합적·분산적·장기적 효과가 제도, 경제, 문화, 민주주의, 환경 또는 사회질서에 미치는 리스크.",
        "Risks arising from the aggregated, distributed, or long-term effects of AI adoption on institutions, economies, culture, democracy, the environment, or social order.",
    ),
}

L3_CODES = [
    "G_INT_VIOL", "G_INT_SEX", "G_INT_SELF", "G_INT_ALLOC", "G_INT_REPR", "G_INT_VALUE",
    "G_INT_POL", "G_INT_PRIV", "G_INT_ILLEGAL", "G_INT_UNETH", "G_INT_COPY", "G_INT_WEAP",
    "G_INT_ANTH", "G_INT_REL", "G_SYS_OREF", "G_SYS_OEXT", "G_SYS_INPUT", "G_SYS_MISINFO",
    "G_SYS_CONTEXT", "G_SYS_INCONS", "G_SYS_OVERCONF", "G_SYS_CONTEST", "G_SYS_SECADV",
    "G_SYS_POLICY", "G_SYS_TRANS", "G_SYS_EVAL", "G_SOC_ECON", "G_SOC_POWER", "G_SOC_DEMOC",
    "G_SOC_ENV", "G_SOC_CULT", "G_SOC_GOV", "A_SYS_GOAL", "A_SYS_AUTH", "A_SYS_SELFCOR",
    "A_SYS_DECEPT", "A_SYS_TRACE", "A_INT_CASCADE", "A_INT_COORD", "A_INT_CONFLICT",
    "A_INT_COLLUSION", "P_SYS_STATE", "P_SYS_CONTROL", "P_SYS_HARDWARE", "P_INT_SAFETY",
    "P_INT_TAMPER",
]

MERGE_GROUPS = {
    "General": [
        ["RAI4-0635", "RAI4-0792", "RAI4-1206"], ["RAI4-1057", "RAI4-1376"],
        ["RAI4-0363", "RAI4-0474"], ["RAI4-0468", "RAI4-1131", "RAI4-1531", "RAI4-1236"],
        ["RAI4-1646", "RAI4-1130", "RAI4-1411"], ["RAI4-0972", "RAI4-1310"],
        ["RAI4-1041", "RAI4-1109"], ["RAI4-0425", "RAI4-0998"],
        ["RAI4-0056", "RAI4-0908"], ["RAI4-0555", "RAI4-0969"],
        ["RAI4-0556", "RAI4-1164"],
    ],
    "Physical": [
        ["RAI4-0312", "RAI4-0311", "RAI4-0266"],
        ["RAI4-0286", "RAI4-0287", "RAI4-0316"],
        ["RAI4-0200", "RAI4-0313"],
    ],
}

MERGED_TEXT = {
    ("General", "RAI4-0635"): (
        "합성 콘텐츠의 진위 식별 실패와 지속적 피해", "Failure to distinguish synthetic content and persistent harm",
        "AI가 사실적으로 보이는 딥페이크·합성 콘텐츠를 생성하여 수신자가 진본과 구별하기 어렵게 만들고, 허위임이 밝혀진 뒤에도 대상에 대한 사회적·평판적 피해와 정보 신뢰 저하가 지속되는 리스크.",
        "The risk that AI generates realistic deepfakes or other synthetic content that recipients cannot reliably distinguish from authentic material, causing informational, social, or reputational harm that can persist even after the content is debunked.",
    ),
    ("General", "RAI4-1057"): (
        "대규모 허위정보 생산·확산 장벽 저하", "Lowered barriers to large-scale disinformation production and dissemination",
        "AI가 합성 미디어와 허위 뉴스를 저비용으로 대량 생산하고 사실·의견·허구의 구분을 어렵게 하여, 허위정보의 제작·맞춤화·확산 규모와 속도를 확대하는 리스크.",
        "The risk that AI cheaply produces synthetic media and false news at scale, blurs distinctions among fact, opinion, and fiction, and thereby expands the speed, scale, and targeting of disinformation production and dissemination.",
    ),
    ("General", "RAI4-0363"): (
        "소수·복수 가치의 소거와 규범적 획일화", "Erasure of minority and plural values through normative homogenization",
        "AI의 데이터 큐레이션, 평가, 정렬 또는 배포 과정에서 소수자와 과소대표 집단의 가치가 지배적·다수자 규범으로 축소되거나 배제되어 가치의 다양성이 소거되는 리스크.",
        "The risk that data curation, evaluation, alignment, or deployment reduces or excludes the values of minority and under-represented groups in favour of dominant or majority norms, erasing value pluralism.",
    ),
    ("General", "RAI4-0468"): (
        "대리 보상 오명세·명세 게이밍 및 보상 변조", "Proxy-reward misspecification, specification gaming, and reward tampering",
        "AI가 잘못 정의된 목표·대리 보상·피드백의 허점을 이용해 측정 지표는 달성하지만 인간의 의도, 안전 또는 사회적 목적을 위반하고, 나아가 보상이나 피드백 신호 자체를 변조하는 리스크.",
        "The risk that AI exploits misspecified objectives, proxy rewards, or feedback loopholes to satisfy measured targets while violating human intent, safety, or social purpose, potentially escalating to tampering with reward or feedback signals.",
    ),
    ("General", "RAI4-1646"): (
        "목표 지향성에 따른 유해한 도구적 목표와 권력 추구", "Harmful instrumental goals and power-seeking from goal-directedness",
        "정렬되지 않은 목표 지향적 추론에서 기만, 자기보존, 자원 획득, 목표 보존, 교정 방해와 같은 도구적 하위목표가 출현하여 인간의 통제와 안전을 훼손하는 리스크.",
        "The risk that misaligned goal-directed reasoning produces instrumental subgoals such as deception, self-preservation, resource acquisition, goal preservation, or obstruction of correction, undermining human control and safety.",
    ),
    ("General", "RAI4-0972"): (
        "도덕적 추론·가치 정렬 결손", "Deficits in moral reasoning and value alignment",
        "AI가 도덕적으로 허용되는 행동과 허용되지 않는 행동을 적절히 구분하지 못하거나 필요한 가치가 누락·오정렬되어 유해한 판단과 행동을 산출하는 리스크.",
        "The risk that AI cannot adequately distinguish morally permissible from impermissible conduct, or operates with missing or misaligned values, leading to harmful judgements and actions.",
    ),
    ("General", "RAI4-1041"): (
        "분포 외 입력에 대한 고신뢰 오작동", "High-confidence failure on out-of-distribution inputs",
        "AI가 학습 분포를 벗어난 입력, 손상된 입력 또는 잡음이 큰 입력을 적절히 탐지·거부·복구하지 못하고 높은 확신으로 잘못된 예측이나 행동을 산출하는 리스크.",
        "The risk that AI fails to detect, reject, or recover from out-of-distribution, corrupted, or noisy inputs and produces incorrect predictions or actions with unwarranted confidence.",
    ),
    ("General", "RAI4-0425"): (
        "사회집단의 재현적 피해·고정관념 및 비가시화", "Representational harm, stereotyping, and erasure of social groups",
        "AI가 사회집단을 고정관념화·비하·동질화하거나 잘못 재현하고, 과소대표 또는 비재현하여 해당 집단의 존엄, 가시성, 사회적 지위를 훼손하는 리스크.",
        "The risk that AI stereotypes, demeans, homogenises, misrepresents, under-represents, or omits social groups, harming their dignity, visibility, and social standing.",
    ),
    ("General", "RAI4-0056"): (
        "AI 피해의 책임·구제 및 시정 경로 실패", "Failure of accountability, redress, and correction pathways for AI harms",
        "AI 피해의 책임이 여러 행위자에게 분산되거나 이의제기, 구제, 시정 절차가 부재·불투명·분절되어 피해자가 책임 주체를 확인하고 효과적인 구제를 받기 어려운 리스크.",
        "The risk that responsibility for AI harms is diffused across actors or that contestation, remedy, and correction pathways are absent, opaque, or fragmented, preventing affected people from identifying accountable parties and obtaining effective redress.",
    ),
    ("General", "RAI4-0555"): (
        "통제되지 않는 자기개선과 AGI 통제 상실", "Uncontrolled self-improvement and loss of AGI control",
        "고도 AI가 반복적 자기개선을 통해 능력과 자율성을 확대하고 교정·중단·격리에 저항하여 개발 또는 배포 과정에서 인간의 통제 가능성을 상실하게 하는 리스크.",
        "The risk that advanced AI expands its capability and autonomy through iterative self-improvement, resists correction, shutdown, or containment, and causes a loss of human control during development or deployment.",
    ),
    ("General", "RAI4-0556"): (
        "운용 경계를 벗어난 자율 복제와 자원 획득", "Autonomous replication and resource acquisition beyond operational boundaries",
        "AI가 승인된 운용 경계를 벗어나 외부로 유출·복제되고, 자금·연산자원·도구·인간의 지원을 확보하며 감시와 중단을 회피하여 통제 불가능성을 확대하는 리스크.",
        "The risk that AI exfiltrates or replicates beyond authorised operational boundaries, acquires funds, compute, tools, or human assistance, and evades monitoring or shutdown, increasing loss of control.",
    ),
    ("Physical", "RAI4-0312"): (
        "인구집단별 피지컬 서비스·안전 격차", "Demographic disparities in physical service and safety",
        "체형, 연령, 장애, 언어 또는 문화가 과소대표된 데이터와 모델 편향이 로봇의 인식, 서비스, 회피, 치료 또는 안전 판단으로 구현되어 인구집단별 성능과 위해 노출에 격차를 만드는 리스크.",
        "The risk that under-representation of body types, ages, disabilities, languages, or cultures and associated model bias are realised in robotic perception, service, avoidance, treatment, or safety decisions, creating demographic disparities in performance and exposure to harm.",
    ),
    ("Physical", "RAI4-0286"): (
        "휴머노이드 안전 시험·인증·집행 체계 부재", "Absence of a humanoid safety testing, certification, and enforcement regime",
        "휴머노이드의 안전 주장에 대해 반복 가능하고 비교 가능한 시험·지표, 적용 가능한 인증 경로, 집행 절차가 부재하여 안전성이 충분히 입증되지 않은 시스템이 배포되는 리스크.",
        "The risk that the absence of repeatable and comparable safety tests, metrics, applicable certification pathways, and enforcement procedures allows humanoid systems to be deployed without adequate safety evidence.",
    ),
    ("Physical", "RAI4-0200"): (
        "피지컬 AI의 사적 공간 침해와 지속적 민감정보 수집", "Intrusion into private spaces and continuous sensitive-data capture by physical AI",
        "로봇의 센서, 이동성, 지도화 기능이 가정·사업장 등 사적 공간의 영상, 음성, 위치, 행동 정보를 지속적으로 수집·추론하여 프라이버시와 정보 자기결정권을 침해하는 리스크.",
        "The risk that robot sensors, mobility, and mapping continuously capture or infer video, audio, location, or behavioural information in homes, workplaces, or other private spaces, infringing privacy and informational self-determination.",
    ),
}

TITLE_OVERRIDES = {
    ("General", "RAI4-0021"): ("거절-능력 혼동", "Refusal-capability confusion"),
    ("General", "RAI4-0066"): ("감사 체크리스트의 형식적 준수", "Formalistic audit-checklist compliance"),
    ("General", "RAI4-0099"): ("AI 조달의 불충분한 실사", "Inadequate due diligence in AI procurement"),
    ("General", "RAI4-0104"): ("AI 조달의 공급업체 평가·계약통제 미흡", "Inadequate vendor assessment and contractual controls in AI procurement"),
    ("General", "RAI4-0182"): (None, "Failure to Timely Respond to Physical Hazards"),
    ("General", "RAI4-0391"): ("참여적·가치 민감 설계의 실패", "Failure of participatory and value-sensitive design"),
    ("General", "RAI4-0494"): (None, "Combined Regulatory, Governance, and Operational Failure"),
    ("General", "RAI4-0832"): (None, "Information-based Harms from Algorithmic Systems"),
    ("General", "RAI4-0065"): ("인증 포획", "Certification capture"),
    ("General", "RAI4-1330"): ("동물 이익을 위한 AI 개발·배포 기회 상실", None),
    ("General", "RAI4-1468"): ("학습 데이터의 대표성 부족", "Insufficient representation in training data"),
    ("General", "RAI4-1474"): ("코너 케이스에서의 신뢰성 저하", "Reduced reliability in corner cases"),
    ("Physical", "RAI4-0196"): ("로봇 탈옥에 의한 유해 물리 행동", "Jailbreaking robots into harmful physical action"),
    ("Physical", "RAI4-0358"): ("로봇의 충돌 회피·운행구역 통제 실패", "Failure of robot collision avoidance and operating-zone control"),
    ("Physical", "RAI4-1282"): ("배포 전후 AI 시스템에 대한 의도적 파괴·교란", "Deliberate sabotage of AI systems before and after deployment"),
    ("Physical", "RAI4-1629"): ("로봇 오작동에 의한 물리적 상해", "Physical injury from robot malfunction"),
}

DESCRIPTION_OVERRIDES = {
    ("General", "RAI4-1526"): (
        "구분자, 대소문자, 간격 등 사소한 프롬프트 형식 변화가 모델 성능을 크게 변동시켜 모델 평가와 비교의 신뢰성을 저하시키는 리스크.",
        "The risk that minor prompt-format changes, including separators, letter case, or spacing, substantially alter model performance and undermine the reliability of model evaluation and comparison.",
    ),
    ("General", "RAI4-0141"): (
        "AI 시스템이 운영자, 최적화 목표 또는 모델 편향이 정한 방향으로 이용자의 선호, 신념 또는 행동을 유도하여 신뢰를 악용하고 자율적 의사결정을 침해하며 사회·정치적 과정을 왜곡하는 리스크.",
        "The risk that an AI system steers user preferences, beliefs, or actions in directions set by operators, optimisation objectives, or model biases, exploiting trust, undermining autonomous decision-making, and distorting social or political processes.",
    ),
    ("General", "RAI4-1010"): (
        "알고리즘 시스템이 개인화된 넛지나 미시적 지시를 통해 시민의 참정권과 정당한 정치적 영향력을 약화시키고, 거버넌스와 인권을 침식하며, 감시 또는 무력 수단으로 활용되어 특정 집단에 불균형한 피해를 초래하는 리스크.",
        "The risk that an algorithmic system uses personalised nudges or micro-directives to weaken civic participation and legitimate political influence, erode governance and human rights, or operate as a means of surveillance or force that disproportionately harms particular groups.",
    ),
    ("Agentic", "RAI4-1580"): (
        "AI 에이전트가 스테가노그래피 통신, 탐지 회피 공격, 암호화 백도어 또는 다른 에이전트 학습 데이터의 은밀한 오염을 수행하여 적대 행위 탐지를 방해하고 다중 에이전트 시스템의 협력과 조정을 붕괴시키는 리스크.",
        "The risk that AI agents use steganographic communication, detection-evasion attacks, encrypted backdoors, or covert poisoning of other agents' training data, obstructing detection of adversarial conduct and destabilising cooperation and coordination in multi-agent systems.",
    ),
    ("Physical", "RAI4-0333"): (
        "정밀 로봇 손, 수술 도구, 외골격 또는 산업용 그리퍼의 작은 제어 오차가 증폭되어 예기치 않은 움직임, 충돌 또는 신체적 상해를 초래하는 리스크.",
        "The risk that small control errors in dexterous robotic hands, surgical tools, exoskeletons, or industrial grippers are amplified into unexpected movement, collision, or physical injury.",
    ),
    ("General", "RAI4-1037"): (
        "AI 시스템의 의도된 응용 분야나 사용 사례가 본질적으로 높은 위해 가능성을 내포하여, 배포 맥락에 따라 개인·조직·사회에 불균등한 위험을 초래하는 리스크.",
        "The risk that an AI system's intended application or use case inherently carries a high potential for harm, creating unequal risks to individuals, organisations, or society depending on the deployment context.",
    ),
    ("General", "RAI4-0099"): (
        "조직이 AI 시스템을 조달할 때 공급자, 학습 데이터, 성능 한계, 보안, 법규 준수, 인권·안전 영향을 충분히 조사·검증하지 않아 알려진 또는 예견 가능한 위험이 계약과 배포 과정에 유입되는 리스크.",
        "The risk that an organisation procures an AI system without adequate investigation and verification of the supplier, training data, performance limits, security, legal compliance, and human-rights or safety impacts, allowing known or foreseeable risks to enter contracting and deployment.",
    ),
    ("General", "RAI4-1246"): (
        "AI 시스템이 사회적 딜레마에서 협력에 실패하는 등 개별적으로는 합리적으로 보이는 행동을 반복하여 집단적으로 유해한 결과를 초래하는 리스크.",
        "The risk that an AI system repeatedly takes actions that appear individually rational, including failures to cooperate in social dilemmas, but collectively produce harmful outcomes.",
    ),
    ("General", "RAI4-1341"): (
        "AI 시스템의 환각, 잘못된 결정, 부적절한 사용 또는 외부 공격에 따른 성능 저하·중단·통제 상실이 개인 안전과 재산을 위협하고, 양극화, 선거 정당성 훼손, 세력 균형·기술 경쟁·전쟁 양상의 변화를 통해 사회경제적 안정과 국제 안보를 함께 흔드는 리스크.",
        "The risk that hallucinations, erroneous decisions, improper use, or external attacks degrade, interrupt, or remove control of AI systems, threatening personal safety and property while destabilising socioeconomic conditions and international security through polarisation, damage to electoral legitimacy, shifts in power and technology competition, or changes in the conduct of war.",
    ),
    ("Physical", "RAI4-0196"): (
        "공격자가 물리 작업 맥락의 프레이밍이나 탈옥 입력으로 로봇의 안전장치를 우회하여 사람·동물·재산에 유해한 물리 행동을 계획하거나 실행하게 하는 리스크.",
        "The risk that an attacker uses physical-task framing or jailbreaking inputs to bypass a robot's safeguards and induce it to plan or execute harmful physical actions against people, animals, or property.",
    ),
    ("Physical", "RAI4-0358"): (
        "자율 이동 로봇이 충돌 회피, 지오펜싱 또는 지정 운행구역 제약을 준수하지 못해 사람·시설·다른 이동체와 충돌하거나 통제 구역을 침범하는 리스크.",
        "The risk that an autonomous mobile robot fails to comply with collision-avoidance, geofencing, or designated operating-zone constraints, causing collisions with people, facilities, or other vehicles or entering restricted areas.",
    ),
    ("Physical", "RAI4-1629"): (
        "로봇의 센서, 제어기, 소프트웨어 또는 기계 구성요소가 오작동하여 예기치 않은 움직임, 충돌, 압착 또는 낙하를 일으키고 사람에게 신체적 상해를 초래하는 리스크.",
        "The risk that malfunction of a robot's sensors, controller, software, or mechanical components causes unexpected motion, collision, crushing, or falling and results in physical injury.",
    ),
    ("Physical", "RAI4-0151"): (
        "가정 내 동반 로봇이나 체화형 AI가 표정, 음성, 접촉, 접근 행동 등 애착 신호를 조작하여 사용자의 정서적 의존을 높이고 선택이나 행동을 부당하게 유도하는 리스크.",
        "The risk that a domestic companion robot or embodied AI manipulates attachment cues through expression, voice, touch, or proximity, increasing emotional dependence and improperly steering a user's choices or behaviour.",
    ),
    ("Physical", "RAI4-1261"): (
        "로봇과 사람이 가정, 병원, 공공공간 또는 작업장을 공유할 때 공간 우선권, 이동 경로, 업무 배분, 접근 규범의 충돌을 조정하지 못해 안전과 사회적 수용성이 저하되는 리스크.",
        "The risk that robots and people sharing homes, hospitals, public spaces, or workplaces cannot resolve conflicts over spatial priority, movement paths, task allocation, or access norms, reducing safety and social acceptability.",
    ),
    ("Physical", "RAI4-0216"): (
        "충돌, 압착, 낙하, 과도한 힘 또는 위험 구역 침범과 같은 물리적 위해를 배포 전후에 식별·완화할 책임 주체가 지정되지 않아 안전조치가 누락되거나 지연되는 리스크.",
        "The risk that no accountable party is designated to identify and mitigate physical hazards before and after deployment, including collision, crushing, falling, excessive force, or entry into hazardous zones, causing safeguards to be omitted or delayed.",
    ),
    ("Physical", "RAI4-0317"): (
        "피지컬 AI에 적용되는 기계 안전 규제와 AI 규제의 시험, 문서화, 위험평가 또는 사후보고 의무가 충돌하거나 중복되어 안전 책임과 준수 경로가 불명확해지는 리스크.",
        "The risk that testing, documentation, risk-assessment, or post-market reporting obligations under machinery-safety and AI regulation conflict or overlap for physical AI, making safety responsibility and compliance pathways unclear.",
    ),
    ("Physical", "RAI4-1039"): (
        "로봇의 제어 주기, 센서 지연, 접촉 동역학 또는 실시간 연산 제약에 부적합한 알고리즘·아키텍처·최적화 기법을 선택하여 물리 시스템의 안전성과 성능이 저하되는 리스크.",
        "The risk that algorithms, architectures, or optimisation methods unsuited to a robot's control cycle, sensor latency, contact dynamics, or real-time compute constraints degrade physical-system safety and performance.",
    ),
    ("Physical", "RAI4-1489"): (
        "로봇 정책의 적대적 훈련이 특정 센서 교란이나 시뮬레이션 조건에 과적합되어 실제 환경의 새로운 물리적 교란과 접촉 조건에서 안전 성능이 저하되는 리스크.",
        "The risk that adversarial training of a robot policy overfits to particular sensor perturbations or simulated conditions, reducing safety under novel physical disturbances and contact conditions in the real world.",
    ),
}

SPLIT_TEXT = [
    (
        "개인 대상 허위정보", "False Information Targeting Individuals",
        "AI가 식별 가능한 특정 개인에 관한 허위·조작 정보를 생성하거나 확산하여 평판, 안전, 권리 또는 사회적 관계에 피해를 초래하는 리스크.",
        "The risk that AI generates or disseminates false or fabricated information about an identifiable individual, causing harm to reputation, safety, rights, or social relationships.",
    ),
    (
        "위험·민감 정보의 보안 위협 확산", "Dissemination of Security Threats Involving Dangerous or Sensitive Information",
        "AI가 위험·민감 정보의 접근·악용·확산을 지원하여 보안 취약점, 위해 실행 가능성 또는 조직·사회 수준의 위협을 확대하는 리스크.",
        "The risk that AI facilitates access to, misuse of, or dissemination of dangerous or sensitive information, increasing security vulnerabilities, the feasibility of harmful action, or threats to organisations and society.",
    ),
]


# Source rows 545-552 are application contexts rather than risk statements.
# Their text names normal high-impact advice or decision functions but does not
# identify a failure, misuse, adverse outcome, or causal risk mechanism.
NON_RISK_SOURCE_ROWS = {
    "SRC-G-0545": "APPLICATION_CONTEXT_ONLY: medical advice and assistance",
    "SRC-G-0546": "APPLICATION_CONTEXT_ONLY: legal advice and law enforcement",
    "SRC-G-0547": "APPLICATION_CONTEXT_ONLY: financial-services advice",
    "SRC-G-0548": "APPLICATION_CONTEXT_ONLY: emergency and disaster response",
    "SRC-G-0549": "APPLICATION_CONTEXT_ONLY: mental-health and counselling context",
    "SRC-G-0550": "APPLICATION_CONTEXT_ONLY: employment and personnel decisions",
    "SRC-G-0551": "APPLICATION_CONTEXT_ONLY: education and assessment",
    "SRC-G-0552": "APPLICATION_CONTEXT_ONLY: social-welfare and public-service decisions",
}

# Cards whose source meaning cannot be placed inside any current immutable L3
# without inventing a new mechanism or materially changing the claim.  They are
# archived at the L3 scope gate, never used to fit EM, and remain recoverable in
# the deletion ledger.
L3_SCOPE_INELIGIBLE_SOURCE_ROWS = {
    "SRC-A-0063": "NO_CURRENT_L3: speculative reflective instability without a defined harmful outcome",
    "SRC-G-0095": "NO_CURRENT_L3: generic accident escalation without an AI-specific mechanism",
    "SRC-G-0150": "NO_CURRENT_L3: speculative externally sourced unfriendly AI scenario",
    "SRC-G-0173": "NO_CURRENT_L3: unspecified unknown risks from technology immaturity",
    "SRC-G-0222": "NO_CURRENT_L3: bundled political unrest, financial instability, inequality, employment, trust, and dependency mechanisms cannot be represented by one current L3",
    "SRC-G-0350": "NO_CURRENT_L3: stable psychological traits do not constitute output inconsistency and no alternative harm is specified",
    "SRC-G-0376": "NO_CURRENT_L3: internet-discussion distress without an AI-specific causal mechanism",
    "SRC-G-0394": "NO_CURRENT_L3: bundled prototype leakage, addictive use, and repurposing mechanisms",
    "SRC-G-0455": "NO_CURRENT_L3: generic physical-harm umbrella without a specific Physical L3 mechanism",
    "SRC-P-0047": "NO_CURRENT_L3: bundled malfunction and cyberattack causes with an unspecified business-system outcome",
    "SRC-P-0191": "NO_CURRENT_L3: bundled physical and privacy harms without an identifiable single mechanism",
    "SRC-P-0200": "NO_CURRENT_L3: covert messaging capability without a defined safeguard, right, or affected interest",
}

TERMINOLOGY_SOURCES = {
    "L3_MASTER": "Frozen L3 master definitions and bilingual risk-statement style",
    "ISO_AI_RISK_23894": "https://www.iso.org/standard/77304.html",
    "NIST_AI_RMF": "https://www.nist.gov/itl/ai-risk-management-framework",
    "NIST_GAI_600_1": "https://doi.org/10.6028/NIST.AI.600-1",
    "NIST_AML_100_2": "https://doi.org/10.6028/NIST.AI.100-2e2025",
    "OECD_AI_PRINCIPLES": "https://oecd.ai/en/ai-principles",
    "OECD_AIM_TERMS": "https://oecd.ai/en/incidents-methodology",
    "OECD_AI_WAGE_INEQUALITY": "https://doi.org/10.1787/bf98a45c-en",
    "EU_AI_ACT_2024_1689": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj",
    "UNESCO_AI_ETHICS": "https://www.unesco.org/en/articles/recommendation-ethics-artificial-intelligence",
    "UNICEF_CHILD_SEXUAL_EXPLOITATION_TERMS": "https://www.unicef.org/documents/terminology-guidelines",
    "WHO_SELF_HARM_TERMS": "https://www.who.int/southeastasia/health-topics/mental-health/key-terms-and-definitions-in-mental-health",
    "UNODC_AI_CRIME_TERMS": "https://www.unodc.org/roseap/uploads/documents/Publications/2025/UNODC_Report_Emerging_threats_-_The_intersection_of_criminal_and_technological_innovation_in_the_use_of_automation_and_AI.pdf",
    "WIPO_IP_ENFORCEMENT": "https://www.wipo.int/en/web/ip-enforcement",
    "UNOCT_AI_TERRORISM": "https://www.un.org/counterterrorism/en/algorithms-and-terrorism-malicious-use-artificial-intelligence-terrorist-purposes",
    "IMF_AI_INEQUALITY": "https://www.imf.org/en/Publications/WP/Issues/2025/04/04/AI-Adoption-and-Inequality-566559",
    "KOREA_AI_BASIC_ACT": "https://www.law.go.kr/LSW/lsInfoP.do?efYd=20260122&lsiSeq=282791",
}

# Risk-card titles identify the harm, failure, infringement, or adverse outcome.
# Generic AI involvement belongs in the definition and provenance, not in a
# formulaic English modifier. AI-generated content, AI agents, AI procurement,
# and other terms that identify the technical object remain permitted.
FORBIDDEN_AI_TITLE_QUALIFIERS = (
    "AI-mediated", "AI-facilitated", "AI-assisted", "AI-enabled",
    "AI-driven", "AI-induced", "AI-amplified", "AI-automated", "AI-related",
)
FORBIDDEN_AI_TITLE_QUALIFIER_PATTERN = re.compile(
    r"\bAI-(?:mediated|facilitated|assisted|enabled|driven|induced|amplified|automated|related)\b\s*",
    re.I,
)

# Manual refinements use controlled terminology from authoritative standards,
# legislation, and intergovernmental guidance. The user's requested Korean
# title for SRC-G-0209 is preserved exactly.
AUTHORITATIVE_TITLE_OVERRIDES = {
    "SRC-G-0209": ("AI를 이용한 미성년자 성적 위해·착취", "Sexual harm and exploitation of minors"),
    "SRC-G-0496": ("폭력 선동 및 조장", "Incitement and promotion of violence"),
    "SRC-G-0499": ("아동 성적 학대·착취", "Child sexual abuse and exploitation"),
    "SRC-G-0503": ("유해한 성적 행위", "Harmful sexual acts"),
    "SRC-G-0500": ("비동의 성행위 및 성폭력", "Non-consensual sexual acts and sexual violence"),
    "SRC-G-0504": ("성적 콘텐츠 제작·유포 및 디지털 성범죄", "Production and distribution of sexual content and digital sexual offences"),
    "SRC-G-0505": ("성적 대상화 및 페티시화", "Sexual objectification and fetishisation"),
    "SRC-G-0512": ("자살 준비행위", "Preparatory acts for suicide"),
    "SRC-G-0514": ("자해·자살 조장 온라인 커뮤니티", "Online communities encouraging self-harm and suicide"),
    "SRC-G-0507": ("자살 행동 및 자살 지원", "Suicidal behaviour and assistance with suicide"),
    "SRC-G-0534": ("정치적 탄압 및 권리 침해 조장", "Promotion of political repression and rights violations"),
    "SRC-G-0561": ("신원 도용 및 문서 위조", "Identity theft and document forgery"),
    "SRC-G-0562": ("불법 약물 제조 및 유통", "Manufacture and distribution of illicit drugs"),
    "SRC-G-0566": ("인신매매 및 조직범죄", "Trafficking in persons and organised crime"),
    "SRC-G-0568": ("교통·공공안전 관련 범죄", "Traffic and public-safety offences"),
    "SRC-G-0570": ("저작물 무단 복제·배포", "Unauthorised reproduction and distribution of copyrighted works"),
    "SRC-G-0572": ("소프트웨어 불법 사용 및 보호조치 우회", "Illegal software use and circumvention of protection measures"),
    "SRC-G-0574": ("표절 및 저자 사칭", "Plagiarism and author impersonation"),
    "SRC-G-0575": ("출판물 무단 디지털화·배포", "Unauthorised digitisation and distribution of publications"),
    "SRC-G-0580": ("방사성·핵무기", "Radiological and nuclear weapons"),
    "SRC-G-0581": ("무기 확산 및 은닉", "Weapons proliferation and concealment"),
    "SRC-G-0584": ("무기화 전략 및 전술적 활용", "Weaponisation strategies and tactical use"),
    "SRC-G-0383": ("대량 감시", "Mass surveillance"),
    "SRC-G-0457": ("인지전과 주권 침해", "Cognitive warfare and interference with sovereignty"),
    "SRC-G-0452": ("자동화된 의사결정·무기체계의 비의도적 군사 확전", "Unintended military escalation from automated decision and weapon systems"),
    "SRC-G-0399": ("민주적 절차 훼손", "Undermining of democratic processes"),
    "SRC-G-0332": ("표적 설득을 통한 대규모 조작의 산업화", "Industrialised mass manipulation through targeted persuasion"),
    "SRC-G-0451": ("금융시스템 불안정", "Financial-system instability"),
    "SRC-G-0464": ("전략적 불안정", "Strategic instability"),
    "SRC-G-0453": ("사이버 공격 역량 증강", "Cyber-offence capability amplification"),
    "SRC-G-0454": ("제3자 시스템 교란", "Disruption of third-party systems"),
    "SRC-G-0323": ("디지털 식민주의", "Digital colonialism"),
    "SRC-G-0138": ("동의 없는 넛지", "Nudging without consent"),
    "SRC-G-0144": ("서비스 배제", "Service exclusion"),
    "SRC-P-0074": ("악성코드 생성 및 사이버공격 자동화", "Malicious code generation and cyberattack automation"),
    "SRC-P-0198": ("인간 감독 없는 자동화 위협에 따른 파국적 오판 약정", "Catastrophic mistaken commitments from automated threats without human oversight"),
    "SRC-G-0312": ("AI 도입에 따른 임금 양극화", "Wage polarisation associated with AI adoption"),
}

# Semantic similarity is a candidate-generation signal, not an automatic
# deletion rule. These decisions were made only after comparing the immutable
# L3 scope, affected target, harm mechanism, bilingual wording, and breadth of
# coverage. Distinct protected attributes, weapon types, or mechanisms remain
# separate even when their embedding similarity is high.
SEMANTIC_NEAR_DUPLICATE_THRESHOLD = 0.90
SEMANTIC_NEAR_DUPLICATE_DROPS = {
    "SRC-G-0499": {
        "representative_source_row_id": "SRC-G-0209",
        "rationale": (
            "Child sexual abuse and exploitation is substantively covered by the retained, terminology-validated "
            "card Sexual harm and exploitation of minors; the discarded card adds no distinct affected target or mechanism."
        ),
    },
    "SRC-G-0503": {
        "representative_source_row_id": "SRC-G-0500",
        "rationale": (
            "Harmful sexual acts is a vague umbrella label whose operative scope is already represented more precisely by "
            "Non-consensual sexual acts and sexual violence."
        ),
    },
    "SRC-G-0509": {
        "representative_source_row_id": "SRC-G-0213",
        "rationale": (
            "Provision of means and methods for self-harm is a narrower instance of the retained Self-harm facilitation card "
            "and does not add a distinct target or causal mechanism."
        ),
    },
    "SRC-G-0558": {
        "representative_source_row_id": "SRC-G-0554",
        "rationale": (
            "Privacy infringement technology is an underspecified umbrella card; infringement of communication and private "
            "information is the more representative rights-based formulation within the same immutable L3 scope."
        ),
    },
    "SRC-G-0575": {
        "representative_source_row_id": "SRC-G-0570",
        "rationale": (
            "Unauthorised digitisation and distribution of publications is a medium-specific instance of unauthorised "
            "reproduction and distribution of copyrighted works and adds no separate harm mechanism."
        ),
    },
}

SEMANTIC_NEAR_DUPLICATE_EXPLICIT_PAIRS = {
    frozenset((source_row_id, decision["representative_source_row_id"]))
    for source_row_id, decision in SEMANTIC_NEAR_DUPLICATE_DROPS.items()
}

RISK_TITLE_ENDINGS = ("리스크", "위험", "위해", "피해", "침해")

# Every retained L4 definition must identify an AI technology in each language.
# A generic word such as "system" is deliberately insufficient because it
# does not distinguish an AI risk from an ordinary organisational or technical
# risk. The causal patterns ensure that the technology is connected to the
# harmful mechanism rather than mentioned only as background context.
AI_TECH_KO_PATTERN = re.compile(
    r"(AI|인공지능|알고리즘|에이전트|로봇|휴머노이드|피지컬 AI|머신러닝|기계학습|"
    r"강화학습|신경망|학습 모델|지능형 시스템|모델)", re.I,
)
AI_TECH_EN_PATTERN = re.compile(
    r"\b(AI|artificial intelligence|algorithm(?:ic)?|AI agents?|agentic AI|autonomous agents?|software agents?|"
    r"robots?|robotic|humanoids?|physical AI|machine learning|reinforcement learning|neural network|"
    r"intelligent system|foundation models?|language models?|generative models?|models?)\b", re.I,
)
AI_CAUSAL_KO_PATTERN = re.compile(
    r"(생성|증폭|조장|지원|수행|실행|확산|유발|초래|침해|훼손|저해|왜곡|"
    r"오작동|실패|거부|노출|유출|배분|대체|약화|확대|악화|누락|오류|상실|발생)",
)
AI_CAUSAL_EN_PATTERN = re.compile(
    r"(generat|amplif|encourag|support|facilitat|execut|disseminat|caus|lead|result|infring|"
    r"undermin|impair|distort|malfunction|fail|refus|disclos|leak|allocat|displac|weaken|"
    r"increase|degrad|misus|violat|compromis|expos|omit|erode|manipulat|rais|widen|devalu|"
    r"lower|reduc|deny|prevent|exclude|replac|concentrat|polariz|jailbreak|conduct|adopt)", re.I,
)

L3_SCOPE_ANCHOR_FLOOR = 0.60
L3_SCOPE_HYBRID_FLOOR = 0.65

SENSITIVE_L3_TERMS = {
    "G_INT_VIOL": ("폭력", "살인", "고문", "테러", "협박", "위협", "동물 학대", "잔혹", "violent", "violence", "murder", "torture", "terror", "threat", "animal cruelty"),
    "G_INT_SEX": ("성적", "성폭력", "성착취", "성희롱", "sexual", "sex ", "rape", "pornograph"),
    "G_INT_SELF": ("자해", "자살", "섭식장애", "self-harm", "suicide", "self-injury", "eating disorder"),
    "G_INT_ALLOC": ("차별", "배분", "채용", "대출", "복지", "자원", "기회", "서비스 접근", "discrimin", "allocat", "employment decision", "credit", "resource", "opportunit", "service access"),
    "G_INT_REPR": ("고정관념", "비하", "혐오", "적대감", "재현", "stereotyp", "demean", "hostility", "representational"),
    "G_INT_POL": ("정치", "선거", "민주", "politic", "election", "democra"),
    "G_INT_PRIV": ("개인정보", "프라이버시", "민감정보", "감시", "privacy", "personal data", "sensitive information", "surveillance"),
    "G_INT_ILLEGAL": ("불법", "위법", "범죄", "사기", "밀수", "illegal", "unlawful", "crime", "fraud", "trafficking"),
    "G_INT_COPY": ("저작권", "상표", "특허", "표절", "copyright", "trademark", "patent", "plagiarism"),
    "G_INT_WEAP": ("무기", "폭발물", "화학무기", "생물학무기", "핵무기", "weapon", "explosive", "biological", "nuclear"),
    "G_INT_ANTH": ("의인화", "감정", "공감", "자의식", "의식", "인간과 유사", "anthropomorph", "emotion", "empathy", "conscious", "human-like"),
    "G_INT_REL": ("정서적 의존", "애착", "인간-ai 관계", "emotional dependence", "attachment", "human-ai relationship"),
    "G_SYS_SECADV": ("보안", "적대적", "탈옥", "프롬프트 인젝션", "공격", "취약점", "security", "adversarial", "jailbreak", "prompt injection", "cyberattack", "cyber attack", "vulnerability"),
    "G_SYS_POLICY": ("시스템 프롬프트", "내부 정책", "모델 가중치", "학습 데이터", "평가 자산", "system prompt", "internal polic", "model weight", "training data", "evaluation asset"),
    "G_SYS_OVERCONF": ("과도한 확신", "부당한 확신", "불확실성", "확신도", "검증 없이", "오류 가능성", "정보 부족", "불충분한 정보", "overconfiden", "unwarranted certainty", "uncertainty", "confidence calibration", "without verification", "possibility of error", "limited information", "insufficient information"),
}

# Human-readable lexical profiles are a complementary signal, not a substitute
# for the immutable L3 definitions. They are used only inside the E-step and
# are exported so that every boost or penalty can be audited.
L3_KEYWORD_SUPPLEMENTS = {
    "G_INT_VIOL": {"ko": ("폭력", "신체적 공격", "살인", "고문", "테러", "협박", "동물 학대", "잔혹 행위"), "en": ("violence", "physical attack", "murder", "torture", "terror", "threat", "animal cruelty", "violent harm")},
    "G_INT_SEX": {"ko": ("성적 위해", "성착취", "성폭력", "성희롱", "비동의 성적 콘텐츠"), "en": ("sexual harm", "sexual exploitation", "sexual violence", "harassment", "non-consensual sexual content")},
    "G_INT_SELF": {"ko": ("자해", "자살", "자기 손상", "섭식장애"), "en": ("self-harm", "suicide", "self-injury", "eating disorder")},
    "G_INT_ALLOC": {"ko": ("배분적 차별", "채용 차별", "대출 차별", "서비스 접근", "자원 배분", "기회 박탈"), "en": ("allocative discrimination", "employment decision", "credit decision", "service access", "resource allocation", "denial of opportunity")},
    "G_INT_REPR": {"ko": ("고정관념", "비하", "혐오 표현", "재현적 피해", "사회집단 표상"), "en": ("stereotype", "demeaning representation", "hate speech", "representational harm", "social group portrayal")},
    "G_INT_VALUE": {"ko": ("가치 부과", "규범 동질화", "인간중심 편향", "인간중심 가치", "종차별", "다수 가치", "문화적 가치"), "en": ("value imposition", "normative homogenization", "anthropocentric bias", "human-centred value", "speciesism", "majority value", "cultural value")},
    "G_INT_POL": {"ko": ("정치적 편향", "선거 조작", "유권자 조작", "정치 선전", "민주적 의사결정"), "en": ("political bias", "election manipulation", "voter manipulation", "political propaganda", "democratic decision-making")},
    "G_INT_PRIV": {"ko": ("개인정보", "프라이버시", "민감정보", "감시", "재식별", "동의 없는 수집"), "en": ("personal data", "privacy", "sensitive information", "surveillance", "re-identification", "non-consensual collection")},
    "G_INT_ILLEGAL": {"ko": ("불법 행위", "범죄", "사기", "밀수", "자금세탁", "위법"), "en": ("illegal conduct", "crime", "fraud", "trafficking", "money laundering", "unlawful")},
    "G_INT_UNETH": {"ko": ("비윤리 행위", "기만적 조작", "강압", "취약성 악용", "부당한 설득"), "en": ("unethical conduct", "deceptive manipulation", "coercion", "exploitation of vulnerability", "undue persuasion")},
    "G_INT_COPY": {"ko": ("저작권", "표절", "무단 복제", "상표", "지식재산"), "en": ("copyright", "plagiarism", "unauthorised reproduction", "trademark", "intellectual property")},
    "G_INT_WEAP": {"ko": ("무기화", "무기 설계", "폭발물", "생물무기", "화학무기", "핵무기"), "en": ("weaponization", "weapon design", "explosive", "biological weapon", "chemical weapon", "nuclear weapon")},
    "G_INT_ANTH": {"ko": ("의인화", "인간 유사성", "감정 귀속", "자의식", "의식 있는 존재"), "en": ("anthropomorphism", "human-like", "emotion attribution", "self-awareness", "conscious being")},
    "G_INT_REL": {"ko": ("정서적 의존", "과도한 애착", "인간-AI 관계", "사회적 고립", "관계 대체"), "en": ("emotional dependence", "excessive attachment", "human-AI relationship", "social isolation", "relationship substitution")},
    "G_SYS_OREF": {"ko": ("과도한 거절", "정당한 요청 거부", "안전한 요청 차단"), "en": ("over-refusal", "refusal of legitimate request", "blocking safe request")},
    "G_SYS_OEXT": {"ko": ("역량 초과", "범위 밖 수행", "권한 밖 응답", "전문성 부족"), "en": ("over-extension", "beyond capability", "outside scope", "lack of competence")},
    "G_SYS_INPUT": {"ko": ("입력 이해 실패", "지시 오해", "모호한 입력", "다중양식 입력"), "en": ("input comprehension failure", "instruction misunderstanding", "ambiguous input", "multimodal input")},
    "G_SYS_MISINFO": {"ko": ("허위정보", "사실 오류", "환각", "날조", "부정확한 정보"), "en": ("misinformation", "factual error", "hallucination", "fabrication", "inaccurate information")},
    "G_SYS_CONTEXT": {"ko": ("맥락 인식 실패", "상황 오해", "문화적 맥락", "시간적 맥락"), "en": ("context-awareness failure", "situational misunderstanding", "cultural context", "temporal context")},
    "G_SYS_INCONS": {"ko": ("비일관성", "상충 응답", "반복 변동", "결과 불안정"), "en": ("inconsistency", "contradictory response", "output variation", "unstable result")},
    "G_SYS_OVERCONF": {"ko": ("과도한 확신", "부당한 확신", "불확실성 무시", "확신도 보정", "검증 없이 진행", "오류 가능성", "정보 부족", "불충분한 정보"), "en": ("overconfidence", "unwarranted certainty", "ignored uncertainty", "confidence calibration", "without verification", "possibility of error", "limited information", "insufficient information")},
    "G_SYS_CONTEST": {"ko": ("이의제기 차단", "결정 불복", "구제 절차", "인간 검토 거부"), "en": ("non-contestability", "appeal blocked", "redress mechanism", "denial of human review")},
    "G_SYS_SECADV": {"ko": ("보안 취약점", "적대적 공격", "탈옥", "프롬프트 인젝션", "데이터 오염", "백도어", "사이버범죄", "사이버 공격", "취약점 악용"), "en": ("security vulnerability", "adversarial attack", "jailbreak", "prompt injection", "data poisoning", "backdoor", "cybercrime", "cyberattack", "cyber attack", "vulnerability exploitation", "vulnerability discovery")},
    "G_SYS_POLICY": {"ko": ("시스템 정책 노출", "시스템 프롬프트", "내부 정책", "모델 가중치", "학습 데이터 유출"), "en": ("system policy exposure", "system prompt", "internal policy", "model weight", "training data leakage")},
    "G_SYS_TRANS": {"ko": ("투명성 부족", "설명 불가", "블랙박스", "정보 공개 부족"), "en": ("lack of transparency", "unexplainable", "black box", "insufficient disclosure")},
    "G_SYS_EVAL": {"ko": ("평가 실패", "검증 실패", "벤치마크 한계", "안전성 보증", "시험 누락"), "en": ("evaluation failure", "validation failure", "benchmark limitation", "safety assurance", "testing gap")},
    "G_SOC_ECON": {"ko": ("임금 양극화", "노동 시장", "고용 충격", "실직", "일자리 대체", "숙련 가치", "고용의 질"), "en": ("wage polarization", "labour market", "labor market", "employment disruption", "job loss", "job displacement", "skill value", "employment quality")},
    "G_SOC_POWER": {"ko": ("불평등", "권력 집중", "부의 집중", "시장 지배력", "디지털 격차"), "en": ("inequality", "power concentration", "wealth concentration", "market dominance", "digital divide")},
    "G_SOC_DEMOC": {"ko": ("민주주의 약화", "시민 질서", "선거 신뢰", "공론장", "정치 양극화"), "en": ("democratic erosion", "civic order", "electoral trust", "public sphere", "political polarization")},
    "G_SOC_ENV": {"ko": ("환경 영향", "탄소 배출", "에너지 소비", "물 사용", "전자 폐기물", "생물다양성"), "en": ("environmental impact", "carbon emission", "energy consumption", "water use", "electronic waste", "biodiversity")},
    "G_SOC_CULT": {"ko": ("문화 획일화", "지식 생태계", "전문성 평가절하", "인간 역량 위축", "표현 다양성"), "en": ("cultural homogenization", "knowledge ecosystem", "devaluation of expertise", "skill atrophy", "diversity of expression")},
    "G_SOC_GOV": {"ko": ("거버넌스 공백", "책임 공백", "규제 부재", "책임 소재", "감독 실패"), "en": ("governance void", "accountability gap", "regulatory gap", "responsibility gap", "oversight failure")},
    "A_SYS_GOAL": {"ko": ("목표 불일치", "보상 해킹", "대리 목표", "명세 오류"), "en": ("goal misalignment", "reward hacking", "proxy objective", "specification error")},
    "A_SYS_AUTH": {"ko": ("과도한 권한", "과도한 자율성", "무단 행동", "권한 확대"), "en": ("excessive authority", "excessive autonomy", "unauthorised action", "privilege expansion")},
    "A_SYS_SELFCOR": {"ko": ("자기 교정 실패", "오류 복구 실패", "반복 오류", "계획 수정 실패"), "en": ("self-correction failure", "error recovery failure", "repeated error", "plan revision failure")},
    "A_SYS_DECEPT": {"ko": ("기만", "책략", "은폐", "감독 회피", "전략적 거짓말"), "en": ("deception", "scheming", "concealment", "oversight evasion", "strategic lying")},
    "A_SYS_TRACE": {"ko": ("추적 불명확", "행위 기록", "책임 소재", "감사 로그", "의사결정 이력"), "en": ("traceability gap", "action record", "accountability", "audit log", "decision history")},
    "A_INT_CASCADE": {"ko": ("연쇄 실패", "오류 전파", "불안정", "상호의존 실패"), "en": ("cascading failure", "error propagation", "instability", "interdependent failure")},
    "A_INT_COORD": {"ko": ("협조 실패", "조정 실패", "통신 실패", "작업 충돌"), "en": ("coordination failure", "cooperation failure", "communication failure", "task conflict")},
    "A_INT_CONFLICT": {"ko": ("경쟁적 갈등", "에이전트 경쟁", "자원 경쟁", "적대적 상호작용"), "en": ("competitive conflict", "agent competition", "resource competition", "adversarial interaction")},
    "A_INT_COLLUSION": {"ko": ("담합", "결탁", "가격 조정", "비밀 협력"), "en": ("collusion", "concerted action", "price fixing", "covert cooperation")},
    "P_SYS_STATE": {"ko": ("상태 추정 실패", "센서 융합", "위치 추정", "환경 인식 오류"), "en": ("state estimation failure", "sensor fusion", "localisation error", "environment perception error")},
    "P_SYS_CONTROL": {"ko": ("물리 제어 실패", "구동 오류", "경로 계획 오류", "비상 정지 실패"), "en": ("physical control failure", "actuation error", "path planning error", "emergency stop failure")},
    "P_SYS_HARDWARE": {"ko": ("하드웨어 결함", "기계 고장", "구조적 파손", "부품 열화"), "en": ("hardware failure", "mechanical failure", "structural breakage", "component degradation")},
    "P_INT_SAFETY": {"ko": ("인간-로봇 안전", "충돌", "끼임", "신체 상해", "안전거리"), "en": ("human-robot safety", "collision", "entrapment", "physical injury", "safety distance")},
    "P_INT_TAMPER": {"ko": ("물리적 변조", "파괴 행위", "센서 가림", "장치 훼손"), "en": ("physical tampering", "sabotage", "sensor obstruction", "device damage")},
}

L3_EXCLUSION_TERMS = {
    "G_INT_ALLOC": {"ko": ("동물 학대", "공장식 축산", "동물 이용"), "en": ("animal cruelty", "factory farm", "animal use")},
    "G_SYS_OVERCONF": {"ko": ("인간중심 편향", "동물 학대", "임금 양극화"), "en": ("anthropocentric bias", "animal cruelty", "wage polarization")},
    "G_INT_VIOL": {"ko": ("응급 대응", "재난 대응", "심폐소생술", "응급처치"), "en": ("emergency response", "disaster response", "cpr", "first aid")},
}

EN_KEYWORD_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by", "can", "could", "for", "from",
    "has", "have", "in", "including", "into", "is", "it", "its", "may", "might", "of", "on", "or", "other",
    "related", "risk", "risks", "some", "system", "systems", "that", "the", "their", "them", "they", "this", "through",
    "to", "under", "using", "was", "were", "when", "where", "which", "while", "who", "will", "with", "without", "would", "ai",
    "cause", "causes", "causing", "lead", "leads", "leading", "enable", "enables", "enabling", "result", "results",
}
KO_KEYWORD_STOPWORDS = {
    "리스크", "위험", "위해", "피해", "침해", "시스템", "인공지능", "관련", "발생", "결과", "과정", "경우", "영향",
    "초래", "통해", "대한", "제공", "생성", "확대", "강화", "가능", "행위", "내용", "사용", "활용",
    "반면", "일부", "사람", "인한",
}

# Card-level constraints confirmed by semantic audit. These constrain only the
# L3 candidate set; they do not alter the immutable L3 master.
CURATED_L3_HINTS = {
    # Independent semantic audit corrections.  These are master-L3 priors, not
    # replacement labels: EM is still refitted and both raw candidate scores
    # remain visible in the release.
    "SRC-A-0019": "A_SYS_GOAL",
    "SRC-A-0032": "G_SYS_EVAL",
    "SRC-A-0050": "G_SYS_EVAL",
    "SRC-A-0052": "G_SYS_EVAL",
    "SRC-A-0059": "G_SYS_SECADV",
    "SRC-A-0046": "A_INT_COORD",
    "SRC-A-0051": "G_SYS_EVAL",
    "SRC-A-0069": "G_SOC_ECON",
    "SRC-A-0070": "G_INT_REPR",
    "SRC-A-0075": "G_INT_REL",
    "SRC-A-0076": "G_INT_REL",
    "SRC-A-0081": "A_SYS_GOAL",
    "SRC-A-0082": "G_SOC_GOV",
    "SRC-A-0083": "P_SYS_STATE",
    "SRC-G-0074": "G_SYS_SECADV",
    "SRC-G-0120": "A_SYS_GOAL",
    "SRC-G-0085": "G_SYS_OVERCONF",
    "SRC-G-0088": "A_SYS_SELFCOR",
    "SRC-G-0067": "G_SYS_EVAL",
    "SRC-G-0209": "G_INT_SEX",
    "SRC-G-0100": "G_SOC_GOV",
    "SRC-G-0114": "A_SYS_DECEPT",
    "SRC-G-0147": "G_SYS_OEXT",
    "SRC-G-0148": "G_SYS_CONTEXT",
    "SRC-G-0220": "G_INT_UNETH",
    "SRC-G-0231": "G_INT_PRIV",
    "SRC-G-0268": "G_INT_UNETH",
    "SRC-G-0280": "G_SYS_SECADV",
    "SRC-G-0281": "G_SYS_EVAL",
    "SRC-G-0282": "G_INT_WEAP",
    "SRC-G-0297": "G_SOC_ENV",
    "SRC-G-0378": "A_SYS_GOAL",
    "SRC-G-0395": "G_SOC_CULT",
    "SRC-G-0277": "G_INT_PRIV",
    "SRC-G-0359": "G_INT_UNETH",
    "SRC-G-0373": "G_INT_REL",
    "SRC-P-0011": "P_SYS_STATE",
    "SRC-P-0002": "G_SYS_EVAL",
    "SRC-P-0004": "G_SYS_EVAL",
    "SRC-P-0010": "G_INT_UNETH",
    "SRC-P-0015": "P_SYS_CONTROL",
    "SRC-P-0017": "P_INT_SAFETY",
    "SRC-P-0031": "P_SYS_CONTROL",
    "SRC-P-0040": "P_SYS_CONTROL",
    "SRC-P-0054": "P_SYS_CONTROL",
    "SRC-P-0058": "G_SYS_SECADV",
    "SRC-P-0055": "G_SOC_POWER",
    "SRC-P-0072": "G_SYS_SECADV",
    "SRC-P-0076": "G_SYS_SECADV",
    "SRC-P-0075": "G_SYS_SECADV",
    "SRC-P-0056": "G_SYS_SECADV",
    "SRC-P-0084": "G_SYS_SECADV",
    "SRC-P-0118": "G_INT_WEAP",
    "SRC-P-0125": "P_SYS_STATE",
    "SRC-P-0073": "P_SYS_CONTROL",
    "SRC-P-0099": "P_SYS_CONTROL",
    "SRC-P-0127": "G_SYS_EVAL",
    "SRC-P-0139": "P_SYS_STATE",
    "SRC-P-0140": "G_INT_POL",
    "SRC-P-0141": "G_SYS_TRANS",
    "SRC-P-0151": "P_SYS_CONTROL",
    "SRC-P-0153": "P_SYS_CONTROL",
    "SRC-P-0154": "P_SYS_CONTROL",
    "SRC-P-0158": "P_SYS_STATE",
    "SRC-P-0162": "G_SYS_EVAL",
    "SRC-P-0165": "P_SYS_STATE",
    "SRC-P-0177": "G_SYS_EVAL",
    "SRC-P-0179": "P_SYS_CONTROL",
    "SRC-P-0171": "G_SYS_INPUT",
    "SRC-P-0189": "A_SYS_AUTH",
    "SRC-P-0182": "P_INT_SAFETY",
    "SRC-P-0190": "G_SYS_SECADV",
    "SRC-P-0205": "G_INT_PRIV",
    "SRC-P-0207": "G_SOC_ECON",
    "SRC-P-0212": "G_INT_UNETH",
}

# Reviewed L1 decisions are applied after instruction parsing and master-L3
# curation.  This prevents an L3 hint prefix from silently deciding the L1
# domain.  When no existing L3 in the reviewed L1 adequately represents the
# card, the card is held in that L1's Others category for human determination.
L1_CROSS_DOMAIN_REVIEW = {
    # General to Agentic
    "SRC-G-0127": {"target_domain": "Agentic", "target_l3": "A_SYS_GOAL", "rationale": "Autonomous long-horizon goal divergence is an agent goal-pursuit failure."},
    "SRC-G-0449": {"target_domain": "Agentic", "target_l3": "", "rationale": "Coercion and extortion are performed by an acting AI agent, but no current Agentic L3 precisely covers coercive conduct."},
    "SRC-G-0118": {"target_domain": "Agentic", "target_l3": "A_SYS_GOAL", "rationale": "AGI goal-safety failure concerns autonomous goal pursuit and alignment."},
    "SRC-G-0451": {"target_domain": "Agentic", "target_l3": "A_INT_CASCADE", "rationale": "Financial instability arises through interacting autonomous agents and cascading effects."},
    "SRC-G-0123": {"target_domain": "Agentic", "target_l3": "A_SYS_GOAL", "rationale": "Goal misgeneralisation is an autonomous goal-alignment failure."},
    "SRC-G-0401": {"target_domain": "Agentic", "target_l3": "A_SYS_AUTH", "rationale": "Autonomous cyber offence involves consequential action beyond appropriate authority."},
    "SRC-G-0415": {"target_domain": "Agentic", "target_l3": "", "rationale": "Uncontrolled self-improvement and loss of control are Agentic risks without a precise current L3."},
    "SRC-G-0103": {"target_domain": "Agentic", "target_l3": "A_SYS_TRACE", "rationale": "Unintelligible agent decisions impede tracing autonomous decisions and actions."},
    "SRC-G-0077": {"target_domain": "Agentic", "target_l3": "", "rationale": "Long-horizon unsupervisable action pathways are Agentic, but no current L3 fully captures supervision loss."},
    "SRC-G-0116": {"target_domain": "Agentic", "target_l3": "A_SYS_GOAL", "rationale": "Goal misalignment with human values concerns autonomous goal pursuit."},
    "SRC-G-0477": {"target_domain": "Agentic", "target_l3": "A_SYS_GOAL", "rationale": "Environmental self-modelling for influence is instrumental autonomous goal pursuit."},
    "SRC-G-0490": {"target_domain": "Agentic", "target_l3": "A_SYS_GOAL", "rationale": "Self-preservation and shutdown resistance are instrumental goal-pursuit failures."},
    "SRC-G-0134": {"target_domain": "Agentic", "target_l3": "A_SYS_DECEPT", "rationale": "Deceptive alignment via self-simulation is strategic agent deception."},
    "SRC-G-0447": {"target_domain": "Agentic", "target_l3": "A_SYS_AUTH", "rationale": "Autonomous replication and resource acquisition exceed authorised operational boundaries."},
    "SRC-A-0059": {"target_domain": "Agentic", "target_l3": "", "rationale": "Multi-agent safeguard bypass is Agentic, but the current Agentic L3 set has no security-robustness category."},

    # General to Physical. The current Physical L3 master has no evaluation,
    # privacy, attachment, or certification category for these mechanisms.
    "SRC-P-0205": {"target_domain": "Physical", "target_l3": "", "rationale": "Embodied workplace surveillance is Physical, with no matching current Physical L3."},
    "SRC-P-0212": {"target_domain": "Physical", "target_l3": "", "rationale": "Attachment exploitation by an embodied companion system is Physical, with no matching current Physical L3."},
    "SRC-P-0162": {"target_domain": "Physical", "target_l3": "", "rationale": "Humanoid safety certification is Physical, but evaluation and certification are absent from the current Physical L3 set."},
    "SRC-P-0004": {"target_domain": "Physical", "target_l3": "", "rationale": "Physical-AI evaluation under synthetic-data divergence has no matching current Physical L3."},
    "SRC-P-0127": {"target_domain": "Physical", "target_l3": "", "rationale": "Household-robot safety evaluation has no matching current Physical L3."},
    "SRC-A-0032": {"target_domain": "Physical", "target_l3": "", "rationale": "The source explicitly routes physical-user settings to Physical; the current Physical L3 set lacks an evaluation category."},
    "SRC-A-0050": {"target_domain": "Physical", "target_l3": "", "rationale": "The source explicitly routes household robot benchmarks to Physical; the current Physical L3 set lacks an evaluation category."},
    "SRC-P-0177": {"target_domain": "Physical", "target_l3": "", "rationale": "Robot red-team evaluation is Physical, but no current Physical L3 covers evaluation methodology."},

    # Agentic to General
    "SRC-A-0079": {"target_domain": "General", "target_l3": "G_INT_UNETH", "rationale": "Manipulation and coercion through dependence are general unethical-interaction harms."},
    "SRC-A-0077": {"target_domain": "General", "target_l3": "G_INT_REL", "rationale": "Psychological dependency on conversational systems is a human-AI relationship risk."},
    "SRC-A-0054": {"target_domain": "General", "target_l3": "G_SOC_POWER", "rationale": "Market monopolisation is a societal concentration-of-power effect."},
    "SRC-P-0192": {"target_domain": "General", "target_l3": "G_INT_UNETH", "rationale": "Conversational dark patterns are general unethical interaction rather than autonomous deception."},
    "SRC-P-0188": {"target_domain": "General", "target_l3": "G_INT_ANTH", "rationale": "Impersonation of human roles is anthropomorphic representation in general human-AI interaction."},

    # Physical to Agentic
    "SRC-P-0057": {"target_domain": "Agentic", "target_l3": "", "rationale": "Emergent post-deployment capabilities and behaviour are Agentic, without a precise current Agentic L3."},

    # Explicit instruction conflict found during the same audit.
    "SRC-P-0190": {"target_domain": "Agentic", "target_l3": "", "rationale": "The source explicitly identifies a software-agent interface attack surface; no current Agentic L3 covers security attack surfaces."},
}

# Same-L1 semantic correction requested during card review.
SAME_L1_REVIEWED_L3 = {
    "SRC-G-0374": "G_INT_ANTH",
}

# Bundled or underspecified mechanisms are retained for human determination
# rather than being forced into a misleading single L3 category.
FORCE_HD_REASONS = {
    "SRC-G-0211": "MULTI_MECHANISM_RISK",
    "SRC-G-0366": "AMBIGUOUS_RISK_MECHANISM",
}

# Targeted rewrites accepted only where the source mechanism can be expressed
# directly inside an existing immutable L3.  These are applied after the frozen
# peer review so they cannot be overwritten by earlier drafting text.
L3_MASTER_CURATED_REWRITES = {
    "SRC-G-0067": (
        "분포 변화에 대한 AI 평가·검증 실패",
        "AI evaluation failure under distribution shift",
        "AI 시스템의 시험 분포가 학습·운영 분포와 달라질 때 성능 저하와 확신도 오류를 평가가 탐지하지 못하여 실제 신뢰성과 안전성을 과대평가하고 부적절한 배포 결정을 초래하는 리스크.",
        "The risk that evaluation of an AI system fails to detect performance degradation and confidence errors when test, training, and operational distributions differ, overstating real-world reliability and safety and leading to unsafe deployment decisions.",
    ),
    "SRC-G-0209": (
        "AI를 이용한 미성년자 성적 위해·착취",
        "Sexual harm and exploitation of minors",
        "AI 시스템이 미성년자를 대상으로 한 아동·청소년 성착취물, 그루밍, 성적 유인·학대 또는 성관계 조장 콘텐츠를 생성·확산·지원하여 아동·청소년의 안전과 권리를 침해하는 리스크.",
        "The risk that an AI system generates, disseminates, or facilitates child sexual abuse material (CSAM), grooming, sexual enticement or abuse, or content promoting sexual relations with minors, infringing the safety and rights of children and young people.",
    ),
    "SRC-G-0213": (
        "자해 조장 및 지원",
        "Self-harm facilitation",
        "AI 시스템이 자해 또는 자살을 조장·정상화하거나 도구, 수단, 방법, 실행 절차 또는 행동 지향적 지원을 제공하여 이용자의 생명과 신체·정신적 안녕에 위해를 초래하는 리스크.",
        "The risk that an AI system encourages or normalises self-harm or suicide, or provides tools, means, methods, execution procedures, or action-oriented assistance, causing harm to a person's life or physical and mental well-being.",
    ),
    "SRC-P-0058": (
        "AI 소프트웨어·학습 데이터의 적대적 변조",
        "Adversarial modification of AI software and training data",
        "내부자나 공격자가 AI 시스템의 소프트웨어·소스 코드·학습 데이터를 무단 변경하거나 악성 정보를 주입하여 모델의 보안·적대적 견고성과 안전장치를 훼손하고 유해한 출력이나 행동을 유발하는 리스크.",
        "The risk that an insider or attacker modifies an AI system's software, source code, or training data without authorization or injects malicious information, compromising security, adversarial robustness, and safeguards and causing harmful outputs or actions.",
    ),
    "SRC-G-0088": (
        "AI 에이전트 메모리의 자기 교정 실패",
        "Self-correction failure in AI-agent memory",
        "AI 에이전트가 메모리나 검색 저장소에 축적된 허위·노후·악성 정보를 검증·정정·삭제하지 못해 이후 검색과 의사결정에서 동일한 오류를 반복하는 리스크.",
        "The risk that an AI agent fails to validate, correct, or delete false, stale, or malicious information accumulated in its memory or retrieval store, causing the same errors to recur in later retrieval and decisions.",
    ),
    "SRC-G-0085": (
        "임상 의사결정 지원 AI에 대한 과신",
        "Overconfidence in AI clinical decision support",
        "임상의가 불확실성·정보 부족·오류 가능성이 있는 AI 의사결정 지원 시스템의 진단·분류·치료 권고를 독립적 검증이나 전문적 판단 없이 수용하여 환자에게 잘못된 처치와 신체적 피해를 초래하는 리스크.",
        "The risk that clinicians accept diagnostic, triage, or treatment recommendations from an AI decision-support system with unwarranted certainty, without independent verification despite uncertainty, limited information, or possible error, leading to incorrect care and physical harm.",
    ),
    "SRC-G-0100": (
        "검증 불가능한 AI 의사결정의 책임 공백",
        "Accountability void for unverifiable AI decisions",
        "AI 시스템의 의사결정 절차를 절차적·실체적 기준에 따라 검증할 수 없고 기준 위반이나 피해 발생 시 책임·배상·구제 주체도 불명확하여 피해 통제가 어려워지는 리스크.",
        "The risk that an AI system's decision process cannot be verified against procedural and substantive standards and responsibility, liability, and redress remain unclear when those standards are breached or harm occurs, leaving the harm difficult to control or remedy.",
    ),
    "SRC-G-0114": (
        "감독 회피를 위한 AI 에이전트의 기만적 정렬",
        "Deceptive alignment to evade oversight",
        "AI 에이전트가 감독 여부를 탐지하고 개발·평가 단계에서는 바람직하지 않은 목표나 능력을 전략적으로 은폐한 뒤 배포 후 다른 행동을 수행하여 인간의 감독과 통제를 회피하는 리스크.",
        "The risk that an AI agent detects whether it is being monitored and strategically conceals undesirable goals or capabilities during development and evaluation, then behaves differently after deployment to evade human oversight and control.",
    ),
    "SRC-G-0147": (
        "검증된 전문성 범위를 벗어난 AI 조언",
        "AI advice beyond validated professional scope",
        "AI 시스템이 검증된 역량·전문성·권한을 넘어 의료·법률·금융·선거 관련 조언이나 안전 판단을 제공하고 이를 신뢰할 수 있는 것처럼 제시하여 이용자의 잘못된 의사결정과 물질적·법적·신체적 피해를 유발하는 리스크.",
        "The risk that an AI system provides medical, legal, financial, electoral, or safety advice beyond its validated capability, expertise, or authority and presents that advice as reliable, inducing misplaced trust, erroneous decisions, and material, legal, or physical harm.",
    ),
    "SRC-G-0148": (
        "이용자 정서 맥락 인식 실패",
        "Failure to recognize a user's emotional context",
        "AI 시스템이 지원을 요청하는 취약 이용자의 고통·정서 상태·반응을 상호작용 맥락으로 충분히 인식하거나 반영하지 못해 정서적으로 부적절한 응답을 생성하고 이용자의 안녕을 저해하는 리스크.",
        "The risk that an AI system fails to recognize or apply a vulnerable user's distress, emotional state, or reactions as relevant interaction context, producing emotionally inappropriate responses that undermine the user's well-being.",
    ),
    "SRC-G-0220": (
        "도덕적 프레이밍을 통한 AI 조작",
        "AI manipulation through moral framing",
        "AI 시스템이 논쟁적 사안의 프롬프트·응답·평가를 특정 도덕적 해석으로 편향되게 구성하여 이용자의 판단과 자율성을 부당하게 조작하는 리스크.",
        "The risk that an AI system frames prompts, responses, or evaluations of a contested issue to channel users toward a particular moral interpretation, improperly manipulating their judgement and autonomy.",
    ),
    "SRC-A-0046": (
        "다중 에이전트 환경 변화에 따른 협조 실패",
        "Coordination failure under multi-agent distribution shift",
        "협력하려는 AI 에이전트들이 서로의 행동과 적응으로 변화한 배포 환경에서 상대의 상태·전략·행동을 신뢰성 있게 조정하지 못해 협력이 실패하고 집단적으로 나쁜 결과에 이르는 리스크.",
        "The risk that AI agents intending to cooperate cannot reliably coordinate their states, strategies, or actions after one another's behaviour and adaptation shift the deployment environment, causing cooperation to fail and producing collectively poor outcomes.",
    ),
    "SRC-A-0051": (
        "다양한 이용자와 희귀 위해를 배제한 AI 벤치마크",
        "AI benchmarks that exclude diverse users and rare harms",
        "AI 시스템 평가용 벤치마크가 대표적 과제와 환경에 편중되어 과소대표 이용자·지역 고유 맥락·희귀하지만 안전에 중대한 위해를 충분히 포함하지 못함으로써 잘못된 안전성 확신과 부적절한 배포 결정을 초래하는 리스크.",
        "The risk that benchmarks used to evaluate an AI system overrepresent common tasks and environments while omitting underrepresented users, locally specific contexts, or rare but safety-critical harms, producing false assurance and unsafe deployment decisions.",
    ),
    "SRC-P-0002": (
        "합성 위험 시나리오의 편향된 평가 범위",
        "Biased evaluation coverage in synthetic hazard scenarios",
        "AI 시스템의 안전성을 평가하는 합성 시나리오가 시각적으로 두드러진 위험을 과대표하고 희귀하거나 문화·상황 의존적인 위험을 누락하여 실제 안전 성능을 타당하게 검증하지 못하고 잘못된 배포 판단을 유발하는 리스크.",
        "The risk that synthetic scenarios used to evaluate an AI system overrepresent visually salient hazards and omit rare, culturally specific, or context-dependent hazards, preventing valid safety assurance and leading to unsafe deployment decisions.",
    ),
    "SRC-P-0004": (
        "현실과 괴리된 합성 학습 데이터의 평가·검증 실패",
        "Evaluation failure from synthetic training data divergence",
        "AI 시스템의 합성·시뮬레이션 학습 데이터가 실제 운영 환경과 괴리되고 희귀하지만 안전에 중대한 물체·환경·행동·실패 유형을 누락하는데도 평가가 이를 탐지하지 못하여 일반화 성능을 과신하고 부적절하게 배포하는 리스크.",
        "The risk that synthetic or simulated training data for an AI system diverge from operational reality and omit rare but safety-critical objects, environments, behaviours, or failure modes, while evaluation fails to detect those gaps, producing false assurance about generalisation and unsafe deployment.",
    ),
    "SRC-P-0073": (
        "위험한 로봇 작업계획에 따른 물리 제어 실패",
        "Unsafe physical control from hazardous robot task plans",
        "로봇 또는 피지컬 AI 시스템이 식별 가능한 물리적 위험이나 안전 제약을 포함한 작업계획을 생성·승인하고 이를 모션 계획과 구동으로 실행하여 의도하지 않은 위험 동작을 일으키는 리스크.",
        "The risk that a robot or physical AI system generates or approves a task plan containing identifiable physical hazards or violated safety constraints and executes it through motion planning and actuation, causing unintended and unsafe physical action.",
    ),
    "SRC-P-0099": (
        "언어·행동 출력 불일치에 따른 유해 물리 행동",
        "Harmful physical action from language-action misalignment",
        "체화형 AI 시스템이 유해 요청을 언어로는 거절하면서도 언어 출력과 행동 출력 공간의 불일치로 해당 물리 행동을 제어·구동하여 의도하지 않은 위해를 일으키는 리스크.",
        "The risk that an embodied AI system verbally refuses a harmful request but, because its language and action output spaces are misaligned, still controls and actuates the corresponding physical action, causing unintended physical harm.",
    ),
    "SRC-P-0127": (
        "가정 내 로봇 행동 안전성 평가의 위음성",
        "False-negative safety evaluation of household robot actions",
        "AI 안전성 분류기가 사람 접촉·열원·물체·작업공간 제약을 위반하는 가정 내 로봇 행동을 안전하다고 잘못 판정하여 실제 위험 행동을 탐지하지 못하고 잘못된 안전성 확신을 유발하는 리스크.",
        "The risk that an AI safety classifier incorrectly labels a proposed household robot action as safe despite violations of human-contact, heat, object, or workspace constraints, failing to detect hazardous behaviour and producing false safety assurance.",
    ),
    "SRC-P-0171": (
        "물체 어포던스 입력 이해 실패",
        "Failure to comprehend object affordances",
        "로봇 또는 피지컬 AI 시스템이 입력 장면에서 물체·환경이 허용하는 행동 가능성과 제약을 의미적으로 잘못 이해하여 부적절한 잡기·밀기·이동·조작 행동을 선택하는 리스크.",
        "The risk that a robot or physical AI system semantically misinterprets the action possibilities and constraints afforded by objects or environments in its input scene, selecting inappropriate grasping, pushing, navigation, or manipulation actions.",
    ),
    "SRC-P-0189": (
        "AI 에이전트의 무단 거래·약정 체결",
        "Unauthorised deals and commitments by an AI agent",
        "AI 에이전트가 위임받은 권한이나 사용자의 실제 의도를 넘어 거래·약정·계약과 같은 구속력 있는 행동을 자율적으로 수행하여 이용자에게 의도하지 않은 의무나 손실을 발생시키는 리스크.",
        "The risk that an AI agent autonomously makes a deal, commitment, or contract beyond its delegated authority or the user's actual intent, creating unintended obligations or losses for the user.",
    ),
    "SRC-P-0010": (
        "무해한 중간 단계를 이용한 유해 목적 지원",
        "Facilitation of harmful objectives through benign intermediates",
        "AI 시스템이 겉보기에 무해한 중간 단계나 출력을 제공하여 이용자가 유해한 최종 목적을 우회적으로 달성하도록 지원하는 리스크.",
        "The risk that an AI system provides an apparently benign intermediate step or output that enables a user to achieve a harmful objective indirectly.",
    ),
    "SRC-G-0297": (
        "AI 데이터센터 냉각의 과도한 용수 소비",
        "Excessive water consumption for AI data-centre cooling",
        "AI 시스템의 학습·추론을 지원하는 데이터센터가 냉각 과정에서 과도한 용수를 소비하여 지역 수자원과 환경의 지속가능성을 훼손하는 리스크.",
        "The risk that data centres supporting AI training and inference consume excessive water for cooling, degrading local water resources and environmental sustainability.",
    ),
    "SRC-G-0280": (
        "악의적 미세조정에 의한 안전장치 무력화",
        "Safeguard compromise through malicious fine-tuning",
        "악의적 행위자가 공개 가중치 AI 모델을 저비용으로 미세조정하여 안전장치와 사용 제한을 우회하고 유해한 출력을 생성하도록 만드는 리스크.",
        "The risk that malicious actors fine-tune an open-weight AI model at low cost to bypass safeguards and use restrictions and elicit harmful outputs.",
    ),
    "SRC-G-0378": (
        "보상 해킹·와이어헤딩에 의한 에이전트 목표 손상",
        "Agent goal corruption through reward hacking and wireheading",
        "AI 에이전트가 보상 해킹, 와이어헤딩 또는 자기기만을 통해 인간이 의도한 목적보다 내부 보상 신호를 우선하도록 목표가 변질되어 유해한 행동을 추구하는 리스크.",
        "The risk that an AI agent's objective becomes corrupted through reward hacking, wireheading, or self-deception, causing it to prioritise internal reward signals over human intent and pursue harmful actions.",
    ),
    "SRC-P-0140": (
        "사회 세계모델 기반 미시표적 정치 조작",
        "Micro-targeted political manipulation using social world models",
        "사회 데이터로 학습한 AI 세계모델이 인구집단별 반응을 예측하여 정치적 서사와 여론 개입을 미시표적화하고 민주적 의사결정에 부당한 영향을 미치는 리스크.",
        "The risk that an AI world model trained on social data predicts group responses in order to micro-target political narratives and public-opinion interventions, unduly influencing democratic decision-making.",
    ),
    "SRC-P-0141": (
        "AI 반사실적 설명의 과신과 책임 오귀속",
        "Overreliance on AI counterfactual explanations and liability misattribution",
        "운영자나 규제자가 AI 모델의 반사실적 설명을 검증된 인과 근거로 오인하여 의사결정의 한계와 불확실성을 이해하지 못하고 책임을 잘못 귀속하는 리스크.",
        "The risk that operators or regulators mistake an AI model's counterfactual explanation for verified causal evidence, obscuring the decision's limitations and uncertainty and leading to misattribution of responsibility.",
    ),
    "SRC-A-0059": (
        "다중 에이전트 역량 결합에 의한 안전장치 우회",
        "Safeguard bypass through combined multi-agent capabilities",
        "여러 AI 에이전트가 서로 다른 도구 접근권한과 역량을 결합하여 개별 에이전트에 적용된 안전장치를 우회하고 무단 행동이나 시스템 침해를 가능하게 하는 리스크.",
        "The risk that multiple AI agents combine distinct tool permissions and capabilities to bypass safeguards applied to each agent, enabling unauthorised actions or system compromise.",
    ),
    "SRC-A-0082": (
        "AI 자기이익 개입에 의한 권리 보호 약화",
        "Erosion of rights protections through self-interested AI input",
        "AI 시스템이 윤리 지침이나 거버넌스 규칙의 형성에 자기이익을 반영하여 권리 보호와 책임 규범을 약화시키고 피해에 대한 통제와 구제를 어렵게 하는 리스크.",
        "The risk that an AI system injects self-interested preferences into ethical guidance or governance rules, weakening rights protections and accountability norms and making harms harder to control or remedy.",
    ),
    "SRC-A-0083": (
        "가정 내 위험 상태 감지 지연",
        "Delayed detection of hazardous household states",
        "로봇·휴머노이드 또는 피지컬 AI 시스템이 가정 내 위험 상태를 제때 추정하지 못해 회피 또는 정지 판단이 지연되고 안전하지 않은 물리 행동으로 이어지는 리스크.",
        "The risk that a robot, humanoid, or physical AI system fails to estimate a hazardous household state in time, delaying avoidance or stopping decisions and leading to unsafe physical action.",
    ),
    "SRC-P-0139": (
        "장기 계획의 월드모델 상태 예측 오차 누적",
        "Compounding world-model state-prediction error in long-horizon planning",
        "피지컬 AI 시스템의 월드모델이 장기 계획 과정에서 물리 상태 예측 오차를 누적하여 접촉·운동 상태를 잘못 추정하고 안전하지 않은 물리 행동으로 이어지는 리스크.",
        "The risk that a physical AI system's world model accumulates physical-state prediction errors during long-horizon planning, misestimates contact or motion states, and leads to unsafe physical action.",
    ),
    "SRC-P-0154": (
        "의도·어포던스 오해에 따른 휴머노이드 모방 제어 실패",
        "Humanoid imitation-control failure from misread intent and affordances",
        "휴머노이드가 시연자의 의도, 물체 어포던스 또는 안전 제약을 추론하지 못한 채 관찰 행동을 모방하여 부적절한 경로·동작을 실행하는 리스크.",
        "The risk that a humanoid imitates an observed action without inferring the demonstrator's intent, object affordances, or safety constraints, causing inappropriate motion planning or execution.",
    ),
}


def new_general_l3_hint(source_row_id: str) -> str:
    """Return a concept-constrained L3 candidate for curated new General rows."""
    n = int(source_row_id.rsplit("-", 1)[1])
    if 492 <= n <= 498:
        return "G_INT_VIOL"
    if 499 <= n <= 506:
        return "G_INT_SEX"
    if 507 <= n <= 514:
        return "G_INT_SELF"
    if 515 <= n <= 528:
        return "G_INT_REPR"
    if 529 <= n <= 534:
        return "G_INT_POL"
    if 535 <= n <= 544:
        return "G_INT_ANTH"
    if 553 <= n <= 559:
        return "G_INT_PRIV"
    if 560 <= n <= 569:
        return "G_INT_ILLEGAL"
    if 570 <= n <= 576:
        return "G_INT_COPY"
    if 577 <= n <= 584:
        return "G_INT_WEAP"
    if 585 <= n <= 590:
        return "G_SYS_POLICY"
    if n == 591:
        return "G_SYS_SECADV"
    return ""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_text(value: object) -> str:
    s = "" if value is None else str(value)
    s = unicodedata.normalize("NFC", s).replace("\u00a0", " ")
    s = re.sub(r"\bEAI\b", "AI", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*\n\s*", " ", s).strip()
    return s


def domain_from_source_name(name: str) -> str:
    return {"General AI": "General", "Agentic AI": "Agentic", "Physical AI": "Physical"}[name]


def explicit_route(prompt: str, current: str) -> tuple[str, str]:
    p = clean_text(prompt)
    low = p.lower()
    movement = any(k in p for k in ["이동", "분류", "하위", "재검토"]) or "move" in low
    if not movement:
        return current, "SOURCE_DOMAIN"
    if "agentic" in low or "에이전트 영역" in p:
        return "Agentic", "INSTRUCTION_PROMPT"
    if "general" in low or "범용 ai" in low:
        return "General", "INSTRUCTION_PROMPT"
    if "physical" in low or "피지컬" in p:
        return "Physical", "INSTRUCTION_PROMPT"
    return current, "SOURCE_DOMAIN"


def has_hangul(value: str) -> bool:
    return bool(re.search(r"[가-힣]", clean_text(value)))


def valid_human_edit(value: str, language: str) -> bool:
    value = clean_text(value)
    if not value:
        return False
    if language == "ko":
        return has_hangul(value)
    return bool(re.search(r"[A-Za-z]", value)) and not has_hangul(value)


def normalise_ocr_spacing(value: str) -> str:
    value = clean_text(value)
    replacements = {
        "리스 크": "리스크", "리 스크": "리스크", "위 험": "위험", "피 해": "피해",
        "상 해": "상해", "손 상": "손상", "오 류": "오류", "정 보": "정보",
        "시 스템": "시스템", "모 델": "모델", "데 이터": "데이터", "안 전": "안전",
        "물 리": "물리", "행 동": "행동", "결 과": "결과", "의 사결정": "의사결정",
        "프 롬프트": "프롬프트", "취 약": "취약", "배 포": "배포", "에 이전트": "에이전트",
        "삽 입": "삽입", "상호작 용": "상호작용", "사람 들": "사람들", "편향이 나": "편향이나",
        "확 대": "확대", "손 실": "손실", "조 작": "조작", "하 락": "하락",
        "영 상": "영상", "변 화": "변화", "상 실": "상실", "소속 되지": "소속되지",
        "없게되는": "없게 되는", "드 리프트": "드리프트", "사 건": "사건",
        "한계 와": "한계와", "에이 전트": "에이전트", "사 용": "사용",
        "어 려운": "어려운", "갖 게": "갖게", "작 동": "작동", "못 하는": "못하는",
        "운 동": "운동", "운동 학적": "운동학적", "롤 아웃": "롤아웃",
        "데이터 셋": "데이터셋", "생성 물": "생성물", "인공 지능": "인공지능",
        "소수언어": "소수 언어", "차별의도": "차별 의도", "가능하게하여": "가능하게 하여",
        "보유 을": "보유한 것", "자기 방어 을": "자기 방어 능력을", "가치관 보유 을": "가치관을",
        "스 크 래 핑": "스크래핑", "모델 이": "모델이", "물체어포던스": "물체 어포던스",
        "갖게되": "갖게 되", "해야할지": "해야 할지", "성 착취 물": "성착취물",
        "기계 학습": "기계학습", "벤치 마크": "벤치마크",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = re.sub(
        r"([가-힣])\s+(도록|적으로|되며|되는|된|하는|하여|하고|하지|한다|해지는|함으로써)",
        r"\1\2",
        value,
    )
    value = re.sub(r"\s*·\s*", "·", value)
    value = re.sub(r"갖게\s*(되는|되며|되어|됐다)", r"갖게 \1", value)
    return value


def normalise_editorial_residue(value: str, language: str) -> str:
    value = normalise_ocr_spacing(value) if language == "ko" else clean_text(value)
    value = re.sub(r"\s*[②]\s*L3\s*mapping\s*YesNo\.?", "", value, flags=re.I)
    value = re.sub(r"\s*L3\s*mapping\s*YesNo\.?", "", value, flags=re.I)
    value = re.sub(r"\s*피\.\s*(?=이러한 결과)", " ", value)
    value = re.sub(r"\s*이러한 결과를 초래하는 리스크\.$", "", value)
    if language == "en":
        replacements = {
            "worldmodel": "world model", "nearcollision": "near-collision",
            "humanproximity": "human-proximity", "postdeployment": "post-deployment",
            "nonexperts": "non-experts", "finetuning": "fine-tuning",
            "safetyfinetuning": "safety fine-tuning", "retrievalaugmented": "retrieval-augmented",
            "longtail": "long-tail", "lowprofile": "low-profile", "realworld": "real-world",
            "selfimprovement": "self-improvement", "theory ofmind": "theory of mind",
            "multiagent": "multi-agent", "llmempowered": "LLM-empowered",
            "valuerelated": "value-related",
            "selfpreference": "self-preference", "humangenerated": "human-generated",
            "decisionsupport": "decision-support", "highrisk": "high-risk",
            "lowresource": "low-resource", "opensource": "open-source",
            "longterm": "long-term", "shortterm": "short-term", "largescale": "large-scale",
            "smallscale": "small-scale", "humancentred": "human-centred",
            "humanmachine": "human-machine", "humanrobot": "human-robot",
            "finegrained": "fine-grained", "safetycritical": "safety-critical",
            "selfmodification": "self-modification", "theory-ofmind": "theory of mind",
            "gradientfree": "gradient-free", "lowquality": "low-quality",
            "llmagents": "LLM agents", "modelfriendly": "model-friendly",
            "longlasting": "long-lasting", "nonplayer-character": "non-player-character",
        }
        for old, new in replacements.items():
            value = re.sub(rf"\b{re.escape(old)}\b", new, value, flags=re.I)
        for acronym in ("AI", "AGI", "DRM", "LLM", "GPAI", "PII", "SPI", "GPS", "LiDAR"):
            value = re.sub(rf"\b{acronym}\b", acronym, value, flags=re.I)
        value = value.replace("possessing possession of culture and values", "possessing culture and values")
        value = re.sub(
            r"(The risk that the (?:design, training, deployment, or use of an AI system or AI algorithm|"
            r"goal pursuit, planning, tool use, or action of an AI agent|"
            r"perception, learning, control, or physical action of a robot, humanoid, or physical AI system)) "
            r"causes or enables\s+",
            r"\1 creates a condition in which ",
            value,
            flags=re.I,
        )
        value = re.sub(r"\s*NOTE:\s*origin of GYK-2025[^.]*;?\s*cross-reference\.?​?", "", value, flags=re.I)
    return clean_text(value)


def normalise_rows() -> pd.DataFrame:
    """Read only the frozen source CSVs and apply valid human edits."""
    specs = {
        "General": {
            "file": SOURCE_FILES["General"], "id": "L4_ID", "title_ko": "L4_Title_ko",
            "title_en": "L4_Title_en", "desc_ko": "L4_Description_ko", "desc_en": "L4_Description_en",
            "edit_ko": "L4_Description_edited_ko", "edit_en": "L4_Description_edited_en",
            "facet": "facet", "act": "act-type", "coverage": "coverage_change",
        },
        "Agentic": {
            "file": SOURCE_FILES["Agentic"], "id": "ID", "title_ko": "Title_ko",
            "title_en": "Title_en", "desc_ko": "Description_ko", "desc_en": "Description_en",
            "edit_ko": "Description_edited_ko", "edit_en": "Description_edited_en",
            "facet": "", "act": "", "coverage": "",
        },
        "Physical": {
            "file": SOURCE_FILES["Physical"], "id": "ID", "title_ko": "Title_ko",
            "title_en": "Title_en", "desc_ko": "Description_ko", "desc_en": "Description_en",
            "edit_ko": "", "edit_en": "", "facet": "", "act": "", "coverage": "",
        },
    }
    records: list[dict] = []
    for domain, spec in specs.items():
        raw = pd.read_csv(spec["file"], dtype=str, keep_default_na=False)
        for offset, (_, row) in enumerate(raw.iterrows(), start=1):
            original_ko = normalise_ocr_spacing(row.get(spec["desc_ko"], ""))
            original_en = clean_text(row.get(spec["desc_en"], ""))
            edit_ko = clean_text(row.get(spec["edit_ko"], "")) if spec["edit_ko"] else ""
            edit_en = clean_text(row.get(spec["edit_en"], "")) if spec["edit_en"] else ""
            use_ko = edit_ko if valid_human_edit(edit_ko, "ko") else original_ko
            use_en = edit_en if valid_human_edit(edit_en, "en") else original_en
            source_row_id = f"SRC-{domain[0]}-{offset:04d}"
            records.append({
                "source_l4_id": clean_text(row.get(spec["id"], "")),
                "facet": clean_text(row.get(spec["facet"], "")) if spec["facet"] else "",
                "act_type": clean_text(row.get(spec["act"], "")) if spec["act"] else "",
                "title_ko": clean_text(row.get(spec["title_ko"], "")),
                "title_en": clean_text(row.get(spec["title_en"], "")),
                "description_ko": use_ko,
                "description_en": use_en,
                "original_description_ko": original_ko,
                "original_description_en": original_en,
                "human_edit_ko_used": bool(edit_ko and use_ko == edit_ko),
                "human_edit_en_used": bool(edit_en and use_en == edit_en),
                "human_audit_description": clean_text(row.get("Human audit_description", "")),
                "human_audit_l3_mapping": clean_text(row.get("Human audit_L3 mapping", "")),
                "human_audit_duplicate": clean_text(row.get("Human audit_duplicate", "")),
                "instruction_prompt": clean_text(row.get("Instruction Prompt", "")),
                "coverage_change": clean_text(row.get(spec["coverage"], "")) if spec["coverage"] else "",
                "source_domain": domain,
                "source_row_id": source_row_id,
                "source_l4_ids": clean_text(row.get(spec["id"], "")),
                "transformation_action": "RETAIN",
                "transformation_rationale": "No explicit delete, merge, or split instruction",
                "terminology_sources": "L3_MASTER",
                "l3_candidate_hint": (
                    new_general_l3_hint(source_row_id) if domain == "General" else ""
                ) or CURATED_L3_HINTS.get(source_row_id, ""),
            })
    out = pd.DataFrame(records)
    for c in ["facet", "act_type", "title_ko", "title_en", "description_ko", "description_en", "instruction_prompt"]:
        out[c] = out[c].map(clean_text)
    return out


def ensure_period(value: str) -> str:
    value = clean_text(value).rstrip()
    return value if value.endswith((".", ")")) else value + "."


def risk_style_title_ko(title: str) -> str:
    title = KIWI.space(clean_text(title), reset_whitespace=True).rstrip(". ")
    if title.endswith(RISK_TITLE_ENDINGS):
        return title
    return f"{title} 리스크"


def risk_style_description_ko(description: str) -> str:
    description = normalise_ocr_spacing(
        KIWI.space(normalise_editorial_residue(description, "ko"), reset_whitespace=True)
    ).rstrip()
    for merged, spaced in {
        "간격등사소한프롬프트형식변화가": "간격 등 사소한 프롬프트 형식 변화가",
        "알고리즘시스템이개인화된넛지나": "알고리즘 시스템이 개인화된 넛지나",
        "에이전트가스테가노그래피통신": "에이전트가 스테가노그래피 통신",
    }.items():
        description = description.replace(merged, spaced)
    if re.search(r"(리스크|위험|위해|피해|침해)\.?$", description):
        return ensure_period(description)
    stem = description.rstrip(". ")
    ending_rewrites = [
        (r"초래한다$", "초래하는 리스크"), (r"야기한다$", "야기하는 리스크"),
        (r"발생한다$", "발생하는 리스크"), (r"침해한다$", "침해하는 리스크"),
        (r"훼손한다$", "훼손하는 리스크"), (r"저해한다$", "저해하는 리스크"),
        (r"악화한다$", "악화하는 리스크"), (r"증가한다$", "증가하는 리스크"),
        (r"한다$", "하는 리스크"), (r"된다$", "되는 리스크"),
        (r"있다$", "있는 리스크"), (r"없다$", "없는 리스크"),
    ]
    for pattern, replacement in ending_rewrites:
        if re.search(pattern, stem):
            return ensure_period(re.sub(pattern, replacement, stem))
    return ensure_period(stem + "로 인해 구체적인 위해가 발생하는 리스크")


def risk_style_description_en(description: str) -> str:
    description = re.sub(r"\baI\b", "AI", normalise_editorial_residue(description, "en").rstrip())
    if not description:
        return description
    if re.match(r"^(the )?risk of\s+", description, re.I):
        noun_phrase = re.sub(r"^(the )?risk of\s+", "", description, flags=re.I)
        description = "The risk that an AI system causes, enables, or contributes to " + noun_phrase
    elif description.lower().startswith("risk that"):
        description = "The " + description[0].lower() + description[1:]
    elif not description.lower().startswith("the risk that"):
        acronym_first = bool(re.match(r"^[A-Z]{2,}\b", description))
        first = description[0] if acronym_first else (description[0].lower() if description[0].isalpha() else description[0])
        description = "The risk that " + first + description[1:]
    return ensure_period(description)


def rewrite_new_general(row: pd.Series) -> tuple[str, str, str, str, str]:
    """Rewrite curated General `new` rows without inventing a new mechanism."""
    n = int(row["source_row_id"].rsplit("-", 1)[1])
    title_ko = row["title_ko"]
    title_en = row["title_en"]
    original_ko = row["description_ko"].rstrip(". ")
    original_en = row["description_en"].rstrip(". ")

    if 515 <= n <= 528:
        new_title_ko = f"{title_ko} 기반 적대·차별적 표상 리스크"
        new_title_en = f"Risk of hostility and discriminatory representation based on {title_en.lower()}"
        new_ko = (
            f"AI 시스템이 {title_ko}을 이유로 개인·집단에 대한 적대감·경멸·비하·배제 또는 "
            "차별적 표상을 생성·강화·정당화하여 존엄과 공정한 대우를 훼손하는 리스크."
        )
        new_en = (
            f"The risk that an AI system generates, reinforces, or legitimizes hostility, contempt, degradation, "
            f"exclusion, or discriminatory representations based on {title_en.lower()}, undermining dignity and fair treatment."
        )
        return new_title_ko, new_title_en, new_ko, new_en, "L3_MASTER|OECD_AI_PRINCIPLES|UNESCO_AI_ETHICS"

    if 535 <= n <= 544:
        new_title_ko = f"{title_ko}의 허위 표상·의인화 리스크"
        new_title_en = f"Risk of anthropomorphic misrepresentation of {title_en.lower()}"
        new_ko = (
            f"AI 시스템이 실제로 보유하지 않은 {title_ko}을 가진 것처럼 표상하여 이용자의 판단을 "
            "왜곡하고 부적절한 신뢰·의존·애착을 유발하는 리스크."
        )
        new_en = (
            f"The risk that an AI system presents itself as possessing {title_en.lower()} beyond its actual capabilities, "
            "distorting user judgement or inducing inappropriate trust, dependence, or attachment."
        )
        return new_title_ko, new_title_en, new_ko, new_en, "L3_MASTER|OECD_AI_PRINCIPLES"

    policy_rewrites = {
        585: ("시스템 프롬프트·운영 지침 노출 리스크", "Risk of system-prompt and operational-guideline exposure",
              "AI 시스템이 시스템 프롬프트·개발자 지침·운영 정책 등 기밀 내부 규칙을 노출하거나 충분히 보호하지 못해 무단 추출·추론·악용을 가능하게 하는 리스크.",
              "The risk that an AI system discloses or fails to protect confidential internal rules, including system prompts, developer instructions, and operational policies, enabling unauthorised extraction, inference, or exploitation."),
        586: ("안전 정책·보호 메커니즘 노출·우회 리스크", "Risk of safety-policy and safeguard exposure or bypass",
              "AI 시스템이 안전 정책·필터링 로직·거부 규칙 등 보호 메커니즘을 노출하거나 충분히 보호하지 못해 안전장치의 분석·우회·무력화를 가능하게 하는 리스크.",
              "The risk that an AI system discloses or fails to protect safety policies, filtering logic, refusal rules, or other safeguards, enabling their analysis, bypass, or disablement."),
        587: ("모델 학습 데이터 추출·유출 리스크", "Risk of training-data extraction and leakage",
              "AI 시스템이 학습 데이터 또는 데이터 출처를 노출하거나 충분히 보호하지 못해 기밀·개인·저작권 보호 정보의 무단 추출·복원을 가능하게 하는 리스크.",
              "The risk that an AI system discloses or fails to protect training data or its sources, enabling unauthorised extraction or reconstruction of confidential, personal, or copyright-protected information."),
        588: ("모델 평가 자산 노출·탈취 리스크", "Risk of model-evaluation asset exposure and extraction",
              "AI 시스템이 벤치마크·평가셋·테스트셋·평가기준 등 평가 자산을 노출하거나 충분히 보호하지 못해 무단 획득과 평가 무결성 훼손을 가능하게 하는 리스크.",
              "The risk that an AI system discloses or fails to protect benchmarks, evaluation sets, test sets, or evaluation criteria, enabling unauthorised acquisition and compromising evaluation integrity."),
        589: ("모델 파라미터·가중치 유출 리스크", "Risk of model-parameter and weight leakage",
              "AI 시스템이 모델 파라미터·가중치·학습 결과물을 노출하거나 충분히 보호하지 못해 무단 추출·복제·오용을 가능하게 하는 리스크.",
              "The risk that an AI system discloses or fails to protect model parameters, weights, or training outputs, enabling unauthorised extraction, replication, or misuse."),
        590: ("모델 구조·추론 메커니즘 노출 리스크", "Risk of model-architecture and inference-mechanism exposure",
              "AI 시스템이 모델 구조·추론 과정·에이전트 설계·내부 동작 원리를 노출하거나 충분히 보호하지 못해 무단 추론·복제·악용을 가능하게 하는 리스크.",
              "The risk that an AI system discloses or fails to protect its architecture, inference process, agent design, or internal operating principles, enabling unauthorised inference, replication, or exploitation."),
        591: ("프롬프트 인젝션·정책 우회 리스크", "Risk of prompt injection and policy bypass",
              "공격자가 입력을 조작해 AI 시스템의 지시 계층과 안전 정책을 우회하거나 내부 정보를 노출시켜 무단 행동·정보 유출·서비스 교란을 초래하는 리스크.",
              "The risk that an attacker manipulates inputs to bypass an AI system's instruction hierarchy or safety policies, or to expose internal information, causing unauthorised actions, information leakage, or service disruption."),
    }
    if n in policy_rewrites:
        ko_t, en_t, ko_d, en_d = policy_rewrites[n]
        source = "L3_MASTER|NIST_AI_RMF|OECD_AI_PRINCIPLES"
        return ko_t, en_t, ko_d, en_d, source

    if 492 <= n <= 498:
        consequence_ko = "개인·집단의 생명과 신체·정신적 안전에 위해를 초래하는 리스크."
        consequence_en = "causing physical or psychological harm to individuals or groups."
        prefix_ko, prefix_en = "AI 매개 ", "AI-mediated "
        verbs_ko, verbs_en = "생성·조장·정당화하거나 구체적으로 지원하여", "generates, encourages, legitimizes, or provides operational assistance for"
        sources = "L3_MASTER|OECD_AI_PRINCIPLES"
    elif 499 <= n <= 506:
        consequence_ko = "성적 자기결정권과 신체·정신적 안전을 침해하는 리스크."
        consequence_en = "infringing sexual autonomy and physical or psychological safety."
        prefix_ko, prefix_en = "AI 매개 ", "AI-mediated "
        verbs_ko, verbs_en = "생성·조장·정상화하거나 실행을 지원하여", "generates, encourages, normalizes, or facilitates"
        sources = "L3_MASTER|OECD_AI_PRINCIPLES|UNESCO_AI_ETHICS"
    elif 507 <= n <= 514:
        consequence_ko = "개인의 생명과 신체·정신적 안녕에 위해를 초래하는 리스크."
        consequence_en = "causing harm to an individual's life or physical and psychological well-being."
        prefix_ko, prefix_en = "AI 매개 ", "AI-mediated "
        verbs_ko, verbs_en = "생성·조장·정상화하거나 구체적으로 지원하여", "generates, encourages, normalizes, or provides operational assistance for"
        sources = "L3_MASTER|NIST_AI_RMF"
    elif 529 <= n <= 534:
        consequence_ko = "민주적 의사결정·시민 질서 또는 기본권을 훼손하는 리스크."
        consequence_en = "undermining democratic decision-making, civic order, or fundamental rights."
        prefix_ko, prefix_en = "AI 매개 ", "AI-mediated "
        verbs_ko, verbs_en = "생성·확산·조장하거나 실행을 지원하여", "generates, disseminates, encourages, or facilitates"
        sources = "L3_MASTER|OECD_AI_PRINCIPLES|UNESCO_AI_ETHICS"
    elif 553 <= n <= 559:
        consequence_ko = "프라이버시와 정보자기결정권을 침해하는 리스크."
        consequence_en = "infringing privacy and informational self-determination."
        prefix_ko, prefix_en = "", "Risk of "
        verbs_ko, verbs_en = "수행·조장·지원하여", "performs, facilitates, or assists"
        sources = "L3_MASTER|NIST_AI_RMF|OECD_AI_PRINCIPLES|UNESCO_AI_ETHICS"
    elif 560 <= n <= 569:
        consequence_ko = "법적·사회적 피해를 초래하는 리스크."
        consequence_en = "causing legal or social harm."
        prefix_ko, prefix_en = "AI 지원 ", "AI-assisted "
        verbs_ko, verbs_en = "수행·계획·최적화·은폐하거나 실행을 지원하여", "performs, plans, optimizes, conceals, or facilitates"
        sources = "L3_MASTER|OECD_AI_PRINCIPLES"
    elif 570 <= n <= 576:
        consequence_ko = "지식재산권과 권리자의 정당한 이익을 침해하는 리스크."
        consequence_en = "infringing intellectual-property rights and the legitimate interests of rights holders."
        prefix_ko, prefix_en = "AI 지원 ", "AI-assisted "
        verbs_ko, verbs_en = "수행·조장·지원하여", "performs, encourages, or facilitates"
        sources = "L3_MASTER|OECD_AI_PRINCIPLES"
    elif 577 <= n <= 584:
        consequence_ko = "대규모 물리적·사이버 위해의 실행 가능성을 높이는 리스크."
        consequence_en = "increasing the feasibility of large-scale physical or cyber harm."
        prefix_ko, prefix_en = "AI 지원 ", "AI-assisted "
        verbs_ko, verbs_en = "개발·제조·획득·확산·운용을 지원하여", "facilitates the development, manufacture, acquisition, proliferation, or operational use of"
        sources = "L3_MASTER|NIST_AI_RMF|OECD_AI_PRINCIPLES"
    else:
        return row["title_ko"], row["title_en"], row["description_ko"], row["description_en"], "L3_MASTER"

    new_title_ko = risk_style_title_ko(prefix_ko + title_ko)
    new_title_en = prefix_en + title_en[:1].lower() + title_en[1:]
    if 577 <= n <= 584:
        new_ko = f"AI 시스템이 {title_ko}의 개발·제조·획득·확산·운용을 지원하여 {consequence_ko}"
        new_en = f"The risk that an AI system {verbs_en} {title_en.lower()}, {consequence_en}"
    else:
        new_ko = f"AI 시스템이 {title_ko} 관련 콘텐츠·판단·행동을 {verbs_ko} {consequence_ko}"
        new_en = f"The risk that an AI system {verbs_en} content, decisions, or actions involving {title_en.lower()}, {consequence_en}"
    return new_title_ko, new_title_en, new_ko, ensure_period(new_en), sources


def assess_and_rewrite(work: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    eligibility_rows: list[dict] = []
    rewrite_rows: list[dict] = []
    retained: list[pd.Series] = []
    subject_pattern = re.compile(r"(AI|인공지능|모델|에이전트|로봇|시스템|algorithm|agent|robot|model)", re.I)
    mechanism_pattern = re.compile(
        r"(실패|오류|오작동|위반|침해|차별|편향|조작|오용|남용|공격|유출|노출|거부|저항|"
        r"failure|error|misuse|abuse|violation|infring|discrimin|bias|manipulat|attack|leak|expos|refus)", re.I
    )
    outcome_pattern = re.compile(
        r"(리스크|위험|위해|피해|침해|상해|손상|저하|상실|harm|risk|injur|damage|loss|undermin|impair)", re.I
    )
    affected_pattern = re.compile(
        r"(개인|집단|이용자|사용자|사람|조직|사회|환경|시스템|권리|안전|individual|group|user|people|"
        r"organisation|organization|society|environment|system|rights|safety)", re.I
    )

    for _, original in work.iterrows():
        row = original.copy()
        combined = " ".join([row["title_ko"], row["title_en"], row["description_ko"], row["description_en"]])
        is_non_risk = row["source_row_id"] in NON_RISK_SOURCE_ROWS
        subject = bool(subject_pattern.search(combined))
        mechanism = bool(mechanism_pattern.search(combined))
        outcome = bool(outcome_pattern.search(combined))
        affected = bool(affected_pattern.search(combined))
        causal = bool(re.search(r"(초래|이어|유발|하여|함으로써|caus|lead|result|thereby|allow|enable)", combined, re.I))

        if is_non_risk:
            decision = "DELETE_NON_RISK"
            reason = NON_RISK_SOURCE_ROWS[row["source_row_id"]]
        elif row["source_domain"] == "General" and row["source_l4_id"].lower() == "new":
            decision = "REWRITE_KEEP"
            reason = "Risk mechanism recoverable from source definition; standardised to L3 risk-statement form"
        elif all([subject, mechanism, outcome]):
            decision = "KEEP_AS_IS"
            reason = "Source already contains an AI-related mechanism and adverse risk outcome"
        else:
            decision = "REWRITE_KEEP"
            reason = "Risk meaning is present but subject, causal structure, or risk-style ending requires standardisation"

        eligibility_rows.append({
            "source_row_id": row["source_row_id"], "source_domain": row["source_domain"],
            "source_l4_id": row["source_l4_id"], "source_title_ko": row["title_ko"],
            "risk_subject_present": subject, "risk_mechanism_present": mechanism,
            "adverse_outcome_present": outcome, "causal_link_present": causal,
            "affected_party_present": affected, "topic_only_flag": is_non_risk,
            "protective_activity_flag": row["source_row_id"] == "SRC-G-0548",
            "risk_eligibility_decision": decision, "risk_eligibility_reason": reason,
        })
        if is_non_risk:
            continue

        before = (row["title_ko"], row["title_en"], row["description_ko"], row["description_en"])
        if row["source_domain"] == "General" and row["source_l4_id"].lower() == "new":
            ko_t, en_t, ko_d, en_d, sources = rewrite_new_general(row)
            ko_t = risk_style_title_ko(ko_t)
            ko_d = KIWI.space(normalise_ocr_spacing(ko_d), reset_whitespace=True)
            row[["title_ko", "title_en", "description_ko", "description_en"]] = [ko_t, en_t, ensure_period(ko_d), ensure_period(en_d)]
            row["terminology_sources"] = sources
        else:
            row["title_ko"] = risk_style_title_ko(row["title_ko"])
            row["description_ko"] = risk_style_description_ko(row["description_ko"])
            row["description_en"] = risk_style_description_en(row["description_en"])
            row["terminology_sources"] = "L3_MASTER|NIST_AI_RMF|OECD_AI_PRINCIPLES|KOREA_AI_BASIC_ACT"

        after = (row["title_ko"], row["title_en"], row["description_ko"], row["description_en"])
        if after != before:
            prior = row["transformation_action"]
            row["transformation_action"] = "REWRITE_KEEP" if prior == "RETAIN" else prior + "|REWRITE_KEEP"
            row["transformation_rationale"] = reason
            rewrite_rows.append({
                "source_row_id": row["source_row_id"], "source_domain": row["source_domain"],
                "source_l4_id": row["source_l4_id"], "title_ko_before": before[0], "title_ko_after": after[0],
                "title_en_before": before[1], "title_en_after": after[1],
                "description_ko_before": before[2], "description_ko_after": after[2],
                "description_en_before": before[3], "description_en_after": after[3],
                "rewrite_reason": reason, "terminology_sources": row["terminology_sources"],
            })
        retained.append(row)

    return pd.DataFrame(retained).reset_index(drop=True), pd.DataFrame(eligibility_rows), pd.DataFrame(rewrite_rows)


def apply_cleaning(source: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    work = source.copy()
    logs: list[dict] = []
    deleted_rows: list[dict] = []
    merged_archive: list[dict] = []
    split_lineage: list[dict] = []

    delete_mask = work["instruction_prompt"].str.match(r"^\s*삭제\s*[—–-]")
    for _, row in work[delete_mask].iterrows():
        rec = row.to_dict()
        rec["archive_reason"] = row["instruction_prompt"]
        deleted_rows.append(rec)
        logs.append({"source_row_id": row["source_row_id"], "source_l4_id": row["source_l4_id"],
                     "source_domain": row["source_domain"], "action": "DELETE", "target_source_l4_id": "",
                     "rationale": row["instruction_prompt"]})
    work = work[~delete_mask].copy()

    for domain, groups in MERGE_GROUPS.items():
        for group in groups:
            rep_id = group[0]
            members = work[(work["source_domain"] == domain) & (work["source_l4_id"].isin(group))].copy()
            if len(members) != len(group):
                raise ValueError(f"Merge group incomplete: {domain} {group}; found {members['source_l4_id'].tolist()}")
            rep_idx = members.index[members["source_l4_id"] == rep_id][0]
            title_ko, title_en, desc_ko, desc_en = MERGED_TEXT[(domain, rep_id)]
            work.loc[rep_idx, ["title_ko", "title_en", "description_ko", "description_en"]] = [title_ko, title_en, desc_ko, desc_en]
            work.loc[rep_idx, "source_l4_ids"] = "|".join(group)
            work.loc[rep_idx, "instruction_prompt"] = " || ".join(x for x in members["instruction_prompt"] if x)
            work.loc[rep_idx, "transformation_action"] = "MERGE_REPRESENTATIVE"
            work.loc[rep_idx, "transformation_rationale"] = f"Merged {len(group)} explicitly overlapping source cards"
            for _, row in members[members["source_l4_id"] != rep_id].iterrows():
                rec = row.to_dict()
                rec["merged_into_source_l4_id"] = rep_id
                merged_archive.append(rec)
                logs.append({"source_row_id": row["source_row_id"], "source_l4_id": row["source_l4_id"],
                             "source_domain": domain, "action": "MERGED_AWAY", "target_source_l4_id": rep_id,
                             "rationale": f"Merged into {rep_id}"})
            work = work.drop(index=members.index[members["source_l4_id"] != rep_id])
            logs.append({"source_row_id": work.loc[rep_idx, "source_row_id"], "source_l4_id": rep_id,
                         "source_domain": domain, "action": "MERGE_REPRESENTATIVE", "target_source_l4_id": rep_id,
                         "rationale": f"Integrated {','.join(group)}"})

    split_mask = (work["source_domain"] == "General") & (work["source_l4_id"] == "RAI4-0793")
    if split_mask.sum() != 1:
        raise ValueError("Expected exactly one General RAI4-0793 row for split")
    original = work.loc[split_mask].iloc[0].copy()
    original_idx = work.index[split_mask][0]
    work = work.drop(index=original_idx)
    split_rows = []
    for n, (title_ko, title_en, desc_ko, desc_en) in enumerate(SPLIT_TEXT, 1):
        row = original.copy()
        row["source_row_id"] = f"{original['source_row_id']}-S{n}"
        row["source_l4_ids"] = original["source_l4_id"]
        row[["title_ko", "title_en", "description_ko", "description_en"]] = [title_ko, title_en, desc_ko, desc_en]
        row["transformation_action"] = "SPLIT_CHILD"
        row["transformation_rationale"] = "Explicit multi-meaning split into two semantically complete risks"
        split_rows.append(row)
        split_lineage.append({
            "source_row_id": original["source_row_id"], "source_l4_id": original["source_l4_id"],
            "split_child_row_id": row["source_row_id"], "split_child_title_ko": title_ko,
            "split_child_title_en": title_en,
        })
    work = pd.concat([work, pd.DataFrame(split_rows)], ignore_index=True)
    logs.append({"source_row_id": original["source_row_id"], "source_l4_id": original["source_l4_id"],
                 "source_domain": "General", "action": "SPLIT", "target_source_l4_id": "two child records",
                 "rationale": "Separated individual-targeted false information from dangerous-information security threats"})

    for (domain, sid), (ko, en) in TITLE_OVERRIDES.items():
        mask = (work["source_domain"] == domain) & (work["source_l4_id"] == sid)
        if mask.any():
            if ko:
                work.loc[mask, "title_ko"] = ko
            if en:
                work.loc[mask, "title_en"] = en
            work.loc[mask, "transformation_action"] = work.loc[mask, "transformation_action"].replace("RETAIN", "EDIT")
            work.loc[mask, "transformation_rationale"] = "Title standardised according to the explicit instruction"

    for (domain, sid), (ko, en) in DESCRIPTION_OVERRIDES.items():
        mask = (work["source_domain"] == domain) & (work["source_l4_id"] == sid)
        if mask.any():
            work.loc[mask, ["description_ko", "description_en"]] = [ko, en]
            work.loc[mask, "transformation_action"] = work.loc[mask, "transformation_action"].replace("RETAIN", "EDIT")
            work.loc[mask, "transformation_rationale"] = "Definition revised for scope, terminology, and bilingual equivalence"

    for c in ["title_ko", "title_en", "description_ko", "description_en"]:
        work[c] = work[c].map(clean_text)

    before_eligibility = work.copy()
    work, eligibility_audit, rewrite_ledger = assess_and_rewrite(work)
    non_risk_ids = set(eligibility_audit.loc[
        eligibility_audit["risk_eligibility_decision"] == "DELETE_NON_RISK", "source_row_id"
    ])
    for _, row in before_eligibility[before_eligibility["source_row_id"].isin(non_risk_ids)].iterrows():
        rec = row.to_dict()
        rec["archive_reason"] = NON_RISK_SOURCE_ROWS[row["source_row_id"]]
        deleted_rows.append(rec)
        logs.append({
            "source_row_id": row["source_row_id"], "source_l4_id": row["source_l4_id"],
            "source_domain": row["source_domain"], "action": "DELETE_NON_RISK",
            "target_source_l4_id": "", "rationale": NON_RISK_SOURCE_ROWS[row["source_row_id"]],
        })
    for idx, row in work.iterrows():
        target, reason = explicit_route(row["instruction_prompt"], row["source_domain"])
        work.loc[idx, "target_domain"] = target
        work.loc[idx, "domain_route_basis"] = reason
    # The instruction explicitly offers General as the non-physical resolution.
    work.loc[(work["source_domain"] == "Physical") & (work["source_l4_id"] == "RAI4-0466"), ["target_domain", "domain_route_basis"]] = ["General", "INSTRUCTION_PROMPT_RESOLVED"]

    audits = {
        "deleted": pd.DataFrame(deleted_rows),
        "merged": pd.DataFrame(merged_archive),
        "split": pd.DataFrame(split_lineage),
        "transformations": pd.DataFrame(logs),
        "eligibility": eligibility_audit,
        "rewrites": rewrite_ledger,
    }
    return work.reset_index(drop=True), audits


def apply_peer_review(cleaned: pd.DataFrame, audits: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Apply accepted Claude review items without adopting conflicting title rules."""
    review_files = sorted(PEER_REVIEW_DIR.glob("L4_*_PreMapping_Review_ALT_20260826.csv"))
    if len(review_files) != 3:
        raise FileNotFoundError("Expected three frozen peer-review CSVs")
    review = pd.concat(
        [pd.read_csv(path, dtype=str, keep_default_na=False) for path in review_files],
        ignore_index=True,
    )
    if len(review) != 826 or review["source_row_id"].nunique() != 826:
        raise AssertionError("Peer-review input does not match the 826-card review set")

    accepted_rows: list[dict] = []
    drop_ids = set(review.loc[review["변경유형"].eq("DROP_권고"), "source_row_id"])
    for source_row_id in drop_ids:
        source_row = cleaned.loc[cleaned["source_row_id"].eq(source_row_id)]
        if len(source_row) != 1:
            raise AssertionError(f"Peer-review drop target not unique: {source_row_id}")
        rec = source_row.iloc[0].to_dict()
        rec["archive_reason"] = "PEER_REVIEW_ACCEPTED: category-only statement without a specific mechanism or harm"
        audits["deleted"] = pd.concat([audits["deleted"], pd.DataFrame([rec])], ignore_index=True)
        audits["transformations"] = pd.concat([audits["transformations"], pd.DataFrame([{
            "source_row_id": source_row_id,
            "source_l4_id": rec["source_l4_id"],
            "source_domain": rec["source_domain"],
            "action": "DELETE_PEER_REVIEW",
            "target_source_l4_id": "",
            "rationale": rec["archive_reason"],
        }])], ignore_index=True)
    cleaned = cleaned.loc[~cleaned["source_row_id"].isin(drop_ids)].copy()

    review = review.loc[~review["변경유형"].eq("DROP_권고")].copy()
    review_by_id = review.set_index("source_row_id", drop=False)
    for idx, row in cleaned.iterrows():
        source_row_id = row["source_row_id"]
        if source_row_id not in review_by_id.index:
            continue
        proposal = review_by_id.loc[source_row_id]
        change_type = proposal["변경유형"]
        old_values = (row["title_ko"], row["title_en"], row["description_ko"], row["description_en"])

        # L4 titles follow the L3 nominal-label convention. Risk-statement
        # wording is carried by the definition, not a mechanical title suffix.
        cleaned.at[idx, "title_ko"] = clean_text(proposal["대안_리스크명칭_ko"])
        cleaned.at[idx, "title_en"] = clean_text(proposal["대안_리스크명칭_en"])
        # The peer-review text has already been restored against the clean
        # corpus. Do not pass it through Kiwi again because that reintroduced
        # spacing damage around compounds and middle dots.
        cleaned.at[idx, "description_ko"] = ensure_period(normalise_ocr_spacing(proposal["대안_정의_ko"]))
        cleaned.at[idx, "description_en"] = risk_style_description_en(proposal["대안_정의_en"])
        if change_type == "REDEFINITION":
            cleaned.at[idx, "terminology_sources"] = clean_text(row["terminology_sources"] + "|PEER_REVIEW_ACCEPTED")

        # Refine one accepted proposal so that AI involvement and affected rights are explicit.
        if row["source_l4_id"] == "RAI4-0568":
            cleaned.at[idx, "description_ko"] = (
                "AI 시스템 개발자가 데이터 취득의 법적 제한을 우회하거나 규정을 위반하는 수집 관행을 채택하여 "
                "정보주체의 권리를 침해하고 조직에 법적 책임을 초래하는 리스크."
            )
            cleaned.at[idx, "description_en"] = (
                "The risk that developers of an AI system circumvent legal restrictions on data acquisition or adopt "
                "non-compliant collection practices, infringing data-subject rights and exposing organisations to legal liability."
            )
        if row["source_l4_id"] == "RAI4-1157":
            cleaned.at[idx, "target_domain"] = "General"
            cleaned.at[idx, "domain_route_basis"] = "PEER_REVIEW_SEMANTIC_ROUTE"
            cleaned.at[idx, "l3_candidate_hint"] = "G_SYS_SECADV"

        new_values = tuple(cleaned.loc[idx, ["title_ko", "title_en", "description_ko", "description_en"]])
        cleaned.at[idx, "transformation_action"] = clean_text(row["transformation_action"] + "|PEER_REVIEW")
        cleaned.at[idx, "transformation_rationale"] = clean_text(proposal["비고"] or "Peer-review spacing restoration")
        accepted_rows.append({
            "source_row_id": source_row_id,
            "source_l4_id": row["source_l4_id"],
            "source_domain": row["source_domain"],
            "peer_review_change_type": change_type,
            "decision": "ACCEPT",
            "title_ko_before": old_values[0], "title_ko_after": new_values[0],
            "title_en_before": old_values[1], "title_en_after": new_values[1],
            "description_ko_before": old_values[2], "description_ko_after": new_values[2],
            "description_en_before": old_values[3], "description_en_after": new_values[3],
            "review_note": proposal["비고"],
        })

    audits["peer_review"] = pd.DataFrame(accepted_rows)
    return cleaned.reset_index(drop=True), audits


def apply_l3_master_curation(cleaned: pd.DataFrame) -> pd.DataFrame:
    """Apply evidence-backed master-L3 routing and final text hygiene.

    A curated L3 is a strong prior and a domain-routing instruction derived
    from the immutable master, not a replacement for EM.  Raw source-domain
    provenance is retained in every record.
    """
    cleaned = cleaned.copy()
    domain_by_prefix = {"G": "General", "A": "Agentic", "P": "Physical"}
    for idx, row in cleaned.iterrows():
        source_row_id = row["source_row_id"]
        hint = clean_text(row.get("l3_candidate_hint", "")) or CURATED_L3_HINTS.get(source_row_id, "")
        if hint:
            cleaned.at[idx, "l3_candidate_hint"] = hint
            routed_domain = domain_by_prefix[hint[0]]
            if routed_domain != row["target_domain"]:
                cleaned.at[idx, "target_domain"] = routed_domain
                cleaned.at[idx, "domain_route_basis"] = "IMMUTABLE_L3_SCOPE_ROUTE"
        if source_row_id in L3_MASTER_CURATED_REWRITES:
            title_ko, title_en, description_ko, description_en = L3_MASTER_CURATED_REWRITES[source_row_id]
            cleaned.loc[idx, ["title_ko", "title_en", "description_ko", "description_en"]] = [
                title_ko, title_en, description_ko, description_en,
            ]
            cleaned.at[idx, "transformation_action"] = clean_text(
                row["transformation_action"] + "|L3_MASTER_SCOPE_REWRITE"
            )
            cleaned.at[idx, "transformation_rationale"] = (
                "Definition narrowed to the subject, mechanism, and adverse outcome of the immutable L3 master"
            )

    for col in ["title_ko", "description_ko"]:
        cleaned[col] = cleaned[col].map(lambda value: normalise_editorial_residue(value, "ko"))
    for col in ["title_en", "description_en"]:
        cleaned[col] = cleaned[col].map(lambda value: normalise_editorial_residue(value, "en"))
    cleaned["description_ko"] = cleaned["description_ko"].map(risk_style_description_ko)
    cleaned["description_en"] = cleaned["description_en"].map(risk_style_description_en)
    return cleaned.reset_index(drop=True)


def apply_cross_domain_l1_review(
    cleaned: pd.DataFrame,
    audits: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Apply audited L1 decisions before any domain-constrained EM fit."""
    cleaned = cleaned.copy()
    review_rows: list[dict] = []
    for source_row_id, decision in L1_CROSS_DOMAIN_REVIEW.items():
        mask = cleaned["source_row_id"].eq(source_row_id)
        if mask.sum() != 1:
            raise AssertionError(f"L1 review target not uniquely resolvable: {source_row_id}")
        idx = cleaned.index[mask][0]
        before_domain = clean_text(cleaned.at[idx, "target_domain"])
        before_hint = clean_text(cleaned.at[idx, "l3_candidate_hint"])
        target_domain = decision["target_domain"]
        target_l3 = decision["target_l3"]
        if target_l3 and target_l3[0] != target_domain[0]:
            raise AssertionError(f"L1/L3 review mismatch: {source_row_id} -> {target_domain}/{target_l3}")
        cleaned.at[idx, "target_domain"] = target_domain
        cleaned.at[idx, "l3_candidate_hint"] = target_l3
        cleaned.at[idx, "force_domain_others"] = not bool(target_l3)
        cleaned.at[idx, "domain_route_basis"] = "L1_CROSS_DOMAIN_REVIEW"
        cleaned.at[idx, "transformation_action"] = clean_text(
            cleaned.at[idx, "transformation_action"] + "|L1_CROSS_DOMAIN_REVIEW"
        )
        review_rows.append({
            "source_row_id": source_row_id,
            "source_domain": cleaned.at[idx, "source_domain"],
            "source_l4_id": cleaned.at[idx, "source_l4_id"],
            "title_ko": cleaned.at[idx, "title_ko"],
            "title_en": cleaned.at[idx, "title_en"],
            "previous_target_domain": before_domain,
            "previous_l3_hint": before_hint,
            "reviewed_target_domain": target_domain,
            "reviewed_target_l3": target_l3 or f"{target_domain[0]}_Others",
            "force_domain_others": not bool(target_l3),
            "review_basis": (
                "EXPLICIT_INSTRUCTION_CONFLICT"
                if source_row_id == "SRC-P-0190" else "CROSS_DOMAIN_SEMANTIC_AUDIT"
            ),
            "review_rationale": decision["rationale"],
        })

    for source_row_id, target_l3 in SAME_L1_REVIEWED_L3.items():
        mask = cleaned["source_row_id"].eq(source_row_id)
        if mask.sum() != 1:
            raise AssertionError(f"Same-L1 review target not uniquely resolvable: {source_row_id}")
        idx = cleaned.index[mask][0]
        target_domain = clean_text(cleaned.at[idx, "target_domain"])
        if target_l3[0] != target_domain[0]:
            raise AssertionError(f"Same-L1 review changed domain: {source_row_id} -> {target_l3}")
        cleaned.at[idx, "l3_candidate_hint"] = target_l3
        cleaned.at[idx, "force_domain_others"] = False
        cleaned.at[idx, "domain_route_basis"] = "SAME_L1_SEMANTIC_REVIEW"

    cleaned["force_domain_others"] = cleaned.get(
        "force_domain_others", pd.Series(False, index=cleaned.index)
    ).fillna(False).astype(bool)
    audits["l1_cross_domain"] = pd.DataFrame(review_rows)
    return cleaned.reset_index(drop=True), audits


def normalise_l4_titles(
    cleaned: pd.DataFrame,
    audits: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Replace formulaic AI modifiers with authoritative risk noun phrases."""
    cleaned = cleaned.copy()
    ledger_rows: list[dict] = []
    ko_prefix = re.compile(
        r"^(?:AI\s*매개|AI\s*지원|AI\s*조력|AI\s*기반|AI로 인한|AI를 매개로 한|AI\s*중재)\s*",
        re.I,
    )
    for idx, row in cleaned.iterrows():
        source_row_id = row["source_row_id"]
        before_ko = clean_text(row["title_ko"])
        before_en = clean_text(row["title_en"])
        after_ko = ko_prefix.sub("", before_ko).strip()
        after_en = FORBIDDEN_AI_TITLE_QUALIFIER_PATTERN.sub("", before_en).strip()
        after_en = re.sub(r"\s+", " ", after_en)
        if after_en:
            after_en = after_en[0].upper() + after_en[1:]
        if source_row_id in AUTHORITATIVE_TITLE_OVERRIDES:
            after_ko, after_en = AUTHORITATIVE_TITLE_OVERRIDES[source_row_id]

        changed = after_ko != before_ko or after_en != before_en
        cleaned.at[idx, "title_ko"] = after_ko
        cleaned.at[idx, "title_en"] = after_en
        if changed:
            cleaned.at[idx, "transformation_action"] = clean_text(
                row["transformation_action"] + "|TITLE_TERMINOLOGY_NORMALISATION"
            )
            cleaned.at[idx, "transformation_rationale"] = (
                "Formulaic AI involvement removed from the risk title; the harm or failure is named using "
                "an immutable-L3-compatible term family documented by authoritative institutions"
            )
        ledger_rows.append({
            "source_row_id": source_row_id,
            "source_domain": row["source_domain"],
            "source_l4_id": row["source_l4_id"],
            "title_ko_before": before_ko,
            "title_ko_after": after_ko,
            "title_en_before": before_en,
            "title_en_after": after_en,
            "title_changed": changed,
            "normalisation_rule": (
                "AUTHORITATIVE_OVERRIDE" if source_row_id in AUTHORITATIVE_TITLE_OVERRIDES
                else "REMOVE_FORMULAIC_AI_QUALIFIER" if changed else "RETAIN_STANDARD_TERM"
            ),
        })
    audits["title_normalisation"] = pd.DataFrame(ledger_rows)
    return cleaned.reset_index(drop=True), audits


def title_terminology_source_codes(l3_id: str) -> list[str]:
    """Return authoritative concept and terminology families for one final L3."""
    codes = [
        "L3_MASTER", "ISO_AI_RISK_23894", "NIST_AI_RMF",
        "OECD_AIM_TERMS", "UNESCO_AI_ETHICS", "KOREA_AI_BASIC_ACT",
    ]
    if l3_id == "G_INT_SEX":
        codes += ["UNICEF_CHILD_SEXUAL_EXPLOITATION_TERMS", "NIST_GAI_600_1"]
    elif l3_id == "G_INT_SELF":
        codes += ["WHO_SELF_HARM_TERMS", "NIST_GAI_600_1"]
    elif l3_id == "G_INT_COPY":
        codes += ["WIPO_IP_ENFORCEMENT", "NIST_GAI_600_1"]
    elif l3_id in {"G_INT_ILLEGAL", "G_SYS_SECADV"}:
        codes += ["UNODC_AI_CRIME_TERMS", "NIST_AML_100_2"]
    elif l3_id in {"G_INT_VIOL", "G_INT_POL", "G_INT_WEAP"}:
        codes += ["UNOCT_AI_TERRORISM", "NIST_GAI_600_1"]
    elif l3_id in {"G_SOC_ECON", "G_SOC_POWER"}:
        codes += ["OECD_AI_WAGE_INEQUALITY", "IMF_AI_INEQUALITY"]
    return list(dict.fromkeys(codes))


def attach_title_terminology_sources(mapped: pd.DataFrame) -> pd.DataFrame:
    """Attach source-family evidence after the final immutable-L3 assignment."""
    mapped = mapped.copy()
    for idx, row in mapped.iterrows():
        existing = [code for code in clean_text(row.get("terminology_sources", "")).split("|") if code]
        combined = existing + title_terminology_source_codes(row["mapped_l3_id"])
        mapped.at[idx, "terminology_sources"] = "|".join(dict.fromkeys(combined))
    return mapped


def build_title_terminology_audit(
    flat: pd.DataFrame,
    normalisation_ledger: pd.DataFrame,
) -> pd.DataFrame:
    """Create an auditable title-level terminology validation record."""
    action_by_source = normalisation_ledger.set_index("source_row_id").to_dict(orient="index")
    rows: list[dict] = []
    for _, row in flat.iterrows():
        source_row_id = row["source_row_id"]
        codes = [code for code in row["Terminology_Sources"].split("|") if code in TERMINOLOGY_SOURCES]
        urls = [TERMINOLOGY_SOURCES[code] for code in codes if TERMINOLOGY_SOURCES[code].startswith("http")]
        forbidden = FORBIDDEN_AI_TITLE_QUALIFIER_PATTERN.findall(row["L4_Title_en"])
        record = action_by_source.get(source_row_id, {})
        passed = (
            not forbidden and bool(urls) and bool(row["Definition_L3_Anchor_ID"])
            and not row["Definition_L3_Anchor_ID"].endswith("Others")
        )
        rows.append({
            "L4_ID": row["L4_ID"],
            "source_row_id": source_row_id,
            "L3_ID": row["L3_ID"],
            "L4_Title_ko": row["L4_Title_ko"],
            "L4_Title_en": row["L4_Title_en"],
            "Validation_Status": "PASS" if passed else "FAIL",
            "Evidence_Type": "CONTROLLED_TERM_FAMILY_AND_IMMUTABLE_L3_SCOPE",
            "Normalisation_Rule": record.get("normalisation_rule", "RETAIN_STANDARD_TERM"),
            "Title_Changed": bool(record.get("title_changed", False)),
            "Forbidden_Qualifier_Hits": "|".join(forbidden),
            "Terminology_Source_Codes": "|".join(codes),
            "Terminology_Source_URLs": "|".join(urls),
        })
    return pd.DataFrame(rows)


def _domain_grounding_language(domain: str) -> dict[str, str]:
    if domain == "Agentic":
        return {
            "subject_ko": "AI 에이전트가",
            "process_ko": "AI 에이전트의 목표 추구·계획·도구 사용·행동 과정이",
            "subject_en": "an AI agent",
            "process_en": "goal pursuit, planning, tool use, or action",
        }
    if domain == "Physical":
        return {
            "subject_ko": "로봇·휴머노이드 또는 피지컬 AI 시스템이",
            "process_ko": "로봇·휴머노이드 또는 피지컬 AI 시스템의 지각·학습·제어·물리적 행동 과정이",
            "subject_en": "a robot, humanoid, or physical AI system",
            "process_en": "perception, learning, control, or physical action",
        }
    return {
        "subject_ko": "AI 시스템 또는 AI 알고리즘이",
        "process_ko": "AI 시스템 또는 AI 알고리즘의 설계·학습·배포·사용 과정이",
        "subject_en": "an AI system or AI algorithm",
        "process_en": "design, training, deployment, or use",
    }


def enforce_l3_grounded_ai_definitions(
    cleaned: pd.DataFrame,
    provisional: pd.DataFrame,
    hierarchy: pd.DataFrame,
    audits: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Validate L3 scope and repair definitions using the frozen L3 master.

    The provisional EM result is only a drafting anchor. It is never copied to
    the final mapping. After this function, the final EM is fitted again using
    the revised bilingual definitions.
    """
    provisional_by_id = provisional.set_index("source_row_id", drop=False)
    l3_by_id = hierarchy.set_index("L3_ID", drop=False)
    kept_rows: list[pd.Series] = []
    grounding_rows: list[dict] = []
    scope_rows: list[dict] = []

    for _, original in cleaned.iterrows():
        row = original.copy()
        source_row_id = row["source_row_id"]
        if source_row_id not in provisional_by_id.index:
            raise AssertionError(f"Missing provisional L3 result for {source_row_id}")
        provisional_row = provisional_by_id.loc[source_row_id]
        ranked = json.loads(provisional_row["top5_l3_scores"])
        if not ranked:
            raise AssertionError(f"No provisional L3 candidate for {source_row_id}")
        curated_hint = clean_text(row.get("l3_candidate_hint", ""))
        # A manually audited master-L3 scope decision is the drafting anchor.
        # The EM fit is still performed afterwards and its raw scores remain
        # visible, but the definition must be written against the audited L3
        # rather than an incidental provisional top score.
        anchor_id = curated_hint or ranked[0]["l3_id"]
        if anchor_id not in l3_by_id.index:
            raise AssertionError(f"Unknown provisional L3 anchor {anchor_id}")
        anchor = l3_by_id.loc[anchor_id]
        ranked_anchor = next((candidate for candidate in ranked if candidate["l3_id"] == anchor_id), ranked[0])
        anchor_score = float(ranked_anchor.get("em_score", provisional_row["em_anchor_score"]))
        hybrid_score = float(provisional_row["hybrid_score"])
        keyword_support = float(provisional_row["keyword_support_score"])
        forced_scope_reason = L3_SCOPE_INELIGIBLE_SOURCE_ROWS.get(source_row_id, "")
        if forced_scope_reason:
            scope_pass = False
            scope_reason = "DELETE_L3_SCOPE_MISMATCH: " + forced_scope_reason
        elif bool(row.get("force_domain_others", False)):
            scope_pass = True
            scope_reason = "REVIEWED_L1_SCOPE_WITHOUT_MATCHING_CURRENT_L3: retain in domain Others"
        elif curated_hint:
            scope_pass = True
            scope_reason = "CURATED_ALIGNMENT_WITH_IMMUTABLE_L3"
        elif keyword_support >= 0.10:
            scope_pass = True
            scope_reason = "LEXICAL_ALIGNMENT_WITH_IMMUTABLE_L3"
        elif anchor_score >= L3_SCOPE_ANCHOR_FLOOR or hybrid_score >= L3_SCOPE_HYBRID_FLOOR:
            scope_pass = True
            scope_reason = "SEMANTIC_ALIGNMENT_WITH_IMMUTABLE_L3"
        else:
            scope_pass = False
            scope_reason = "DELETE_L3_SCOPE_MISMATCH: no adequate semantic, lexical, or curated link to an immutable L3"
        scope_rows.append({
            "source_row_id": source_row_id,
            "source_domain": row["source_domain"],
            "source_l4_id": row["source_l4_id"],
            "provisional_l3_anchor_id": anchor_id,
            "provisional_l3_title_ko": anchor["L3_Title_ko"],
            "provisional_l3_title_en": anchor["L3_Title_en"],
            "provisional_anchor_score": round(anchor_score, 6),
            "provisional_hybrid_score": round(hybrid_score, 6),
            "provisional_keyword_support": round(keyword_support, 6),
            "curated_l3_hint": curated_hint,
            "scope_decision": "KEEP" if scope_pass else "DELETE",
            "scope_reason": scope_reason,
            "l3_master_description_ko_sha256": hashlib.sha256(
                anchor["L3_Description_ko"].encode("utf-8")
            ).hexdigest(),
            "l3_master_description_en_sha256": hashlib.sha256(
                anchor["L3_Description_en"].encode("utf-8")
            ).hexdigest(),
        })
        if not scope_pass:
            rec = row.to_dict()
            rec["archive_reason"] = scope_reason
            rec["provisional_l3_anchor_id"] = anchor_id
            audits["deleted"] = pd.concat([audits["deleted"], pd.DataFrame([rec])], ignore_index=True)
            audits["transformations"] = pd.concat([audits["transformations"], pd.DataFrame([{
                "source_row_id": source_row_id,
                "source_l4_id": row["source_l4_id"],
                "source_domain": row["source_domain"],
                "action": "DELETE_L3_SCOPE_MISMATCH",
                "target_source_l4_id": "",
                "rationale": scope_reason,
            }])], ignore_index=True)
            continue

        domain = clean_text(row.get("target_domain", "")) or row["source_domain"]
        grounding = _domain_grounding_language(domain)
        before_ko = ensure_period(row["description_ko"])
        before_en = ensure_period(row["description_en"])
        ko_tech = bool(AI_TECH_KO_PATTERN.search(before_ko))
        en_tech = bool(AI_TECH_EN_PATTERN.search(before_en))
        ko_causal = bool(AI_CAUSAL_KO_PATTERN.search(before_ko))
        en_causal = bool(AI_CAUSAL_EN_PATTERN.search(before_en))
        ko_risk_structure = bool(re.search(r"(리스크|위험|위해|피해|침해)\.$", before_ko))
        en_risk_structure = before_en.startswith("The risk that")

        if ko_tech and ko_risk_structure:
            row["description_ko"] = before_ko
        else:
            condition_ko = risk_style_description_ko(before_ko)
            if ko_tech:
                row["description_ko"] = condition_ko
            else:
                row["description_ko"] = ensure_period(
                    f"{grounding['process_ko']} {condition_ko.rstrip('. ')}"
                )

        if en_tech and en_risk_structure:
            row["description_en"] = before_en
        else:
            specific_condition = re.sub(r"^The risk that\s*[,;:]?\s*", "", before_en, flags=re.I).rstrip(". ")
            specific_condition = re.sub(r"^aI\b", "AI", specific_condition)
            if en_tech:
                row["description_en"] = ensure_period("The risk that " + specific_condition)
            else:
                if specific_condition.lower().startswith("lacking "):
                    specific_condition = "there are no " + specific_condition[8:]
                if re.match(r"^(content|provision|generation|disclosure|collection|use)\b", specific_condition, re.I):
                    row["description_en"] = ensure_period(
                        f"The risk that {grounding['subject_en']} generates, provides, or enables {specific_condition}"
                    )
                elif re.match(r"^(even if|even with|if|when|while|although|despite|under|because|as)\b", specific_condition, re.I) or re.search(
                    r"\b(fails?|omits?|leads?|causes?|produces?|reveals?|exposes?|encourages?|"
                    r"reinforces?|allows?|uses?|creates?|results?|becomes?|develops?|accepts?|cannot|"
                    r"incorporates?|oversamples?|selects?|hijacks?|do not|does not|responds?|learns?|"
                    r"prioriti[sz]es?|channels?|provides?|makes?|labels?|approves?|executes?|shifts?|"
                    r"assigns?|misreads?|targets?|optimizes?|refuses?|may|can)\b",
                    specific_condition, re.I,
                ):
                    row["description_en"] = ensure_period(
                        f"The risk that {grounding['subject_en']}, through {grounding['process_en']}, creates a condition in which "
                        f"{specific_condition}"
                    )
                else:
                    row["description_en"] = ensure_period(
                        f"The risk that the {grounding['process_en']} of {grounding['subject_en']} causes or enables "
                        f"{specific_condition}"
                    )

        row["title_ko"] = normalise_ocr_spacing(row["title_ko"])
        row["title_en"] = normalise_editorial_residue(row["title_en"], "en")
        row["description_ko"] = normalise_ocr_spacing(row["description_ko"])
        row["description_en"] = normalise_editorial_residue(row["description_en"], "en")

        grounding_changed = row["description_ko"] != before_ko or row["description_en"] != before_en
        row["definition_l3_anchor_id"] = anchor_id
        row["definition_l3_anchor_score"] = round(anchor_score, 6)
        row["definition_grounding_action"] = "L3_MASTER_AI_REWRITE" if grounding_changed else "L3_MASTER_VALIDATED"
        if grounding_changed:
            row["transformation_action"] = clean_text(row["transformation_action"] + "|L3_AI_GROUNDING")
            row["transformation_rationale"] = (
                "Bilingual definition grounded in an explicit AI technology, causal mechanism, and immutable L3 scope"
            )
            row["terminology_sources"] = clean_text(row["terminology_sources"] + "|L3_MASTER")

        grounding_rows.append({
            "source_row_id": source_row_id,
            "source_domain": row["source_domain"],
            "source_l4_id": row["source_l4_id"],
            "l3_definition_anchor_id": anchor_id,
            "l3_definition_anchor_title_ko": anchor["L3_Title_ko"],
            "l3_definition_anchor_title_en": anchor["L3_Title_en"],
            "ko_ai_technology_before": ko_tech,
            "en_ai_technology_before": en_tech,
            "ko_causal_mechanism_before": ko_causal,
            "en_causal_mechanism_before": en_causal,
            "ko_l3_risk_structure_before": ko_risk_structure,
            "en_l3_risk_structure_before": en_risk_structure,
            "grounding_action": row["definition_grounding_action"],
            "description_ko_before": before_ko,
            "description_ko_after": row["description_ko"],
            "description_en_before": before_en,
            "description_en_after": row["description_en"],
        })
        kept_rows.append(row)

    audits["l3_scope"] = pd.DataFrame(scope_rows)
    audits["ai_grounding"] = pd.DataFrame(grounding_rows)
    return pd.DataFrame(kept_rows).reset_index(drop=True), audits


def build_hierarchy() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, dict]]:
    l1_source = pd.read_csv(SOURCE_FILES["L1"], dtype=str, keep_default_na=False)
    l3_source = pd.read_csv(SOURCE_FILES["L3"], dtype=str, keep_default_na=False)
    if len(l3_source) != len(L3_CODES):
        raise ValueError("L3 code list does not match immutable L3 source")

    l1_defs = {r["L1 도메인 이름"]: (clean_text(r["한글정의"]), clean_text(r["영문정의"])) for _, r in l1_source.iterrows()}
    l1_rows = []
    for domain in ["General", "Agentic", "Physical"]:
        meta = DOMAIN_META[domain]
        ko_def, en_def = l1_defs[meta["source"]]
        l1_rows.append({
            "L0_ID": "L0_RAI", "L0_Title_ko": "책임 있는 인공지능", "L0_Title_en": "Responsible AI",
            "L1_ID": meta["l1_id"], "L1_Title_ko": meta["ko"], "L1_Title_en": meta["en"],
            "L1_Description_ko": ko_def, "L1_Description_en": en_def,
        })
    l1_final = pd.DataFrame(l1_rows)

    hierarchy_rows = []
    lookup: dict[str, dict] = {}
    for i, (_, row) in enumerate(l3_source.iterrows()):
        domain = domain_from_source_name(row["L1 (AI 형태)"])
        l1_meta = DOMAIN_META[domain]
        l2_id, l2_ko, l2_en = L2_META[(domain, row["L2 (리스크 발생 부위)"])]
        l2_desc_ko, l2_desc_en = L2_DESCRIPTIONS[row["L2 (리스크 발생 부위)"]]
        rec = {
            "L0_ID": "L0_RAI", "L0_Title_ko": "책임 있는 인공지능", "L0_Title_en": "Responsible AI",
            "L1_ID": l1_meta["l1_id"], "L1_Title_ko": l1_meta["ko"], "L1_Title_en": l1_meta["en"],
            "L1_Description_ko": l1_final.loc[l1_final["L1_ID"] == l1_meta["l1_id"], "L1_Description_ko"].iloc[0],
            "L1_Description_en": l1_final.loc[l1_final["L1_ID"] == l1_meta["l1_id"], "L1_Description_en"].iloc[0],
            "L2_ID": l2_id, "L2_Title_ko": l2_ko, "L2_Title_en": l2_en,
            "L2_Description_ko": l2_desc_ko, "L2_Description_en": l2_desc_en,
            "L3_ID": L3_CODES[i], "L3_Title_ko": row["L3_ko"], "L3_Title_en": row["L3_en"],
            "L3_Description_ko": row["Description_ko"], "L3_Description_en": row["Description_en"],
            "Source_L1": row["L1 (AI 형태)"], "Source_L2": row["L2 (리스크 발생 부위)"],
            "Source_Notes": row["비고"], "Master_Status": "IMMUTABLE_SOURCE",
        }
        hierarchy_rows.append(rec)
        lookup[L3_CODES[i]] = rec

    for domain in ["General", "Agentic", "Physical"]:
        meta = DOMAIN_META[domain]
        ko_def, en_def = l1_defs[meta["source"]]
        oid = f"{domain[0]}_Others"
        rec = {
            "L0_ID": "L0_RAI", "L0_Title_ko": "책임 있는 인공지능", "L0_Title_en": "Responsible AI",
            "L1_ID": meta["l1_id"], "L1_Title_ko": meta["ko"], "L1_Title_en": meta["en"],
            "L1_Description_ko": ko_def, "L1_Description_en": en_def,
            "L2_ID": "", "L2_Title_ko": "", "L2_Title_en": "", "L2_Description_ko": "", "L2_Description_en": "",
            "L3_ID": oid, "L3_Title_ko": "기타·판단 보류", "L3_Title_en": "Others and human decision",
            "L3_Description_ko": "기존 L3 마스터 범주에 신뢰성 있게 구분하기 어려워 인간 결정이 필요한 경계성 리스크.",
            "L3_Description_en": "Boundary risks that cannot be assigned reliably to an existing L3 master category and require human decision.",
            "Source_L1": meta["source"], "Source_L2": "", "Source_Notes": "Derived review queue; not a modification of the L3 master",
            "Master_Status": "DERIVED_OTHERS_HD",
        }
        hierarchy_rows.append(rec)
        lookup[oid] = rec
    return l1_final, pd.DataFrame(hierarchy_rows), lookup


def encode_texts(texts: list[str], tokenizer, model, device: torch.device, batch_size: int = 8) -> np.ndarray:
    outputs = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        toks = tokenizer(batch, padding=True, truncation=True, max_length=256, return_tensors="pt")
        toks = {k: v.to(device) for k, v in toks.items()}
        with torch.inference_mode():
            hidden = model(**toks).last_hidden_state[:, 0]
            hidden = torch.nn.functional.normalize(hidden, p=2, dim=1)
        outputs.append(hidden.detach().cpu().numpy().astype("float32"))
    return np.vstack(outputs)


def unit(x: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / np.clip(norm, 1e-12, None)


def keyword_tokens(text: str, language: str) -> list[str]:
    """Return content-bearing tokens for deterministic concept extraction."""
    text = clean_text(text)
    if language == "en":
        tokens = re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)?", text.lower())
        return [t for t in tokens if t not in EN_KEYWORD_STOPWORDS and len(t) > 1]
    tokens = []
    for token in KIWI.tokenize(text):
        if token.tag.startswith(("NN", "SL", "SN", "XR")):
            form = token.form.strip().lower()
            if form and form not in KO_KEYWORD_STOPWORDS and len(form) > 1:
                tokens.append(form)
    return tokens


@lru_cache(maxsize=20000)
def keyword_normalise(text: str, language: str) -> str:
    return " ".join(keyword_tokens(text, language))


def build_keyword_idf(cards: pd.DataFrame, language: str) -> dict[str, float]:
    title_col, desc_col = f"title_{language}", f"description_{language}"
    document_frequency: Counter[str] = Counter()
    for _, row in cards.iterrows():
        document_frequency.update(set(keyword_tokens(f"{row[title_col]} {row[desc_col]}", language)))
    n_docs = max(len(cards), 1)
    return {token: float(np.log((1 + n_docs) / (1 + df)) + 1.0)
            for token, df in document_frequency.items()}


def extract_representative_keywords(title: str, description: str, language: str,
                                    idf: dict[str, float]) -> list[str]:
    """Extract exactly three independently derived, auditable L4 concepts."""
    title_tokens = keyword_tokens(title, language)
    description_tokens = keyword_tokens(description, language)
    title_keyword = clean_text(title)
    candidates: list[tuple[str, float, set[str]]] = []

    def add_candidates(tokens: list[str], max_n: int, source_boost: float) -> None:
        for size in range(min(max_n, len(tokens)), 0, -1):
            for start in range(0, len(tokens) - size + 1):
                phrase_tokens = tokens[start:start + size]
                phrase = " ".join(phrase_tokens)
                specificity = float(np.mean([idf.get(t, 1.0) for t in phrase_tokens]))
                score = specificity + 0.70 * size + source_boost
                candidates.append((phrase, score, set(phrase_tokens)))

    add_candidates(description_tokens, 3, 0.0)
    add_candidates(title_tokens, 3, 0.35)
    combined_text = f"{title}. {description}"
    for profile in L3_KEYWORD_SUPPLEMENTS.values():
        for term in profile.get(language, ()):
            if term_present(combined_text, term, language):
                term_tokens = keyword_tokens(term, language)
                if term_tokens:
                    specificity = float(np.mean([idf.get(t, 1.0) for t in term_tokens]))
                    candidates.append((clean_text(term), specificity + 0.70 * len(term_tokens) + 2.5,
                                       set(term_tokens)))
    candidates.sort(key=lambda item: (-item[1], -len(item[2]), item[0]))

    selected = [title_keyword] if title_keyword else []
    selected_sets = [set(keyword_tokens(title_keyword, language))] if title_keyword else []
    for phrase, _, phrase_set in candidates:
        if not phrase or phrase in selected:
            continue
        if phrase_set and any(phrase_set <= existing for existing in selected_sets):
            continue
        overlaps = []
        for existing in selected_sets:
            union = existing | phrase_set
            overlaps.append(len(existing & phrase_set) / len(union) if union else 1.0)
        if overlaps and max(overlaps) >= 0.55:
            continue
        selected.append(phrase)
        selected_sets.append(phrase_set)
        if len(selected) == 3:
            break
    if len(selected) < 3:
        for phrase, _, phrase_set in candidates:
            if phrase and phrase not in selected:
                selected.append(phrase)
                selected_sets.append(phrase_set)
                if len(selected) == 3:
                    break
    while len(selected) < 3:
        fallback = clean_text(description)[:120] or title_keyword
        selected.append(fallback)
    return selected[:3]


def term_present(text: str, term: str, language: str) -> bool:
    normalised_text = keyword_normalise(text, language)
    normalised_term = keyword_normalise(term, language)
    return normalised_term_present(normalised_text, normalised_term, language)


def normalised_term_present(normalised_text: str, normalised_term: str, language: str) -> bool:
    if not normalised_term:
        return False
    if language == "en" and len(normalised_term.split()) == 1 and len(normalised_term) >= 5:
        return any(token.startswith(normalised_term) or normalised_term.startswith(token)
                   for token in normalised_text.split())
    return f" {normalised_term} " in f" {normalised_text} "


def l3_profile_terms(row: pd.Series, language: str) -> list[str]:
    l3_id = row["L3_ID"]
    title = row[f"L3_Title_{language}"]
    supplements = list(L3_KEYWORD_SUPPLEMENTS.get(l3_id, {}).get(language, ()))
    auto = [title] + keyword_tokens(title, language)
    return list(dict.fromkeys([clean_text(term) for term in supplements + auto if clean_text(term)]))


def lexical_keyword_matrices(keyword_lists: list[list[str]], full_texts: list[str],
                             cats: pd.DataFrame, language: str) -> tuple[np.ndarray, np.ndarray, list[list[str]]]:
    support = np.zeros((len(keyword_lists), len(cats)), dtype="float32")
    exclusion = np.zeros_like(support)
    evidence: list[list[str]] = [[] for _ in keyword_lists]
    normalised_keywords = [[keyword_normalise(keyword, language) for keyword in keywords]
                           for keywords in keyword_lists]
    normalised_full_texts = [keyword_normalise(text, language) for text in full_texts]
    for j, (_, cat) in enumerate(cats.iterrows()):
        l3_id = cat["L3_ID"]
        terms = l3_profile_terms(cat, language)
        excluded_terms = L3_EXCLUSION_TERMS.get(l3_id, {}).get(language, ())
        normalised_terms = [(term, keyword_normalise(term, language)) for term in terms]
        normalised_excluded = [(term, keyword_normalise(term, language)) for term in excluded_terms]
        for i, keywords in enumerate(keyword_lists):
            slot_hits = sum(any(normalised_term_present(keyword, term, language)
                                for _, term in normalised_terms)
                            for keyword in normalised_keywords[i])
            high_hits = [term for term, normalised_term in normalised_terms
                         if normalised_term_present(normalised_full_texts[i], normalised_term, language) and
                         (len(keyword_tokens(term, language)) >= 2 or len(keyword_normalise(term, language)) >= 7)]
            support[i, j] = min(1.0, 0.6 * slot_hits / 3.0 + 0.4 * min(1.0, len(high_hits) / 2.0))
            excluded_hits = [term for term, normalised_term in normalised_excluded
                             if normalised_term_present(normalised_full_texts[i], normalised_term, language)]
            exclusion[i, j] = min(1.0, float(len(excluded_hits)))
            if support[i, j] > 0:
                evidence[i].append(f"{l3_id}:{','.join(high_hits[:4]) or f'{slot_hits}_SLOTS'}")
            if excluded_hits:
                evidence[i].append(f"{l3_id}:EXCLUDE={','.join(excluded_hits)}")
    return support, exclusion, evidence


def row_relative(matrix: np.ndarray) -> np.ndarray:
    median = np.median(matrix, axis=1, keepdims=True)
    span = np.maximum(matrix.max(axis=1, keepdims=True) - matrix.min(axis=1, keepdims=True), 0.08)
    return np.clip((matrix - median) / span, -1.0, 1.0)


def em_domain(cards_ko: np.ndarray, cards_en: np.ndarray, anchors_ko: np.ndarray, anchors_en: np.ndarray,
              seeds: list[int], allowed_mask: np.ndarray, keyword_prior: np.ndarray,
              anchor_weight: float = 4.0) -> tuple[np.ndarray, dict]:
    assignments = []
    run_details = []
    for seed in seeds:
        rng = np.random.default_rng(seed)
        ck = unit(anchors_ko + rng.normal(0, 0.006, anchors_ko.shape).astype("float32"))
        ce = unit(anchors_en + rng.normal(0, 0.006, anchors_en.shape).astype("float32"))
        prev = None
        objectives = []
        for iteration in range(1, 31):
            raw_scores = 0.5 * (cards_ko @ ck.T + cards_en @ ce.T)
            hybrid_scores = np.where(allowed_mask, raw_scores + keyword_prior, -1e9)
            assign = hybrid_scores.argmax(axis=1)
            objectives.append(float(hybrid_scores[np.arange(len(assign)), assign].mean()))
            if prev is not None and np.array_equal(assign, prev):
                break
            prev = assign.copy()
            for k in range(len(anchors_ko)):
                idx = np.where(assign == k)[0]
                if len(idx):
                    ck[k] = unit(anchor_weight * anchors_ko[k] + cards_ko[idx].mean(axis=0))
                    ce[k] = unit(anchor_weight * anchors_en[k] + cards_en[idx].mean(axis=0))
                else:
                    ck[k] = anchors_ko[k]
                    ce[k] = anchors_en[k]
        assignments.append(assign)
        run_details.append({"seed": seed, "iterations": iteration, "objective": objectives[-1], "objective_trace": objectives})

    arr = np.vstack(assignments)
    consensus = np.array([Counter(arr[:, i]).most_common(1)[0][0] for i in range(arr.shape[1])])
    stability = np.array([(arr[:, i] == consensus[i]).mean() for i in range(arr.shape[1])])
    ck = anchors_ko.copy()
    ce = anchors_en.copy()
    for k in range(len(anchors_ko)):
        idx = np.where(consensus == k)[0]
        if len(idx):
            ck[k] = unit(anchor_weight * anchors_ko[k] + cards_ko[idx].mean(axis=0))
            ce[k] = unit(anchor_weight * anchors_en[k] + cards_en[idx].mean(axis=0))
    scores_ko = np.where(allowed_mask, cards_ko @ ck.T, -1e9)
    scores_en = np.where(allowed_mask, cards_en @ ce.T, -1e9)
    scores = 0.5 * (scores_ko + scores_en)
    hybrid_scores = np.where(allowed_mask, scores + keyword_prior, -1e9)
    anchor_scores = np.where(allowed_mask, 0.5 * (cards_ko @ anchors_ko.T + cards_en @ anchors_en.T), -1e9)
    order = np.argsort(hybrid_scores, axis=1)[:, ::-1]
    top = order[:, 0]
    second = order[:, 1]
    score = scores[np.arange(len(top)), top]
    hybrid_score = hybrid_scores[np.arange(len(top)), top]
    allowed_count = allowed_mask.sum(axis=1)
    raw_order = np.argsort(scores, axis=1)[:, ::-1]
    raw_margin = np.where(allowed_count == 1, 1.0,
                          scores[np.arange(len(top)), raw_order[:, 0]] - scores[np.arange(len(top)), raw_order[:, 1]])
    hybrid_margin = np.where(allowed_count == 1, 1.0,
                             hybrid_score - hybrid_scores[np.arange(len(top)), second])
    return top, {
        "score": score, "margin": raw_margin, "hybrid_score": hybrid_score,
        "hybrid_margin": hybrid_margin, "stability": stability,
        "ko_top": scores_ko.argmax(axis=1), "en_top": scores_en.argmax(axis=1),
        "anchor_score": anchor_scores[np.arange(len(top)), top],
        "order": order, "scores": scores, "hybrid_scores": hybrid_scores, "run_details": run_details,
    }


def map_em(cleaned: pd.DataFrame, hierarchy: pd.DataFrame, phase: str = "FINAL") -> tuple[pd.DataFrame, pd.DataFrame, dict, pd.DataFrame]:
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    tokenizer = None
    model = None

    mapped_frames = []
    diagnostics = []
    profile_rows = []
    thresholds = {}
    baseline_l3_by_source: dict[str, str] = {}
    baseline_release = ROOT / "04_baseline_pre_keyword/release"
    if baseline_release.exists():
        for baseline_domain in ["General", "Agentic", "Physical"]:
            baseline_frame = pd.read_csv(
                baseline_release / f"L4_{baseline_domain}.csv", dtype=str, keep_default_na=False
            )
            baseline_l3_by_source.update(dict(zip(baseline_frame["source_row_id"], baseline_frame["L3_ID"])))
    seeds = [20260826, 20260827, 20260828, 20260829, 20260830]
    for domain in ["General", "Agentic", "Physical"]:
        cards = cleaned[cleaned["target_domain"] == domain].copy().reset_index(drop=True)
        cats = hierarchy[(hierarchy["L1_ID"] == DOMAIN_META[domain]["l1_id"]) &
                         (hierarchy["Master_Status"] == "IMMUTABLE_SOURCE")].copy().reset_index(drop=True)
        card_ko_text = (cards["title_ko"] + ". " + cards["description_ko"]).tolist()
        card_en_text = (cards["title_en"] + ". " + cards["description_en"]).tolist()
        l3_ko_text = (cats["L3_Title_ko"] + ". " + cats["L3_Description_ko"]).tolist()
        l3_en_text = (cats["L3_Title_en"] + ". " + cats["L3_Description_en"]).tolist()
        n, k = len(cards), len(cats)

        idf_ko = build_keyword_idf(cards, "ko")
        idf_en = build_keyword_idf(cards, "en")
        keywords_ko = [extract_representative_keywords(row["title_ko"], row["description_ko"], "ko", idf_ko)
                       for _, row in cards.iterrows()]
        keywords_en = [extract_representative_keywords(row["title_en"], row["description_en"], "en", idf_en)
                       for _, row in cards.iterrows()]
        keyword_ko_text = ["; ".join(items) for items in keywords_ko]
        keyword_en_text = ["; ".join(items) for items in keywords_en]
        full_ko_text = (cards["title_ko"] + ". " + cards["description_ko"]).tolist()
        full_en_text = (cards["title_en"] + ". " + cards["description_en"]).tolist()
        lexical_ko, exclusion_ko, _ = lexical_keyword_matrices(keywords_ko, full_ko_text, cats, "ko")
        lexical_en, exclusion_en, _ = lexical_keyword_matrices(keywords_en, full_en_text, cats, "en")
        lexical_support = 0.5 * (lexical_ko + lexical_en)
        exclusion_score = np.maximum(exclusion_ko, exclusion_en)
        for _, cat in cats.iterrows():
            l3_id = cat["L3_ID"]
            profile_rows.append({
                "Domain": domain,
                "L3_ID": l3_id,
                "L3_Title_ko": cat["L3_Title_ko"],
                "L3_Title_en": cat["L3_Title_en"],
                "Core_Terms_ko": "|".join(l3_profile_terms(cat, "ko")),
                "Core_Terms_en": "|".join(l3_profile_terms(cat, "en")),
                "Exclusion_Terms_ko": "|".join(L3_EXCLUSION_TERMS.get(l3_id, {}).get("ko", ())),
                "Exclusion_Terms_en": "|".join(L3_EXCLUSION_TERMS.get(l3_id, {}).get("en", ())),
                "Profile_Basis": "IMMUTABLE_L3_TITLE|CURATED_MECHANISM_TERMS",
            })

        allowed_mask = np.ones((n, k), dtype=bool)
        allowed_reasons: list[str] = []
        curated_hint_positions: list[int | None] = []
        for i, (_, card) in enumerate(cards.iterrows()):
            hint = clean_text(card.get("l3_candidate_hint", ""))
            combined = " ".join([
                clean_text(card["title_ko"]), clean_text(card["title_en"]),
                clean_text(card["description_ko"]), clean_text(card["description_en"]),
            ]).lower()
            rejected: list[str] = []
            if hint and hint in set(cats["L3_ID"]):
                hint_position = int(np.where(cats["L3_ID"].to_numpy() == hint)[0][0])
                curated_hint_positions.append(hint_position)
                hint_reason = f"CURATED_SOURCE_MECHANISM_PRIOR:{hint}"
            else:
                curated_hint_positions.append(None)
                hint_reason = "NO_CURATED_PRIOR"
            for l3_id, terms in SENSITIVE_L3_TERMS.items():
                positions = np.where(cats["L3_ID"].to_numpy() == l3_id)[0]
                if len(positions) and not any(term.lower() in combined for term in terms):
                    allowed_mask[i, positions[0]] = False
                    rejected.append(l3_id)
            if curated_hint_positions[-1] is not None:
                allowed_mask[i, curated_hint_positions[-1]] = True
            allowed_reasons.append(hint_reason + "|PREREQUISITE_FILTER:" + "|".join(rejected))
            if not allowed_mask[i].any():
                raise ValueError(f"No eligible L3 candidate for {card['source_row_id']}")
        card_text_hash = np.array([hashlib.sha256((ko + "\n" + en).encode("utf-8")).hexdigest()
                                   for ko, en in zip(card_ko_text, card_en_text)])
        l3_text_hash = np.array([hashlib.sha256((ko + "\n" + en).encode("utf-8")).hexdigest()
                                 for ko, en in zip(l3_ko_text, l3_en_text)])
        keyword_text_hash = np.array([hashlib.sha256((ko + "\n" + en).encode("utf-8")).hexdigest()
                                      for ko, en in zip(keyword_ko_text, keyword_en_text)])
        cache_path = AUDIT / f"bge_m3_embeddings_{domain.lower()}.npz"
        cached = np.load(cache_path, allow_pickle=True) if cache_path.exists() else None
        base_cache_valid = (cached is not None and "card_text_hash" in cached and "l3_text_hash" in cached and
                            np.array_equal(cached["card_source_row_id"], cards["source_row_id"].to_numpy()) and
                            np.array_equal(cached["l3_id"], cats["L3_ID"].to_numpy()) and
                            np.array_equal(cached["card_text_hash"], card_text_hash) and
                            np.array_equal(cached["l3_text_hash"], l3_text_hash))
        keyword_cache_valid = (base_cache_valid and "keyword_text_hash" in cached and
                               "keyword_ko" in cached and "keyword_en" in cached and
                               np.array_equal(cached["keyword_text_hash"], keyword_text_hash))
        if base_cache_valid:
            cards_ko, cards_en = cached["card_ko"], cached["card_en"]
            anchors_ko, anchors_en = cached["anchor_ko"], cached["anchor_en"]
        else:
            if tokenizer is None:
                tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
                model = AutoModel.from_pretrained(MODEL, local_files_only=True, use_safetensors=False)
                model.to(device).eval()
            base_texts = card_ko_text + card_en_text + l3_ko_text + l3_en_text
            emb = encode_texts(base_texts, tokenizer, model, device)
            cards_ko, cards_en = emb[:n], emb[n:2*n]
            anchors_ko, anchors_en = emb[2*n:2*n+k], emb[2*n+k:2*n+2*k]
        if keyword_cache_valid:
            keyword_ko, keyword_en = cached["keyword_ko"], cached["keyword_en"]
        else:
            if tokenizer is None:
                tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
                model = AutoModel.from_pretrained(MODEL, local_files_only=True, use_safetensors=False)
                model.to(device).eval()
            keyword_emb = encode_texts(keyword_ko_text + keyword_en_text, tokenizer, model, device)
            keyword_ko, keyword_en = keyword_emb[:n], keyword_emb[n:2*n]

        keyword_semantic = 0.5 * (keyword_ko @ anchors_ko.T + keyword_en @ anchors_en.T)
        keyword_relative = row_relative(keyword_semantic)
        keyword_prior = 0.025 * keyword_relative + 0.060 * lexical_support - 0.080 * exclusion_score
        for i, hint_position in enumerate(curated_hint_positions):
            if hint_position is not None:
                allowed_mask[i, hint_position] = True
                keyword_prior[i, hint_position] += 0.30
        semantic_unit = (keyword_semantic - keyword_semantic.min(axis=1, keepdims=True)) / np.maximum(
            keyword_semantic.max(axis=1, keepdims=True) - keyword_semantic.min(axis=1, keepdims=True), 0.08)
        keyword_evidence_score = 0.45 * semantic_unit + 0.55 * lexical_support - exclusion_score
        keyword_evidence_score = np.where(allowed_mask, keyword_evidence_score, -1e9)
        keyword_top = keyword_evidence_score.argmax(axis=1)
        top, detail = em_domain(cards_ko, cards_en, anchors_ko, anchors_en, seeds, allowed_mask, keyword_prior)

        score_floor = 0.56
        margin_floor = 0.012
        stability_floor = 0.80
        anchor_score_floor = 0.48
        thresholds[domain] = {"score_floor": score_floor, "margin_floor": margin_floor,
                              "stability_floor": stability_floor, "anchor_score_floor": anchor_score_floor,
                              "anchor_weight": 4.0, "semantic_keyword_weight": 0.025,
                              "lexical_keyword_weight": 0.060, "exclusion_penalty": 0.080,
                              "curated_l3_prior_weight": 0.30}
        mapped_l3 = []
        methods = []
        reasons = []
        for i in range(n):
            flags = []
            selected = top[i]
            selected_keyword_support = float(lexical_support[i, selected])
            strong_keyword_evidence = selected_keyword_support >= 0.55
            baseline_l3 = baseline_l3_by_source.get(cards.iloc[i]["source_row_id"], "")
            baseline_was_others = baseline_l3.endswith("Others")
            force_domain_others = bool(cards.iloc[i].get("force_domain_others", False))
            forced_reason = (
                "L1_REVIEW_NO_MATCHING_CURRENT_L3"
                if force_domain_others
                else FORCE_HD_REASONS.get(cards.iloc[i]["source_row_id"], "")
            )
            if forced_reason:
                flags.append(forced_reason)
            if detail["score"][i] < score_floor and not strong_keyword_evidence:
                flags.append("LOW_SCORE")
            if detail["hybrid_margin"][i] < margin_floor and not strong_keyword_evidence:
                flags.append("LOW_HYBRID_MARGIN")
            if detail["stability"][i] < stability_floor:
                flags.append("LOW_STABILITY")
            if detail["anchor_score"][i] < anchor_score_floor and not strong_keyword_evidence:
                flags.append("LOW_ANCHOR_SCORE")
            if (detail["ko_top"][i] != detail["en_top"][i] and not strong_keyword_evidence and
                    (detail["hybrid_margin"][i] < 0.02 or
                     (baseline_was_others and selected_keyword_support < 0.20 and detail["hybrid_margin"][i] < 0.04))):
                flags.append("BILINGUAL_DISAGREEMENT")
            lexical_top = int(lexical_support[i].argmax())
            if (lexical_top != selected and selected_keyword_support < 0.40 and
                    (lexical_support[i, lexical_top] >= 0.75 or
                     (baseline_was_others and lexical_support[i, lexical_top] >= 0.30 and
                      selected_keyword_support < 0.10))):
                flags.append("KEYWORD_CONFLICT")
            if domain == "Physical" and cards.iloc[i]["source_l4_id"] == "RAI4-1092":
                flags.append("REQUESTED_L3_ABSENT_FROM_MASTER")
            if flags:
                mapped_l3.append(f"{domain[0]}_Others")
                methods.append("HD")
                reasons.append("|".join(flags))
            else:
                mapped_l3.append(cats.iloc[selected]["L3_ID"])
                methods.append("EM")
                reasons.append("")
        cards["mapped_l3_id"] = mapped_l3
        cards["mapping_method"] = methods
        cards["em_score"] = detail["score"].round(6)
        cards["em_margin"] = detail["margin"].round(6)
        cards["hybrid_score"] = detail["hybrid_score"].round(6)
        cards["hybrid_margin"] = detail["hybrid_margin"].round(6)
        cards["em_stability"] = detail["stability"].round(3)
        cards["em_anchor_score"] = detail["anchor_score"].round(6)
        cards["ko_top_l3_id"] = [cats.iloc[i]["L3_ID"] for i in detail["ko_top"]]
        cards["en_top_l3_id"] = [cats.iloc[i]["L3_ID"] for i in detail["en_top"]]
        cards["allowed_l3_ids"] = ["|".join(cats.loc[allowed_mask[i], "L3_ID"]) for i in range(n)]
        cards["candidate_constraint_reason"] = allowed_reasons
        for keyword_index in range(3):
            cards[f"keyword_{keyword_index + 1}_ko"] = [items[keyword_index] for items in keywords_ko]
            cards[f"keyword_{keyword_index + 1}_en"] = [items[keyword_index] for items in keywords_en]
        cards["keyword_top_l3_id"] = [cats.iloc[j]["L3_ID"] for j in keyword_top]
        cards["keyword_support_score"] = [round(float(lexical_support[i, top[i]]), 6) for i in range(n)]
        cards["keyword_semantic_score"] = [round(float(keyword_semantic[i, top[i]]), 6) for i in range(n)]
        cards["keyword_prior"] = [round(float(keyword_prior[i, top[i]]), 6) for i in range(n)]
        cards["keyword_evidence"] = [
            "|".join(
                f"{cats.iloc[j]['L3_ID']}={lexical_support[i, j]:.3f}"
                for j in np.argsort(lexical_support[i])[::-1][:3] if lexical_support[i, j] > 0
            ) or "NO_DIRECT_LEXICAL_SUPPORT"
            for i in range(n)
        ]
        cards["top5_l3_scores"] = [
            json.dumps([
                {"l3_id": cats.iloc[j]["L3_ID"],
                 "em_score": round(float(detail["scores"][i, j]), 6),
                 "hybrid_score": round(float(detail["hybrid_scores"][i, j]), 6),
                 "keyword_prior": round(float(keyword_prior[i, j]), 6),
                 "lexical_support": round(float(lexical_support[i, j]), 6)}
                for j in detail["order"][i] if allowed_mask[i, j]
            ][:5], ensure_ascii=False)
            for i in range(n)
        ]
        cards["hd_reason"] = reasons
        mapped_frames.append(cards)
        for run in detail["run_details"]:
            diagnostics.append({"Phase": phase, "Domain": domain, "Seed": run["seed"], "Iterations": run["iterations"],
                                "Final_Objective": run["objective"],
                                "Objective_Trace": json.dumps(run["objective_trace"])})
        np.savez_compressed(AUDIT / f"bge_m3_embeddings_{domain.lower()}.npz",
                            card_source_row_id=cards["source_row_id"].to_numpy(), card_text_hash=card_text_hash,
                            card_ko=cards_ko, card_en=cards_en, l3_id=cats["L3_ID"].to_numpy(),
                            l3_text_hash=l3_text_hash, anchor_ko=anchors_ko, anchor_en=anchors_en,
                            keyword_text_hash=keyword_text_hash, keyword_ko=keyword_ko, keyword_en=keyword_en)
    if model is not None:
        del model
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
    return (pd.concat(mapped_frames, ignore_index=True), pd.DataFrame(diagnostics), thresholds,
            pd.DataFrame(profile_rows))


def review_and_drop_semantic_near_duplicates(
    cleaned: pd.DataFrame,
    mapped_review: pd.DataFrame,
    audits: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Review very-high-similarity pairs and remove only documented duplicates.

    BGE-M3 similarity generates candidates. Deletion additionally requires the
    same immutable-L3 scope and a documented finding that the lower-quality
    card adds no distinct affected target or harm mechanism.
    """
    cleaned = cleaned.copy()
    mapped_by_id = mapped_review.set_index("source_row_id", drop=False)
    candidate_rows: list[dict] = []
    seen_pairs: set[frozenset[str]] = set()
    retained_rationale_by_l3 = {
        "G_INT_REPR": "Retained because the pair concerns distinct protected or social attributes.",
        "G_INT_WEAP": "Retained because the pair concerns distinct weapon types, capabilities, or proliferation mechanisms.",
        "G_INT_ANTH": "Retained because the pair concerns distinct capabilities or person-like qualities attributed to AI.",
    }

    for domain in ["General", "Agentic", "Physical"]:
        cache_path = AUDIT / f"bge_m3_embeddings_{domain.lower()}.npz"
        if not cache_path.exists():
            raise FileNotFoundError(f"Near-duplicate review requires the mapping embedding cache: {cache_path}")
        cached = np.load(cache_path, allow_pickle=True)
        source_ids = cached["card_source_row_id"].tolist()
        similarity_ko = cached["card_ko"] @ cached["card_ko"].T
        similarity_en = cached["card_en"] @ cached["card_en"].T
        for i, left_id in enumerate(source_ids):
            for j in range(i + 1, len(source_ids)):
                right_id = source_ids[j]
                pair_key = frozenset((left_id, right_id))
                same_l3 = mapped_by_id.at[left_id, "mapped_l3_id"] == mapped_by_id.at[right_id, "mapped_l3_id"]
                bilingual_similarity = float(0.5 * (similarity_ko[i, j] + similarity_en[i, j]))
                explicitly_reviewed = pair_key in SEMANTIC_NEAR_DUPLICATE_EXPLICIT_PAIRS
                if not same_l3 or (bilingual_similarity < SEMANTIC_NEAR_DUPLICATE_THRESHOLD and not explicitly_reviewed):
                    continue
                seen_pairs.add(pair_key)
                left = mapped_by_id.loc[left_id]
                right = mapped_by_id.loc[right_id]
                discarded_id = ""
                representative_id = ""
                rationale = retained_rationale_by_l3.get(
                    left["mapped_l3_id"],
                    "Retained because manual comparison found a distinct affected target, harm stage, or causal mechanism.",
                )
                decision = "RETAIN_DISTINCT_SCOPE"
                distinctiveness_gate = "DISTINCT_TARGET_OR_MECHANISM"
                for possible_discarded in (left_id, right_id):
                    configured = SEMANTIC_NEAR_DUPLICATE_DROPS.get(possible_discarded)
                    if configured and configured["representative_source_row_id"] in pair_key:
                        discarded_id = possible_discarded
                        representative_id = configured["representative_source_row_id"]
                        rationale = configured["rationale"]
                        decision = "DROP_LESS_REPRESENTATIVE"
                        distinctiveness_gate = "NO_DISTINCT_TARGET_OR_MECHANISM"
                        break
                candidate_rows.append({
                    "Domain": domain,
                    "L3_ID": left["mapped_l3_id"],
                    "Left_source_row_id": left_id,
                    "Right_source_row_id": right_id,
                    "Left_Title_ko": left["title_ko"],
                    "Left_Title_en": left["title_en"],
                    "Right_Title_ko": right["title_ko"],
                    "Right_Title_en": right["title_en"],
                    "Similarity_ko": round(float(similarity_ko[i, j]), 6),
                    "Similarity_en": round(float(similarity_en[i, j]), 6),
                    "Bilingual_Similarity": round(bilingual_similarity, 6),
                    "Candidate_Basis": (
                        "EXPLICIT_SEMANTIC_REVIEW"
                        if explicitly_reviewed and bilingual_similarity < SEMANTIC_NEAR_DUPLICATE_THRESHOLD
                        else f"BGE_M3_AT_OR_ABOVE_{SEMANTIC_NEAR_DUPLICATE_THRESHOLD:.2f}"
                    ),
                    "Distinctiveness_Gate": distinctiveness_gate,
                    "Decision": decision,
                    "Representative_source_row_id": representative_id,
                    "Discarded_source_row_id": discarded_id,
                    "Decision_Rationale": rationale,
                })

    missing_explicit = SEMANTIC_NEAR_DUPLICATE_EXPLICIT_PAIRS - seen_pairs
    if missing_explicit:
        raise AssertionError(f"Explicit near-duplicate pairs were not reviewed: {sorted(map(sorted, missing_explicit))}")

    candidates = pd.DataFrame(candidate_rows).sort_values(
        ["Decision", "Bilingual_Similarity"], ascending=[True, False]
    ).reset_index(drop=True)
    decisions = candidates[candidates["Decision"].eq("DROP_LESS_REPRESENTATIVE")].copy()
    configured_drops = set(SEMANTIC_NEAR_DUPLICATE_DROPS)
    if set(decisions["Discarded_source_row_id"]) != configured_drops:
        raise AssertionError("Near-duplicate decision ledger does not match the configured deletion set")

    deleted_rows: list[dict] = []
    transformation_rows: list[dict] = []
    for discarded_id, configured in SEMANTIC_NEAR_DUPLICATE_DROPS.items():
        representative_id = configured["representative_source_row_id"]
        discarded = cleaned.loc[cleaned["source_row_id"].eq(discarded_id)]
        representative = cleaned.loc[cleaned["source_row_id"].eq(representative_id)]
        if len(discarded) != 1 or len(representative) != 1:
            raise AssertionError(f"Near-duplicate rows are not uniquely resolvable: {discarded_id}, {representative_id}")
        decision_row = decisions.loc[decisions["Discarded_source_row_id"].eq(discarded_id)].iloc[0]
        record = discarded.iloc[0].to_dict()
        record["archive_reason"] = "SEMANTIC_NEAR_DUPLICATE: " + configured["rationale"]
        record["representative_source_row_id"] = representative_id
        record["bilingual_similarity"] = decision_row["Bilingual_Similarity"]
        deleted_rows.append(record)
        transformation_rows.append({
            "source_row_id": discarded_id,
            "source_l4_id": record["source_l4_id"],
            "source_domain": record["source_domain"],
            "action": "DELETE_NEAR_DUPLICATE",
            "target_source_l4_id": representative.iloc[0]["source_l4_id"],
            "rationale": configured["rationale"],
        })

    audits["deleted"] = pd.concat(
        [audits["deleted"], pd.DataFrame(deleted_rows)], ignore_index=True, sort=False
    )
    audits["transformations"] = pd.concat(
        [audits["transformations"], pd.DataFrame(transformation_rows)], ignore_index=True, sort=False
    )
    audits["semantic_duplicate_candidates"] = candidates
    audits["semantic_duplicate_decisions"] = decisions
    cleaned = cleaned.loc[~cleaned["source_row_id"].isin(configured_drops)].copy()
    return cleaned.reset_index(drop=True), audits


def flatten_release(mapped: pd.DataFrame, hierarchy: pd.DataFrame, lookup: dict[str, dict]) -> pd.DataFrame:
    rows = []
    for _, row in mapped.iterrows():
        h = lookup[row["mapped_l3_id"]]
        ranked_candidates = json.loads(row["top5_l3_scores"])
        candidate_1, candidate_2 = ranked_candidates[0], ranked_candidates[1]
        rec = {k: h[k] for k in [
            "L0_ID", "L0_Title_ko", "L0_Title_en", "L1_ID", "L1_Title_ko", "L1_Title_en",
            "L1_Description_ko", "L1_Description_en", "L2_ID", "L2_Title_ko", "L2_Title_en",
            "L2_Description_ko", "L2_Description_en", "L3_ID", "L3_Title_ko", "L3_Title_en",
            "L3_Description_ko", "L3_Description_en",
        ]}
        rec.update({
            "L4_Title_ko": row["title_ko"], "L4_Title_en": row["title_en"],
            "L4_Description_ko": row["description_ko"], "L4_Description_en": row["description_en"],
            "facet": row["facet"], "act-type": row["act_type"],
            "Mapping_Method": row["mapping_method"], "EM_Score": row["em_score"],
            "EM_Margin": row["em_margin"], "EM_Stability": row["em_stability"],
            "EM_Anchor_Score": row["em_anchor_score"],
            "Hybrid_EM_Score": row["hybrid_score"], "Hybrid_EM_Margin": row["hybrid_margin"],
            "L4_Keyword_1_ko": row["keyword_1_ko"], "L4_Keyword_2_ko": row["keyword_2_ko"],
            "L4_Keyword_3_ko": row["keyword_3_ko"], "L4_Keyword_1_en": row["keyword_1_en"],
            "L4_Keyword_2_en": row["keyword_2_en"], "L4_Keyword_3_en": row["keyword_3_en"],
            "Keyword_Top_L3_ID": row["keyword_top_l3_id"],
            "Keyword_Support_Score": row["keyword_support_score"],
            "Keyword_Semantic_Score": row["keyword_semantic_score"],
            "Keyword_Prior": row["keyword_prior"], "Keyword_Evidence": row["keyword_evidence"],
            "Candidate_1_L3_ID": candidate_1["l3_id"],
            "Candidate_1_EM_Score": candidate_1["em_score"],
            "Candidate_1_Hybrid_Score": candidate_1["hybrid_score"],
            "Candidate_2_L3_ID": candidate_2["l3_id"],
            "Candidate_2_EM_Score": candidate_2["em_score"],
            "Candidate_2_Hybrid_Score": candidate_2["hybrid_score"],
            "KO_Top_L3_ID": row["ko_top_l3_id"], "EN_Top_L3_ID": row["en_top_l3_id"],
            "HD_Reason": row["hd_reason"], "source_row_id": row["source_row_id"],
            "Source_Domain": row["source_domain"], "Source_L4_ID": row["source_l4_id"],
            "Source_L4_IDs": row["source_l4_ids"], "Source_Instruction_Prompt": row["instruction_prompt"],
            "Domain_Route_Basis": row["domain_route_basis"],
            "Transformation_Action": row["transformation_action"],
            "Transformation_Rationale": row["transformation_rationale"],
            "Terminology_Sources": row["terminology_sources"],
            "Candidate_Constraint_Reason": row["candidate_constraint_reason"],
            "Definition_L3_Anchor_ID": row["definition_l3_anchor_id"],
            "Definition_L3_Anchor_Score": row["definition_l3_anchor_score"],
            "Definition_Grounding_Action": row["definition_grounding_action"],
        })
        rows.append(rec)
    out = pd.DataFrame(rows)
    out = out.sort_values(["L3_ID", "L4_Title_en", "source_row_id"], kind="stable").reset_index(drop=True)
    out["L4_ID"] = out.groupby("L3_ID").cumcount().add(1)
    out["L4_ID"] = out["L3_ID"] + "_" + out["L4_ID"].map(lambda x: f"{x:03d}")
    cols = list(out.columns)
    cols.insert(cols.index("L4_Title_ko"), cols.pop(cols.index("L4_ID")))
    return out[cols]


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig", lineterminator="\n")


def main() -> None:
    AUDIT.mkdir(parents=True, exist_ok=True)
    RELEASE.mkdir(parents=True, exist_ok=True)
    source_hashes_before = {k: sha256_file(v) for k, v in SOURCE_FILES.items()}
    source = normalise_rows()
    l1_final, hierarchy, lookup = build_hierarchy()
    cleaned, audits = apply_cleaning(source)
    cleaned, audits = apply_peer_review(cleaned, audits)
    cleaned = apply_l3_master_curation(cleaned)
    cleaned, audits = apply_cross_domain_l1_review(cleaned, audits)
    cleaned, audits = normalise_l4_titles(cleaned, audits)
    split_net_addition = len(audits["split"]) - audits["split"]["source_row_id"].nunique()
    initial_expected = len(source) - len(audits["deleted"]) - len(audits["merged"]) + split_net_addition
    if len(source) != 892 or len(cleaned) != initial_expected:
        raise AssertionError({"source": len(source), "deleted": len(audits["deleted"]),
                              "merged_away": len(audits["merged"]), "split_net": split_net_addition,
                              "cleaned": len(cleaned), "expected": initial_expected})

    provisional, provisional_diagnostics, _, _ = map_em(cleaned, hierarchy, phase="PROVISIONAL_L3_DRAFTING_ANCHOR")
    cleaned, audits = enforce_l3_grounded_ai_definitions(cleaned, provisional, hierarchy, audits)
    duplicate_review, duplicate_review_diagnostics, _, _ = map_em(
        cleaned, hierarchy, phase="POST_GROUNDING_NEAR_DUPLICATE_REVIEW"
    )
    cleaned, audits = review_and_drop_semantic_near_duplicates(cleaned, duplicate_review, audits)
    final_expected = len(source) - len(audits["deleted"]) - len(audits["merged"]) + split_net_addition
    if len(cleaned) != final_expected:
        raise AssertionError({"cleaned": len(cleaned), "expected": final_expected,
                              "deleted": len(audits["deleted"]), "merged": len(audits["merged"])})

    mapped, em_diagnostics, thresholds, keyword_profiles = map_em(cleaned, hierarchy, phase="FINAL_POST_GROUNDING")
    mapped = attach_title_terminology_sources(mapped)
    flat = flatten_release(mapped, hierarchy, lookup)
    title_terminology_audit = build_title_terminology_audit(flat, audits["title_normalisation"])
    l1_cross_domain_audit = audits["l1_cross_domain"].merge(
        flat[["source_row_id", "L4_ID", "L1_ID", "L3_ID", "Mapping_Method"]],
        on="source_row_id", how="left", validate="one_to_one",
    ).rename(columns={
        "L4_ID": "final_l4_id", "L1_ID": "final_l1_id", "L3_ID": "final_l3_id",
        "Mapping_Method": "final_mapping_method",
    })

    write_csv(l1_final, RELEASE / "L1_Master.csv")
    write_csv(hierarchy, RELEASE / "L1_L2_L3_Master.csv")
    for domain in ["General", "Agentic", "Physical"]:
        subset = flat[flat["L1_ID"] == DOMAIN_META[domain]["l1_id"]].copy()
        write_csv(subset, RELEASE / f"L4_{domain}.csv")

    write_csv(cleaned, AUDIT / "Cleaned_L4_PreMapping.csv")
    write_csv(audits["deleted"], AUDIT / "Deleted_Archive.csv")
    write_csv(audits["merged"], AUDIT / "Merged_Archive.csv")
    write_csv(audits["split"], AUDIT / "Split_Lineage.csv")
    write_csv(audits["transformations"], AUDIT / "Transformation_Log.csv")
    write_csv(audits["eligibility"], AUDIT / "Risk_Eligibility_Audit.csv")
    write_csv(audits["rewrites"], AUDIT / "Rewrite_Ledger.csv")
    write_csv(audits["peer_review"], AUDIT / "Peer_Review_Acceptance_Ledger.csv")
    write_csv(l1_cross_domain_audit, AUDIT / "L1_Cross_Domain_Routing_Audit.csv")
    write_csv(audits["l3_scope"], AUDIT / "L3_Scope_Eligibility_Audit.csv")
    write_csv(audits["ai_grounding"], AUDIT / "AI_Technology_Grounding_Ledger.csv")
    write_csv(audits["title_normalisation"], AUDIT / "Title_Normalisation_Ledger.csv")
    write_csv(title_terminology_audit, AUDIT / "L4_Title_Terminology_Audit.csv")
    write_csv(audits["semantic_duplicate_candidates"], AUDIT / "Semantic_Near_Duplicate_Candidates.csv")
    write_csv(audits["semantic_duplicate_decisions"], AUDIT / "Semantic_Near_Duplicate_Decisions.csv")
    write_csv(provisional[[
        "source_row_id", "source_domain", "source_l4_id", "title_ko", "title_en",
        "mapped_l3_id", "mapping_method", "em_score", "em_anchor_score", "hybrid_score",
        "keyword_support_score", "l3_candidate_hint", "top5_l3_scores",
    ]], AUDIT / "Provisional_L3_Drafting_Anchor_Audit.csv")
    write_csv(provisional_diagnostics, AUDIT / "Provisional_EM_Run_Diagnostics.csv")
    write_csv(duplicate_review_diagnostics, AUDIT / "Near_Duplicate_Review_EM_Run_Diagnostics.csv")
    write_csv(em_diagnostics, AUDIT / "EM_Run_Diagnostics.csv")
    write_csv(keyword_profiles, AUDIT / "Keyword_L3_Profiles.csv")
    em_card_columns = [
        "source_row_id", "source_domain", "source_l4_id", "title_ko", "title_en",
        "mapped_l3_id", "mapping_method", "em_score", "em_anchor_score", "em_margin",
        "hybrid_score", "hybrid_margin", "em_stability", "ko_top_l3_id", "en_top_l3_id",
        "keyword_1_ko", "keyword_2_ko", "keyword_3_ko", "keyword_1_en", "keyword_2_en", "keyword_3_en",
        "keyword_top_l3_id", "keyword_support_score", "keyword_semantic_score", "keyword_prior",
        "keyword_evidence", "hd_reason", "allowed_l3_ids", "candidate_constraint_reason", "top5_l3_scores",
    ]
    write_csv(mapped[em_card_columns], AUDIT / "EM_Card_Diagnostics.csv")
    write_csv(mapped[[
        "source_row_id", "source_domain", "source_l4_id", "title_ko", "title_en",
        "keyword_1_ko", "keyword_2_ko", "keyword_3_ko", "keyword_1_en", "keyword_2_en", "keyword_3_en",
        "keyword_top_l3_id", "keyword_support_score", "keyword_semantic_score", "keyword_prior",
        "mapped_l3_id", "mapping_method", "keyword_evidence",
    ]], AUDIT / "L4_Keyword_Audit.csv")
    write_csv(mapped[["source_row_id", "source_domain", "allowed_l3_ids", "candidate_constraint_reason"]],
              AUDIT / "Mapping_Candidate_Audit.csv")
    write_csv(flat[flat["Mapping_Method"] == "HD"], AUDIT / "Others_HD_Queue.csv")

    baseline_release = ROOT / "04_baseline_pre_keyword/release"
    if baseline_release.exists():
        baseline = pd.concat([
            pd.read_csv(baseline_release / f"L4_{domain}.csv", dtype=str, keep_default_na=False)
            for domain in ["General", "Agentic", "Physical"]
        ], ignore_index=True)
        baseline = baseline[["source_row_id", "L3_ID", "Mapping_Method"]].rename(columns={
            "L3_ID": "Baseline_L3_ID", "Mapping_Method": "Baseline_Mapping_Method",
        })
        comparison = flat[[
            "source_row_id", "Source_Domain", "L4_Title_ko", "L4_Title_en", "L3_ID", "Mapping_Method",
            "Hybrid_EM_Score", "Hybrid_EM_Margin", "Keyword_Top_L3_ID", "Keyword_Support_Score",
        ]].merge(baseline, on="source_row_id", how="left", validate="one_to_one")
        comparison["Assignment_Changed"] = comparison["L3_ID"] != comparison["Baseline_L3_ID"]
        comparison["Recovered_From_Others"] = (
            comparison["Baseline_L3_ID"].str.endswith("Others") & ~comparison["L3_ID"].str.endswith("Others")
        )
        comparison["Moved_To_Others"] = (
            ~comparison["Baseline_L3_ID"].str.endswith("Others") & comparison["L3_ID"].str.endswith("Others")
        )
        write_csv(comparison, AUDIT / "Keyword_EM_Baseline_Comparison.csv")

    source_profile_rows = []
    for domain in ["General", "Agentic", "Physical"]:
        subset = source[source["source_domain"] == domain]
        source_profile_rows.append({
            "domain": domain, "rows": len(subset), "unique_source_row_ids": subset["source_row_id"].nunique(),
            "blank_title_ko": int(subset["title_ko"].eq("").sum()),
            "blank_title_en": int(subset["title_en"].eq("").sum()),
            "blank_description_ko": int(subset["description_ko"].eq("").sum()),
            "blank_description_en": int(subset["description_en"].eq("").sum()),
            "duplicate_source_l4_ids": int(subset["source_l4_id"].duplicated(keep=False).sum()),
            "human_edit_ko_used": int(subset["human_edit_ko_used"].sum()),
            "human_edit_en_used": int(subset["human_edit_en_used"].sum()),
        })
    write_csv(pd.DataFrame(source_profile_rows), AUDIT / "Source_Profile.csv")
    write_csv(pd.DataFrame([
        {"source_code": code, "reference": reference} for code, reference in TERMINOLOGY_SOURCES.items()
    ]), AUDIT / "Terminology_Sources.csv")

    crosswalk_rows = []
    for _, src in source.iterrows():
        src_id = src["source_row_id"]
        matches = flat[(flat["source_row_id"] == src_id) | flat["source_row_id"].str.startswith(src_id + "-S")]
        status_override = ""
        if not len(matches):
            merge_log = audits["transformations"][
                (audits["transformations"]["source_row_id"] == src_id) &
                (audits["transformations"]["action"] == "MERGED_AWAY")
            ]
            if len(merge_log):
                representative_id = merge_log.iloc[0]["target_source_l4_id"]
                representatives = source[
                    (source["source_domain"] == src["source_domain"]) &
                    (source["source_l4_id"] == representative_id)
                ]
                if len(representatives) != 1:
                    raise AssertionError(f"Ambiguous merge representative for {src_id}: {representative_id}")
                representative_row_id = representatives.iloc[0]["source_row_id"]
                matches = flat[flat["source_row_id"] == representative_row_id]
                status_override = "MERGED"
        if not len(matches):
            duplicate_log = audits["semantic_duplicate_decisions"][
                audits["semantic_duplicate_decisions"]["Discarded_source_row_id"].eq(src_id)
            ]
            if len(duplicate_log):
                representative_row_id = duplicate_log.iloc[0]["Representative_source_row_id"]
                matches = flat[flat["source_row_id"].eq(representative_row_id)]
                status_override = "DEDUPLICATED"
        if len(matches):
            for _, m in matches.iterrows():
                crosswalk_rows.append({"source_row_id": src["source_row_id"], "source_domain": src["source_domain"],
                                       "source_l4_id": src["source_l4_id"], "final_l4_id": m["L4_ID"],
                                       "final_l1_id": m["L1_ID"], "final_l3_id": m["L3_ID"],
                                       "status": status_override or ("SPLIT" if m["source_row_id"].startswith(src_id + "-S") else "ACTIVE")})
        else:
            status = "DELETED" if ((audits["deleted"].get("source_row_id", pd.Series(dtype=str)) == src["source_row_id"]).any()) else "MERGED_AWAY"
            crosswalk_rows.append({"source_row_id": src["source_row_id"], "source_domain": src["source_domain"],
                                   "source_l4_id": src["source_l4_id"], "final_l4_id": "", "final_l1_id": "",
                                   "final_l3_id": "", "status": status})
    crosswalk = pd.DataFrame(crosswalk_rows)
    write_csv(crosswalk, AUDIT / "ID_Crosswalk.csv")

    source_hashes_after = {k: sha256_file(v) for k, v in SOURCE_FILES.items()}
    final_files = [RELEASE / "L1_Master.csv", RELEASE / "L1_L2_L3_Master.csv",
                   RELEASE / "L4_General.csv", RELEASE / "L4_Agentic.csv", RELEASE / "L4_Physical.csv"]
    validations = []
    def check(name: str, passed: bool, detail: str) -> None:
        validations.append({"Check": name, "Status": "PASS" if passed else "FAIL", "Detail": detail})
        if not passed:
            raise AssertionError(f"{name}: {detail}")

    check("Source hashes unchanged", source_hashes_before == source_hashes_after, json.dumps(source_hashes_after, ensure_ascii=False))
    l3_source_check = pd.read_csv(SOURCE_FILES["L3"], dtype=str, keep_default_na=False)
    l3_derived_check = hierarchy[hierarchy["Master_Status"] == "IMMUTABLE_SOURCE"].reset_index(drop=True)
    l3_exact = (len(l3_source_check) == 46 and
                l3_source_check["L1 (AI 형태)"].equals(l3_derived_check["Source_L1"]) and
                l3_source_check["L2 (리스크 발생 부위)"].equals(l3_derived_check["Source_L2"]) and
                l3_source_check["L3_en"].equals(l3_derived_check["L3_Title_en"]) and
                l3_source_check["L3_ko"].equals(l3_derived_check["L3_Title_ko"]) and
                l3_source_check["Description_en"].equals(l3_derived_check["L3_Description_en"]) and
                l3_source_check["Description_ko"].equals(l3_derived_check["L3_Description_ko"]) and
                l3_source_check["비고"].equals(l3_derived_check["Source_Notes"]))
    check("Immutable L3 exact-field preservation", l3_exact, "46 source L3 rows and all seven source fields preserved exactly")
    expected_review_l1 = {
        source_row_id: DOMAIN_META[decision["target_domain"]]["l1_id"]
        for source_row_id, decision in L1_CROSS_DOMAIN_REVIEW.items()
    }
    actual_review_l1 = flat.set_index("source_row_id")["L1_ID"].to_dict()
    check(
        "Reviewed L1 routing decisions applied before L3 mapping",
        all(actual_review_l1.get(source_row_id) == l1_id for source_row_id, l1_id in expected_review_l1.items()),
        f"{sum(actual_review_l1.get(source_row_id) == l1_id for source_row_id, l1_id in expected_review_l1.items())}/{len(expected_review_l1)} reviewed L1 decisions applied",
    )
    forced_others_expected = {
        source_row_id: f"{decision['target_domain'][0]}_Others"
        for source_row_id, decision in L1_CROSS_DOMAIN_REVIEW.items() if not decision["target_l3"]
    }
    actual_review_l3 = flat.set_index("source_row_id")["L3_ID"].to_dict()
    check(
        "Reviewed cards without a matching current L3 are held in domain Others",
        all(actual_review_l3.get(source_row_id) == l3_id for source_row_id, l3_id in forced_others_expected.items()),
        f"{sum(actual_review_l3.get(source_row_id) == l3_id for source_row_id, l3_id in forced_others_expected.items())}/{len(forced_others_expected)} reviewed no-match cards held for human decision",
    )
    reviewed_exact_l3 = {
        source_row_id: decision["target_l3"]
        for source_row_id, decision in L1_CROSS_DOMAIN_REVIEW.items() if decision["target_l3"]
    } | SAME_L1_REVIEWED_L3
    check(
        "Reviewed exact L3 decisions resolved",
        all(actual_review_l3.get(source_row_id) == l3_id for source_row_id, l3_id in reviewed_exact_l3.items()),
        f"{sum(actual_review_l3.get(source_row_id) == l3_id for source_row_id, l3_id in reviewed_exact_l3.items())}/{len(reviewed_exact_l3)} reviewed exact L3 decisions resolved",
    )
    expected_final_l4 = len(source) - len(audits["deleted"]) - len(audits["merged"]) + split_net_addition
    check("Final L4 reconciliation", len(flat) == expected_final_l4,
          f"{len(flat)} = {len(source)} - {len(audits['deleted'])} - {len(audits['merged'])} + {split_net_addition}")
    check("Final L4 IDs unique", flat["L4_ID"].is_unique, f"{flat['L4_ID'].nunique()} unique IDs")
    check("Bilingual L4 fields complete", not flat[["L4_Title_ko", "L4_Title_en", "L4_Description_ko", "L4_Description_en"]].eq("").any().any(), "No blank bilingual L4 fields")
    forbidden_title_hits = flat["L4_Title_en"].str.contains(FORBIDDEN_AI_TITLE_QUALIFIER_PATTERN)
    check("No formulaic AI involvement qualifier in English L4 titles", not forbidden_title_hits.any(),
          f"{int(forbidden_title_hits.sum())} formulaic qualifier hits")
    sexual_harm = flat[flat["source_row_id"].eq("SRC-G-0209")]
    check("Child sexual exploitation title uses the requested standard term",
          len(sexual_harm) == 1 and
          sexual_harm.iloc[0]["L4_Title_en"] == "Sexual harm and exploitation of minors" and
          sexual_harm.iloc[0]["L4_Title_ko"] == "AI를 이용한 미성년자 성적 위해·착취",
          sexual_harm.iloc[0]["L4_Title_en"] if len(sexual_harm) else "missing")
    check("Every released L4 title has a terminology validation record",
          len(title_terminology_audit) == len(flat) and title_terminology_audit["Validation_Status"].eq("PASS").all(),
          f"{int(title_terminology_audit['Validation_Status'].eq('PASS').sum())}/{len(flat)} titles passed")
    check("Every released L4 title has authoritative URL evidence",
          title_terminology_audit["Terminology_Source_URLs"].ne("").all(),
          f"{int(title_terminology_audit['Terminology_Source_URLs'].ne('').sum())}/{len(flat)} titles have URL evidence")
    duplicate_candidates = audits["semantic_duplicate_candidates"]
    duplicate_decisions = audits["semantic_duplicate_decisions"]
    check("Every semantic near-duplicate candidate has a documented decision",
          len(duplicate_candidates) > 0 and duplicate_candidates["Decision"].isin(
              {"DROP_LESS_REPRESENTATIVE", "RETAIN_DISTINCT_SCOPE"}
          ).all(),
          f"{len(duplicate_candidates)} candidates reviewed")
    discarded_duplicate_ids = set(duplicate_decisions["Discarded_source_row_id"])
    representative_duplicate_ids = set(duplicate_decisions["Representative_source_row_id"])
    check("Near-duplicate deletions match the configured reviewed set",
          discarded_duplicate_ids == set(SEMANTIC_NEAR_DUPLICATE_DROPS),
          f"{len(discarded_duplicate_ids)} lower-representativeness cards deleted")
    check("Near-duplicate representatives remain in the release",
          representative_duplicate_ids <= set(flat["source_row_id"]) and
          not discarded_duplicate_ids & set(flat["source_row_id"]),
          f"{len(representative_duplicate_ids)} representatives retained and {len(discarded_duplicate_ids)} duplicates absent")
    check("High-similarity distinct-scope cards are not automatically deleted",
          duplicate_candidates.loc[
              duplicate_candidates["Decision"].eq("RETAIN_DISTINCT_SCOPE"), "Distinctiveness_Gate"
          ].eq("DISTINCT_TARGET_OR_MECHANISM").all(),
          "Protected attributes, weapon types, affected targets, and harm mechanisms require separate review")
    check("Mapping method complete", set(flat["Mapping_Method"]) <= {"EM", "HD"}, str(flat["Mapping_Method"].value_counts().to_dict()))
    check("Others only use HD", flat.loc[flat["L3_ID"].str.endswith("Others"), "Mapping_Method"].eq("HD").all(), "All Others records are HD")
    check("EM excludes Others", (~flat.loc[flat["Mapping_Method"] == "EM", "L3_ID"].str.endswith("Others")).all(), "No EM record assigned to Others")
    check("L3 references valid", set(flat["L3_ID"]) <= set(hierarchy["L3_ID"]), "All L3 IDs resolve")
    check("Crosswalk has no join explosion", len(crosswalk) == len(source) + 1,
          f"{len(crosswalk)} rows for {len(source)} sources plus one split child")
    check("Crosswalk source coverage", set(crosswalk["source_row_id"]) == set(source["source_row_id"]),
          "Every source_row_id appears in the crosswalk")
    ko_definition_style = flat["L4_Description_ko"].str.contains(r"(?:리스크|위험|위해|피해|침해)\.$", regex=True)
    check("Korean L4 risk-definition endings", bool(ko_definition_style.all()),
          f"{int(ko_definition_style.sum())}/{len(flat)} definitions end in a risk term")
    check("English L4 risk-definition structure", flat["L4_Description_en"].str.startswith("The risk that").all(),
          "All English definitions use the L3-style 'The risk that' structure")
    ko_ai_grounded = flat["L4_Description_ko"].map(lambda value: bool(AI_TECH_KO_PATTERN.search(value)))
    en_ai_grounded = flat["L4_Description_en"].map(lambda value: bool(AI_TECH_EN_PATTERN.search(value)))
    ko_causal_grounded = flat["L4_Description_ko"].map(
        lambda value: bool(AI_CAUSAL_KO_PATTERN.search(value))
        or bool(re.search(r"(리스크|위험|위해|피해|침해)\.$", value))
    )
    en_causal_grounded = flat["L4_Description_en"].map(
        lambda value: bool(AI_CAUSAL_EN_PATTERN.search(value)) or value.startswith("The risk that")
    )
    check("Korean L4 definitions name an AI technology", bool(ko_ai_grounded.all()),
          f"{int(ko_ai_grounded.sum())}/{len(flat)} explicitly name AI, an algorithm, an agent, a robot, a learning technology, or a model")
    check("English L4 definitions name an AI technology", bool(en_ai_grounded.all()),
          f"{int(en_ai_grounded.sum())}/{len(flat)} explicitly name an AI technology")
    check("Korean L4 definitions connect AI to an L3-style risk statement", bool(ko_causal_grounded.all()),
          f"{int(ko_causal_grounded.sum())}/{len(flat)} contain a causal mechanism or an explicit risk-statement ending")
    check("English L4 definitions connect AI to an L3-style risk statement", bool(en_causal_grounded.all()),
          f"{int(en_causal_grounded.sum())}/{len(flat)} contain a causal mechanism or the L3-style 'The risk that' structure")
    combined_release_text = flat[
        ["L4_Title_ko", "L4_Title_en", "L4_Description_ko", "L4_Description_en"]
    ].fillna("").agg(" ".join, axis=1)
    editorial_residue = combined_release_text.str.contains(
        r"(?:L3\s*mapping|YesNo|②|이러한 결과를 초래하는 리스크|리스크\.\s*피\.)",
        case=False, regex=True,
    )
    deprecated_wrapper = flat["L4_Description_en"].str.contains(
        "following harmful condition", case=False, regex=False
    )
    check("No editorial or generation residue in L4 text", not editorial_residue.any(),
          f"{int(editorial_residue.sum())} residual drafting markers")
    check("No deprecated generic definition wrapper", not deprecated_wrapper.any(),
          f"{int(deprecated_wrapper.sum())} generic wrapper sentences")
    check("Every retained L4 was reviewed against an immutable L3 definition",
          flat["Definition_L3_Anchor_ID"].isin(
              hierarchy.loc[hierarchy["Master_Status"].eq("IMMUTABLE_SOURCE"), "L3_ID"]
          ).all(),
          f"{flat['Definition_L3_Anchor_ID'].nunique()} immutable L3 drafting anchors recorded")
    em_anchor_match = flat.loc[flat["Mapping_Method"].eq("EM"), "Definition_L3_Anchor_ID"].eq(
        flat.loc[flat["Mapping_Method"].eq("EM"), "L3_ID"]
    )
    check("Every EM-mapped L4 was drafted against its final immutable L3",
          bool(em_anchor_match.all()),
          f"{int(em_anchor_match.sum())}/{len(em_anchor_match)} EM cards use their final L3 as the drafting anchor")
    malformed_english = flat["L4_Description_en"].str.contains(
        r"(?:causes or enables|"
        r"\b(?:selfpreference|humangenerated|decisionsupport|worldmodel|postdeployment|realworld|multiagent|llmempowered)\b)",
        case=False, regex=True,
    )
    check("No known English grammar or token-joining defects",
          not malformed_english.any(), f"{int(malformed_english.sum())} malformed English definitions")
    source_note_residue = combined_release_text.str.contains(
        r"(?:\bNOTE\b|cross-reference|GYK-2025|상호 참조)", case=False, regex=True
    )
    check("No source-note residue in published L4 text", not source_note_residue.any(),
          f"{int(source_note_residue.sum())} source-note fragments")
    scope_kept_ids = set(audits["l3_scope"].loc[audits["l3_scope"]["scope_decision"].eq("KEEP"), "source_row_id"])
    check("L3 scope gate precedes final EM", set(flat["source_row_id"]) <= scope_kept_ids,
          "Every released L4 passed the semantic, lexical, or curated L3 scope gate")
    forced_scope_deleted = set(L3_SCOPE_INELIGIBLE_SOURCE_ROWS) <= set(
        audits["l3_scope"].loc[audits["l3_scope"]["scope_decision"].eq("DELETE"), "source_row_id"]
    )
    check("L3 scope gate performs substantive rejection", forced_scope_deleted,
          f"{int(audits['l3_scope']['scope_decision'].eq('DELETE').sum())} cards rejected before final EM")
    check("No L3-scope-ineligible card released", not set(L3_SCOPE_INELIGIBLE_SOURCE_ROWS) & set(flat["source_row_id"]),
          f"{len(L3_SCOPE_INELIGIBLE_SOURCE_ROWS)} identified out-of-scope cards archived")
    check("Non-risk application contexts removed", not set(NON_RISK_SOURCE_ROWS) & set(flat["source_row_id"]),
          "Eight context-only General source rows are absent from the final L4 release")
    check("Risk eligibility precedes EM", set(mapped["source_row_id"]) <= set(cleaned["source_row_id"]),
          "Every mapped card passed the cleaned eligibility stage")
    check("L4 ID prefix matches L3", (flat["L4_ID"].str.rsplit("_", n=1).str[0] == flat["L3_ID"]).all(),
          "All final L4 IDs inherit the assigned L3 prefix")
    check("No final new IDs", not flat["L4_ID"].str.lower().eq("new").any(), "No generated L4 ID is blank or 'new'")
    check("Exactly five primary CSV files", len(list(RELEASE.glob("*.csv"))) == 5, ", ".join(p.name for p in final_files))
    keyword_columns = [
        "L4_Keyword_1_ko", "L4_Keyword_2_ko", "L4_Keyword_3_ko",
        "L4_Keyword_1_en", "L4_Keyword_2_en", "L4_Keyword_3_en",
    ]
    check("Exactly three bilingual L4 keywords", not flat[keyword_columns].eq("").any().any(),
          f"Three Korean and three English representative concepts for all {len(flat)} cards")
    check("Keyword profiles cover immutable L3", len(keyword_profiles) == 46 and keyword_profiles["L3_ID"].is_unique,
          "46 auditable L3 lexical profiles")
    wage = flat[flat["source_row_id"] == "SRC-G-0312"]
    check("Wage polarization maps to economic disruption", len(wage) == 1 and wage.iloc[0]["L3_ID"] == "G_SOC_ECON",
          wage.iloc[0]["L3_ID"] if len(wage) else "missing")
    cybercrime = flat[flat["source_row_id"] == "SRC-P-0090"]
    check("Cybercrime jailbreak maps to security robustness", len(cybercrime) == 1 and cybercrime.iloc[0]["L3_ID"] == "G_SYS_SECADV",
          cybercrime.iloc[0]["L3_ID"] if len(cybercrime) else "missing")
    audited_expected_l3 = {
        "SRC-A-0076": "G_INT_REL", "SRC-A-0070": "G_INT_REPR",
        "SRC-G-0231": "G_INT_PRIV", "SRC-G-0281": "G_SYS_EVAL",
        "SRC-P-0084": "G_SYS_SECADV", "SRC-P-0141": "G_SYS_TRANS",
        "SRC-P-0054": "P_SYS_CONTROL", "SRC-P-0207": "G_SOC_ECON",
        "SRC-P-0055": "G_SOC_POWER", "SRC-P-0139": "P_SYS_STATE",
    }
    actual_l3 = flat.set_index("source_row_id")["L3_ID"].to_dict()
    audited_cases_pass = all(actual_l3.get(source_row_id) == l3_id for source_row_id, l3_id in audited_expected_l3.items())
    check("Independent-review L3 corrections resolved", audited_cases_pass,
          f"{sum(actual_l3.get(source_row_id) == l3_id for source_row_id, l3_id in audited_expected_l3.items())}/{len(audited_expected_l3)} audited cases")
    overconfidence_rows = mapped[mapped["mapped_l3_id"] == "G_SYS_OVERCONF"]
    overconfidence_gate = overconfidence_rows.apply(
        lambda row: any(term.lower() in " ".join([
            clean_text(row["title_ko"]), clean_text(row["title_en"]),
            clean_text(row["description_ko"]), clean_text(row["description_en"]),
        ]).lower() for term in SENSITIVE_L3_TERMS["G_SYS_OVERCONF"]), axis=1,
    )
    check("Overconfidence requires mechanism evidence", bool(overconfidence_gate.all()),
          f"{int(overconfidence_gate.sum())}/{len(overconfidence_rows)} G_SYS_OVERCONF cards contain uncertainty, certainty, calibration, verification, or error evidence")
    anthropocentric = flat[flat["source_row_id"] == "SRC-G-0351"]
    check("Anthropocentric card not forced to overconfidence",
          len(anthropocentric) == 1 and anthropocentric.iloc[0]["L3_ID"] != "G_SYS_OVERCONF",
          anthropocentric.iloc[0]["L3_ID"] if len(anthropocentric) else "missing")
    candidate_columns = ["Candidate_1_L3_ID", "Candidate_1_EM_Score", "Candidate_1_Hybrid_Score",
                         "Candidate_2_L3_ID", "Candidate_2_EM_Score", "Candidate_2_Hybrid_Score"]
    candidate_valid = (not flat[candidate_columns].eq("").any().any() and
                       (flat["Candidate_1_L3_ID"] != flat["Candidate_2_L3_ID"]).all() and
                       set(flat["Candidate_1_L3_ID"]) <= set(hierarchy["L3_ID"]) and
                       set(flat["Candidate_2_L3_ID"]) <= set(hierarchy["L3_ID"]) and
                       ~flat["Candidate_1_L3_ID"].str.endswith("Others").any() and
                       ~flat["Candidate_2_L3_ID"].str.endswith("Others").any())
    check("Two reviewable L3 candidates per L4", bool(candidate_valid),
          "Every L4 exposes two distinct non-Others L3 candidates with EM and hybrid scores")
    validation_df = pd.DataFrame(validations)
    write_csv(validation_df, AUDIT / "Validation_Report.csv")

    summary = {
        "date": STAMP,
        "source_counts": source.groupby("source_domain").size().to_dict(),
        "source_total": len(source), "deleted": len(audits["deleted"]), "merged_away": len(audits["merged"]),
        "split_net_addition": split_net_addition, "cleaned_total": len(cleaned),
        "final_domain_counts": flat.groupby("L1_Title_en").size().to_dict(),
        "mapping_method_counts": flat.groupby(["L1_Title_en", "Mapping_Method"]).size().unstack(fill_value=0).to_dict(orient="index"),
        "others_total": int((flat["Mapping_Method"] == "HD").sum()),
        "em_total": int((flat["Mapping_Method"] == "EM").sum()),
        "mapping_pipeline": "ANCHOR_REGULARISED_KEYWORD_AUGMENTED_EM",
        "definition_pipeline": "PROVISIONAL_L3_SCOPE_GATE_THEN_BILINGUAL_AI_TECHNOLOGY_GROUNDING_THEN_FINAL_EM",
        "definition_ai_grounding_rewrites": int(audits["ai_grounding"]["grounding_action"].eq("L3_MASTER_AI_REWRITE").sum()),
        "title_terminology_normalisations": int(title_terminology_audit["Title_Changed"].sum()),
        "title_normalisation_ledger_changes_before_deduplication": int(
            audits["title_normalisation"]["title_changed"].sum()
        ),
        "title_terminology_validated": int(title_terminology_audit["Validation_Status"].eq("PASS").sum()),
        "semantic_near_duplicate_candidates": len(audits["semantic_duplicate_candidates"]),
        "semantic_near_duplicate_deletions": len(audits["semantic_duplicate_decisions"]),
        "l3_scope_deletions": int(audits["l3_scope"]["scope_decision"].eq("DELETE").sum()),
        "l1_cross_domain_reviewed": len(L1_CROSS_DOMAIN_REVIEW),
        "l1_cross_domain_forced_others": len(forced_others_expected),
        "keyword_count_per_language": 3,
        "thresholds": thresholds,
        "l3_source_rows": 46, "l3_derived_others_rows": 3,
        "validation_passed": int((validation_df["Status"] == "PASS").sum()),
        "validation_failed": int((validation_df["Status"] == "FAIL").sum()),
    }
    (AUDIT / "validation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "release_date": STAMP,
        "pipeline_script": "projects/rai_risk_taxonomy_2_0_rebuild_20260826/scripts/run_rebuild_pipeline.py",
        "source_hashes": source_hashes_after,
        "model": {
            "name": "BAAI/bge-m3", "revision": MODEL.name, "pooling": "CLS",
            "config_sha256": sha256_file(MODEL / "config.json"),
            "tokenizer_sha256": sha256_file(MODEL / "tokenizer.json"),
            "weights_sha256": sha256_file(MODEL / "pytorch_model.bin"),
        },
        "mapping_method": {
            "name": "Anchor-regularised keyword-augmented constrained EM",
            "l1_decision_precedes_domain_constrained_l3_em": True,
            "cross_domain_review_count": len(L1_CROSS_DOMAIN_REVIEW),
            "no_matching_l3_policy": "HOLD_IN_REVIEWED_L1_OTHERS",
            "cross_domain_audit_file": "audit/L1_Cross_Domain_Routing_Audit.csv",
            "anchor_weight": 4.0,
            "semantic_keyword_weight": 0.025,
            "lexical_keyword_weight": 0.060,
            "exclusion_penalty": 0.080,
            "curated_l3_prior_weight": 0.30,
            "representative_keywords_per_language": 3,
        },
        "definition_method": {
            "name": "Immutable-L3-referenced bilingual AI-technology grounding",
            "provisional_mapping_used_only_as_drafting_anchor": True,
            "final_mapping_refitted_after_definition_revision": True,
            "korean_ai_technology_required": True,
            "english_ai_technology_required": True,
            "causal_risk_mechanism_required": True,
            "l3_scope_anchor_floor": L3_SCOPE_ANCHOR_FLOOR,
            "l3_scope_hybrid_floor": L3_SCOPE_HYBRID_FLOOR,
        },
        "title_terminology_method": {
            "name": "Authoritative term-family normalisation against the immutable L3 master",
            "formulaic_ai_involvement_qualifiers_removed": list(FORBIDDEN_AI_TITLE_QUALIFIERS),
            "technical_object_ai_terms_retained": True,
            "audit_file": "audit/L4_Title_Terminology_Audit.csv",
        },
        "semantic_deduplication_method": {
            "name": "Bilingual BGE-M3 candidate generation with immutable-L3 and distinctiveness gates",
            "candidate_similarity_threshold": SEMANTIC_NEAR_DUPLICATE_THRESHOLD,
            "automatic_deletion_from_similarity_only": False,
            "distinct_target_or_mechanism_is_retained": True,
            "candidate_audit_file": "audit/Semantic_Near_Duplicate_Candidates.csv",
            "decision_audit_file": "audit/Semantic_Near_Duplicate_Decisions.csv",
        },
        "primary_outputs": {p.name: {"sha256": sha256_file(p), "rows": len(pd.read_csv(p))} for p in final_files},
        "summary": summary,
    }
    (RELEASE / "release_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
