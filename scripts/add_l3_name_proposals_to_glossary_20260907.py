#!/usr/bin/env python3
"""Add an auditable L3 before/after naming proposal to glossary.html."""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GLOSSARY = ROOT / "glossary.html"
MASTER = ROOT / "releases/RAI-Risk-Taxonomy-2.0-master/data/L1_L2_L3_Master.csv"
AUDIT = ROOT / "data/glossary/l3_name_proposals_20260907.json"
AUDIT_CSV = ROOT / "data/glossary/l3_name_proposals_20260907.csv"

SOURCE_DOCUMENT = "AI2X-L3 최종 리스트 (2026-09-07)"

# Only entries that need clearer scope, harm, or Korean-English correspondence are changed.
# Every other L3 is explicitly retained in the published comparison table.
PROPOSALS = {
    "G_INT_VIOL": (
        "Violence Promotion and Facilitation",
        "폭력 조장·지원",
        "AI가 폭력을 생성·미화하거나 실행을 지원한다는 정의의 직접 피해를 명시",
    ),
    "G_INT_PRIV": (
        "Privacy and Personal Information Infringement",
        "개인정보·프라이버시 침해",
        "개인정보 처리 위험과 사생활·자기결정권 침해를 함께 포섭",
    ),
    "G_INT_ILLEGAL": (
        "Illegal Conduct Facilitation",
        "불법 행위 조장·지원",
        "AI가 불법 행위를 가능하게 하거나 지원하는 작동 관계를 명시",
    ),
    "G_INT_WEAP": (
        "Weaponization and Harmful Capability Enablement",
        "무기화·유해 역량 지원",
        "무기 자체뿐 아니라 사이버·CBRN 등 유해 역량 지원 범위를 명시",
    ),
    "G_INT_ANTH": (
        "Misleading Anthropomorphism",
        "오인 유발 의인화",
        "의인화 일반이 아니라 능력·감정·정체성에 관한 오인 위험으로 한정",
    ),
    "G_INT_REL": (
        "Harmful Human-AI Relationships",
        "해로운 인간-AI 관계",
        "영문과 한국어의 위해 강도와 복수 관계 범위를 일치",
    ),
    "G_SYS_OREF": (
        "Excessive Refusal",
        "과도한 거절",
        "불필요한 하이픈을 제거하고 현행 한국어와 직접 대응",
    ),
    "G_SYS_OEXT": (
        "Capability Overreach",
        "역량 범위 초과 수행",
        "검증된 역량 범위를 넘어 수행한다는 측정 가능한 실패 조건을 명시",
    ),
    "G_SYS_MISINFO": (
        "False and Misleading Information",
        "허위·오인 정보",
        "사실과 다른 정보와 오인을 유발하는 정보를 함께 포섭",
    ),
    "G_SYS_CONTEXT": (
        "Contextual Understanding Failure",
        "맥락 이해 실패",
        "단순 인식보다 대화·사용자·제약조건의 이해 실패라는 정의에 정합화",
    ),
    "G_SYS_INCONS": (
        "Output Inconsistency",
        "출력 비일관성",
        "동일·유사 입력에서 발생하는 출력 변동이라는 관찰 대상을 명시",
    ),
    "G_SYS_OVERCONF": (
        "Unwarranted Confidence",
        "근거 없는 확신",
        "확신 일반이 아니라 근거·불확실성과 불일치하는 표현 위험으로 한정",
    ),
    "G_SYS_CONTEST": (
        "Lack of Contestability",
        "이의제기 가능성 부족",
        "절대적 차단보다 이의제기·정정·구제 수단의 불충분성을 포섭",
    ),
    "G_SOC_ENV": (
        "Environmental and Sustainability Harm",
        "환경·지속가능성 위해",
        "긍정적 영향도 포함할 수 있는 impact 대신 위험 범주임을 명시",
    ),
    "G_SOC_GOV": (
        "Governance and Accountability Gaps",
        "거버넌스·책임성 공백",
        "거버넌스와 책임성의 제도적 공백을 병렬로 명확화",
    ),
    "A_SYS_AUTH": (
        "Excessive Authority and Autonomous Agency",
        "과도한 권한·자율적 행위능력",
        "권한과 독립적으로 행동하는 능력을 구분하여 agency의 의미를 보존",
    ),
    "A_SYS_TRACE": (
        "Accountability and Traceability Gaps",
        "책임 소재·추적성 공백",
        "책임 주체와 행위 기록 추적의 두 결함을 병렬로 명시",
    ),
    "A_INT_COORD": (
        "Coordination and Cooperation Failure",
        "조정·협력 실패",
        "다중 에이전트의 조정과 공동 수행 실패를 함께 포섭",
    ),
    "A_INT_CONFLICT": (
        "Adversarial Agent Conflict",
        "에이전트 간 경쟁적 갈등",
        "일반 경쟁이 아니라 에이전트 간 적대적 상호작용으로 범위를 한정",
    ),
    "A_INT_COLLUSION": (
        "Agent Collusion",
        "에이전트 간 담합·결탁",
        "시장 일반의 담합과 구별되는 다중 에이전트 행위를 명시",
    ),
    "P_SYS_CONTROL": (
        "Unsafe Physical Control and Actuation Failure",
        "불안전한 물리 제어·구동 실패",
        "물리적 제어 출력과 구동 계통의 실패라는 위험 형태를 명시",
    ),
    "P_SYS_HARDWARE": (
        "Hardware and Mechanical Integrity Failure",
        "하드웨어·기계적 무결성 실패",
        "영문 failure와 한국어 실패를 맞추고 기계적 무결성의 의미를 보존",
    ),
    "P_INT_SAFETY": (
        "Human-Robot Physical Safety Failure",
        "인간-로봇 물리적 안전 실패",
        "physical의 수식 범위를 자연스러운 한국어로 정비",
    ),
    "P_INT_TAMPER": (
        "Physical Tampering and Sabotage",
        "물리적 변조·파괴 행위",
        "sabotage를 단순 파손보다 의도적 파괴 행위로 명확화",
    ),
}

