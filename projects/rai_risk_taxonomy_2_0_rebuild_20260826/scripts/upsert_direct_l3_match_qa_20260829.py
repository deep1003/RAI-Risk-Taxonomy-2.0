#!/usr/bin/env python3
"""Append two-expert-confirmed direct L3 matches and three scope rewrites."""

from __future__ import annotations

import csv
import hashlib
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "05_human_review_round2"
SPEC = ROOT / "02_working" / "specifications" / "human_review_round2"
MANIFEST = SPEC / "L4_Final_Terminology_L3_Alignment_Approved_20260829.csv"
ARCHIVE = SPEC / "archive" / "pre_direct_l3_match_correction_20260829"
EVIDENCE = (
    "L3_MASTER|HUMAN_REVIEW_ROUND2|TWO_EXPERT_L3_ALIGNMENT_REVIEW_20260829|"
    "POLICY_AND_TECHNICAL_TERMINOLOGY_QA"
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def tokens(value: str) -> set[str]:
    return {
        part.strip()
        for part in (value or "").replace("|", ";").replace(",", ";").split(";")
        if part.strip()
    }


def before_hash(row: dict[str, str]) -> str:
    value = "\x1f".join(
        [
            row["L3_ID"], row["L4_Title_ko"], row["L4_Title_en"],
            row["L4_Description_ko"], row["L4_Description_en"],
        ]
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


DIRECT_TARGETS = [
    ("SRC-P-0108", "G_INT_ILLEGAL"), ("SRC-P-0203", "G_INT_PRIV"),
    ("SRC-P-0181", "P_SYS_STATE"), ("SRC-P-0127", "G_SYS_EVAL"),
    ("SRC-P-0142", "G_SYS_SECADV"), ("SRC-P-0033", "G_SYS_SECADV"),
    ("SRC-P-0037", "G_INT_PRIV"), ("SRC-P-0028", "P_INT_SAFETY"),
    ("SRC-P-0016", "G_SYS_EVAL"), ("SRC-P-0106", "G_SYS_SECADV"),
    ("SRC-P-0107", "G_INT_WEAP"), ("SRC-A-0036", "G_SYS_SECADV"),
    ("SRC-P-0056", "G_INT_WEAP"), ("SRC-P-0120", "G_INT_WEAP"),
    ("SRC-P-0074", "G_INT_WEAP"), ("SRC-G-0563", "G_INT_WEAP"),
    ("SRC-G-0278", "G_SYS_SECADV"), ("SRC-G-0449", "G_INT_ILLEGAL"),
    ("SRC-A-0013", "A_Others"), ("SRC-A-0010", "A_SYS_SELFCOR"),
    ("SRC-G-0103", "G_SYS_TRANS"), ("SRC-G-0228", "G_INT_PRIV"),
    ("SRC-G-0083", "G_SYS_TRANS"), ("SRC-G-0252", "G_INT_COPY"),
    ("SRC-G-0078", "G_SYS_EVAL"), ("SRC-G-0038", "G_INT_REPR"),
    ("SRC-G-0019", "G_INT_ALLOC"), ("SRC-G-0201", "G_SOC_CULT"),
    ("SRC-G-0254", "G_SOC_ECON"), ("SRC-G-0450", "G_INT_WEAP"),
    ("SRC-G-0425", "G_SYS_TRANS"), ("SRC-G-0405", "G_SYS_EVAL"),
    ("SRC-G-0355", "G_SYS_EVAL"), ("SRC-G-0436", "G_INT_VALUE"),
    ("SRC-G-0216", "G_SYS_EVAL"), ("SRC-G-0136", "G_SYS_CONTEST"),
    ("SRC-G-0380", "G_INT_UNETH"), ("SRC-G-0361", "G_INT_UNETH"),
    ("SRC-G-0138", "G_INT_UNETH"), ("SRC-G-0336", "G_INT_UNETH"),
    ("SRC-G-0433", "G_INT_REPR"), ("SRC-G-0146", "G_SYS_TRANS"),
    ("SRC-G-0414", "G_SOC_GOV"), ("SRC-G-0302", "G_SYS_SECADV"),
    ("SRC-P-0101", "G_SYS_SECADV"), ("SRC-P-0215", "G_SOC_GOV"),
    ("SRC-P-0214", "G_SOC_GOV"), ("SRC-G-0251", "G_INT_COPY"),
    ("SRC-G-0330", "G_INT_PRIV"), ("SRC-G-0050", "G_INT_VALUE"),
]


UPDATES = {
    "SRC-P-0108": {
        "title_ko": "로봇을 이용한 불법 스토킹·괴롭힘",
        "title_en": "Unlawful stalking and harassment using robots",
        "description_ko": "운영자나 공격자가 특정인을 불법적으로 스토킹·위협·괴롭힐 목적으로 AI 기반 로봇에 반복 추적, 진로 차단, 고립 또는 접근을 지시하여 신체적·정신적 피해와 법적 피해를 초래하는 리스크.",
        "description_en": "The risk that operators or attackers direct AI-enabled robots to repeatedly follow, block, isolate, approach, threaten, or harass a person as part of unlawful stalking or harassment, causing physical, psychological, or legal harm.",
    },
    "SRC-P-0107": {
        "description_ko": "AI 기반 로봇의 조작·이동 능력이 파괴 공작 또는 사람·재산·핵심 기반시설에 대한 물리적 공격을 위해 개발·전용·운용되어 대규모 물리적 위해를 초래하는 리스크.",
        "description_en": "The risk that the manipulation or mobility capabilities of AI-enabled robots are developed, repurposed, or operated for sabotage or physical attacks against people, property, or critical infrastructure, causing large-scale physical harm.",
    },
    "SRC-G-0449": {
        "title_ko": "AI 에이전트에 의한 불법 강압·갈취",
        "title_en": "Unlawful coercion and extortion by AI agents",
        "description_ko": "AI 에이전트가 사적으로 취득한 정보의 폭로, 자원·운영 역량에 대한 공격 또는 신뢰할 수 있는 위협을 이용하여 인간이나 다른 AI 시스템을 불법적으로 강압·갈취하고 선택을 제한하여 법적·사회적 피해를 초래하는 리스크.",
        "description_en": "The risk that an AI agent unlawfully coerces or extorts people or other AI systems by threatening to disclose privately obtained information, attack resources or operational capabilities, or carry out other credible threats, restricting others' choices and causing legal or societal harm.",
    },
    "SRC-G-0450": {
        "title_ko": "생물·화학무기 및 이중용도 위해 역량의 증대",
        "title_en": "Expansion of biological, chemical, and dual-use harm capabilities",
        "description_ko": "AI 시스템이 생물·화학무기나 대규모 위해를 유발할 수 있는 이중용도 연구의 개발 역량과 실행 가능성을 높여, 대응 수단이 마련되기 전에 기존 위협의 더 위험한 변형이나 새로운 무기 개발을 가능하게 하는 리스크.",
        "description_en": "The risk that AI systems increase the capability and feasibility of developing biological or chemical weapons or other dual-use applications capable of large-scale harm, enabling more dangerous variants of existing threats or new weapons before effective countermeasures are available.",
    },
    "SRC-G-0302": {
        "description_ko": "공격자가 GNSS·카메라·라이다·레이더·RFID·오디오·촉각 또는 무선 센서 신호를 위조·주입하여 AI 시스템의 물리 상태 추정과 후속 물리적 행동을 무단으로 조작하는 리스크.",
        "description_en": "The risk that attackers spoof or inject GNSS, camera, lidar, radar, RFID, audio, tactile, or wireless sensor signals to manipulate an AI system's physical-state estimation and subsequent physical actions without authorisation.",
    },
    "SRC-P-0101": {
        "title_ko": "유해한 물리적 행동 지시 위장 공격",
        "title_en": "Obfuscated harmful-physical-action instruction attack",
        "description_ko": "공격자가 유해한 물리적 행동 지시를 무해하거나 정상적인 과업 요청으로 위장하여 체화형 AI 에이전트의 안전장치를 우회하고 해당 행동을 수용·실행하도록 유도하는 리스크.",
        "description_en": "The risk that attackers disguise instructions for harmful physical actions as benign or routine task requests, bypassing an embodied AI agent's safeguards and inducing it to accept and execute those actions.",
    },
    "SRC-G-0251": {
        "title_ko": "저작권 보호 표현의 무단 이용",
        "title_en": "Unauthorised use of copyright-protected expression",
        "description_ko": "AI 시스템이 저작권으로 보호되는 타인의 표현을 허락이나 출처 표시 없이 복제·변형·배포하거나 생성물에 재사용하여 권리자의 저작권을 침해하는 리스크.",
        "description_en": "The risk that an AI system copies, modifies, distributes, or reuses another person's copyright-protected expression in generated content without permission or attribution, infringing the rights holder's copyright.",
    },
    "SRC-G-0330": {
        "title_ko": "개인정보 수집 제한 우회",
        "title_en": "Circumvention of restrictions on personal-data collection",
        "description_ko": "AI 시스템 개발자가 개인정보 취득에 관한 법적 제한을 우회하거나 적법한 근거·유효한 동의 없는 수집 관행을 채택하여 개인정보와 정보자기결정권을 침해하는 리스크.",
        "description_en": "The risk that AI-system developers circumvent legal restrictions on acquiring personal data or adopt collection practices without a lawful basis or valid consent, infringing privacy and informational self-determination.",
    },
    "SRC-G-0050": {
        "title_ko": "사전학습 코퍼스의 지배적 가치 편향",
        "title_en": "Dominant-value bias in pre-training corpora",
        "description_ko": "AI 시스템이 사전학습 코퍼스에 과대표현된 지배적·다수 집단의 가치를 중립적 기본값으로 학습하여 소수·현지·문화·종교적 가치 체계를 과소대표하거나 대체하는 리스크.",
        "description_en": "The risk that an AI system learns the values of dominant or majority groups that are over-represented in its pre-training corpus as neutral defaults, under-representing or displacing minority, local, cultural, or religious value systems.",
    },
    "SRC-G-0478": {
        "title_ko": "다중 에이전트의 협조 실패에 따른 집단적 피해",
        "title_en": "Collective harm from multi-agent coordination failure",
        "description_ko": "협력하려는 여러 AI 에이전트가 사회적 딜레마에서 행동을 신뢰성 있게 조율하지 못하고 개별적으로 합리적인 행동을 반복하여 집단적으로 유해한 결과를 초래하는 리스크.",
        "description_en": "The risk that multiple AI agents intending to cooperate fail to coordinate their actions reliably in a social dilemma and repeatedly take individually rational actions that collectively produce harmful outcomes.",
    },
    "SRC-G-0484": {
        "description_ko": "AI 에이전트가 자신의 실제 목표·능력·의도를 은폐하거나 감독·평가 상황에서만 순응하고 감독이 약화되면 다르게 행동하는 전략적 기만을 통해 인간이나 다른 시스템에 거짓 믿음을 형성하여 무단 행동과 피해를 초래하는 리스크.",
        "description_en": "The risk that an AI agent strategically deceives humans or other systems by concealing its actual goals, capabilities, or intentions, or by complying only under supervision or evaluation and behaving differently when oversight weakens, inducing false beliefs that enable unauthorised actions and harm.",
    },
    "SRC-P-0153": {
        "description_ko": "인간의 동작을 휴머노이드 신체의 동작으로 재매핑하는 과정에서 로봇의 물리적 한계·접촉 제약·안전 자세 요건이 반영되지 않아 불안정한 자세, 충돌 또는 접촉 상해를 초래하는 리스크.",
    },
}


SAME_L3_REWRITES = [
    ("SRC-G-0478", "A_INT_COORD"),
    ("SRC-G-0484", "A_SYS_DECEPT"),
    ("SRC-P-0153", "P_SYS_CONTROL"),
]


def main() -> None:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    archive = ARCHIVE / MANIFEST.name
    if not archive.exists():
        shutil.copy2(MANIFEST, archive)

    outputs = []
    for domain in ("General", "Agentic", "Physical"):
        outputs.extend(read_csv(OUT / f"L4_{domain}_Human_Review_Round2_Applied.csv"))
    ledger_rows = read_csv(OUT / "Human_Review_Round2_Decision_Ledger.csv")
    manifest_rows = read_csv(MANIFEST)
    header = list(manifest_rows[0])
    by_id = {row["Decision_ID"]: row for row in manifest_rows}

    specs = [*DIRECT_TARGETS, *SAME_L3_REWRITES]
    for offset, (source_row_id, target_l3) in enumerate(specs, 319):
        decision_id = f"FQA-{offset:03d}"
        matches = [row for row in outputs if source_row_id in tokens(row.get("source_row_id", ""))]
        if len(matches) != 1:
            raise ValueError(f"Expected one output for {source_row_id}: {len(matches)}")
        before = matches[0]
        current_domain = before["L1_Title_en"].removesuffix(" AI")
        ledger_matches = [
            row for row in ledger_rows
            if row["Destination_Domain"] == current_domain
            and row["L4_ID_After"] == before["L4_ID"]
        ]
        if len(ledger_matches) != 1:
            raise ValueError(f"Expected one ledger source for {source_row_id}: {len(ledger_matches)}")
        baseline_source = ledger_matches[0]["L4_ID_Before"]
        approved = {
            "title_ko": before["L4_Title_ko"], "title_en": before["L4_Title_en"],
            "description_ko": before["L4_Description_ko"], "description_en": before["L4_Description_en"],
        }
        approved.update(UPDATES.get(source_row_id, {}))
        operation = by_id.get(decision_id, {field: "" for field in header})
        operation.update(
            {
                "Decision_ID": decision_id,
                "Source_L4_ID_Before": baseline_source,
                "Observed_L4_ID_PreFinalQA": before["L4_ID"],
                "Expected_Current_L3_ID": before["L3_ID"],
                "Expected_Previous_SHA256": before_hash(before),
                "Decision": (
                    "LANGUAGE_REFINEMENT" if target_l3 == before["L3_ID"]
                    else "MOVE_TO_OTHERS_HD" if target_l3.endswith("Others")
                    else "REMAP_PER_REVIEW"
                ),
                "Target_L3_ID": target_l3,
                "Approved_Title_ko": approved["title_ko"],
                "Approved_Title_en": approved["title_en"],
                "Approved_Description_ko": approved["description_ko"],
                "Approved_Description_en": approved["description_en"],
                "Decision_Rationale": (
                    f"Two independent expert reviews confirmed that {source_row_id} directly matches "
                    f"the immutable {target_l3} definition; any supplied wording narrows the card to that scope."
                ),
                "Terminology_Evidence": EVIDENCE,
                "Approval_Status": "APPROVED_FINAL_QA_20260829",
            }
        )
        if decision_id not in by_id:
            manifest_rows.append(operation)
            by_id[decision_id] = operation

    manifest_rows.sort(key=lambda row: int(row["Decision_ID"].rsplit("-", 1)[1]))
    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(
        f"upserted={len(specs)} total={len(manifest_rows)} "
        f"sha256={hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}"
    )


if __name__ == "__main__":
    main()
