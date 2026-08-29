#!/usr/bin/env python3
"""Validate the second-round human-review application without running EM."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "03_outputs" / "release"
SPEC = ROOT / "02_working" / "specifications" / "human_review_round2"
OUT = Path(os.environ.get("RAI_HR2_OUT", ROOT / "05_human_review_round2"))
EXPECTED_L3_HASH = "e9439ced64fb49c1496f1955013b5f038ecc7d271b9d6c9704f1e1bf6b0094df"
DOMAINS = ("General", "Agentic", "Physical")
DOMAIN_BY_L1 = {"L1_G": "General", "L1_A": "Agentic", "L1_P": "Physical"}
REQUIRED_L4_FIELDS = (
    "L4_Title_ko", "L4_Title_en", "L4_Description_ko", "L4_Description_en",
)
HIERARCHY_FIELDS = (
    "L0_ID", "L0_Title_ko", "L0_Title_en", "L1_ID", "L1_Title_ko", "L1_Title_en",
    "L1_Description_ko", "L1_Description_en", "L2_ID", "L2_Title_ko", "L2_Title_en",
    "L2_Description_ko", "L2_Description_en", "L3_ID", "L3_Title_ko", "L3_Title_en",
    "L3_Description_ko", "L3_Description_en",
)
STALE_EVIDENCE_FIELDS = (
    "EM_Score", "EM_Margin", "EM_Stability", "EM_Anchor_Score", "Hybrid_EM_Score",
    "Hybrid_EM_Margin", "L4_Keyword_1_ko", "L4_Keyword_2_ko", "L4_Keyword_3_ko",
    "L4_Keyword_1_en", "L4_Keyword_2_en", "L4_Keyword_3_en", "Keyword_Top_L3_ID",
    "Keyword_Support_Score", "Keyword_Semantic_Score", "Keyword_Prior", "Keyword_Evidence",
    "Candidate_1_L3_ID", "Candidate_1_EM_Score", "Candidate_1_Hybrid_Score",
    "Candidate_2_L3_ID", "Candidate_2_EM_Score", "Candidate_2_Hybrid_Score",
    "KO_Top_L3_ID", "EN_Top_L3_ID", "Definition_L3_Anchor_ID", "Definition_L3_Anchor_Score",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def attribute_tokens(value: str) -> set[str]:
    return {part.strip() for part in re.split(r"[,;|]", value or "") if part.strip()}


def verify_round2_source_manifest() -> tuple[bool, str]:
    manifest_path = ROOT / "00_source_snapshot" / "source_manifest_human_review_round2_20260828.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    valid = True
    for item in manifest["files"]:
        path = ROOT / item["path"]
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            columns = len(next(reader))
            row_count = sum(1 for _ in reader)
        valid &= hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        valid &= row_count == item["rows"] and columns == item["columns"]
    return valid, hashlib.sha256(manifest_path.read_bytes()).hexdigest()


def main() -> None:
    source_manifest_valid, source_manifest_hash = verify_round2_source_manifest()
    summary = json.loads((OUT / "Human_Review_Round2_Summary.json").read_text(encoding="utf-8"))
    ledger = read_csv(OUT / "Human_Review_Round2_Decision_Ledger.csv")
    master_rows = read_csv(RELEASE / "L1_L2_L3_Master.csv")
    master_by_l3 = {row["L3_ID"]: row for row in master_rows}

    outputs: list[dict[str, str]] = []
    for domain in DOMAINS:
        for row in read_csv(OUT / f"L4_{domain}_Human_Review_Round2_Applied.csv"):
            row["_file_domain"] = domain
            outputs.append(row)

    baseline: list[dict[str, str]] = []
    for domain in DOMAINS:
        baseline.extend(read_csv(RELEASE / f"L4_{domain}.csv"))
    baseline_by_id = {row["L4_ID"]: row for row in baseline}
    output_by_id = {row["L4_ID"]: row for row in outputs}
    ledger_by_source = {row["L4_ID_Before"]: row for row in ledger}
    user_operations_path = SPEC / "user_directed_operations.csv"
    user_operations = read_csv(user_operations_path) if user_operations_path.exists() else []
    copyedit_path = SPEC / "L4_Korean_Copyedit_Approved_20260829.csv"
    english_copyedit_path = SPEC / "L4_English_Copyedit_Approved_20260829.csv"
    final_qa_path = SPEC / "L4_Final_Terminology_L3_Alignment_Approved_20260829.csv"
    copyedit_operations = read_csv(copyedit_path)
    english_copyedit_operations = read_csv(english_copyedit_path)
    final_qa_operations = read_csv(final_qa_path)
    user_operations_hash = hashlib.sha256(user_operations_path.read_bytes()).hexdigest()
    copyedit_manifest_hash = hashlib.sha256(copyedit_path.read_bytes()).hexdigest()
    english_copyedit_manifest_hash = hashlib.sha256(english_copyedit_path.read_bytes()).hexdigest()
    final_qa_manifest_hash = hashlib.sha256(final_qa_path.read_bytes()).hexdigest()

    failures: dict[str, list[object]] = defaultdict(list)
    output_ids = [row["L4_ID"] for row in outputs]
    duplicate_ids = [key for key, count in Counter(output_ids).items() if count > 1]
    failures["unique_l4_ids"].extend(duplicate_ids)

    for row in outputs:
        master = master_by_l3.get(row["L3_ID"])
        if master is None:
            failures["master_hierarchy"].append([row["L4_ID"], "unknown L3", row["L3_ID"]])
            continue
        for field in HIERARCHY_FIELDS:
            if row.get(field, "") != master.get(field, ""):
                failures["master_hierarchy"].append([row["L4_ID"], field])
        if DOMAIN_BY_L1.get(row["L1_ID"]) != row["_file_domain"]:
            failures["domain_file"].append([row["L4_ID"], row["_file_domain"], row["L1_ID"]])
        if not re.fullmatch(re.escape(row["L3_ID"]) + r"_\d{3}", row["L4_ID"]):
            failures["id_prefix"].append([row["L4_ID"], row["L3_ID"]])
        for field in REQUIRED_L4_FIELDS:
            if not row.get(field, "").strip():
                failures["bilingual_fields"].append([row["L4_ID"], field])

    by_l3: dict[str, list[int]] = defaultdict(list)
    for row in outputs:
        by_l3[row["L3_ID"]].append(int(row["L4_ID"].rsplit("_", 1)[1]))
    for l3_id, numbers in by_l3.items():
        if sorted(numbers) != list(range(1, len(numbers) + 1)):
            failures["id_continuity"].append([l3_id, sorted(numbers)])

    card_keys = Counter(
        (row["L3_ID"], row["L4_Title_ko"].strip(), row["L4_Title_en"].strip())
        for row in outputs
    )
    failures["exact_duplicates"].extend([list(key) for key, count in card_keys.items() if count > 1])

    linked_sources: dict[str, list[str]] = defaultdict(list)
    for item in ledger:
        after_ids = [part.strip() for part in item["L4_ID_After"].split("|") if part.strip()]
        if "DELETE_APPLIED" in item["Decision"]:
            if after_ids:
                failures["deleted_source_links"].append([item["L4_ID_Before"], after_ids])
            continue
        if not after_ids:
            failures["lost_sources"].append(item["L4_ID_Before"])
        for after_id in after_ids:
            if after_id not in output_by_id:
                failures["invalid_ledger_links"].append([item["L4_ID_Before"], after_id])
            else:
                linked_sources[after_id].append(item["L4_ID_Before"])
    failures["unlinked_outputs"].extend([output_id for output_id in output_ids if output_id not in linked_sources])

    for output_id, source_ids in linked_sources.items():
        output = output_by_id[output_id]
        expected_facet = set().union(*(attribute_tokens(baseline_by_id[s]["facet"]) for s in source_ids))
        expected_act_type = set().union(*(attribute_tokens(baseline_by_id[s]["act-type"]) for s in source_ids))
        if attribute_tokens(output["facet"]) != expected_facet:
            failures["facet_preservation"].append([output_id, source_ids])
        if attribute_tokens(output["act-type"]) != expected_act_type:
            failures["act_type_preservation"].append([output_id, source_ids])
        expected_source_row_ids = set().union(
            *(attribute_tokens(baseline_by_id[s].get("source_row_id", "")) for s in source_ids)
        )
        expected_source_l4_ids = set().union(
            *(attribute_tokens(baseline_by_id[s].get("Source_L4_IDs", "")) for s in source_ids)
        )
        if attribute_tokens(output.get("source_row_id", "")) != expected_source_row_ids:
            failures["source_row_id_preservation"].append(
                [output_id, sorted(expected_source_row_ids), sorted(attribute_tokens(output.get("source_row_id", "")))]
            )
        if attribute_tokens(output.get("Source_L4_IDs", "")) != expected_source_l4_ids:
            failures["source_l4_id_preservation"].append(
                [output_id, sorted(expected_source_l4_ids), sorted(attribute_tokens(output.get("Source_L4_IDs", "")))]
            )
        if any("Mapping evidence" in ledger_by_source[s]["Changed_Fields"] for s in source_ids):
            stale = [field for field in STALE_EVIDENCE_FIELDS if output.get(field, "").strip()]
            if stale:
                failures["stale_mapping_evidence"].append([output_id, stale])

    for operation in user_operations:
        source_ids = [part.strip() for part in operation["Source_L4_IDs_Before"].split("|") if part.strip()]
        after_id_sets = [
            {
                part.strip()
                for part in ledger_by_source[source_id]["L4_ID_After"].split("|")
                if part.strip()
            }
            for source_id in source_ids
            if source_id in ledger_by_source
        ]
        shared_after_ids = set.intersection(*after_id_sets) if after_id_sets else set()
        matching_shared_ids = {
            output_id
            for output_id in shared_after_ids
            if output_id in output_by_id
            and output_by_id[output_id]["L3_ID"] == operation["Target_L3_ID"]
            and output_by_id[output_id]["L4_Title_ko"] == operation["L4_Title_ko"]
            and output_by_id[output_id]["L4_Title_en"] == operation["L4_Title_en"]
        }
        if len(matching_shared_ids) != 1:
            failures["user_directed_merges"].append([operation["Current_L4_IDs"], "not one shared output"])
            continue
        output_id = next(iter(matching_shared_ids))
        output = output_by_id.get(output_id)
        if output is None:
            failures["user_directed_merges"].append([operation["Current_L4_IDs"], "missing output"])
            continue
        expected_fields = {
            "L3_ID": operation["Target_L3_ID"],
            "Mapping_Method": operation["Mapping_Method"],
            "L4_Title_ko": operation["L4_Title_ko"],
            "L4_Title_en": operation["L4_Title_en"],
        }
        mismatches = [field for field, expected in expected_fields.items() if output.get(field, "") != expected]
        if output["L4_Description_ko"] != operation["L4_Description_ko"]:
            approved_ko = any(
                candidate["Target_L3_ID"] == operation["Target_L3_ID"]
                and candidate["Expected_Title_en"] == operation["L4_Title_en"]
                and candidate["Expected_Description_ko_Before"] == operation["L4_Description_ko"]
                and candidate["Approved_Description_ko_After"] == output["L4_Description_ko"]
                for candidate in copyedit_operations
            )
            if not approved_ko:
                mismatches.append("L4_Description_ko")
        if output["L4_Description_en"] != operation["L4_Description_en"]:
            approved_en = any(
                candidate["Target_L3_ID"] == operation["Target_L3_ID"]
                and candidate["Expected_Title_en_Before"] == operation["L4_Title_en"]
                and candidate["Expected_Description_en_Before"] == operation["L4_Description_en"]
                and candidate["Approved_Description_en_After"] == output["L4_Description_en"]
                for candidate in english_copyedit_operations
            )
            if not approved_en:
                mismatches.append("L4_Description_en")
        if "USER_DIRECTED_MERGE" not in output.get("Transformation_Action", "").split("|"):
            mismatches.append("Transformation_Action")
        if not attribute_tokens(operation["Terminology_Sources"]).issubset(
            attribute_tokens(output.get("Terminology_Sources", ""))
        ):
            mismatches.append("Terminology_Sources")
        decisions = {ledger_by_source[source_id]["Decision"] for source_id in source_ids}
        expected_decisions = {"USER_DIRECTED_MERGE_ABSORBED", "USER_DIRECTED_MERGE_REPRESENTATIVE"}
        if mismatches or decisions != expected_decisions:
            failures["user_directed_merges"].append(
                [operation["Current_L4_IDs"], output_id, mismatches, sorted(decisions)]
            )

    output_by_copyedit_selector: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    output_by_lineage_selector: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for output in outputs:
        lineage_selector = (
            "|".join(sorted(attribute_tokens(output.get("source_row_id", "")))),
            "|".join(sorted(attribute_tokens(output.get("Source_L4_IDs", "")))),
        )
        output_by_lineage_selector[lineage_selector].append(output)
        selector = (
            *lineage_selector,
            output["L3_ID"],
            output["L4_Title_en"],
        )
        output_by_copyedit_selector[selector].append(output)

    def exact_final_overrides(output: dict[str, str]) -> list[dict[str, str]]:
        """Return final-QA decisions whose approved final identity is this row.

        Baseline L4 IDs and raw source-card IDs are different namespaces. The
        decision ledger is the authoritative bridge between a baseline source
        and its final output, including splits and consolidations.
        """
        baseline_sources = set(linked_sources.get(output["L4_ID"], []))
        return [
            operation
            for operation in final_qa_operations
            if operation["Source_L4_ID_Before"] in baseline_sources
            and output["L3_ID"] == operation["Target_L3_ID"]
            and output["L4_Title_ko"] == operation["Approved_Title_ko"]
            and output["L4_Title_en"] == operation["Approved_Title_en"]
            and output["L4_Description_ko"] == operation["Approved_Description_ko"]
            and output["L4_Description_en"] == operation["Approved_Description_en"]
        ]
    english_title_after_by_before_selector = {
        (
            "|".join(sorted(attribute_tokens(operation["Source_Row_IDs"]))),
            "|".join(sorted(attribute_tokens(operation["Source_L4_IDs_Before"]))),
            operation["Target_L3_ID"],
            operation["Expected_Title_en_Before"],
        ): operation["Approved_Title_en_After"]
        for operation in english_copyedit_operations
    }
    for operation in copyedit_operations:
        before_selector = (
            "|".join(sorted(attribute_tokens(operation["Source_Row_IDs"]))),
            "|".join(sorted(attribute_tokens(operation["Source_L4_IDs_Before"]))),
            operation["Target_L3_ID"],
            operation["Expected_Title_en"],
        )
        selector = (*before_selector[:3], english_title_after_by_before_selector.get(before_selector, before_selector[3]))
        matches = output_by_copyedit_selector.get(selector, [])
        lineage_matches = output_by_lineage_selector.get(before_selector[:2], [])
        if len(matches) != 1:
            decision_matches = [
                output
                for output in lineage_matches
                if operation["Decision_ID"] in output.get("Transformation_Rationale", "")
            ]
            matches = decision_matches if decision_matches else lineage_matches
        if len(matches) != 1:
            failures["korean_copyedit_exact"].append([operation["Decision_ID"], "match_count", len(matches)])
            continue
        output = matches[0]
        final_override = exact_final_overrides(output)
        mismatches = []
        expected_title_ko = (
            output["L4_Title_ko"]
            if final_override
            else operation["Approved_Title_ko_After"]
        )
        expected_description_ko = (
            output["L4_Description_ko"]
            if final_override
            else operation["Approved_Description_ko_After"]
        )
        if output["L4_Title_ko"] != expected_title_ko:
            mismatches.append("L4_Title_ko")
        if output["L4_Description_ko"] != expected_description_ko:
            mismatches.append("L4_Description_ko")
        if "KOREAN_COPYEDIT" not in output.get("Transformation_Action", ""):
            mismatches.append("Transformation_Action")
        if output.get("Definition_Grounding_Action", "") != "STALE_AFTER_TEXT_EDIT_NO_EM_RERUN":
            mismatches.append("Definition_Grounding_Action")
        if operation["Clear_Mapping_Evidence"] == "YES":
            stale = [field for field in STALE_EVIDENCE_FIELDS if output.get(field, "").strip()]
            if stale:
                mismatches.append("cleared_mapping_evidence:" + "|".join(stale))
        if mismatches:
            failures["korean_copyedit_exact"].append([operation["Decision_ID"], mismatches])

    output_by_english_copyedit_selector: dict[
        tuple[str, str, str, str], list[dict[str, str]]
    ] = defaultdict(list)
    for output in outputs:
        selector = (
            "|".join(sorted(attribute_tokens(output.get("source_row_id", "")))),
            "|".join(sorted(attribute_tokens(output.get("Source_L4_IDs", "")))),
            output["L3_ID"],
            output["L4_Title_en"],
        )
        output_by_english_copyedit_selector[selector].append(output)
    for operation in english_copyedit_operations:
        selector = (
            "|".join(sorted(attribute_tokens(operation["Source_Row_IDs"]))),
            "|".join(sorted(attribute_tokens(operation["Source_L4_IDs_Before"]))),
            operation["Target_L3_ID"],
            operation["Approved_Title_en_After"],
        )
        matches = output_by_english_copyedit_selector.get(selector, [])
        lineage_matches = output_by_lineage_selector.get(selector[:2], [])
        if len(matches) != 1:
            decision_matches = [
                output
                for output in lineage_matches
                if operation["Decision_ID"] in output.get("Transformation_Rationale", "")
            ]
            matches = decision_matches if decision_matches else lineage_matches
        if len(matches) != 1:
            failures["english_copyedit_exact"].append(
                [operation["Decision_ID"], "match_count", len(matches)]
            )
            continue
        output = matches[0]
        final_override = exact_final_overrides(output)
        mismatches = []
        expected_description_en = (
            output["L4_Description_en"]
            if final_override
            else operation["Approved_Description_en_After"]
        )
        if output["L4_Description_en"] != expected_description_en:
            mismatches.append("L4_Description_en")
        if "ENGLISH_COPYEDIT" not in output.get("Transformation_Action", ""):
            mismatches.append("Transformation_Action")
        if output.get("Definition_Grounding_Action", "") != "STALE_AFTER_TEXT_EDIT_NO_EM_RERUN":
            mismatches.append("Definition_Grounding_Action")
        if operation["Clear_Mapping_Evidence"] == "YES":
            stale = [field for field in STALE_EVIDENCE_FIELDS if output.get(field, "").strip()]
            if stale:
                mismatches.append("cleared_mapping_evidence:" + "|".join(stale))
        if mismatches:
            failures["english_copyedit_exact"].append([operation["Decision_ID"], mismatches])

    final_qa_position = {
        operation["Decision_ID"]: position
        for position, operation in enumerate(final_qa_operations)
    }
    for operation in final_qa_operations:
        decision_id = operation["Decision_ID"]
        source_id = operation["Source_L4_ID_Before"]
        ledger_item = ledger_by_source.get(source_id)
        if ledger_item is None:
            failures["final_qa_exact"].append([decision_id, "missing_ledger_source"])
            continue
        expected = {
            "L3_ID": operation["Target_L3_ID"],
            "L4_Title_ko": operation["Approved_Title_ko"],
            "L4_Title_en": operation["Approved_Title_en"],
            "L4_Description_ko": operation["Approved_Description_ko"],
            "L4_Description_en": operation["Approved_Description_en"],
        }
        # A split source can remain in more than one final card, and a later
        # consolidation can retain that same source in a different child. Use
        # immutable lineage together with the approved final identity instead
        # of assuming that one ledger source has exactly one output ID.
        matches = [
            output
            for output in outputs
            if source_id in linked_sources.get(output["L4_ID"], [])
            and all(output.get(field, "") == value for field, value in expected.items())
        ]
        superseded = False
        if len(matches) != 1:
            decision_matches = [
                output
                for output in outputs
                if source_id in linked_sources.get(output["L4_ID"], [])
                and decision_id in output.get("Transformation_Rationale", "")
            ]
            later_ids = {
                later["Decision_ID"]
                for later in final_qa_operations
                if later["Source_L4_ID_Before"] == source_id
                and final_qa_position[later["Decision_ID"]] > final_qa_position[decision_id]
            }
            superseded_matches = [
                output
                for output in decision_matches
                if any(
                    later_id in output.get("Transformation_Rationale", "")
                    for later_id in later_ids
                )
            ]
            if len(superseded_matches) != 1:
                failures["final_qa_exact"].append([decision_id, "match_count", len(matches)])
                continue
            matches = superseded_matches
            superseded = True
        output = matches[0]
        mismatches = [] if superseded else [
            field for field, value in expected.items() if output.get(field, "") != value
        ]
        if decision_id not in {
            part.strip()
            for part in ledger_item.get("Final_QA_Decision_IDs", "").split("|")
            if part.strip()
        }:
            mismatches.append("Final_QA_Decision_IDs")
        if ledger_item.get("Final_QA_Applied") != "YES":
            mismatches.append("Final_QA_Applied")
        if f"FINAL_QA_{operation['Decision']}" not in {
            part.strip()
            for part in ledger_item.get("Decision", "").split("|")
            if part.strip()
        }:
            mismatches.append("Decision")
        if not superseded and operation["Decision"] in {"REMAP_PER_REVIEW", "MOVE_TO_OTHERS_HD"}:
            if output["Mapping_Method"] != "HD":
                mismatches.append("Mapping_Method")
        if operation["Decision"] != "ACCEPT_CURRENT":
            if "FINAL_TERMINOLOGY_L3_QA" not in output.get("Transformation_Action", "").split("|"):
                mismatches.append("Transformation_Action")
            if decision_id not in output.get("Transformation_Rationale", ""):
                mismatches.append("Transformation_Rationale")
            if not attribute_tokens(operation["Terminology_Evidence"]).issubset(
                attribute_tokens(output.get("Terminology_Sources", ""))
            ):
                mismatches.append("Terminology_Sources")
            stale = [field for field in STALE_EVIDENCE_FIELDS if output.get(field, "").strip()]
            if stale:
                mismatches.append("cleared_mapping_evidence:" + "|".join(stale))
        if mismatches:
            failures["final_qa_exact"].append([decision_id, mismatches])

    forbidden_literals = (
        "AI 시스템 또는 AI 알고리즘의 설계·학습·배포·사용 과정이 ",
        "AI 에이전트의 목표 추구·계획·도구 사용·행동 과정이 ",
        "로봇·휴머노이드 또는 피지컬 AI 시스템의 지각·학습·제어·물리적 행동 과정이 ",
        "로 인해 구체적인 위해가 발생하는 리스크.",
        "하게되는", "게되는", "하게하는", "게하는", "로하여금", "되어야할",
        "프롬 프 트", "산출 물", "백 도어", "롱 테 일", "그래 디 언 트",
        "그 래 디 언 트", "섭 동", "모달 리 티", "외 란", "동 역학",
        "안전장 치", "부수효 과", "불확실 성", "지식 재산 이", "작은 교란 이",
        "문화·가치관 보유한 것 가진 것처럼", "부하 하에 서열적",
        "딥 러닝", "멀티 모달", "레드 팀", "민감 정보", "정보 자기 결정권",
        "사회 경제적", "지식 재산", "허위 정보", "오 해석", "메타 데이터",
        "시스템프롬프트", "하류배포자", "프라이버 시", "질의·탐 침",
        "질의·탐침하여", "다 당파적", "어포던스또는", "자연 어", "심각 도",
        "나노 봇", "다운 스트림", "체크 리스트", "외 집단", "외 골격",
        "그리 퍼", "크라우드 소싱", "오 일반화", "대리지표조작",
        "언어 사용 역", "사이 버전", "위협이되는", "대체물이되는",
        "표적이된", "해가되는", "기술시스템이넛지", "안전 임계 값",
        "미시 표적화", "인간 AI", "하게하고", "게하고", "맡아야할",
        "들여야하는", "을하는", "가능하게하고", "그렇지 않았다면하지",
        "자극 받아", "그럴 듯하지만", "미루게하여", "불명확하게하고",
        "시스템의상 전이", "복잡 도가", "부정적 부수 효과", "과소 평가",
        "모방 충실 도", "충돌 심각 도", "임계 값을", "구현 체", "비안전",
        "피지컬 행동", "제2 격", "다 행위자", "성 착취", "프롬프팅",
        "목표오 일반화", "목표오일반화", "대리지표 조작", "파국적 망각이 발생시키고",
        "허위정보와고", "제어 정책으로하여금", "감시 하에서는", "드러난다로 인해",
        "신체성 (Physical Embodiment)", "권리 주체성 (기본권)",
        "고도 AI에 의한 실존적·재앙적",
        "실제의 도", "위임 받은", "대응 약정", "유해한 응낙", "위협 받고",
        "침해적인 식별", "전신 동작 및 환경 접촉이 충분히 고려되지 않아",
        "사고연쇄", "성적 자기 결정권", "오래된 상태에서 작동이",
        "센서 풍부 작업장", "엔드이펙터",
        "프레임 워크", "오버 헤드", "오케스트레이션레이어", "embodied 에이전트",
        "물리 행동", "피지컬 제약", "학업 부정 행위", "지지 망", "어렵게하여",
        "여성·소수자가과소대표되어", "모델이스테가노그래피", "통제 대상밖에",
        "용이하게 함하는", "안전하지 않은하거나", "안전하지 않은 힘인가를",
        "동의절차없는개인화넛지", "네트워크한 부분", "못하게 함하는",
        "운용제 약간", "인간이 로봇을 과도하게 신뢰하거나 모방해",
        "압력·파지·이동", "미리 정해진 위험하거나",
        "다중에이전트", "협상실패", "모바일앱", "현실감각", "공통원인",
        "공격표면", "지오 펜싱", "이동 체", "위험 완화책임",
        "제어 루프 데드라인 미달", "통신 지연이나 시계 불일치로 로봇의 상태 추정값",
        "보호적 또는 보조적 휴머노이드", "부적절한 피지컬 방식",
        "광범위한 역량 또는 기능을 오용함으로써", "잘못 타이밍된 힘",
        "인간 공학적 상해", "이동을 제한함으로써 발생되는", "유효한 동의가 없거나 또는",
        "비인간화와 객관화", "합법·사회용인적", "성실성 오류",
        "모델 동작으로 인해서", "모델이 배포해도", "자아실현 저해 피해",
        "검색증강", "마음이론(Theory of Mind) 능력",
        "안전하지 않은 하위 행동", "고압적 직무", "위험 로봇 행동",
        "정지·회피·인간 근접 한계", "개입 타이밍 실패", "계약통제",
        "공공 기관", "자연 환경", "실제 피해를 발생시키는", "환경 비용을 발생시키는",
        "범용인공지능", "시장점유", "생물·화학 무기", "대량 살상무기",
        "대량 살상 무기", "인간중심", "기반모델", "인명피해", "정보환경",
        "공격면", "월드모델", "검증범위", "금융시스템",
        "자기개선", "자율행동", "보상해킹", "자기수정", "안전필터",
        "원격조작", "반사 실적 설명", "남반구 공동체", "데이터셋 시프트",
        "거절-능력 혼동", "무감독 에이전트 방출", "로 인해서",
        "소수 사업자나 행위자가", "AI 개발에 추출되는",
        "유용성이 저하되고 최종 사용자의 생산성을 저하시키는",
        "와이어 헤딩", "자율 안전 우선 개입", "데이터셋의 오픈 월드 조건",
        "환경 유발 결함 변이", "지능 시스템 내부", "의도되지 않은 행동 변이",
        "행복을 명분으로", "조작적 행동을 하도록 유인되는", "원 에이전트",
        "개체 수·자원 사용량", "악용 가능한 정보와 설계 역량에 대한 접근이나 합성",
        "자해 및 자살 의미화·정당화", "기본 값", "피해인지·측정·인정",
        "디지털 지식 공유 재", "생물 다양성", "나노 입자", "배포 자",
        "중앙 집중식 장애 점", "갈등의 발화 점", "선도 국과 후발국",
        "역량임계값", "영향 받는 공동체", "영업 비밀", "지속적 지시 미세조정",
        "센서 입력 간섭, 또는", "안전임계 엣지 케이스",
        "리스크가 관리되지 않는 리스크", "되돌리는 일이 과도한 비용이 들거나",
        "신무기를 여는 과학적 발견", "무기화 전략 및 전술 활용의 개발",
        "무기 확산 및 은닉의 개발", "자율성 상실을 대가로",
    )
    ai_technology_pattern = re.compile(r"AI|인공지능|알고리즘|모델|에이전트|로봇|휴머노이드|머신|학습|지능|자율")
    english_ai_technology_pattern = re.compile(
        r"\b(?:AI|artificial intelligence|algorithm\w*|model\w*|agent\w*|robot\w*|"
        r"humanoid\w*|machine\w*|learning|intelligen\w*|autonomous|automated|"
        r"neural network\w*|chatbot\w*|LLM\w*)\b",
        re.IGNORECASE,
    )
    valid_definition_endings = ("리스크.", "위험.", "위해.", "피해.", "침해.")
    forbidden_english_literals = (
        "promptformat", "humanwritten", "generalpurpose", "decisionmaking",
        "attackerchosen", "communityspecific", "firststrike", "fullbody",
        "humanimperceptible", "humaninteraction", "lowand middle-income",
        "memorybased", "foundation-modelbased", "openworld", "socialengineering",
        "trainingdata", "singleobjective", "wholebody", "zeroday",
        "selfdetermination", "LMbased", "broadlyscoped", "highpressure",
        "problemsolving", "chain-ofthought", "retrievalaugmentation",
        "sensitiveinformation", "AIconformity", "criticalinfrastructure",
        "safetyprinciple", "accustomation", "underapplied",
        "post-deployment environmental effects such as manufacturing defects",
        "intelligent system's internals", "producing unintended behavioral modification",
        "are encouraged into manipulating behaviors", "do not get the message",
        "spreading like a viral disease", "pursues inside objectives",
        "materially nefarious", "Covert behavioral manipulation",
        "ethical judgment ability", "a contact-rich manipulation policy",
        "Absent supervisor autonomy risk", "Financial damage",
        "Intellectual property included in prompts",
        "Dissemination of Security Threats Involving Dangerous or Sensitive Information",
        "General-purpose AI incident escalation failure", "Reverse exposure",
        "Theory of mind capability", "Eroded epistemics",
        "Power asymmetries and geopolitical tension from AI capability",
        "Misuse of AI model by user-performed persuasion", "Unsafe instruction topic",
        "Failure to Timely Respond to Physical Hazards",
        "Dexterous humanoid contact-force risk", "Thermal and power throttling under load",
        "broadly-scoped goals", "steer their behavior", "unauthorized transfers",
        "deployment or behavior of AI systems", "system behaviour unreliable to predict",
        "increase their impact area",
    )
    for output in outputs:
        for field in ("L4_Title_ko", "L4_Description_ko"):
            value = output[field]
            if unicodedata.normalize("NFC", value) != value:
                failures["korean_language_qa"].append([output["L4_ID"], field, "non_nfc"])
            if value != value.strip() or re.search(r"[ \t]{2,}", value):
                failures["korean_language_qa"].append([output["L4_ID"], field, "whitespace"])
            for literal in forbidden_literals:
                if literal in value:
                    failures["korean_language_qa"].append([output["L4_ID"], field, literal])
            if "—" in value or "--" in value:
                failures["korean_language_qa"].append([output["L4_ID"], field, "em_dash"])
        if not output["L4_Description_ko"].endswith(valid_definition_endings):
            failures["korean_language_qa"].append([output["L4_ID"], "L4_Description_ko", "risk_ending"])
        if not ai_technology_pattern.search(output["L4_Description_ko"]):
            failures["korean_language_qa"].append([output["L4_ID"], "L4_Description_ko", "ai_subject_missing"])
        if re.search(r"\S+\s+을 이유로", output["L4_Description_ko"]):
            failures["korean_language_qa"].append([output["L4_ID"], "L4_Description_ko", "object_particle"])
        for field in ("L4_Title_en", "L4_Description_en"):
            value = output[field]
            if unicodedata.normalize("NFC", value) != value:
                failures["english_language_qa"].append([output["L4_ID"], field, "non_nfc"])
            if value != value.strip() or re.search(r"[ \t]{2,}", value):
                failures["english_language_qa"].append([output["L4_ID"], field, "whitespace"])
            for literal in forbidden_english_literals:
                if literal in value:
                    failures["english_language_qa"].append([output["L4_ID"], field, literal])
            if "—" in value or "--" in value:
                failures["english_language_qa"].append([output["L4_ID"], field, "em_dash"])
        if not english_ai_technology_pattern.search(output["L4_Description_en"]):
            failures["english_language_qa"].append(
                [output["L4_ID"], "L4_Description_en", "ai_subject_missing"]
            )
        if not output.get("Definition_Grounding_Action", "").strip():
            failures["mapping_status"].append(
                [output["L4_ID"], "Definition_Grounding_Action", "blank"]
            )

    l3_hash = sha256(RELEASE / "L1_L2_L3_Master.csv")
    operative_specification_files = (
        "expert_review_methodology.csv",
        "intent_correction_operations.csv",
        "expert_review_editorial_operations.csv",
        "expert_cross_group_consolidations.csv",
        "user_directed_operations.csv",
        "L4_Korean_Copyedit_Approved_20260829.csv",
        "L4_English_Copyedit_Approved_20260829.csv",
        "L4_Final_Terminology_L3_Alignment_Approved_20260829.csv",
    )
    baseline_input_files = (
        "L1_L2_L3_Master.csv", "L4_General.csv", "L4_Agentic.csv", "L4_Physical.csv",
    )
    pipeline_script_files = (
        "scripts/apply_human_review_round2.py",
        "scripts/validate_human_review_round2.py",
        "05_human_review_round2/_build_korean_copyedit_manifest.mjs",
        "05_human_review_round2/_build_english_copyedit_manifest.mjs",
        "05_human_review_round2/_edit_user_operations.mjs",
    )
    hashed_output_files = (
        "L4_General_Human_Review_Round2_Applied.csv",
        "L4_Agentic_Human_Review_Round2_Applied.csv",
        "L4_Physical_Human_Review_Round2_Applied.csv",
        "Human_Review_Round2_Decision_Ledger.csv",
        "L3_Human_Review_Round2_Reference.csv",
        "L3_Human_Review_Round2_Decision_Ledger.csv",
        "user_directed_operations.csv",
        "L4_Korean_Copyedit_Approved_20260829.csv",
        "L4_English_Copyedit_Approved_20260829.csv",
        "L4_Final_Terminology_L3_Alignment_Approved_20260829.csv",
    )
    provenance_hashes_exact = (
        summary.get("operative_specifications_sha256")
        == {name: sha256(SPEC / name) for name in operative_specification_files}
        and summary.get("baseline_inputs_sha256")
        == {name: sha256(RELEASE / name) for name in baseline_input_files}
        and summary.get("pipeline_scripts_sha256")
        == {name: sha256(ROOT / name) for name in pipeline_script_files}
        and summary.get("output_sha256")
        == {name: sha256(OUT / name) for name in hashed_output_files}
    )
    checks = {
        "input_rows_match_summary": len(ledger) == summary["input_rows"] == 808,
        "output_rows_match_summary": len(outputs) == summary["output_rows"],
        "domain_counts_match_summary": dict(Counter(row["_file_domain"] for row in outputs)) == summary["output_domain_rows"],
        "review_comment_rows_251": sum(bool(row["Human_Review_Comment"].strip()) for row in ledger) == 251,
        "explicit_deletions_4": sum("DELETE_APPLIED" in row["Decision"] for row in ledger) == 4,
        "no_pending_decisions": not any("PENDING" in row["Decision"] for row in ledger),
        "unique_l4_ids": not failures["unique_l4_ids"],
        "master_hierarchy_exact": not failures["master_hierarchy"],
        "domain_file_matches_l1": not failures["domain_file"],
        "id_prefix_matches_l3": not failures["id_prefix"],
        "id_continuity_per_l3": not failures["id_continuity"],
        "bilingual_fields_complete": not failures["bilingual_fields"],
        "no_exact_duplicate_cards": not failures["exact_duplicates"],
        "source_lineage_complete": not any(failures[key] for key in ("deleted_source_links", "lost_sources", "invalid_ledger_links", "unlinked_outputs")),
        "facet_preserved_or_unioned": not failures["facet_preservation"],
        "act_type_preserved_or_unioned": not failures["act_type_preservation"],
        "source_row_ids_preserved_or_unioned": not failures["source_row_id_preservation"],
        "source_l4_ids_preserved_or_unioned": not failures["source_l4_id_preservation"],
        "no_stale_mapping_evidence": not failures["stale_mapping_evidence"],
        "user_directed_merges_exact": (
            len(user_operations) == summary.get("user_directed_operations")
            and not failures["user_directed_merges"]
        ),
        "korean_copyedit_exact": (
            len(copyedit_operations) == summary.get("korean_copyedit_operations")
            and not failures["korean_copyedit_exact"]
        ),
        "english_copyedit_exact": (
            len(english_copyedit_operations) == summary.get("english_copyedit_operations")
            and not failures["english_copyedit_exact"]
        ),
        "final_terminology_l3_qa_exact": (
            len(final_qa_operations) == summary.get("final_terminology_l3_qa_operations")
            and not failures["final_qa_exact"]
        ),
        "korean_language_qa_passed": not failures["korean_language_qa"],
        "english_language_qa_passed": not failures["english_language_qa"],
        "mapping_score_status_explicit": not failures["mapping_status"],
        "l3_master_hash_unchanged": l3_hash == summary["l3_master_sha256"] == EXPECTED_L3_HASH,
        "round2_source_manifest_unchanged": (
            source_manifest_valid
            and source_manifest_hash == summary.get("round2_source_manifest_sha256")
        ),
        "operative_specification_mirrors_exact": (
            (OUT / "user_directed_operations.csv").read_bytes() == user_operations_path.read_bytes()
            and (OUT / "L4_Korean_Copyedit_Approved_20260829.csv").read_bytes()
            == copyedit_path.read_bytes()
            and (OUT / "L4_English_Copyedit_Approved_20260829.csv").read_bytes()
            == english_copyedit_path.read_bytes()
            and (OUT / "L4_Final_Terminology_L3_Alignment_Approved_20260829.csv").read_bytes()
            == final_qa_path.read_bytes()
            and user_operations_hash == summary.get("user_directed_operations_sha256")
            and copyedit_manifest_hash == summary.get("korean_copyedit_manifest_sha256")
            and english_copyedit_manifest_hash == summary.get("english_copyedit_manifest_sha256")
            and final_qa_manifest_hash == summary.get("final_terminology_l3_qa_manifest_sha256")
        ),
        "provenance_hashes_exact": provenance_hashes_exact,
    }
    result = {
        "method": "deterministic validation of human-review application; no EM or Hybrid EM execution",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "counts": {
            "source_rows": len(ledger),
            "review_comment_rows": sum(bool(row["Human_Review_Comment"].strip()) for row in ledger),
            "output_rows": len(outputs),
            "output_domain_rows": dict(Counter(row["_file_domain"] for row in outputs)),
            "user_directed_operations": len(user_operations),
            "korean_copyedit_operations": len(copyedit_operations),
            "english_copyedit_operations": len(english_copyedit_operations),
            "final_terminology_l3_qa_operations": len(final_qa_operations),
        },
        "l3_master_sha256": l3_hash,
        "user_directed_operations_sha256": user_operations_hash,
        "korean_copyedit_manifest_sha256": copyedit_manifest_hash,
        "english_copyedit_manifest_sha256": english_copyedit_manifest_hash,
        "final_terminology_l3_qa_manifest_sha256": final_qa_manifest_hash,
        "failure_details": {key: values for key, values in failures.items() if values},
    }
    destination = OUT / "Human_Review_Round2_Self_Validation.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
