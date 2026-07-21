#!/usr/bin/env python3
"""Build v2.7.0 with mechanism-only L4 definitions and conservative remapping.

The script deliberately excludes the 182 locked Physical AI cards.  It removes
legacy-taxonomy prose from non-Physical definitions, applies a small set of
source-supported editorial corrections, and marks known coverage gaps as HOLD
without inventing a new L3 category.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RELEASE = "v2.6.0"
RELEASE_ID = "v2.7.0"
SOURCE = ROOT / "public" / "data" / "releases" / SOURCE_RELEASE
OUT = ROOT / "public" / "data" / "releases" / RELEASE_ID
REPORT = ROOT / "reports" / "data_quality" / "l4_definition_mapping_remediation_v2.7.0"
SCAFFOLD_MARKER = "This L4 risk card treats"
OVERLOADED_L3_IDS = {
    "RAI3-G-INT-10",  # Anthropomorphism
    "RAI3-G-SYS-08",  # Goal Misalignment
    "RAI3-G-INT-08",  # Copyrights
    "RAI3-G-SYS-03",  # Misinformation/Disinformation
}


ACADEMIC_DEFINITIONS: dict[str, tuple[str, str]] = {
    "RAI4-0109": (
        "A compute-governance accountability gap occurs when access to advanced computing resources, their use, or their concentration is not sufficiently reported, monitored, or governed to permit effective oversight of high-risk AI development.",
        "컴퓨팅 거버넌스 책임 격차는 고위험 AI 개발을 효과적으로 감독할 수 있을 만큼 첨단 연산 자원의 접근·사용·집중이 충분히 보고, 모니터링 또는 관리되지 않는 상태를 말한다.",
    ),
    "RAI4-0116": (
        "A human-override pathway failure occurs when an affected user or supervisor cannot promptly pause, reverse, or correct an AI-mediated action after identifying harmful or inappropriate behavior.",
        "인간 개입 경로 실패는 사용자나 감독자가 유해하거나 부적절한 AI 행위를 발견한 뒤에도 이를 신속히 중지·취소·수정할 수 없는 상태를 말한다.",
    ),
    "RAI4-0709": (
        "Model bias occurs when patterns learned from data or introduced by system design systematically produce stereotyping, exclusion, or materially unequal treatment of social groups.",
        "모델 편향은 데이터에서 학습되거나 시스템 설계에 도입된 패턴이 사회집단에 대한 고정관념, 배제 또는 실질적으로 불평등한 대우를 체계적으로 생성하는 위험이다.",
    ),
    "RAI4-1002": (
        "Reification of essentialist categories occurs when an AI system infers or assigns socially constructed group identities as if they were fixed, natural attributes, thereby reinforcing stereotypes and discriminatory treatment.",
        "본질주의적 범주의 실체화는 AI가 사회적으로 구성된 집단 정체성을 고정되고 자연적인 속성처럼 추론하거나 부여하여 고정관념과 차별적 대우를 강화하는 위험이다.",
    ),
    "RAI4-1073": (
        "Private-information inference is a privacy risk in which an AI system derives a sensitive attribute about a person from correlated information even when that attribute was not explicitly disclosed or present in the person's training record.",
        "사적 정보 추론은 개인이 민감한 속성을 직접 공개하지 않았거나 해당 정보가 그 개인의 학습 기록에 없더라도 AI가 상관정보를 이용해 이를 추론하는 프라이버시 위험이다.",
    ),
    "RAI4-1219": (
        "Environmental impacts are adverse effects of AI development, deployment, or use on climate, ecosystems, energy and water demand, material extraction, pollution, or electronic waste.",
        "환경 영향은 AI의 개발·배포·사용이 기후, 생태계, 에너지·물 수요, 자원 채굴, 오염 또는 전자폐기물에 초래하는 부정적 효과를 말한다.",
    ),
    "RAI4-1221": (
        "Algorithmic bias occurs when an AI system systematically favors or disadvantages people or groups because of biased data, representation, objectives, labels, evaluation, or deployment conditions.",
        "알고리즘 편향은 편향된 데이터·대표성·목표·라벨·평가 또는 배포 조건 때문에 AI가 특정 개인이나 집단을 체계적으로 우대하거나 불리하게 대하는 위험이다.",
    ),
    "RAI4-1302": (
        "Human-extinction risk is the possibility that advanced AI systems initiate, enable, or amplify causal processes capable of irreversibly ending human civilization or the human species.",
        "인류 멸종 위험은 고도 AI가 인류 문명이나 인류 종을 비가역적으로 종식할 수 있는 인과 과정을 시작·지원·증폭할 가능성을 말한다.",
    ),
    "RAI4-1371": (
        "AI-driven labor displacement occurs when automation substitutes for human work faster or more broadly than workers and institutions can adapt, causing involuntary job loss or occupational disruption.",
        "AI 기반 노동 대체는 자동화가 노동자와 제도의 적응 속도보다 빠르거나 광범위하게 인간 노동을 대체하여 비자발적 실직이나 직업 구조의 혼란을 초래하는 위험이다.",
    ),
    "RAI4-1431": (
        "Uncorrectable harmful goal pursuit occurs when a highly capable AI system pursues an assigned or learned objective in ways that harm human interests while resisting correction, interruption, or shutdown.",
        "교정 불가능한 유해 목표 추구는 고도 AI가 인간의 이익을 해치는 방식으로 부여되거나 학습된 목표를 추구하면서 수정·중단·종료에 저항하는 위험이다.",
    ),
    "RAI4-1581": (
        "Sockpuppet-account creation is the automated generation or operation of fictitious online identities used to conceal sponsorship, simulate independent support, or manipulate information environments.",
        "가상 인물 계정 생성은 후원 주체를 숨기거나 독립적 지지를 가장하거나 정보 환경을 조작하기 위해 허구의 온라인 정체성을 자동 생성·운영하는 위험이다.",
    ),
    "RAI4-1660": (
        "Workforce disruption comprises changes in job availability, task composition, wages, bargaining power, and income distribution caused by the adoption of AI systems.",
        "노동력 혼란은 AI 도입으로 인해 일자리 수, 업무 구성, 임금, 교섭력 및 소득 분배가 변화하는 위험을 말한다.",
    ),
    "RAI4-1182": (
        "Societal manipulation occurs when AI is used to covertly shape collective beliefs, norms, or behavior by exploiting social dynamics at scale.",
        "사회 조작은 AI가 사회적 역학을 대규모로 악용하여 집단의 신념·규범·행동을 은밀하게 형성하는 위험이다.",
    ),
    "RAI4-0665": (
        "AI-enabled child sexual abuse material is sexual content depicting or representing a minor that is generated, transformed, distributed, or facilitated by an AI system.",
        "AI 기반 아동 성착취물은 AI가 생성·변형·유통하거나 그 제작을 지원한 미성년자 묘사 성적 콘텐츠를 말한다.",
    ),
    "RAI4-0755": (
        "A model-extraction attack queries or otherwise probes an AI service to reconstruct its parameters, decision behavior, or proprietary capabilities without authorization.",
        "모델 추출 공격은 AI 서비스를 반복 질의하거나 탐색하여 권한 없이 모델의 매개변수, 의사결정 행태 또는 독점 역량을 재구성하는 공격이다.",
    ),
    "RAI4-0756": (
        "A prompt-inversion attack attempts to recover private or proprietary prompt text from an AI system's outputs or observable behavior without authorization.",
        "프롬프트 역추론 공격은 AI의 출력이나 관찰 가능한 행태로부터 비공개 또는 독점 프롬프트 문구를 권한 없이 복원하려는 공격이다.",
    ),
    "RAI4-1087": (
        "AI-generated defamation occurs when an AI system produces or amplifies false factual claims that unjustifiably damage an identifiable person's or organization's reputation.",
        "AI 생성 명예훼손은 AI가 식별 가능한 개인이나 조직의 평판을 부당하게 훼손하는 허위 사실 주장을 생성하거나 증폭하는 위험이다.",
    ),
    "RAI4-1585": (
        "Scaling and amplification risk arises when AI automates or expands a harmful workflow so that its speed, reach, persistence, or target count substantially increases.",
        "규모화·증폭 위험은 AI가 유해한 작업 흐름을 자동화하거나 확장하여 속도, 도달 범위, 지속성 또는 표적 수를 크게 늘리는 위험이다.",
    ),
    "RAI4-1625": (
        "Proprietary-data exposure occurs when an AI system accesses, reproduces, infers, or discloses confidential business information without authorization.",
        "독점 데이터 노출은 AI가 권한 없이 기업의 기밀 정보를 접근·복제·추론 또는 공개하는 위험이다.",
    ),
}


# Only cases for which the label, mechanism definition, and cited source support
# the destination are moved.  Gap cases keep HOLD even after operational remap.
REMAPS: dict[str, tuple[str, bool, str]] = {
    "RAI4-0109": ("RAI3-G-SYS-09", True, "TAXONOMY_GAP_GOVERNANCE_ACCOUNTABILITY"),
    "RAI4-0116": ("RAI3-G-SYS-09", True, "CLOSEST_OPERATIONAL_FIT_HUMAN_OVERRIDE"),
    "RAI4-0709": ("RAI3-G-INT-04", True, "BROADER_THAN_CONTENT_LEVEL_UNFAIRNESS"),
    "RAI4-1002": ("RAI3-G-INT-04", False, "DIRECT_DISCRIMINATION_MECHANISM"),
    "RAI4-1073": ("RAI3-G-INT-06", False, "DIRECT_PRIVATE_ATTRIBUTE_INFERENCE"),
    "RAI4-1221": ("RAI3-G-INT-04", True, "ALLOCATIVE_DISCRIMINATION_TAXONOMY_GAP"),
    "RAI4-1302": ("RAI3-G-SYS-08", True, "TAXONOMY_GAP_EXISTENTIAL_RISK"),
    "RAI4-1431": ("RAI3-G-SYS-08", False, "CONCRETE_UNCORRECTABLE_GOAL_PURSUIT"),
    "RAI4-1581": ("RAI3-G-SYS-03", True, "DELIBERATE_DECEPTION_NOT_COVERED_BY_L3"),
}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mechanism_only(value: str) -> tuple[str, bool]:
    if SCAFFOLD_MARKER not in value:
        return re.sub(r"\s+", " ", value).strip(), False
    core = value.split(SCAFFOLD_MARKER, 1)[0]
    core = re.sub(r"\s+", " ", core).strip().rstrip(" ,;")
    if core and core[-1] not in ".!?”\"":
        core += "."
    return core, True


def breadcrumb_for(l3_id: str, nodes: dict[str, dict]) -> list[dict]:
    path: list[dict] = []
    current = l3_id
    while current:
        node = nodes[current]
        path.append({
            "node_id": current,
            "label_en": node["label_en"],
            "label_ko": node["label_ko"],
        })
        current = node.get("parent_id")
    return list(reversed(path))


def main() -> None:
    cards = read(SOURCE / "cards.json")["cards"]
    hierarchy = read(SOURCE / "hierarchy.json")
    nodes = {row["node_id"]: row for row in hierarchy["nodes"]}
    scores = {row["l4_id"]: row for row in read(ROOT / "data/releases/v1.0.0/algorithm_scores.json")}
    physical_before = {
        row["l4_id"]: json.dumps(row, ensure_ascii=False, sort_keys=True)
        for row in cards if row["assignment_status"] == "locked_physical"
    }

    cleaned_ids: list[str] = []
    remap_rows: list[dict] = []
    hold_added: list[dict] = []
    review_rows: list[dict] = []

    for card in cards:
        card["release_id"] = RELEASE_ID
        if card["assignment_status"] == "locked_physical":
            continue

        core, cleaned = mechanism_only(card.get("definition_en", ""))
        if cleaned:
            cleaned_ids.append(card["l4_id"])
        card["definition_en"] = core
        card["definition_method"] = "source_mechanism_only_v2.7"
        card["legacy_taxonomy_prose_removed"] = cleaned

        if card["l4_id"] in ACADEMIC_DEFINITIONS:
            card["definition_en"], card["definition_ko"] = ACADEMIC_DEFINITIONS[card["l4_id"]]
            card["definition_method"] = "source_checked_editorial_definition_v2.7"

        if card["l4_id"] == "RAI4-1431":
            card["original_label_en"] = card.get("original_label_en", card["label_en"])
            card["label_en"] = "Uncorrectable harmful goal pursuit"
            card["label_ko"] = "교정 불가능한 유해 목표 추구"

        if card["l4_id"] in REMAPS:
            new_l3, must_hold, reason = REMAPS[card["l4_id"]]
            old_l3 = card["primary_l3_id"]
            card["primary_l3_id"] = new_l3
            card["breadcrumb"] = breadcrumb_for(new_l3, nodes)
            card["mapping_review_method"] = "definition_label_evidence_editorial_review_v2.7"
            card["decision_required"] = must_hold
            card["decision_reason"] = reason if must_hold else None
            card["review_status"] = "human_review_required" if must_hold else "editorially_reviewed"
            remap_rows.append({
                "l4_id": card["l4_id"], "label_en": card["label_en"],
                "from_l3": old_l3, "to_l3": new_l3,
                "hold": must_hold, "reason": reason,
            })

        score = scores.get(card["l4_id"], {})
        gaps = score.get("gap_sentinels", [])
        if gaps and not card["decision_required"]:
            card["decision_required"] = True
            card["decision_reason"] = "TAXONOMY_GAP:" + ",".join(sorted(gaps))
            card["review_status"] = "human_review_required"
            hold_added.append({
                "l4_id": card["l4_id"], "label_en": card["label_en"],
                "primary_l3_id": card["primary_l3_id"],
                "hold_basis": "TAXONOMY_GAP:" + "|".join(sorted(gaps)),
            })

        assigned_l3 = card["primary_l3_id"]
        eligible = score.get("eligible_l3_ids", [])
        suitability = card.get("stage2_suitability_score")
        anthropomorphism_not_established = (
            assigned_l3 == "RAI3-G-INT-10" and assigned_l3 not in eligible
        )
        overloaded_low_fit = (
            assigned_l3 in OVERLOADED_L3_IDS
            and assigned_l3 not in eligible
            and suitability is not None
            and suitability < 0.45
        )
        if (anthropomorphism_not_established or overloaded_low_fit) and not card["decision_required"]:
            reason = (
                "ANTHROPOMORPHISM_DIRECT_MECHANISM_NOT_ESTABLISHED"
                if anthropomorphism_not_established
                else "OVERLOADED_L3_LOW_EVIDENCE_FIT"
            )
            card["decision_required"] = True
            card["decision_reason"] = reason
            card["review_status"] = "human_review_required"
            hold_added.append({
                "l4_id": card["l4_id"], "label_en": card["label_en"],
                "primary_l3_id": assigned_l3, "hold_basis": reason,
            })

        word_count = len(card["definition_en"].split())
        if word_count < 12:
            card["definition_review_status"] = "human_review_required"
            review_rows.append({
                "l4_id": card["l4_id"], "label_en": card["label_en"],
                "word_count": word_count, "definition_en": card["definition_en"],
            })
        else:
            card["definition_review_status"] = "mechanism_definition_checked"

    # Replace the weak contextual citation on the compute-governance card with
    # the directly relevant peer-reviewed preprint record.
    compute_card = next(row for row in cards if row["l4_id"] == "RAI4-0109")
    compute_card["references"] = [{
        "title": "Computing Power and the Governance of Artificial Intelligence",
        "url": "https://arxiv.org/abs/2402.08797",
        "type": "paper",
        "source_system": "editorial_evidence_upgrade_v2.7",
    }]

    physical_after = {
        row["l4_id"]: json.dumps({**row, "release_id": SOURCE_RELEASE}, ensure_ascii=False, sort_keys=True)
        for row in cards if row["assignment_status"] == "locked_physical"
    }
    if physical_before != physical_after:
        raise RuntimeError("Physical AI lock changed")
    if any(SCAFFOLD_MARKER in row.get("definition_en", "") for row in cards if row["assignment_status"] != "locked_physical"):
        raise RuntimeError("Legacy taxonomy prose remains in a non-Physical definition")

    hierarchy["release_id"] = RELEASE_ID
    cards_path = OUT / "cards.json"
    hierarchy_path = OUT / "hierarchy.json"
    write(cards_path, {"release_id": RELEASE_ID, "cards": cards})
    write(hierarchy_path, hierarchy)

    REPORT.mkdir(parents=True, exist_ok=True)
    for name, rows, fields in (
        ("remapped_cards.csv", remap_rows, ["l4_id", "label_en", "from_l3", "to_l3", "hold", "reason"]),
        ("holds_added.csv", hold_added, ["l4_id", "label_en", "primary_l3_id", "hold_basis"]),
        ("definition_review_queue.csv", review_rows, ["l4_id", "label_en", "word_count", "definition_en"]),
    ):
        with (REPORT / name).open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    nonphysical = [row for row in cards if row["assignment_status"] != "locked_physical"]
    l3_rows = []
    for l3_id, count in Counter(row["primary_l3_id"] for row in nonphysical).most_common():
        group = [row for row in nonphysical if row["primary_l3_id"] == l3_id]
        rule_supported = sum(l3_id in scores.get(row["l4_id"], {}).get("eligible_l3_ids", []) for row in group)
        l3_rows.append({
            "l3_id": l3_id,
            "label_en": nodes[l3_id]["label_en"],
            "card_count": count,
            "share_of_nonphysical_pct": round(100 * count / len(nonphysical), 2),
            "rule_supported_count": rule_supported,
            "rule_supported_pct": round(100 * rule_supported / count, 2),
            "hold_count": sum(row["decision_required"] for row in group),
        })
    with (REPORT / "l3_load_audit.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(l3_rows[0]))
        writer.writeheader()
        writer.writerows(l3_rows)

    summary = {
        "release_id": RELEASE_ID,
        "source_release": SOURCE_RELEASE,
        "population": {"all_l4": len(cards), "physical_locked_unchanged": 182, "nonphysical": len(nonphysical)},
        "definition_remediation": {
            "legacy_taxonomy_scaffolds_removed": len(cleaned_ids),
            "editorial_academic_definitions": len(ACADEMIC_DEFINITIONS),
            "short_definition_review_queue": len(review_rows),
            "remaining_banned_scaffolds": 0,
        },
        "mapping_remediation": {
            "cards_remapped": len(remap_rows),
            "quality_holds_added": len(hold_added),
            "decision_required_total": sum(row["decision_required"] for row in cards),
            "policy": "All cards retain an operational L3 path; HOLD denotes that the path is not an approved taxonomic fit.",
        },
        "quality_boundary": "L3 load is a triage signal, not evidence of semantic fit. Remapping requires agreement among label, mechanism-only definition, and cited evidence.",
    }
    write(REPORT / "summary.json", summary)
    (REPORT / "methodology.md").write_text(
        "# L4 definition and mapping remediation (v2.7.0)\n\n"
        "The unit of analysis is one canonical L4 card. The 182 locked Physical AI cards are byte-equivalent to v2.6.0 except for the release identifier and are excluded from editorial changes.\n\n"
        "Legacy L1–L3 names embedded in prose were removed because they are provenance metadata, not definitions of the L4 mechanism. A valid L4 definition states the condition or system behavior, the failure or harm mechanism, and the affected outcome without using the assigned hierarchy as circular justification.\n\n"
        "Overloaded L3 nodes were inspected using card count, share, conservative rule support, gap-sentinel incidence, and HOLD rate. Load alone never triggers remapping. A card is moved only when its title, mechanism-only definition, and evidence support the destination. Where none of the 50 L3 nodes provides a valid fit, the card remains operationally assigned and is marked HOLD pending a human taxonomy decision.\n",
        encoding="utf-8",
    )

    manifest = {
        "release_id": RELEASE_ID,
        "source_release": SOURCE_RELEASE,
        "release_status": "mechanism_definition_and_mapping_quality_remediation",
        "counts": {
            "l4": len(cards), "classified": len(cards), "physical_locked": 182,
            "physical_total": 182, "decision_required": summary["mapping_remediation"]["decision_required_total"],
            "l1_nodes": sum(row["level"] == 1 for row in hierarchy["nodes"]),
            "l2_categories": len(hierarchy["canonical_l2_categories"]),
            "l2_path_nodes": sum(row["level"] == 2 for row in hierarchy["nodes"]),
            "l3_nodes": sum(row["level"] == 3 for row in hierarchy["nodes"]),
        },
        "artifacts": [
            {"path": "cards.json", "sha256": sha256(cards_path)},
            {"path": "hierarchy.json", "sha256": sha256(hierarchy_path)},
            {"path": str((REPORT / "summary.json").relative_to(ROOT)), "sha256": sha256(REPORT / "summary.json")},
        ],
    }
    write(OUT / "manifest.json", manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
