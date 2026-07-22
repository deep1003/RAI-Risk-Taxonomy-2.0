#!/usr/bin/env python3
"""Create v2.16.0 with first-pass evidence enrichment for remediable HOLD cards."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RELEASE = "v2.15.0"
RELEASE_ID = "v2.16.0"
SOURCE = ROOT / "public/data/releases" / SOURCE_RELEASE
OUT = ROOT / "public/data/releases" / RELEASE_ID
REPORT = ROOT / "reports/data_quality/hold_evidence_enrichment_v2.16.0"


EVIDENCE: dict[str, list[dict]] = {
    "RAI4-0080": [
        {
            "title": "EU AI Act, Article 6: Classification rules for high-risk AI systems",
            "url": "https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-6",
            "type": "regulation",
            "source_system": "v2.16_evidence_enrichment",
            "evidence_note": "Directly supports the risk of incorrect high-risk classification and its downstream oversight consequences.",
        }
    ],
    "RAI4-0082": [
        {
            "title": "NIST AI 700-2: Adversarial Machine Learning: A Taxonomy and Terminology of Attacks and Mitigations",
            "url": "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.700-2.pdf",
            "type": "report",
            "source_system": "v2.16_evidence_enrichment",
            "evidence_note": "Provides a direct taxonomy for robustness and adversarial evaluation risks.",
        }
    ],
    "RAI4-0083": [
        {
            "title": "NIST AI 600-1: Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile",
            "url": "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence",
            "type": "report",
            "source_system": "v2.16_evidence_enrichment",
            "evidence_note": "Supports benchmark and measurement governance as a risk-management function for generative AI.",
        }
    ],
    "RAI4-0085": [
        {
            "title": "NIST AI 600-1: Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile",
            "url": "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence",
            "type": "report",
            "source_system": "v2.16_evidence_enrichment",
            "evidence_note": "Supports red-team testing governance, measurement, and control linkage.",
        }
    ],
    "RAI4-0086": [
        {
            "title": "AI Regulation: Competition, Arbitrage & Regulatory Capture",
            "url": "https://scholarship.law.georgetown.edu/facpub/2647/",
            "type": "paper",
            "source_system": "v2.16_evidence_enrichment",
            "evidence_note": "Directly addresses regulatory arbitrage and capture risks in AI governance.",
        }
    ],
    "RAI4-0087": [
        {
            "title": "AI Regulation: Competition, Arbitrage & Regulatory Capture",
            "url": "https://scholarship.law.georgetown.edu/facpub/2647/",
            "type": "paper",
            "source_system": "v2.16_evidence_enrichment",
            "evidence_note": "Directly addresses regulatory capture risk in AI governance.",
        },
        {
            "title": "Regulatory Capture in Frontier AI Governance",
            "url": "https://arxiv.org/html/2410.13042v1",
            "type": "paper",
            "source_system": "v2.16_evidence_enrichment",
            "evidence_note": "Provides a targeted frontier-AI regulatory-capture analysis.",
        },
    ],
    "RAI4-0089": [
        {
            "title": "International AI governance: a complex and fragmented landscape",
            "url": "https://www.nature.com/articles/s41599-024-03560-x",
            "type": "paper",
            "source_system": "v2.16_evidence_enrichment",
            "evidence_note": "Supports the risk of fragmented international coordination in AI governance.",
        }
    ],
    "RAI4-0090": [
        {
            "title": "AI Regulation: Competition, Arbitrage & Regulatory Capture",
            "url": "https://scholarship.law.georgetown.edu/facpub/2647/",
            "type": "paper",
            "source_system": "v2.16_evidence_enrichment",
            "evidence_note": "Supports jurisdictional arbitrage and cross-border enforcement concerns.",
        }
    ],
    "RAI4-0095": [
        {
            "title": "EU AI Act, Article 71: EU database for high-risk AI systems",
            "url": "https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-71",
            "type": "regulation",
            "source_system": "v2.16_evidence_enrichment",
            "evidence_note": "Directly supports registry completeness and metadata disclosure as governance controls.",
        }
    ],
    "RAI4-0099": [
        {
            "title": "Fixing AI Washing: Stronger Rules for AI Claims",
            "url": "https://arxiv.org/abs/2601.06611",
            "type": "paper",
            "source_system": "v2.16_evidence_enrichment",
            "evidence_note": "Directly addresses unsupported AI claims and AI washing.",
        }
    ],
}


DEFINITIONS: dict[str, tuple[str, str]] = {
    "RAI4-0080": (
        "Risk classification error occurs when an AI system is assigned to an incorrect legal, organizational, or operational risk tier, causing oversight, testing, documentation, or accountability duties to be underapplied.",
        "리스크 분류 오류는 AI 시스템이 법적·조직적·운영상의 위험 등급에 잘못 배정되어 감독, 시험, 문서화 또는 책임성 의무가 충분히 적용되지 않는 위험이다.",
    ),
    "RAI4-0082": (
        "Capability evaluation non-disclosure occurs when an organization withholds or obscures evidence about dangerous capabilities, known limitations, adversarial robustness, or residual risks that is needed for external oversight.",
        "역량 평가 비공개는 조직이 외부 감독에 필요한 위험 역량, 알려진 한계, 적대적 강건성 또는 잔여 위험에 관한 평가 근거를 숨기거나 불분명하게 공개하는 위험이다.",
    ),
    "RAI4-0083": (
        "Benchmark governance failure occurs when benchmark design, leakage control, saturation monitoring, or use interpretation is weak enough to produce misleading safety or accountability signals.",
        "벤치마크 거버넌스 실패는 벤치마크 설계, 유출 통제, 포화도 관리 또는 결과 해석이 취약하여 안전성과 책임성에 대해 오해를 낳는 신호를 생성하는 위험이다.",
    ),
    "RAI4-0085": (
        "Red-team governance failure occurs when adversarial testing is too narrow, non-independent, poorly documented, or disconnected from release, mitigation, escalation, and monitoring decisions.",
        "레드팀 거버넌스 실패는 적대적 시험이 지나치게 좁거나 독립성이 부족하거나 문서화가 약하거나 출시, 완화, 상향 보고 및 모니터링 결정과 연결되지 않는 위험이다.",
    ),
    "RAI4-0086": (
        "Regulatory arbitrage occurs when AI developers or deployers structure activities across jurisdictions, sectors, or organizational forms to avoid stronger oversight obligations.",
        "규제 차익거래는 AI 개발자나 배포자가 더 강한 감독 의무를 피하기 위해 관할, 산업 부문 또는 조직 형태를 전략적으로 선택하거나 재구성하는 위험이다.",
    ),
    "RAI4-0087": (
        "Regulatory capture in AI governance occurs when regulated firms or dominant technology providers exert disproportionate influence over standards, oversight institutions, or policy agendas.",
        "AI 거버넌스의 규제 포획은 규제 대상 기업이나 지배적 기술 제공자가 표준, 감독 기관 또는 정책 의제에 과도한 영향력을 행사하는 위험이다.",
    ),
    "RAI4-0089": (
        "International coordination failure occurs when national AI governance regimes do not align sufficiently on cross-border risks, incident reporting, enforcement, or accountability mechanisms.",
        "국제 조정 실패는 국가별 AI 거버넌스 체계가 국경을 넘는 위험, 사고 보고, 집행 또는 책임성 메커니즘에 대해 충분히 정렬되지 않는 위험이다.",
    ),
    "RAI4-0090": (
        "Cross-border enforcement gap occurs when regulators cannot effectively impose duties or remedies because AI providers, models, data, users, and harms span multiple jurisdictions.",
        "국경 간 집행 격차는 AI 제공자, 모델, 데이터, 사용자 및 피해가 여러 관할에 걸쳐 있어 규제기관이 의무나 구제 조치를 효과적으로 집행하지 못하는 위험이다.",
    ),
    "RAI4-0095": (
        "AI registry incompleteness occurs when public or internal AI registers omit deployed systems, intended uses, providers, risk categories, testing evidence, or other oversight-relevant metadata.",
        "AI 등록부 불완전성은 공개 또는 내부 AI 등록부가 배포된 시스템, 의도된 사용, 제공자, 위험 범주, 시험 근거 또는 감독에 필요한 메타데이터를 누락하는 위험이다.",
    ),
    "RAI4-0099": (
        "AI ethics washing occurs when an organization uses responsible-AI commitments, labels, or public claims as reputational signals without operational accountability, evidence, or enforceable controls.",
        "AI 윤리 준수 위장은 조직이 운영상 책임성, 근거 또는 집행 가능한 통제 없이 책임 AI 약속, 라벨 또는 공개 주장을 평판 신호로 사용하는 위험이다.",
    ),
}


URL_VERIFICATIONS = [
    {
        "url": "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence",
        "status": "HTTP 200",
        "verified_on": "2026-07-22",
    },
    {
        "url": "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.700-2.pdf",
        "status": "HTTP 200",
        "verified_on": "2026-07-22",
    },
    {
        "url": "https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-6",
        "status": "HTTP 200",
        "verified_on": "2026-07-22",
    },
    {
        "url": "https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-71",
        "status": "HTTP 200",
        "verified_on": "2026-07-22",
    },
    {
        "url": "https://scholarship.law.georgetown.edu/facpub/2647/",
        "status": "HTTP 200",
        "verified_on": "2026-07-22",
    },
    {
        "url": "https://arxiv.org/html/2410.13042v1",
        "status": "HTTP 200",
        "verified_on": "2026-07-22",
    },
    {
        "url": "https://www.nature.com/articles/s41599-024-03560-x",
        "status": "HTTP 303 to publisher identity flow, article endpoint resolved",
        "verified_on": "2026-07-22",
    },
    {
        "url": "https://arxiv.org/abs/2601.06611",
        "status": "HTTP 200",
        "verified_on": "2026-07-22",
    },
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add_reference(card: dict, ref: dict) -> bool:
    refs = card.setdefault("references", [])
    if any(existing.get("url") == ref["url"] for existing in refs):
        return False
    refs.append(ref)
    return True


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SOURCE, OUT)
    cards_doc = load_json(OUT / "cards.json")
    cards = cards_doc["cards"]
    changed_rows = []
    for card in cards:
        card["release_id"] = RELEASE_ID
        if card["l4_id"] not in EVIDENCE:
            continue
        old_definition_en = card.get("definition_en", "")
        old_definition_ko = card.get("definition_ko", "")
        new_definition_en, new_definition_ko = DEFINITIONS[card["l4_id"]]
        card["definition_en"] = new_definition_en
        card["definition_ko"] = new_definition_ko
        added = 0
        for ref in EVIDENCE[card["l4_id"]]:
            added += int(add_reference(card, ref))
        card["evidence_enrichment_status"] = "first_pass_direct_reference_added_v2.16"
        card["definition_review_status"] = "evidence_enriched_definition_checked"
        card["hold_remediation_class"] = "evidence_enrichment_candidate"
        changed_rows.append({
            "l4_id": card["l4_id"],
            "label_en": card["label_en"],
            "references_added": added,
            "old_definition_en": old_definition_en,
            "new_definition_en": new_definition_en,
            "old_definition_ko": old_definition_ko,
            "new_definition_ko": new_definition_ko,
        })
    cards_doc["release_id"] = RELEASE_ID
    hierarchy_doc = load_json(OUT / "hierarchy.json")
    hierarchy_doc["release_id"] = RELEASE_ID
    write_json(OUT / "cards.json", cards_doc)
    write_json(OUT / "hierarchy.json", hierarchy_doc)

    REPORT.mkdir(parents=True, exist_ok=True)
    write_json(REPORT / "evidence_added.json", {"release_id": RELEASE_ID, "cards": changed_rows})
    write_json(REPORT / "url_verification.json", {"release_id": RELEASE_ID, "urls": URL_VERIFICATIONS})
    summary = {
        "release_id": RELEASE_ID,
        "source_release": SOURCE_RELEASE,
        "cards_enriched": len(changed_rows),
        "references_added": sum(row["references_added"] for row in changed_rows),
        "hold_cards_before": sum(1 for card in cards if card.get("decision_required")),
        "hold_cards_after": sum(1 for card in cards if card.get("decision_required")),
        "hold_removed": 0,
        "url_verifications_recorded": len(URL_VERIFICATIONS),
        "policy": "Evidence enrichment and definition repair do not automatically clear HOLD; remediated cards require a follow-up mapping reliability rerun or human approval.",
    }
    write_json(REPORT / "summary.json", summary)

    manifest = load_json(OUT / "manifest.json")
    manifest["release_id"] = RELEASE_ID
    manifest["source_release"] = SOURCE_RELEASE
    manifest["status"] = "published"
    manifest["summary"]["release_id"] = RELEASE_ID
    manifest["summary"]["source_release"] = SOURCE_RELEASE
    manifest["summary"]["evidence_enrichment"] = summary
    manifest["files"] = [
        {"path": f"public/data/releases/{RELEASE_ID}/cards.json", "sha256": sha256(OUT / "cards.json")},
        {"path": f"public/data/releases/{RELEASE_ID}/hierarchy.json", "sha256": sha256(OUT / "hierarchy.json")},
        {"path": f"reports/data_quality/hold_evidence_enrichment_v2.16.0/summary.json", "sha256": sha256(REPORT / "summary.json")},
        {"path": f"reports/data_quality/hold_evidence_enrichment_v2.16.0/evidence_added.json", "sha256": sha256(REPORT / "evidence_added.json")},
        {"path": f"reports/data_quality/hold_evidence_enrichment_v2.16.0/url_verification.json", "sha256": sha256(REPORT / "url_verification.json")},
    ]
    write_json(OUT / "manifest.json", manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
