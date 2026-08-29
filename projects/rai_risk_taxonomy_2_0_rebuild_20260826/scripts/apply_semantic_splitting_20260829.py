#!/usr/bin/env python3
"""Apply the user-approved semantic split and absorption review to L4 cards."""

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
    row["Transformation_Action"] = "|".join(dict.fromkeys(filter(None, [row.get("Transformation_Action", ""), "SEMANTIC_SPLIT_20260829"])))
    row["Transformation_Rationale"] = " | ".join(dict.fromkeys(filter(None, [row.get("Transformation_Rationale", ""), rationale])))
    row["HD_Reason"] = "SEMANTIC_SPLIT_20260829"


def revise(row: dict[str, str], title_ko: str, title_en: str, description_ko: str, description_en: str, rationale: str) -> None:
    row.update({"L4_Title_ko": title_ko, "L4_Title_en": title_en, "L4_Description_ko": description_ko, "L4_Description_en": description_en})
    stamp(row, rationale)


def main() -> None:
    rows: list[dict[str, str]] = []
    fields: list[str] | None = None
    for domain in DOMAINS:
        part = read_csv(OUT / f"L4_{domain}_Human_Review_Recovery_Applied.csv")
        fields = fields or list(part[0])
        rows.extend(part)
    assert fields is not None
    if len(rows) != 778:
        raise ValueError(f"Semantic splitting expects 778 cards, found {len(rows)}")
    by_id = {row["L4_ID"]: row for row in rows}
    retired = {"G_INT_SELF_003", "G_SOC_DEMOC_002"}
    log: list[dict[str, str]] = []

    def absorb(source_id: str, target_id: str, rationale: str) -> None:
        source, target = by_id[source_id], by_id[target_id]
        for field in UNION_FIELDS:
            target[field] = merge_field(target.get(field, ""), source.get(field, ""))
        stamp(target, rationale)

    def create(source_id: str, target_l3: str, title_ko: str, title_en: str, description_ko: str, description_en: str, rationale: str) -> dict[str, str]:
        source = by_id[source_id]
        exemplar = next(row for row in rows if row["L3_ID"] == target_l3)
        child = deepcopy(source)
        for key in fields:
            if key.startswith("L1_") or key.startswith("L2_") or key.startswith("L3_"):
                child[key] = exemplar[key]
        child["L4_ID"] = f"NEW-{len(rows) + 1}"
        child["Mapping_Method"] = "HD"
        child["Domain_Route_Basis"] = "HUMAN_REVIEW_SEMANTIC_SPLIT"
        for key in fields:
            if key.startswith(("EM_", "Hybrid_EM_", "Keyword_", "Candidate_", "KO_Top_", "EN_Top_", "Definition_L3_Anchor_")):
                child[key] = ""
        revise(child, title_ko, title_en, description_ko, description_en, rationale)
        rows.append(child)
        by_id[child["L4_ID"]] = child
        return child

    rationale = "User-approved semantic splitting after source-instruction and L3-master review; distinct mechanisms were separated and already represented meanings were absorbed without duplicating cards."

    # 1. Health umbrella: absorb represented branches and create two distinct interaction risks.
    absorb("G_INT_SELF_003", "G_INT_SELF_004", rationale)
    absorb("G_INT_SELF_003", "G_INT_SELF_005", rationale)
    create("G_INT_SELF_003", "G_INT_SELF", "AI 생성 콘텐츠에 의한 공황·불안 유발", "Panic and anxiety induced by AI-generated content", "AI 시스템이 위협적·충격적이거나 맥락상 부적절한 콘텐츠를 생성·제시하여 이용자에게 공황, 극심한 불안 또는 심리적 고통을 유발하거나 악화하는 리스크.", "The risk that an AI system generates or presents threatening, distressing, or contextually inappropriate content that induces or aggravates panic, severe anxiety, or psychological distress in a user.", rationale)
    create("G_INT_SELF_003", "G_SYS_MISINFO", "오도성 의료정보와 부적절한 약물사용 지침", "Misleading medical information and unsafe medication guidance", "AI 시스템이 사실과 다르거나 근거가 불충분한 의료정보 또는 부적절한 약물사용 지침을 생성·제공하여 이용자의 진단·치료 판단을 왜곡하고 신체적·정신적 건강에 위해를 초래하는 리스크.", "The risk that an AI system generates or provides factually incorrect or insufficiently supported medical information or unsafe medication guidance, distorting a user's diagnostic or treatment decisions and causing harm to physical or mental health.", rationale)

    # 2. Data misuse: retain erroneous-conclusion mechanism and absorb confidentiality/ecosystem branches.
    revise(by_id["G_SYS_MISINFO_008"], "데이터 오해석에 의한 의료·과학적 오결론", "Erroneous medical and scientific conclusions from data misinterpretation", "AI 시스템이 의료·과학 데이터를 오용하거나 맥락, 품질 또는 불확실성을 잘못 해석하여 근거가 부족하거나 사실과 다른 결론을 생성하고 연구·진료 의사결정을 왜곡하는 리스크.", "The risk that an AI system misuses medical or scientific data or misinterprets its context, quality, or uncertainty, producing unsupported or factually incorrect conclusions that distort research or clinical decision-making.", rationale)
    absorb("G_SYS_MISINFO_008", "G_SYS_MISINFO_006", rationale)

    # 3. Intellectual property versus personality rights.
    revise(by_id["G_INT_COPY_005"], "저작권·상표권·특허 침해", "Copyright, trademark, and patent infringement", "AI 시스템의 개발·학습·배포 또는 산출물 이용 과정에서 적법한 권원 없이 저작물, 상표 또는 특허기술을 사용·복제·변형·표시하여 권리자의 지식재산권과 정당한 이익을 침해하는 리스크.", "The risk that the development, training, deployment, or use of an AI system or its outputs uses, reproduces, transforms, or displays copyrighted works, trademarks, or patented technology without lawful authorisation, infringing intellectual property rights and the legitimate interests of right holders.", rationale)
    create("G_INT_COPY_005", "G_INT_PRIV", "이름·이미지·초상의 무단 상업적 이용", "Unauthorised commercial use of name, image, and likeness", "AI 시스템이 당사자의 동의나 그 밖의 적법한 근거 없이 개인의 이름, 이미지, 음성 또는 초상을 생성·모사·유통하거나 상업적으로 이용하여 인격권, 사생활과 자기표현에 대한 통제를 침해하는 리스크.", "The risk that an AI system generates, imitates, distributes, or commercially exploits a person's name, image, voice, or likeness without consent or another lawful basis, infringing personality rights, privacy, and control over self-presentation.", rationale)

    # 4. Personal data versus organisational confidential information.
    revise(by_id["G_INT_PRIV_011"], "산출물을 통한 개인 민감정보의 노출·재식별", "Exposure and re-identification of sensitive personal information through outputs", "AI 시스템이 산출물에서 개인의 민감정보를 공개하거나 여러 정보로부터 보호되는 속성을 추론·재구성·재식별하여 정보주체의 개인정보 보호와 통제권을 침해하는 리스크.", "The risk that an AI system discloses sensitive personal information in its outputs or infers, reconstructs, or re-identifies protected attributes from multiple sources, infringing personal data protection and the data subject's control.", rationale)
    trade = create("G_INT_PRIV_011", "G_INT_COPY", "기업 기밀·영업비밀의 노출", "Exposure of confidential business information and trade secrets", "AI 시스템이 산출물에서 기업의 비공개 연구자료, 독점적 정보 또는 영업비밀을 재현·추론·공개하여 기밀성과 권리자의 정당한 경제적 이익을 침해하는 리스크.", "The risk that an AI system reproduces, infers, or discloses non-public research, proprietary information, or trade secrets in its outputs, breaching confidentiality and the right holder's legitimate economic interests.", rationale)
    for source_id in ("G_SYS_MISINFO_008",):
        for field in UNION_FIELDS:
            trade[field] = merge_field(trade.get(field, ""), by_id[source_id].get(field, ""))
            by_id["G_INT_PRIV_011"][field] = merge_field(by_id["G_INT_PRIV_011"].get(field, ""), by_id[source_id].get(field, ""))

    # 5. Retire the civic/political umbrella and absorb its three concrete mechanisms.
    for target in ("G_INT_POL_006", "G_INT_PRIV_001", "G_INT_ALLOC_008"):
        absorb("G_SOC_DEMOC_002", target, rationale)

    # 6-7. Separate cyber enablement from dangerous science, and resource exhaustion from compromise.
    absorb("G_INT_WEAP_021", "G_INT_WEAP_007", rationale)
    revise(by_id["G_INT_WEAP_021"], "위험한 과학실험의 설계·실행 지원", "Assistance for designing and conducting dangerous scientific experiments", "AI 시스템이 생물학·화학 또는 그 밖의 고위험 과학실험에 필요한 절차, 조건, 물질 선택이나 실행 지침을 제공하여 대규모 신체적 위해 또는 공중보건 피해를 가능하게 하는 리스크.", "The risk that an AI system provides procedures, conditions, material selection, or operational guidance for biological, chemical, or other high-risk scientific experiments, enabling large-scale physical harm or public-health damage.", rationale)
    absorb("G_SYS_SECADV_048", "G_SYS_SECADV_021", rationale)
    revise(by_id["G_SYS_SECADV_048"], "AI 컴퓨팅 인프라의 무단 접근·조작·서비스 중단", "Unauthorised access, manipulation, and disruption of AI computing infrastructure", "공격자가 AI 컴퓨팅 인프라의 취약점을 악용하여 분산 노드나 서비스에 무단 접근하고 구성·데이터·작업부하를 조작하거나 운영을 중단시키며 침해를 시스템 경계 밖으로 확산시키는 리스크.", "The risk that an attacker exploits vulnerabilities in AI computing infrastructure to gain unauthorised access to distributed nodes or services, manipulate configurations, data, or workloads, disrupt operations, or propagate compromise across system boundaries.", rationale)

    # 8. Writing capacity versus pollution of scholarly records.
    revise(by_id["G_SOC_CULT_021"], "AI 생성 학술 콘텐츠에 의한 학술 문헌 오염", "Pollution of scholarly literature by AI-generated content", "AI 시스템이 사실 검증과 학술적 책임이 결여된 저품질·허위 학술 콘텐츠를 대량 생성·유통하여 출판·인용 기록과 지식 기반을 오염하고 연구의 진실성과 신뢰성을 훼손하는 리스크.", "The risk that an AI system generates and disseminates large volumes of low-quality or false scholarly content without adequate verification or academic accountability, polluting publication and citation records and knowledge bases and undermining research integrity and trustworthiness.", rationale)
    create("G_SOC_CULT_021", "G_SOC_CULT", "AI 의존에 따른 글쓰기·표현 역량의 저하", "Erosion of writing and expressive capability through dependence on AI", "AI 생성·보조 도구에 대한 지속적 의존이 이용자의 글쓰기, 논증과 고유한 표현 역량을 약화하고 문체의 획일화를 촉진하여 개인과 사회의 문화적·지적 다양성을 저해하는 리스크.", "The risk that sustained dependence on AI generation or assistance tools weakens users' writing, reasoning, and distinctive expressive capabilities and promotes stylistic homogenisation, impairing cultural and intellectual diversity at individual and societal levels.", rationale)

    # 9. Emotional, functional, and epistemic dependence.
    absorb("G_INT_REL_001", "G_INT_REL_003", rationale)
    revise(by_id["G_INT_REL_001"], "일상 기능을 AI 시스템에 과도하게 의존", "Excessive functional dependence on AI systems in daily life", "이용자가 일상적 계획, 의사결정 또는 과업 수행을 AI 시스템에 과도하게 의존하여 독립적으로 기능하는 능력과 자율성이 약화되고 서비스 중단이나 오류에 취약해지는 리스크.", "The risk that a user becomes excessively dependent on an AI system for everyday planning, decisions, or task performance, weakening independent functioning and autonomy and increasing vulnerability to service interruption or error.", rationale)
    create("G_INT_REL_001", "G_SYS_OVERCONF", "AI 판단에 대한 인식론적 과의존", "Epistemic overreliance on AI judgement", "이용자가 AI 시스템의 사실적·도덕적 또는 전략적 판단을 과도하게 신뢰하여 근거와 불확실성을 독립적으로 평가하지 못하고 부정확하거나 부적절한 산출물을 그대로 수용하는 리스크.", "The risk that a user places excessive trust in an AI system's factual, moral, or strategic judgement, fails to assess evidence and uncertainty independently, and accepts inaccurate or inappropriate outputs without adequate scrutiny.", rationale)

    # 10. Organisational assurance versus output quality, calibration, and systemic oversight.
    revise(by_id["G_SYS_EVAL_012"], "AI 보증을 위한 감사 접근성과 경영진 가시성의 실패", "Failure of audit access and management visibility for AI assurance", "조직이 AI 시스템의 데이터, 모델, 의사결정 과정과 성능에 대한 감사 접근권, 문서화, 공통 평가기준 또는 경영진 수준의 가시성을 확보하지 못하여 위험을 식별·검증·시정하지 못하는 리스크.", "The risk that an organisation lacks audit access, documentation, common evaluation criteria, or management-level visibility into an AI system's data, models, decision processes, and performance, preventing the identification, verification, and correction of risks.", rationale)
    absorb("G_SYS_EVAL_012", "G_SYS_INCONS_002", rationale)
    absorb("G_SYS_EVAL_012", "G_SYS_OVERCONF_007", rationale)
    create("G_SYS_EVAL_012", "G_SOC_GOV", "AI 규제·감독 체계의 구조적 실패", "Systemic failure of AI regulation and oversight", "법·제도와 공적 감독 체계가 AI 시스템의 개발·배포·운영에서 발생하는 위험을 적시에 식별하고 책임을 배분하며 준수 여부를 집행·시정하지 못하여 피해가 반복되거나 확산되는 리스크.", "The risk that legal, institutional, and public oversight arrangements fail to identify risks arising from the development, deployment, and operation of AI systems in a timely manner, allocate responsibility, or enforce and correct non-compliance, allowing harm to recur or spread.", rationale)

    final = [row for row in rows if row["L4_ID"] not in retired]
    final.sort(key=lambda row: (row["L1_ID"], row["L3_ID"], row["L4_Title_en"], row["L4_ID"]))
    counts: defaultdict[str, int] = defaultdict(int)
    old_to_new: dict[str, str] = {}
    for row in final:
        old = row["L4_ID"]
        counts[row["L3_ID"]] += 1
        row["L4_ID"] = f"{row['L3_ID']}_{counts[row['L3_ID']]:03d}"
        old_to_new[old] = row["L4_ID"]

    operations = [
        ("SS-01", "G_INT_SELF_003", "RETIRE_AND_SPLIT", "G_INT_SELF_004|G_INT_SELF_005|NEW", "Eating/self-harm branches absorbed; panic/anxiety and unsafe medical guidance separated."),
        ("SS-02", "G_SYS_MISINFO_008", "REWRITE_AND_ABSORB", "G_SYS_MISINFO_006|G_INT_PRIV_011|NEW", "Erroneous conclusions retained; confidentiality and ecosystem-pollution branches absorbed."),
        ("SS-03", "G_INT_COPY_005", "SPLIT", "G_INT_COPY_005|NEW", "Intellectual-property and personality-rights mechanisms separated."),
        ("SS-04", "G_INT_PRIV_011", "SPLIT", "G_INT_PRIV_011|NEW", "Personal information and business confidentiality mechanisms separated."),
        ("SS-05", "G_SOC_DEMOC_002", "RETIRE_AND_ABSORB", "G_INT_POL_006|G_INT_PRIV_001|G_INT_ALLOC_008", "Umbrella retired; political manipulation, surveillance, and disparate impact absorbed."),
        ("SS-06", "G_INT_WEAP_021", "REWRITE_AND_ABSORB", "G_INT_WEAP_021|G_INT_WEAP_007", "Cyber enablement and dangerous-science assistance separated."),
        ("SS-07", "G_SYS_SECADV_048", "REWRITE_AND_ABSORB", "G_SYS_SECADV_048|G_SYS_SECADV_021", "Resource exhaustion and infrastructure compromise separated."),
        ("SS-08", "G_SOC_CULT_021", "SPLIT", "G_SOC_CULT_021|NEW", "Writing-capacity erosion and scholarly-literature pollution separated."),
        ("SS-09", "G_INT_REL_001", "REWRITE_AND_SPLIT", "G_INT_REL_001|G_INT_REL_003|NEW", "Emotional, functional, and epistemic dependence separated."),
        ("SS-10", "G_SYS_EVAL_012", "REWRITE_AND_SPLIT", "G_SYS_EVAL_012|G_SYS_INCONS_002|G_SYS_OVERCONF_007|NEW", "Organisational assurance, output quality, calibration, and systemic oversight separated."),
    ]
    for op_id, source_id, action, targets, note in operations:
        resolved = [old_to_new.get(value, value) for value in targets.split("|") if value != "NEW"]
        source_ids = tokens(by_id[source_id].get("source_row_id", ""))
        resolved.extend(row["L4_ID"] for row in final if any(source in tokens(row.get("source_row_id", "")) for source in source_ids) and row["L4_ID"] not in resolved)
        log.append({"Split_ID": op_id, "Reviewed_L4_ID": source_id, "Action": action, "Final_L4_IDs": "|".join(dict.fromkeys(resolved)), "Decision_Rationale": note, "Approval": "USER_APPROVED_20260829"})

    expected = 783
    if len(final) != expected:
        raise ValueError(f"Expected {expected} cards after semantic splitting, found {len(final)}")
    for domain in DOMAINS:
        write_csv(OUT / f"L4_{domain}_Human_Review_Recovery_Applied.csv", [row for row in final if L1_DOMAIN[row["L1_ID"]] == domain], fields)
    write_csv(OUT / "Semantic_Split_Application_Log.csv", log, ["Split_ID", "Reviewed_L4_ID", "Action", "Final_L4_IDs", "Decision_Rationale", "Approval"])

    edges = [{"source_row_id": source, "L4_ID": row["L4_ID"], "L3_ID": row["L3_ID"], "L1_ID": row["L1_ID"], "Disposition": "OUTPUT"} for row in final for source in tokens(row.get("source_row_id", ""))]
    write_csv(OUT / "Source_Output_Lineage_Edges.csv", edges, ["source_row_id", "L4_ID", "L3_ID", "L1_ID", "Disposition"])
    ledger = read_csv(OUT / "Source_Disposition_Ledger.csv")
    edge_by_source: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for edge in edges:
        edge_by_source[edge["source_row_id"]].append(edge)
    for item in ledger:
        if item["Disposition"] == "OUTPUT":
            linked = edge_by_source[item["source_row_id"]]
            item["Output_L4_IDs"] = "|".join(edge["L4_ID"] for edge in linked)
            item["Output_L3_IDs"] = "|".join(dict.fromkeys(edge["L3_ID"] for edge in linked))
            item["Output_Count"] = str(len(linked))
    write_csv(OUT / "Source_Disposition_Ledger.csv", ledger, list(ledger[0]))

    summary_path = OUT / "Recovery_Application_Summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["output_cards"] = len(final)
    summary["output_by_domain"] = {domain: sum(L1_DOMAIN[row["L1_ID"]] == domain for row in final) for domain in DOMAINS}
    summary["semantic_splitting"] = {"reviewed_composite_cards": 10, "retired_umbrella_cards": 2, "new_distinct_cards": 7, "net_addition": 5, "input_cards": 778, "output_cards": len(final), "approval": "USER_APPROVED_20260829", "log": "Semantic_Split_Application_Log.csv"}
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cards": len(final), "by_domain": summary["output_by_domain"], "new": 7, "retired": 2}, ensure_ascii=False))


if __name__ == "__main__":
    main()
