#!/usr/bin/env python3
"""Build v2.8.0 with four conservative Agentic L3 additions.

Every non-Physical card is evaluated on every pass.  A placement changes only
when an Agentic-specific necessary condition and a high-precision mechanism
rule are both satisfied.  Physical locks and clearly supported legacy paths
are preserved.  Re-evaluation stops at a fixed point.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "v2.7.0"
RELEASE_ID = "v2.8.0"
SOURCE = ROOT / "public/data/releases" / SOURCE_ID
OUT = ROOT / "public/data/releases" / RELEASE_ID
REPORT = ROOT / "reports/data_quality/agentic_l3_expansion_v2.8.0"

KOREAN_SOURCE = {
    "title": "L0 L1 L2 L3 3H 속성 정의 대응 방안",
    "type": "User-provided Korean taxonomy report",
    "source_system": "taxonomy_definition_source_ko",
}

REFS = {
    "NIST_GENAI": {
        "title": "Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile (NIST AI 600-1)",
        "url": "https://doi.org/10.6028/NIST.AI.600-1",
        "type": "standard",
    },
    "NIST_RMF": {
        "title": "Artificial Intelligence Risk Management Framework (AI RMF 1.0)",
        "url": "https://doi.org/10.6028/NIST.AI.100-1",
        "type": "standard",
    },
    "OWASP_LLM": {
        "title": "OWASP Top 10 for LLM Applications 2025",
        "url": "https://genai.owasp.org/llm-top-10/",
        "type": "industry taxonomy",
    },
    "OWASP_AGENTIC": {
        "title": "OWASP Top 10 for Agentic Applications 2026",
        "url": "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/",
        "type": "industry taxonomy",
    },
    "OWASP_NAV": {
        "title": "OWASP Agentic Threats Navigator",
        "url": "https://genai.owasp.org/resource/owasp-gen-ai-security-project-agentic-threats-navigator/",
        "type": "industry taxonomy",
    },
    "NIST_AGENT": {
        "title": "CAISI Request for Information About Securing AI Agent Systems",
        "url": "https://www.nist.gov/news-events/news/2026/01/caisi-issues-request-information-about-securing-ai-agent-systems",
        "type": "government guidance",
    },
    "PHYSICAL": {
        "title": "Physical AI Risk Taxonomy",
        "url": "https://deep1003.github.io/Physical-AI-Risk-Taxonomy/",
        "type": "source taxonomy",
    },
}

NEW_NODES = [
    {
        "node_id": "RAI3-A-SYS-07", "level": 3, "parent_id": "RAI2-A-SYS", "sequence": 7,
        "label_en": "Goal & Planning", "label_ko": "목표·계획",
        "definition_en": "Risk that an autonomous agent's persistent objective, subgoals, or multi-step plan drifts, expands, is hijacked, or is optimized against a proxy so that subsequent actions depart from the authorized user intent or safety constraints.",
        "definition_ko": "자율 에이전트가 여러 단계에 걸쳐 목표·하위목표·계획을 유지·수정·실행하는 과정에서 목표가 표류·확장·탈취되거나 대리목표가 잘못 최적화되어 후속 행동이 승인된 사용자 의도나 안전 제약에서 이탈하는 위험.",
        "status": "active", "introduced_in": RELEASE_ID,
        "references": [REFS["OWASP_AGENTIC"], REFS["NIST_AGENT"]],
    },
    {
        "node_id": "RAI3-A-SYS-08", "level": 3, "parent_id": "RAI2-A-SYS", "sequence": 8,
        "label_en": "Tool Calling", "label_ko": "도구 호출",
        "definition_en": "Risk that an agent selects, parameterizes, chains, or repeatedly invokes an API, browser, code executor, MCP service, plug-in, operating-system interface, or other external tool in a way that causes an unintended consequential state change or side effect.",
        "definition_ko": "에이전트가 API·브라우저·코드 실행기·MCP 서비스·플러그인·운영체제 인터페이스 등의 외부 도구를 잘못 선택·매개변수화·연쇄·반복 호출하여 의도하지 않은 실질적 상태 변화나 부작용을 발생시키는 위험.",
        "status": "active", "introduced_in": RELEASE_ID,
        "references": [REFS["OWASP_AGENTIC"], REFS["OWASP_NAV"]],
    },
    {
        "node_id": "RAI3-A-SYS-09", "level": 3, "parent_id": "RAI2-A-SYS", "sequence": 9,
        "label_en": "Memory", "label_ko": "메모리",
        "definition_en": "Risk that memory or state written and reused across agent steps, tasks, sessions, or users is poisoned, mixed, stale, or improperly shared, thereby persistently distorting later retrieval, planning, or autonomous action.",
        "definition_ko": "에이전트가 단계·작업·세션·사용자 경계를 넘어 기록하고 재사용하는 메모리 또는 상태가 오염·혼입·노후화·부적절하게 공유되어 이후 검색·계획·자율 행동을 지속적으로 왜곡하는 위험.",
        "status": "active", "introduced_in": RELEASE_ID,
        "references": [REFS["OWASP_AGENTIC"], REFS["OWASP_NAV"]],
    },
    {
        "node_id": "RAI3-A-SYS-10", "level": 3, "parent_id": "RAI2-A-SYS", "sequence": 10,
        "label_en": "Oversight & Control", "label_ko": "감독·통제",
        "definition_en": "Risk that, after an autonomous execution loop begins, a human or policy-enforcement mechanism cannot adequately observe, approve, constrain, interrupt, correct, roll back, or return the agent to a safe state.",
        "definition_ko": "자율 실행 루프가 시작된 뒤 인간 또는 정책 집행 장치가 에이전트의 행동을 충분히 관찰·승인·제한·중단·수정·롤백하거나 안전 상태로 복귀시키지 못하는 위험.",
        "status": "active", "introduced_in": RELEASE_ID,
        "references": [REFS["OWASP_NAV"], REFS["NIST_AGENT"]],
    },
]

# A match requires one decisive mechanism and the category-specific gate.
RULES = {
    "RAI3-A-SYS-07": {
        "decisive": [
            r"\breward hack", r"\breward tamper", r"\bgoal (?:drift|expansion|hijack)",
            r"\bplan(?:ning| )?(?:/ reasoning-chain |chain )?hijack", r"unsafe exploration",
            r"long[- ]horizon planning", r"goal pursuit", r"objective gaming",
        ],
        "gate": [r"\bagent", r"\bautonom", r"multi[- ]step", r"sequential plan", r"future action"],
        "exclude": [r"reward model(?:ing)? (?:is|may|can|using)", r"benchmark only", r"single response"],
    },
    "RAI3-A-SYS-08": {
        "decisive": [
            r"tool[- ](?:use|calling|call|chain|invocation|execution|using)", r"unsafe tool",
            r"tool misuse", r"real[- ]tool", r"computer[- ]use agent", r"OS-level harmful",
            r"cross[- ]application data exfiltration", r"external tool", r"MCP (?:service|server|tool)",
            r"agent interfaces? to (?:browsers?|operating systems?|mobile apps?|IoT|external APIs?)",
        ],
        "gate": [r"\bagent", r"agentic system", r"subsequent calls", r"external action", r"tool execution"],
        "exclude": [
            r"benchmark overstates", r"emulated environment", r"merely describes",
            r"cascading failure", r"materially assist.*illegal", r"incorrectly classifies user intent",
            r"pose many novel", r"primary mechanism is propagation",
        ],
    },
    "RAI3-A-SYS-09": {
        "decisive": [
            r"agent memory (?:poison|contamin|corrupt)", r"persistent memory", r"memory poisoning",
            r"shared memory poison", r"cross[- ]session memory", r"stored memory.*future",
        ],
        "gate": [r"future decision", r"later retrieval", r"later.*action", r"persistent", r"stored memory"],
        "exclude": [r"working memory capacity", r"memory and storage hardware", r"one[- ]time retrieval"],
    },
    "RAI3-A-SYS-10": {
        "decisive": [
            r"absent supervisor", r"unsafe interrupt", r"autonomy escalation", r"unsupervised autonomous",
            r"shutdown resistance", r"corrigibility failure", r"loss of corrigibility",
            r"human[- ]override pathway failure", r"cannot.*(?:pause|interrupt|shut.?down|roll.?back)",
        ],
        "gate": [r"\bagent", r"\bautonom", r"autonomous execution", r"operation"],
        "exclude": [
            r"automation bias", r"anthropomorph", r"general organizational oversight",
            r"bad behavior of utility-maximizing", r"human-override pathway failure occurs when an affected user",
        ],
    },
}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def has(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text, re.I) for pattern in patterns)


def classify(text: str) -> tuple[str | None, dict[str, dict]]:
    evidence = {}
    for node_id, rule in RULES.items():
        decisive = [p for p in rule["decisive"] if re.search(p, text, re.I)]
        gates = [p for p in rule["gate"] if re.search(p, text, re.I)]
        excluded = [p for p in rule["exclude"] if re.search(p, text, re.I)]
        score = 4 * len(decisive) + 2 * len(gates) - 5 * len(excluded)
        evidence[node_id] = {
            "score": score, "decisive_hits": decisive,
            "gate_hits": gates, "exclusion_hits": excluded,
            "eligible": bool(decisive and gates and not excluded and score >= 6),
        }
    eligible = [(v["score"], k) for k, v in evidence.items() if v["eligible"]]
    eligible.sort(reverse=True)
    if not eligible:
        return None, evidence
    if len(eligible) > 1 and eligible[0][0] - eligible[1][0] < 2:
        return None, evidence
    return eligible[0][1], evidence


def breadcrumb(node_id: str, nodes: dict[str, dict]) -> list[dict]:
    result = []
    while node_id:
        node = nodes[node_id]
        result.append({"node_id": node_id, "label_en": node["label_en"], "label_ko": node["label_ko"]})
        node_id = node.get("parent_id")
    return list(reversed(result))


def references_for(node: dict) -> list[dict]:
    own = [dict(item) for item in node.get("references", [])]
    internal = dict(KOREAN_SOURCE)
    internal["url"] = "reports/sources/l3_definition_source_ko.txt"
    if node["node_id"].startswith("RAI3-P-"):
        external = REFS["PHYSICAL"]
    elif node["node_id"].startswith("RAI3-A-"):
        external = REFS["OWASP_AGENTIC"]
    elif node["node_id"] == "RAI3-G-INT-11":
        external = REFS["OWASP_LLM"]
    elif node["node_id"].startswith("RAI3-G-"):
        external = REFS["NIST_GENAI"]
    else:
        external = REFS["NIST_RMF"]
    keyed = {(r.get("url"), r.get("title")): r for r in [internal, external, *own]}
    return list(keyed.values())


def main() -> None:
    payload = read(SOURCE / "cards.json")
    cards = payload["cards"]
    hierarchy = read(SOURCE / "hierarchy.json")
    original_physical = {
        c["l4_id"]: json.dumps(c, ensure_ascii=False, sort_keys=True)
        for c in cards if c["assignment_status"] == "locked_physical"
    }

    existing_ids = {n["node_id"] for n in hierarchy["nodes"]}
    hierarchy["nodes"].extend(n for n in NEW_NODES if n["node_id"] not in existing_ids)
    nodes = {n["node_id"]: n for n in hierarchy["nodes"]}
    for node in hierarchy["nodes"]:
        if node["level"] == 3:
            if not node.get("definition_en") or not node.get("definition_ko"):
                raise ValueError(f"Missing bilingual definition: {node['node_id']}")
            node["references"] = references_for(node)

    audits = []
    seen_states = set()
    iteration_counts = []
    for iteration in range(1, 11):
        state = tuple((c["l4_id"], c["primary_l3_id"]) for c in cards)
        if state in seen_states:
            break
        seen_states.add(state)
        changed = 0
        for card in cards:
            card["release_id"] = RELEASE_ID
            if card["assignment_status"] == "locked_physical":
                continue
            text = " ".join((card.get("label_en", ""), card.get("definition_en", "")))
            proposal, evidence = classify(text)
            old = card["primary_l3_id"]
            if proposal and proposal != old:
                card["primary_l3_id"] = proposal
                card["breadcrumb"] = breadcrumb(proposal, nodes)
                card["mapping_review_method"] = "agentic_necessity_high_precision_fixed_point_v2.8"
                card["assignment_status"] = "algorithmically_remapped"
                card["review_status"] = "algorithmically_remapped_high_precision"
                card["decision_required"] = False
                card["decision_reason"] = None
                audits.append({
                    "iteration": iteration, "l4_id": card["l4_id"], "label_en": card["label_en"],
                    "from_l3_id": old, "to_l3_id": proposal,
                    "score": evidence[proposal]["score"],
                    "decisive_hits": evidence[proposal]["decisive_hits"],
                    "gate_hits": evidence[proposal]["gate_hits"],
                })
                changed += 1
            card["v2_8_candidate_scores"] = {k: v["score"] for k, v in evidence.items()}
        iteration_counts.append({"iteration": iteration, "changes": changed})
        if changed == 0:
            break

    if not iteration_counts or iteration_counts[-1]["changes"] != 0:
        raise RuntimeError("Classification did not reach a fixed point")

    physical_after = {
        c["l4_id"]: json.dumps({**c, "release_id": SOURCE_ID}, ensure_ascii=False, sort_keys=True)
        for c in cards if c["assignment_status"] == "locked_physical"
    }
    if original_physical != physical_after:
        raise AssertionError("Physical lock changed beyond release_id")

    counts = Counter(c["primary_l3_id"] for c in cards)
    for node in hierarchy["nodes"]:
        if node["level"] == 3:
            node["l4_count"] = counts[node["node_id"]]
    hierarchy["release_id"] = RELEASE_ID
    payload["release_id"] = RELEASE_ID

    OUT.mkdir(parents=True, exist_ok=True)
    write(OUT / "cards.json", payload)
    write(OUT / "hierarchy.json", hierarchy)
    REPORT.mkdir(parents=True, exist_ok=True)
    write(REPORT / "remapping_audit.json", audits)
    write(REPORT / "iteration_summary.json", iteration_counts)
    with (REPORT / "remapping_audit.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = ["iteration", "l4_id", "label_en", "from_l3_id", "to_l3_id", "score", "decisive_hits", "gate_hits"]
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in audits:
            writer.writerow({**row, "decisive_hits": " | ".join(row["decisive_hits"]), "gate_hits": " | ".join(row["gate_hits"])})

    summary = {
        "release_id": RELEASE_ID,
        "source_release": SOURCE_ID,
        "cards_total": len(cards),
        "nonphysical_evaluated_each_iteration": sum(c["assignment_status"] != "locked_physical" for c in cards),
        "physical_locked": len(original_physical),
        "l3_total": sum(n["level"] == 3 for n in hierarchy["nodes"]),
        "l3_with_bilingual_definitions": sum(bool(n["level"] == 3 and n.get("definition_en") and n.get("definition_ko")) for n in hierarchy["nodes"]),
        "l3_with_references": sum(bool(n["level"] == 3 and n.get("references")) for n in hierarchy["nodes"]),
        "new_l3_counts": {n["node_id"]: counts[n["node_id"]] for n in NEW_NODES},
        "remapped_total": len(audits),
        "iterations": iteration_counts,
        "converged": iteration_counts[-1]["changes"] == 0,
        "policy": "All non-Physical cards evaluated; move only on Agentic-specific decisive mechanism plus necessity gate; preserve Physical locks and unmatched existing placements.",
    }
    write(REPORT / "summary.json", summary)

    source_copy = ROOT / "reports/sources/l3_definition_source_ko.txt"
    attachment = Path("/Users/deep1003/.codex/attachments/1b509e3b-f0b8-44d3-916a-99f9483ea1e5/pasted-text.txt")
    source_copy.parent.mkdir(parents=True, exist_ok=True)
    source_text = attachment.read_text(encoding="utf-8")
    source_copy.write_text(
        "\n".join(line.rstrip() for line in source_text.splitlines()) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "release_id": RELEASE_ID,
        "source_release": SOURCE_ID,
        "status": "generated_unpublished",
        "counts": {
            "l4": len(cards),
            "classified": sum(bool(card.get("primary_l3_id")) for card in cards),
            "physical_locked": len(original_physical),
            "decision_required": sum(bool(card.get("decision_required")) for card in cards),
            "l1_nodes": sum(node["level"] == 1 for node in hierarchy["nodes"]),
            "l2_categories": len(hierarchy.get("canonical_l2_categories", [])),
            "l2_path_nodes": sum(node["level"] == 2 for node in hierarchy["nodes"]),
            "l3_nodes": sum(node["level"] == 3 for node in hierarchy["nodes"]),
        },
        "summary": summary,
        "files": [
            {"path": "cards.json", "sha256": sha256(OUT / "cards.json")},
            {"path": "hierarchy.json", "sha256": sha256(OUT / "hierarchy.json")},
            {"path": "reports/data_quality/agentic_l3_expansion_v2.8.0/summary.json", "sha256": sha256(REPORT / "summary.json")},
        ],
    }
    write(OUT / "manifest.json", manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