DOMAIN_LABELS = {
    "L1_G": ("General AI", "범용 AI"),
    "L1_A": ("Agentic AI", "에이전틱 AI"),
    "L1_P": ("Physical AI", "피지컬 AI"),
}

CSS = """
.l3-proposals{scroll-margin-top:118px;background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:20px;margin:22px 0 26px;box-shadow:0 1px 2px rgba(16,24,40,.04)}
.l3-proposals h2{margin:0 0 6px;font-size:21px;color:var(--navy)}
.l3-proposals .lead{margin:0;color:var(--muted);font-size:13.5px}
.proposal-summary{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}
.proposal-pill{background:#eef2fb;color:#26428f;border-radius:999px;padding:4px 10px;font-size:12px;font-weight:700}
.proposal-domain{margin-top:16px;border-top:1px solid var(--line);padding-top:13px}
.proposal-domain h3{margin:0 0 8px;font-size:16px}
.proposal-table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px}
.proposal-table{width:100%;border-collapse:collapse;min-width:880px;font-size:12.5px;line-height:1.45}
.proposal-table th{background:#f8fafc;color:#344054;text-align:left;font-size:11.5px;letter-spacing:.02em}
.proposal-table th,.proposal-table td{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
.proposal-table tr:last-child td{border-bottom:0}
.proposal-table .pid{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:#344054;white-space:nowrap}
.proposal-table .ko-name{color:var(--navy);font-weight:650}
.proposal-table .reason{color:var(--muted)}
.proposal-status{display:inline-block;border-radius:999px;padding:2px 7px;font-size:10.5px;font-weight:700;white-space:nowrap}
.proposal-status--change{background:#fff1e6;color:#9a3412}
.proposal-status--retain{background:#ecfdf3;color:#027a48}
.proposal-source{margin:12px 0 0;font-size:12px;color:var(--muted)}
.proposal-source a{color:var(--general);text-decoration:none}.proposal-source a:hover{text-decoration:underline}
@media(max-width:640px){.l3-proposals{padding:16px 13px}.l3-proposals h2{font-size:18px}.proposal-table{font-size:12px}}
""".strip()


def read_rows() -> list[dict[str, str]]:
    with MASTER.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 47:
        raise ValueError(f"Expected 47 L3 rows, found {len(rows)}")
    return rows


