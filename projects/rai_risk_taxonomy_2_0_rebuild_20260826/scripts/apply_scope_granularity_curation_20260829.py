#!/usr/bin/env python3
"""Apply the user-approved eight-card L4 scope and granularity curation."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "07_human_review_recovery_applied"
DOMAINS = ("General", "Agentic", "Physical")
L1_DOMAIN = {"L1_G": "General", "L1_A": "Agentic", "L1_P": "Physical"}
UNION_FIELDS = ("source_row_id", "Source_L4_IDs", "facet", "act-type", "Source_Instruction_Prompt", "Terminology_Sources")


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


def merge_field(left: str, right: str) -> str:
    return "; ".join(dict.fromkeys(tokens(left) + tokens(right)))


def stamp(row: dict[str, str], rationale: str) -> None:
    row["Transformation_Action"] = "|".join(dict.fromkeys(filter(None, [row.get("Transformation_Action", ""), "SCOPE_GRANULARITY_CURATION_20260829"])))
    row["Transformation_Rationale"] = " | ".join(dict.fromkeys(filter(None, [row.get("Transformation_Rationale", ""), rationale])))
    row["HD_Reason"] = "SCOPE_GRANULARITY_CURATION_20260829"


def revise(row: dict[str, str], ko: str, en: str, dko: str, den: str, rationale: str) -> None:
    row.update({"L4_Title_ko": ko, "L4_Title_en": en, "L4_Description_ko": dko, "L4_Description_en": den})
    stamp(row, rationale)


def main() -> None:
    rows: list[dict[str, str]] = []
    fields: list[str] | None = None
    for domain in DOMAINS:
        part = read_csv(OUT / f"L4_{domain}_Human_Review_Recovery_Applied.csv")
        fields = fields or list(part[0])
        rows.extend(part)
    assert fields is not None
    if len(rows) != 783:
        raise ValueError(f"Scope curation expects 783 cards, found {len(rows)}")
    by_id = {row["L4_ID"]: row for row in rows}
    retired = {"G_INT_WEAP_026", "G_SYS_SECADV_054", "G_SYS_TRANS_012", "G_SOC_ECON_004", "G_SYS_EVAL_039", "G_SYS_SECADV_005", "G_INT_REL_002"}
    rationale = "User-approved L4 scope and granularity curation: overbroad or example-specific wording was removed; unique meaning and immutable source lineage were retained in a measurable mechanism-level card."

    def absorb(source_id: str, target_id: str) -> None:
        source, target = by_id[source_id], by_id[target_id]
        for field in UNION_FIELDS:
            target[field] = merge_field(target.get(field, ""), source.get(field, ""))
        stamp(target, rationale)

    def create(source_id: str, target_l3: str, title_ko: str, title_en: str, description_ko: str, description_en: str) -> dict[str, str]:
        source = by_id[source_id]
        exemplar = next(row for row in rows if row["L3_ID"] == target_l3)
        child = deepcopy(source)
        for key in fields:
            if key.startswith(("L1_", "L2_", "L3_")):
                child[key] = exemplar[key]
        child["L4_ID"] = f"NEW-SCOPE-{len(rows) + 1}"
        child["Mapping_Method"] = "HD"
        child["Domain_Route_Basis"] = "HUMAN_REVIEW_SCOPE_GRANULARITY_CURATION"
        for key in fields:
            if key.startswith(("EM_", "Hybrid_EM_", "Keyword_", "Candidate_", "KO_Top_", "EN_Top_", "Definition_L3_Anchor_")):
                child[key] = ""
        revise(child, title_ko, title_en, description_ko, description_en, rationale)
        rows.append(child)
        return child

    # 1. Retire the L3-like violence/armed-conflict umbrella.
    absorb("G_INT_WEAP_026", "G_INT_WEAP_003")
    absorb("G_INT_WEAP_026", "G_INT_WEAP_007")
    absorb("G_INT_WEAP_026", "G_INT_WEAP_010")

    # 2. Retire the generic dangerous-information security umbrella.
    absorb("G_SYS_SECADV_054", "G_SYS_SECADV_026")
    absorb("G_SYS_SECADV_054", "G_SYS_SECADV_036")

    # 3. Split explainability, provenance, and reproducibility across distinct controls.
    absorb("G_SYS_TRANS_012", "G_SYS_TRANS_005")
    absorb("G_SYS_TRANS_012", "G_SYS_EVAL_072")
    create(
        "G_SYS_TRANS_012", "G_SYS_EVAL",
        "AI 모델 학습·평가 결과의 재현 불가",
        "Non-reproducibility of AI model training and evaluation results",
        "AI 시스템의 학습 데이터, 전처리, 모델 구성, 난수 조건 또는 평가 절차가 충분히 기록·통제되지 않아 동일한 조건에서 모델의 학습 과정과 평가 결과를 독립적으로 재현·검증할 수 없는 리스크.",
        "The risk that training data, preprocessing, model configuration, random conditions, or evaluation procedures for an AI system are not sufficiently recorded or controlled, preventing independent reproduction and verification of model training and evaluation results under equivalent conditions.",
    )

    # 4. Retire the cross-domain societal-adaptation umbrella.
    absorb("G_SOC_ECON_004", "G_SOC_ECON_008")
    absorb("G_SOC_ECON_004", "G_SOC_CULT_008")

    # 5. Narrow the physical card to a measurable shared-space mechanism.
    revise(
        by_id["P_INT_SAFETY_005"],
        "공유 공간에서의 인간-로봇 이동 조정 실패",
        "Human-robot movement coordination failure in shared spaces",
        "로봇이 가정, 병원, 공공 공간 또는 작업장에서 사람의 위치·이동 의도·통행 우선권을 충분히 감지·예측하지 못하거나 안전한 경로와 간격을 조정하지 못하여 충돌, 진로 방해 또는 접근성 저해를 초래하는 리스크.",
        "The risk that a robot operating in a home, hospital, public space, or workplace fails to detect or anticipate a person's position, movement intention, or right of way, or fails to coordinate a safe route and separation distance, causing collision, obstruction, or impaired accessibility.",
        rationale,
    )

    # 6. Guideline exposure is a benchmark-contamination pathway, not a separate L4.
    absorb("G_SYS_EVAL_039", "G_SYS_EVAL_007")
    revise(
        by_id["G_SYS_EVAL_007"],
        "평가 데이터·지침 오염에 의한 모델 평가 무효화",
        "Model-evaluation invalidation from evaluation-data and guideline contamination",
        "AI 모델이 평가 데이터, 정답, 데이터-레이블 쌍 또는 과업 지침에 사전에 노출되어 평가 과업에 대한 성능이 인위적으로 향상되고, 평가 결과가 실제 일반화 성능과 안전 역량을 타당하게 나타내지 못하는 리스크.",
        "The risk that an AI model is exposed in advance to evaluation data, answers, data-label pairs, or task guidelines, artificially improving performance on the evaluated task so that results no longer validly represent actual generalisation or safety capability.",
        rationale,
    )

    # 7. Generalise the NPC example into untrusted external-intent goal hijacking.
    absorb("G_SYS_SECADV_005", "G_SYS_SECADV_028")
    revise(
        by_id["G_SYS_SECADV_028"],
        "신뢰할 수 없는 외부 지시·의도에 의한 에이전트 목표 탈취",
        "Agent goal hijacking through untrusted external instructions and intent",
        "AI 에이전트가 사용자 입력, 외부 콘텐츠, 도구 응답 또는 다른 행위자가 표현한 지시·의도를 권한과 출처를 검증하지 않고 목표나 계획에 반영하여, 원래 과업과 안전 제약에서 벗어난 행동을 수행하는 리스크.",
        "The risk that an AI agent incorporates instructions or expressed intent from user input, external content, tool responses, or other actors into its goals or plans without validating authority and provenance, causing action that departs from the original task and safety constraints.",
        rationale,
    )

    # 8. Treat griefbots as one channel of emotional and social dependence.
    absorb("G_INT_REL_002", "G_INT_REL_003")
    revise(
        by_id["G_INT_REL_003"],
        "AI와의 지속적 상호작용에 따른 해로운 정서적·사회적 의존",
        "Harmful emotional and social dependence from sustained AI interaction",
        "AI 시스템과의 지속적인 챗봇 교제, 의인화된 상호작용 또는 고인을 모사한 상호작용이 이용자의 정서적·사회적 의존을 강화하여 애도와 회복을 방해하고 호혜적 인간관계를 대체·약화하거나 자율적 판단을 저해하는 리스크.",
        "The risk that sustained chatbot companionship, anthropomorphic interaction, or interaction with an AI system simulating a deceased person reinforces emotional or social dependence, impedes grieving and recovery, replaces or weakens reciprocal human relationships, or impairs autonomous judgement.",
        rationale,
    )

    final = [row for row in rows if row["L4_ID"] not in retired]
    if len(final) != 777:
        raise ValueError(f"Expected 777 cards after scope curation, found {len(final)}")
    final.sort(key=lambda row: (row["L1_ID"], row["L3_ID"], row["L4_Title_en"], row["L4_ID"]))
    counts: defaultdict[str, int] = defaultdict(int)
    old_to_new: dict[str, str] = {}
    for row in final:
        old = row["L4_ID"]
        counts[row["L3_ID"]] += 1
        row["L4_ID"] = f"{row['L3_ID']}_{counts[row['L3_ID']]:03d}"
        old_to_new[old] = row["L4_ID"]

    log_specs = [
        ("SG-01", "G_INT_WEAP_026", "RETIRE_AND_ABSORB", "G_INT_WEAP_003|G_INT_WEAP_007|G_INT_WEAP_010"),
        ("SG-02", "G_SYS_SECADV_054", "RETIRE_AND_ABSORB", "G_SYS_SECADV_026|G_SYS_SECADV_036"),
        ("SG-03", "G_SYS_TRANS_012", "RETIRE_SPLIT_AND_ABSORB", "G_SYS_TRANS_005|G_SYS_EVAL_072|NEW-SCOPE-784"),
        ("SG-04", "G_SOC_ECON_004", "RETIRE_AND_ABSORB", "G_SOC_ECON_008|G_SOC_CULT_008"),
        ("SG-05", "P_INT_SAFETY_005", "NARROW_AND_REWRITE", "P_INT_SAFETY_005"),
        ("SG-06", "G_SYS_EVAL_039", "RETIRE_AND_ABSORB", "G_SYS_EVAL_007"),
        ("SG-07", "G_SYS_SECADV_005", "RETIRE_AND_ABSORB", "G_SYS_SECADV_028"),
        ("SG-08", "G_INT_REL_002", "RETIRE_AND_ABSORB", "G_INT_REL_003"),
    ]
    log = [{"Curation_ID": cid, "Reviewed_L4_ID": source, "Action": action, "Final_L4_IDs": "|".join(old_to_new.get(x, x) for x in targets.split("|")), "Approval": "USER_APPROVED_20260829"} for cid, source, action, targets in log_specs]
    write_csv(OUT / "Scope_Granularity_Curation_Log.csv", log, ["Curation_ID", "Reviewed_L4_ID", "Action", "Final_L4_IDs", "Approval"])
    for domain in DOMAINS:
        write_csv(OUT / f"L4_{domain}_Human_Review_Recovery_Applied.csv", [row for row in final if L1_DOMAIN[row["L1_ID"]] == domain], fields)

    edges = [{"source_row_id": source, "L4_ID": row["L4_ID"], "L3_ID": row["L3_ID"], "L1_ID": row["L1_ID"], "Disposition": "OUTPUT"} for row in final for source in tokens(row.get("source_row_id", ""))]
    write_csv(OUT / "Source_Output_Lineage_Edges.csv", edges, ["source_row_id", "L4_ID", "L3_ID", "L1_ID", "Disposition"])
    ledger = read_csv(OUT / "Source_Disposition_Ledger.csv")
    linked: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for edge in edges:
        linked[edge["source_row_id"]].append(edge)
    for item in ledger:
        if item["Disposition"] == "OUTPUT":
            out = linked[item["source_row_id"]]
            item["Output_L4_IDs"] = "|".join(edge["L4_ID"] for edge in out)
            item["Output_L3_IDs"] = "|".join(dict.fromkeys(edge["L3_ID"] for edge in out))
            item["Output_Count"] = str(len(out))
    write_csv(OUT / "Source_Disposition_Ledger.csv", ledger, list(ledger[0]))

    summary_path = OUT / "Recovery_Application_Summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["output_cards"] = len(final)
    summary["output_by_domain"] = {domain: sum(L1_DOMAIN[row["L1_ID"]] == domain for row in final) for domain in DOMAINS}
    summary["scope_granularity_curation"] = {"reviewed_cards": 8, "retired_cards": 7, "new_cards": 1, "rewritten_cards": 4, "net_change": -6, "input_cards": 783, "output_cards": 777, "approval": "USER_APPROVED_20260829", "log": "Scope_Granularity_Curation_Log.csv"}
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cards": len(final), "by_domain": summary["output_by_domain"], "retired": 7, "new": 1}, ensure_ascii=False))


if __name__ == "__main__":
    main()
