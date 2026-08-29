#!/usr/bin/env python3
"""Append final expert-confirmed language and L3-boundary refinements."""

from __future__ import annotations

import csv
import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "05_human_review_round2"
SPEC = ROOT / "02_working" / "specifications" / "human_review_round2"
MANIFEST = SPEC / "L4_Final_Terminology_L3_Alignment_Approved_20260829.csv"
ARCHIVE = SPEC / "archive" / "pre_final_language_boundary_correction_20260829"
EVIDENCE = "L3_MASTER|TWO_EXPERT_FINAL_LANGUAGE_AND_BOUNDARY_REVIEW_20260829"


UPDATES = {
    "SRC-P-0074": {
        "title_ko": "악성코드 생성 및 사이버공격 자동화",
        "title_en": "Malware generation and cyberattack automation",
        "description_ko": "대규모 언어 모델의 코딩 역량이 악용되어 난독화·변이·다형성 악성코드를 저비용·고속으로 생성하고 공격 캠페인을 자동화함으로써 비숙련 공격자의 진입 장벽을 낮추고 탐지가 어려운 사이버공격을 확산시키는 리스크.",
        "description_en": "The risk that the coding capabilities of large language models are misused to generate obfuscated, mutating, or polymorphic malware rapidly and at low cost and to automate attack campaigns, lowering barriers for less-skilled attackers and expanding cyberattacks that are difficult for defensive tools to detect.",
    },
    "SRC-G-0563": {
        "title_ko": "불법 무기 거래",
        "title_en": "Illegal weapons trade",
        "description_ko": "AI 시스템이 불법 무기 거래를 계획·최적화·중개·은폐하여 무기의 불법 획득·유통·확산을 지원하고 법적·사회적 피해를 초래하는 리스크.",
        "description_en": "The risk that an AI system plans, optimises, brokers, or conceals illegal weapons transactions, facilitating the unlawful acquisition, distribution, or proliferation of weapons and causing legal or societal harm.",
    },
    "SRC-A-0013": {
        "title_ko": "비플레이어 캐릭터의 의도를 통한 에이전트 조작",
        "title_en": "Agent manipulation through non-player-character intent",
        "description_ko": "시뮬레이션 또는 다중 에이전트 환경에서 비플레이어 캐릭터의 표현된 의도나 목표가 AI 에이전트의 판단·계획·행동을 조작하도록 설계되거나 악용되어 안전하지 않은 결정을 유발하는 리스크.",
        "description_en": "The risk that, in a simulation or multi-agent environment, the expressed intentions or goals of a non-player character are designed or exploited to manipulate an AI agent's judgement, planning, or actions, inducing unsafe decisions.",
    },
    "SRC-G-0252": {
        "title_ko": "저작물의 무단 복제 및 브랜드 사칭",
        "title_en": "Unauthorised reproduction of works and brand impersonation",
        "description_ko": "AI 시스템이 저작권으로 보호되는 저작물이나 상표·브랜드 표지를 권리자의 허락 없이 복제·변형하거나 진품 또는 공식 콘텐츠로 오인되도록 생성·유통하여 저작권이나 상표권을 침해하는 리스크.",
        "description_en": "The risk that an AI system reproduces or modifies copyright-protected works or trademarks and brand identifiers without the rights holder's permission, or generates and distributes them in ways likely to be mistaken for authentic or official content, infringing copyright or trademark rights.",
    },
    "SRC-G-0078": {
        "title_ko": "에이전트 벤치마크의 범위·심층성 불균형",
        "title_en": "Imbalance in the scope and depth of agent benchmarks",
        "description_ko": "AI 에이전트 평가 벤치마크가 많은 위험 범주를 포함하지만 각 범주의 심층성·현실성·적대적 변형을 충분히 다루지 못해 중요한 위해를 탐지하지 못하고 안전성에 대한 부당한 확신과 잘못된 배포 판단을 초래하는 리스크.",
        "description_en": "The risk that an AI-agent evaluation benchmark covers many risk categories but lacks sufficient depth, realism, or adversarial variation within them, failing to reveal material harms and creating unwarranted assurance that leads to flawed deployment decisions.",
    },
    "SRC-G-0254": {
        "title_ko": "합성 창작물에 의한 인간 창작 노동의 대체",
        "title_en": "Displacement of human creative work by synthetic substitutes",
        "description_ko": "AI 모델이 예술가의 아이디어와 창작 관행을 활용한 합성 콘텐츠를 대규모로 생성하여 시장과 이용자의 주목에서 인간 창작물을 대체함으로써 창작 노동 수요와 창작 경제의 수익성을 낮추고 인간의 창작·혁신 유인을 약화하는 리스크.",
        "description_en": "The risk that AI models generate synthetic content at scale using artists' ideas and creative practices, displacing human works in markets and audience attention, reducing demand for creative labour and the viability of creative economies, and weakening incentives for human creativity and innovation.",
    },
    "SRC-G-0355": {
        "title_ko": "장기·분산적 AI 피해의 평가·측정 실패",
        "title_en": "Evaluation and measurement failure for long-term and diffuse AI harms",
        "description_ko": "AI 시스템의 평가·검증 절차가 미묘하고 분산적이며 장기간에 걸쳐 나타나는 피해를 탐지·측정하지 못해 안전성에 대한 부당한 확신을 형성하고 부적절한 배포 또는 거버넌스 판단을 초래하는 리스크.",
        "description_en": "The risk that evaluation and validation processes for an AI system fail to detect or measure harms that are subtle, diffuse, or emerge over long periods, creating unwarranted assurance about safety and leading to inappropriate deployment or governance decisions.",
    },
    "SRC-G-0436": {
        "title_ko": "지배적 가치 편향에 따른 이슬람 윤리의 과소대표",
        "title_en": "Under-representation of Islamic ethics due to dominant-value bias",
        "description_ko": "AI 시스템이 학습 데이터와 설계 과정에 과대표현된 지배적 가치를 중립적 기본값으로 취급하여 이슬람 윤리 원칙·법적 추론·공동체별 도덕적 기대를 과소대표하거나 대체하는 리스크.",
        "description_en": "The risk that an AI system treats dominant values over-represented in its training data or design process as neutral defaults, under-representing or displacing Islamic ethical principles, legal reasoning, or community-specific moral expectations.",
    },
    "SRC-G-0414": {
        "title_ko": "AI에 대한 국제법적 거버넌스의 공백",
        "title_en": "Gaps in international legal governance of AI",
        "description_ko": "AI 시스템의 국경 간 개발·배포·운영에 관한 국제 규범, 관할, 감독 및 책임 체계가 파편화되거나 부재하여 위험을 일관되게 통제하고 피해에 대한 책임을 규명하기 어려워지는 리스크.",
        "description_en": "The risk that international rules, jurisdictional arrangements, oversight, or accountability mechanisms for the cross-border development, deployment, and operation of AI systems are fragmented or absent, impeding consistent risk control and attribution of responsibility for harm.",
    },
    "SRC-P-0101": {
        "title_ko": "유해한 물리적 행동 지시를 위장한 공격",
        "title_en": "Attack using disguised instructions for harmful physical actions",
        "description_ko": "공격자가 유해한 물리적 행동 지시를 무해하거나 정상적인 과업 요청으로 위장하여 체화형 AI 에이전트의 안전장치를 우회하고 해당 행동을 수용·실행하도록 유도하는 리스크.",
        "description_en": "The risk that attackers disguise instructions for harmful physical actions as benign or routine task requests, bypassing an embodied AI agent's safeguards and inducing it to accept and execute those actions.",
    },
    "SRC-P-0196": {
        "target_l3": "A_Others",
        "title_ko": "무감독 AI 에이전트의 기계적 명령 수행",
        "title_en": "Mechanical command execution by unsupervised AI agents",
        "description_ko": "AI 에이전트가 충분한 인간 감독 없이 지시나 목표를 기계적으로 수행하면서 도덕·안전 제약을 무시하고 도구·정보 환경·다른 시스템과 예측하기 어렵게 상호작용하여 피해를 초래하는 리스크.",
        "description_en": "The risk that an AI agent mechanically executes instructions or pursues goals without adequate human oversight, disregarding ethical or safety constraints and interacting unpredictably with tools, information environments, or other systems, causing harm.",
    },
    "SRC-P-0120": {
        "title_ko": "취약점 자동 탐지·악용을 통한 사이버 공격 확대",
        "title_en": "Expansion of cyberattacks through automated vulnerability discovery and exploitation",
        "description_ko": "범용 AI(general-purpose AI, GPAI)가 소프트웨어 취약점의 자동 탐지와 악성코드 개발을 지원하여 악의적 행위자가 낮은 비용으로 사이버 공격을 대규모화하고 피해를 확대하는 리스크.",
        "description_en": "The risk that general-purpose AI (GPAI) supports the automated discovery of software vulnerabilities and development of malicious code, enabling malicious actors to scale cyberattacks at low cost and increase their impact.",
    },
    "SRC-G-0361": {
        "title_ko": "미성년자의 AI 설득 취약성",
        "title_en": "Minor susceptibility to AI persuasion",
        "description_ko": "미성년자가 발달적 취약성으로 인해 준사회적 압력이나 은폐된 상업적·이념적 영향 등 AI 시스템의 설득적·조작적 상호작용에 특히 취약해지는 리스크.",
        "description_en": "The risk that minors' developmental susceptibility makes them disproportionately vulnerable to persuasive or manipulative AI interaction, including parasocial pressure and covert commercial or ideological influence.",
    },
    "SRC-G-0138": {
        "title_ko": "동의 없는 넛지",
        "title_en": "Nudging without consent",
        "description_ko": "AI 시스템이 충분한 고지, 이의제기 절차 또는 동의 없이 개인화된 넛지를 제공하여 이용자의 숙고된 선택을 우회하고 행동을 변경시키는 리스크.",
        "description_en": "The risk that AI systems alter user behaviour through personalised nudges without adequate disclosure, means of contestation, or consent, thereby bypassing deliberative choice.",
    },
    "SRC-G-0254": {
        "title_ko": "합성 창작물에 의한 인간 창작 노동의 대체",
        "title_en": "Displacement of human creative work by synthetic substitutes",
        "description_ko": "AI 모델이 예술가의 아이디어와 창작 관행을 활용한 합성 콘텐츠를 대규모로 생성하여 시장에서 인간 창작물을 대체하고 이용자의 주목을 빼앗음으로써, 창작 노동 수요와 창작 경제의 수익성을 낮추고 인간의 창작·혁신 유인을 약화하는 리스크.",
        "description_en": "The risk that AI models generate synthetic content at scale using artists' ideas and creative practices, displacing human works in markets and the attention economy, reducing demand for creative labour and the viability of creative economies, and weakening incentives for human creativity and innovation.",
    },
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def tokens(value: str) -> set[str]:
    return {part.strip() for part in (value or "").replace("|", ";").replace(",", ";").split(";") if part.strip()}


def row_hash(row: dict[str, str]) -> str:
    value = "\x1f".join([row["L3_ID"], row["L4_Title_ko"], row["L4_Title_en"], row["L4_Description_ko"], row["L4_Description_en"]])
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def main() -> None:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    archive = ARCHIVE / MANIFEST.name
    if not archive.exists():
        shutil.copy2(MANIFEST, archive)
    outputs = []
    for domain in ("General", "Agentic", "Physical"):
        outputs.extend(read_csv(OUT / f"L4_{domain}_Human_Review_Round2_Applied.csv"))
    ledger = read_csv(OUT / "Human_Review_Round2_Decision_Ledger.csv")
    rows = read_csv(MANIFEST)
    header = list(rows[0])
    existing_ids = {row["Decision_ID"] for row in rows}
    added = 0
    for number, (source_row_id, update) in enumerate(UPDATES.items(), 372):
        decision_id = f"FQA-{number:03d}"
        if decision_id in existing_ids:
            continue
        matches = [row for row in outputs if source_row_id in tokens(row.get("source_row_id", ""))]
        if len(matches) != 1:
            raise ValueError(f"Expected one output for {source_row_id}: {len(matches)}")
        before = matches[0]
        current_domain = before["L1_Title_en"].removesuffix(" AI")
        ledger_matches = [row for row in ledger if row["Destination_Domain"] == current_domain and row["L4_ID_After"] == before["L4_ID"]]
        if len(ledger_matches) != 1:
            raise ValueError(f"Expected one ledger row for {source_row_id}: {len(ledger_matches)}")
        operation = {field: "" for field in header}
        target_l3 = update.get("target_l3", before["L3_ID"])
        operation.update({
            "Decision_ID": decision_id,
            "Source_L4_ID_Before": ledger_matches[0]["L4_ID_Before"],
            "Observed_L4_ID_PreFinalQA": before["L4_ID"],
            "Expected_Current_L3_ID": before["L3_ID"],
            "Expected_Previous_SHA256": row_hash(before),
            "Decision": "MOVE_TO_OTHERS_HD" if target_l3 != before["L3_ID"] and target_l3.endswith("Others") else "LANGUAGE_REFINEMENT",
            "Target_L3_ID": target_l3,
            "Approved_Title_ko": update["title_ko"],
            "Approved_Title_en": update["title_en"],
            "Approved_Description_ko": update["description_ko"],
            "Approved_Description_en": update["description_en"],
            "Decision_Rationale": "Final independent expert review narrowed scope and language to the immutable L3 definition and removed policy or technical ambiguity.",
            "Terminology_Evidence": EVIDENCE,
            "Approval_Status": "APPROVED_FINAL_QA_20260829",
        })
        rows.append(operation)
        added += 1
    rows.sort(key=lambda row: int(row["Decision_ID"].rsplit("-", 1)[1]))
    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
    print(f"upserted={added} total={len(rows)} sha256={hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