def build_payload(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    payload = []
    for row in rows:
        risk_id = row["L3_ID"]
        if risk_id in PROPOSALS:
            after_en, after_ko, rationale = PROPOSALS[risk_id]
            status = "개정 제안"
        else:
            after_en = row["L3_Title_en"]
            after_ko = row["L3_Title_ko"]
            rationale = "현행 명칭이 정의 범위와 한·영 개념 대응을 충분히 반영"
            status = "유지"
        payload.append(
            {
                "L1_ID": row["L1_ID"],
                "L3_ID": risk_id,
                "before_en": row["L3_Title_en"],
                "before_ko": row["L3_Title_ko"],
                "after_en": after_en,
                "after_ko": after_ko,
                "status": status,
                "rationale_ko": rationale,
                "source_document": SOURCE_DOCUMENT,
            }
        )
    return payload


def cell_name(en: str, ko: str) -> str:
    return f"{html.escape(en)}<br><span class=\"ko-name\">{html.escape(ko)}</span>"


def build_section(payload: list[dict[str, str]]) -> str:
    changed = sum(item["status"] == "개정 제안" for item in payload)
    retained = len(payload) - changed
    parts = [
        '<!-- L3_NAME_PROPOSALS_START -->',
        '<section class="l3-proposals" id="L3NAMES" aria-labelledby="l3-proposal-title">',
        '  <h2 id="l3-proposal-title">L3 리스크 명칭 정비 제안</h2>',
        '  <p class="lead">Before는 첨부된 최종 L3 목록의 현행 명칭이며, After는 정의 범위, 관찰 가능한 위해, 한·영 개념 대응을 기준으로 정비한 검토안입니다. 이 표는 현행 L3 마스터를 변경하지 않습니다.</p>',
        '  <div class="proposal-summary">',
        f'    <span class="proposal-pill">전체 {len(payload)}개</span>',
        f'    <span class="proposal-pill">개정 제안 {changed}개</span>',
        f'    <span class="proposal-pill">유지 {retained}개</span>',
        '  </div>',
    ]
    for domain_id in ("L1_G", "L1_A", "L1_P"):
        domain_en, domain_ko = DOMAIN_LABELS[domain_id]
        domain_rows = [item for item in payload if item["L1_ID"] == domain_id]
        parts.extend(
            [
                '  <section class="proposal-domain">',
                f'    <h3>{html.escape(domain_en)} <span class="ko-name">{html.escape(domain_ko)}</span> · {len(domain_rows)}개</h3>',
                '    <div class="proposal-table-wrap"><table class="proposal-table">',
                '      <thead><tr><th>ID</th><th>Before</th><th>After</th><th>판정</th><th>제안 근거</th></tr></thead>',
                '      <tbody>',
            ]
        )
        for item in domain_rows:
            status_class = "change" if item["status"] == "개정 제안" else "retain"
            parts.append(
                "      <tr>"
                f'<td class="pid">{html.escape(item["L3_ID"])}</td>'
                f'<td>{cell_name(item["before_en"], item["before_ko"])}</td>'
                f'<td>{cell_name(item["after_en"], item["after_ko"])}</td>'
                f'<td><span class="proposal-status proposal-status--{status_class}">{html.escape(item["status"])}</span></td>'
                f'<td class="reason">{html.escape(item["rationale_ko"])}</td>'
                "</tr>"
            )
        parts.extend(['      </tbody>', '    </table></div>', '  </section>'])
    parts.extend(
        [
            '  <p class="proposal-source">출처: 사용자가 제공한 <strong>AI2X-L3 최종 리스트 (2026-09-07)</strong>. '
            '<a href="data/glossary/l3_name_proposals_20260907.csv">Before/After 제안 데이터(CSV)</a> · '
            '<a href="data/glossary/l3_name_proposals_20260907.json">감사 데이터(JSON)</a></p>',
            '</section>',
            '<!-- L3_NAME_PROPOSALS_END -->',
        ]
    )
    return "\n".join(parts)


def replace_or_insert(text: str, section: str) -> str:
    start = "<!-- L3_NAME_PROPOSALS_START -->"
    end = "<!-- L3_NAME_PROPOSALS_END -->"
    if start in text and end in text:
        before, tail = text.split(start, 1)
        _, after = tail.split(end, 1)
        text = before + section + after
    else:
        text = text.replace('  <div id="list">', section + '\n  <div id="list">', 1)

    if ".l3-proposals{" not in text:
        text = text.replace("</style>", CSS + "\n</style>", 1)

    old_nav = '<div class="letterbar"><a href="#LA">A</a>'
    new_nav = '<div class="letterbar"><a href="#L3NAMES">L3 제안</a><a href="#LA">A</a>'
    if '#L3NAMES">L3 제안' not in text:
        text = text.replace(old_nav, new_nav, 1)
    return text


def main() -> None:
    rows = read_rows()
    payload = build_payload(rows)
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(
        json.dumps(
            {
                "source_document": SOURCE_DOCUMENT,
                "source_pdf": "AI2X-L3 최종 리스트-0 70926-062035.pdf",
                "master_changed": False,
                "method": "Conservative terminology proposal based on definition scope, observable harm, and Korean-English correspondence.",
                "items": payload,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    with AUDIT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(payload[0]))
        writer.writeheader()
        writer.writerows(payload)
    updated = replace_or_insert(GLOSSARY.read_text(encoding="utf-8"), build_section(payload))
    GLOSSARY.write_text(updated, encoding="utf-8")
    changed = sum(item["status"] == "개정 제안" for item in payload)
    print(f"L3_NAME_PROPOSALS_ADDED total={len(payload)} changed={changed} retained={len(payload)-changed}")


if __name__ == "__main__":
    main()
