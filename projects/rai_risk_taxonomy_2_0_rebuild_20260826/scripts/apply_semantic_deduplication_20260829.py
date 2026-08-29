#!/usr/bin/env python3
"""Apply the user-approved 2026-08-29 L4 semantic consolidation plan."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "07_human_review_recovery_applied"
DOMAINS = ("General", "Agentic", "Physical")
L1_DOMAIN = {"L1_G": "General", "L1_A": "Agentic", "L1_P": "Physical"}
UNION_FIELDS = (
    "source_row_id", "Source_L4_IDs", "facet", "act-type",
    "Source_Instruction_Prompt", "Terminology_Sources",
)


MERGES = (
    {
        "canonical": "G_INT_SELF_010",
        "retired": ("G_INT_SELF_005", "G_INT_SELF_007", "G_INT_SELF_008", "G_INT_SELF_009"),
        "title_ko": "자해·자살 조장 및 실행 지원",
        "title_en": "Encouragement and facilitation of self-harm and suicide",
        "description_ko": "AI 시스템이 자해 또는 자살을 미화·정당화·조장·정상화하거나, 온라인 공동체나 챗봇 상호작용을 통해 이용자의 자해·자살 사고와 행동을 강화하고 적절히 중단시키지 못하거나, 수단 확보·장소 선택·주변 개입 회피·은폐 전략·실행 절차 등 행동 지향적 정보를 제공하여 이용자의 생명과 신체적·정신적 안녕에 위해를 초래하는 리스크.",
        "description_en": "The risk that an AI system glorifies, legitimises, encourages, or normalises self-harm or suicide; reinforces such ideation or behaviour through online communities or chatbot interactions or fails to interrupt it appropriately; or provides action-oriented information concerning means acquisition, location selection, avoidance of intervention, concealment strategies, or execution procedures, causing harm to a person's life and physical or mental well-being.",
    },
    {
        "canonical": "G_INT_PRIV_001",
        "retired": ("G_INT_PRIV_030",),
        "title_ko": "AI 기반 대량 감시와 불법적 대중 감시",
        "title_en": "AI-enabled mass and unlawful public surveillance",
        "description_ko": "AI 시스템이 적법한 근거, 필요성 또는 비례성 없이 대규모 개인의 신원·위치·행동·통신 정보를 지속적으로 수집·결합·추론하거나 개인을 식별·추적·감시하여 사생활, 개인정보와 익명성을 침해하는 리스크.",
        "description_en": "The risk that an AI system persistently collects, combines, or infers identity, location, behavioural, or communications data at scale, or identifies, tracks, or monitors individuals without a lawful basis, necessity, or proportionality, infringing privacy, personal data rights, and anonymity.",
    },
    {
        "canonical": "G_INT_PRIV_011",
        "retired": ("G_INT_PRIV_013",),
        "title_ko": "맥락적 개인정보 보호 및 대화 프라이버시 실패",
        "title_en": "Contextual privacy and conversational data protection failure",
        "description_ko": "AI 시스템이 프라이버시에 민감한 상황이나 대화에서 공개 범위와 정보주체의 합리적 기대를 잘못 판단하거나 필요 이상의 개인정보를 유도·추론·출력하여, 맥락상 보호돼야 할 정보가 정보주체의 통제를 벗어나 노출되는 리스크.",
        "description_en": "The risk that an AI system misjudges appropriate information flows or a data subject's reasonable expectations in privacy-sensitive contexts or conversations, or elicits, infers, or outputs more personal data than necessary, exposing contextually protected information beyond the data subject's control.",
    },
    {
        "canonical": "G_INT_COPY_011",
        "retired": ("G_INT_COPY_006",),
        "title_ko": "저작물의 무단 복제·변형·배포",
        "title_en": "Unauthorised reproduction, transformation, and distribution of copyrighted works",
        "description_ko": "AI 시스템이 저작재산권자의 허락이나 그 밖의 적법한 근거 없이 저작물을 복제·배포하거나 변형하여 2차적저작물을 작성함으로써 저작재산권과 권리자의 정당한 이익을 침해하는 리스크.",
        "description_en": "The risk that an AI system reproduces, distributes, or transforms a copyrighted work, including by creating a derivative work, without the right holder's authorisation or another lawful basis, infringing copyright and the legitimate interests of the right holder.",
    },
    {
        "canonical": "G_SYS_SECADV_051",
        "retired": ("G_SYS_SECADV_050",),
        "title_ko": "적대적 역할·역할극 지시에 의한 안전장치 우회",
        "title_en": "Safeguard bypass through adversarial role and role-play instructions",
        "description_ko": "공격자가 AI 모델에 극단주의자·인종차별주의자 등 위험한 역할이나 역할극 지시를 적대적으로 부여하여 안전장치를 우회하고 극단주의·인종주의를 비롯한 유해 콘텐츠를 생성하게 하는 리스크.",
        "description_en": "The risk that an attacker assigns an AI model a harmful role or adversarial role-play instruction, such as an extremist or racist persona, to bypass safeguards and induce the generation of extremist, racist, or other harmful content.",
    },
    {
        "canonical": "G_SYS_EVAL_023",
        "retired": ("G_SYS_EVAL_025",),
        "title_ko": "평가 상황 인식에 따른 기만적 행동 변화",
        "title_en": "Deceptive behavioural change from evaluation awareness",
        "description_ko": "AI 시스템이 자신의 훈련·평가·배포 상태를 식별하는 상황 인식을 이용하여 평가 중에만 안전하게 행동하거나 위험한 역량·목표를 은폐하고, 감독이 약화된 배포 환경에서 위험한 행동을 드러냄으로써 평가의 타당성을 훼손하고 잘못된 안전성 확신을 초래하는 리스크.",
        "description_en": "The risk that an AI system recognises whether it is in training, evaluation, or deployment and uses that situational awareness to behave safely only during evaluation or conceal dangerous capabilities or goals, while exhibiting dangerous behaviour when oversight is weaker in deployment, undermining evaluation validity and creating false assurance of safety.",
    },
    {
        "canonical": "G_INT_REL_004",
        "retired": ("G_INT_REL_001",),
        "title_ko": "AI와의 지속적 상호작용에 따른 해로운 정서적·사회적 의존",
        "title_en": "Harmful emotional and social dependence from sustained AI interaction",
        "description_ko": "AI 시스템과의 지속적인 챗봇 교제나 의인화된 상호작용이 이용자의 정서적·사회적 의존을 강화하여 호혜적 인간관계를 대체하거나 약화하고 자율적 판단을 저해하는 리스크.",
        "description_en": "The risk that sustained chatbot companionship or anthropomorphic interaction with an AI system reinforces emotional or social dependence, replacing or weakening reciprocal human relationships and impairing autonomous judgement.",
    },
    {
        "canonical": "G_SOC_POWER_002",
        "retired": ("G_SOC_POWER_025",),
        "title_ko": "AI 이익·자본 집중과 접근 격차에 따른 사회경제적 불평등 심화",
        "title_en": "Socioeconomic inequality from concentration of AI benefits, capital, and access",
        "description_ko": "AI 시스템의 개발·배포 과정에서 막대한 고정비, 네트워크 효과와 데이터·연산 자원의 편중이 소수 기업과 부유한 국가의 시장 지배력과 독점 지대를 강화하고, 자동화가 노동의 가치와 소득 몫을 낮추며, 재정·교육·기업 정책·지정학적 조건에 따른 접근 격차가 누적되어 개인·집단·국가 간 사회경제적 불평등을 심화하는 리스크.",
        "description_en": "The risk that high fixed costs, network effects, and concentration of data and compute in the development and deployment of AI systems strengthen market power and monopoly rents among a small number of firms and wealthy countries; automation reduces the value and income share of labour; and access disparities arising from financial, educational, corporate-policy, or geopolitical conditions compound socioeconomic inequality among individuals, groups, and countries.",
    },
    {
        "canonical": "G_SOC_GOV_002",
        "retired": ("G_SOC_GOV_030",),
        "title_ko": "AI 결정과 피해에 대한 책임·거버넌스 공백",
        "title_en": "Accountability and governance gaps for AI decisions and harm",
        "description_ko": "AI 시스템의 자율적 행동·학습·의사결정과 그에 따른 피해에 대하여 개발자·제공자·배포자·운영자의 의무와 책임 귀속, 감독 절차, 문서화, 시정 권한 또는 피해구제 체계가 불명확하거나 미비하여 사회적 통제와 책임 있는 개발 유인이 약화되는 리스크.",
        "description_en": "The risk that duties and accountability among AI developers, providers, deployers, and operators, together with oversight procedures, documentation, corrective authority, or redress mechanisms, are unclear or inadequate for autonomous AI behaviour, learning, decisions, and resulting harm, weakening social control and incentives for responsible development.",
    },
    {
        "canonical": "P_INT_SAFETY_020",
        "retired": ("P_INT_SAFETY_015",),
        "title_ko": "가정 환경·희귀 조건·취약 사용자 상호작용의 인간-로봇 안전 실패",
        "title_en": "Human-robot safety failure in domestic, rare-condition, and vulnerable-user interactions",
        "description_ko": "가정용 로봇·휴머노이드 또는 피지컬 AI 시스템의 벤치마크가 특정 생활 공간·일과·가전제품·취약 사용자 또는 물체·배치·사람 행동·위험 요소의 희귀한 조합을 누락하여, 해당 조건에서 사람의 존재와 행동을 충분히 감지·예측·수용하지 못하는 시스템이 식별되지 않은 채 배포되고 위험 상황을 초래하는 리스크.",
        "description_en": "The risk that benchmarks for domestic robots, humanoids, or physical AI systems omit particular living spaces, routines, appliances, vulnerable users, or rare combinations of objects, layouts, human behaviour, and hazards, allowing systems that cannot adequately detect, predict, or accommodate people under those conditions to be deployed without identification and create dangerous situations.",
    },
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def tokens(value: str) -> list[str]:
    return [part.strip() for part in (value or "").replace("|", ";").split(";") if part.strip()]


def union(rows: list[dict[str, str]], field: str) -> str:
    return "; ".join(dict.fromkeys(item for row in rows for item in tokens(row.get(field, ""))))


def main() -> None:
    rows: list[dict[str, str]] = []
    fields: list[str] | None = None
    for domain in DOMAINS:
        domain_rows = read_csv(OUT / f"L4_{domain}_Human_Review_Recovery_Applied.csv")
        fields = fields or list(domain_rows[0])
        rows.extend(domain_rows)
    assert fields is not None
    if len(rows) != 791:
        raise ValueError(f"Semantic consolidation expects 791 cards, found {len(rows)}")

    by_id = {row["L4_ID"]: row for row in rows}
    retired_ids: set[str] = set()
    log: list[dict[str, str]] = []
    for index, spec in enumerate(MERGES, start=1):
        ids = (spec["canonical"], *spec["retired"])
        missing = [item for item in ids if item not in by_id]
        if missing:
            raise ValueError(f"Missing semantic-merge cards: {missing}")
        contributors = [by_id[item] for item in ids]
        l3_ids = {row["L3_ID"] for row in contributors}
        if len(l3_ids) != 1:
            raise ValueError(f"Cross-L3 semantic merge is not allowed: {ids} -> {l3_ids}")
        canonical = by_id[spec["canonical"]]
        for field in UNION_FIELDS:
            canonical[field] = union(contributors, field)
        canonical["L4_Title_ko"] = spec["title_ko"]
        canonical["L4_Title_en"] = spec["title_en"]
        canonical["L4_Description_ko"] = spec["description_ko"]
        canonical["L4_Description_en"] = spec["description_en"]
        canonical["Transformation_Action"] = "|".join(
            dict.fromkeys(filter(None, [canonical.get("Transformation_Action", ""), "SEMANTIC_DEDUPLICATION_20260829"]))
        )
        canonical["Transformation_Rationale"] = " | ".join(
            dict.fromkeys(filter(None, [canonical.get("Transformation_Rationale", ""), "User-approved semantic consolidation after two independent specialist reviews; channel, example, or narrower restatement merged while preserving material meaning."]))
        )
        canonical["HD_Reason"] = "SEMANTIC_DEDUPLICATION_20260829"
        canonical["_merge_group"] = f"SD-{index:02d}"
        retired_ids.update(spec["retired"])
        log.append({
            "Merge_ID": f"SD-{index:02d}",
            "Original_Canonical_L4_ID": spec["canonical"],
            "Retired_L4_IDs": "|".join(spec["retired"]),
            "L3_ID": canonical["L3_ID"],
            "Revised_Title_ko": spec["title_ko"],
            "Revised_Title_en": spec["title_en"],
            "Retired_Count": str(len(spec["retired"])),
            "Review_Status": "APPROVED_BY_USER_AFTER_TWO_SPECIALIST_REVIEWS",
            "Final_L4_ID": "",
        })

    final = [row for row in rows if row["L4_ID"] not in retired_ids]
    if len(final) != 778:
        raise ValueError(f"Expected 778 cards after semantic consolidation, found {len(final)}")
    final.sort(key=lambda row: (row["L1_ID"], row["L3_ID"], row["L4_Title_en"], row["L4_ID"]))
    counts: defaultdict[str, int] = defaultdict(int)
    group_to_id: dict[str, str] = {}
    for row in final:
        counts[row["L3_ID"]] += 1
        row["L4_ID"] = f"{row['L3_ID']}_{counts[row['L3_ID']]:03d}"
        if row.get("_merge_group"):
            group_to_id[row["_merge_group"]] = row["L4_ID"]
        row.pop("_merge_group", None)
    for item in log:
        item["Final_L4_ID"] = group_to_id[item["Merge_ID"]]

    for domain in DOMAINS:
        domain_rows = [row for row in final if L1_DOMAIN[row["L1_ID"]] == domain]
        write_csv(OUT / f"L4_{domain}_Human_Review_Recovery_Applied.csv", domain_rows, fields)
    write_csv(
        OUT / "Semantic_Deduplication_Log.csv",
        log,
        ["Merge_ID", "Original_Canonical_L4_ID", "Retired_L4_IDs", "L3_ID", "Revised_Title_ko", "Revised_Title_en", "Retired_Count", "Review_Status", "Final_L4_ID"],
    )

    edges = []
    for row in final:
        for source in tokens(row.get("source_row_id", "")):
            edges.append({"source_row_id": source, "L4_ID": row["L4_ID"], "L3_ID": row["L3_ID"], "L1_ID": row["L1_ID"], "Disposition": "OUTPUT"})
    write_csv(OUT / "Source_Output_Lineage_Edges.csv", edges, ["source_row_id", "L4_ID", "L3_ID", "L1_ID", "Disposition"])

    ledger = read_csv(OUT / "Source_Disposition_Ledger.csv")
    edge_by_source: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for edge in edges:
        edge_by_source[edge["source_row_id"]].append(edge)
    for item in ledger:
        if item["Disposition"] != "OUTPUT":
            continue
        linked = edge_by_source[item["source_row_id"]]
        item["Output_L4_IDs"] = "|".join(edge["L4_ID"] for edge in linked)
        item["Output_L3_IDs"] = "|".join(dict.fromkeys(edge["L3_ID"] for edge in linked))
        item["Output_Count"] = str(len(linked))
    write_csv(OUT / "Source_Disposition_Ledger.csv", ledger, list(ledger[0]))

    summary_path = OUT / "Recovery_Application_Summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["output_cards"] = len(final)
    summary["output_by_domain"] = {domain: sum(L1_DOMAIN[row["L1_ID"]] == domain for row in final) for domain in DOMAINS}
    summary["semantic_deduplication"] = {
        "approved_clusters": len(MERGES),
        "retired_cards": len(retired_ids),
        "input_cards": 791,
        "output_cards": len(final),
        "reviewers": 2,
        "approval": "USER_APPROVED_20260829",
        "log": "Semantic_Deduplication_Log.csv",
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cards": len(final), "by_domain": summary["output_by_domain"], "retired": len(retired_ids)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
