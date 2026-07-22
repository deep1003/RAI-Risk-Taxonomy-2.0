#!/usr/bin/env python3
"""Counterfactual reliability simulation for candidate L3 expansion.

This script does not modify release data. It evaluates whether adding a small
set of candidate General and Agentic L3 families would improve embedding-based
assignment diagnostics under conservative reassignment gates.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.preprocessing import normalize


ROOT = Path(__file__).resolve().parents[1]
RELEASE = "v2.17.1"
EMB_DIR = ROOT / "reports/validation/v2.17.0/audit_bge"
OUT_DIR = ROOT / f"reports/validation/{RELEASE}/l3_expansion_simulation"
MODEL_PATH = "/Users/deep1003/.cache/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181"
SEED = 20260722


@dataclass(frozen=True)
class Candidate:
    node_id: str
    label_en: str
    label_ko: str
    definition_en: str
    definition_ko: str
    domain: str
    pattern: str


CANDIDATES = [
    Candidate(
        "SIM3-G-SOC-01",
        "Governance and Accountability",
        "거버넌스·책임성",
        "Risks arising when AI development, deployment, auditing, certification, reporting, regulation, liability, or accountability mechanisms fail to assign responsibility or support enforceable oversight.",
        "AI 개발·배포·감사·인증·보고·규제·책임 배분 체계가 작동하지 않아 책임성과 감독 가능성이 약화되는 위험.",
        "General",
        r"\b(govern|regulat|audit|accountab|liabil|law|policy|oversight|compliance|certification|reporting|standard|responsib)\b",
    ),
    Candidate(
        "SIM3-G-SYS-01",
        "Transparency and Explainability",
        "투명성·설명가능성",
        "Risks arising when AI system behavior, training data, evaluation, documentation, explanation, traceability, or contestability is opaque or unavailable to affected stakeholders.",
        "AI 시스템의 동작, 학습 데이터, 평가, 문서화, 설명, 추적성 또는 이의제기 가능성이 이해관계자에게 충분히 제공되지 않는 위험.",
        "General",
        r"\b(transparen|explain|interpret|opacity|opaque|disclos|documentation|model card|system card|traceab|contest|datasheet)\b",
    ),
    Candidate(
        "SIM3-G-SYS-02",
        "AI Security",
        "AI 보안",
        "Risks arising from attacks, vulnerabilities, jailbreaks, prompt injection, poisoning, backdoors, exfiltration, or compromise of non-embodied AI systems and their digital interfaces.",
        "비임베디드 AI 시스템과 디지털 인터페이스에서 공격, 취약점, 탈옥, 프롬프트 인젝션, 오염, 백도어, 유출 또는 침해가 발생하는 위험.",
        "General",
        r"\b(cyber|security|attack|poison|backdoor|jailbreak|prompt injection|exploit|credential|vulnerab|exfiltrat|compromise|malware)\b",
    ),
    Candidate(
        "SIM3-G-INT-01",
        "Dependency and Manipulation",
        "의존·조작",
        "Risks arising when AI systems create excessive dependence, manipulate preferences or behavior, exploit trust, or shape user choices without adequate autonomy or consent.",
        "AI 시스템이 과도한 의존을 만들거나 신뢰와 취약성을 이용해 선호·행동·선택을 조작하여 자율성과 동의를 약화시키는 위험.",
        "General",
        r"\b(dependen|manipulat|persuasi|addict|attachment|trust|overreliance|decept|parasocial|nudg|influence|vulnerab)\b",
    ),
    Candidate(
        "SIM3-A-SYS-01",
        "Tool and Environment Security",
        "도구·환경 보안",
        "Risks arising when autonomous agents misuse, compromise, or are compromised through tools, external environments, computer-use interfaces, APIs, or execution substrates.",
        "자율 에이전트가 도구, 외부 환경, 컴퓨터 사용 인터페이스, API 또는 실행 기반을 오용하거나 그 경로로 침해되는 위험.",
        "Agentic",
        r"\b(agent|agentic|autonomous|tool|api|environment|computer-use|computer use|execution|interface|orchestrat|actuator|browser)\b",
    ),
    Candidate(
        "SIM3-A-SYS-02",
        "Traceability and Audit",
        "추적성·감사",
        "Risks arising when autonomous agent actions, delegated decisions, tool calls, responsibility chains, audit trails, or human review points cannot be reconstructed or attributed.",
        "자율 에이전트의 행위, 위임된 의사결정, 도구 호출, 책임 경로, 감사 기록 또는 인간 검토 지점을 재구성하거나 귀속하기 어려운 위험.",
        "Agentic",
        r"\b(agent|agentic|autonomous|delegat|audit|traceab|attribut|provenance|responsib|tool call|action log|supervisor|oversight)\b",
    ),
]


def load_release() -> tuple[list[dict], list[dict]]:
    cards = json.loads((ROOT / f"public/data/releases/{RELEASE}/cards.json").read_text())["cards"]
    hierarchy = json.loads((ROOT / f"public/data/releases/{RELEASE}/hierarchy.json").read_text())
    nodes = [n for n in hierarchy["nodes"] if n.get("level") == 3 and "HLD" not in n["node_id"]]
    return cards, nodes


def card_text(card: dict) -> str:
    return f"{card.get('label_en','')}. {card.get('definition_en','')} / {card.get('label_ko','')}. {card.get('definition_ko','')}"


def seed_text(node: dict | Candidate) -> str:
    if isinstance(node, Candidate):
        return f"{node.label_en}. {node.definition_en} / {node.label_ko}. {node.definition_ko}"
    return f"{node.get('label_en','')}. {node.get('definition_en','')} / {node.get('label_ko','')}. {node.get('definition_ko','')}"


def current_l3(card: dict) -> str:
    primary = card.get("primary_l3_id") or ""
    if "HLD" in primary and card.get("hold_semantic_path"):
        return card["hold_semantic_path"]["l3_id"]
    return primary


def encode_candidate_seeds() -> np.ndarray:
    cache = OUT_DIR / "candidate_seed_embeddings.npy"
    if cache.exists():
        return np.load(cache)
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_PATH)
    try:
        model.max_seq_length = 256
    except Exception:
        pass
    vectors = model.encode(
        [seed_text(candidate) for candidate in CANDIDATES],
        normalize_embeddings=True,
        batch_size=16,
        show_progress_bar=False,
    ).astype("float32")
    np.save(cache, vectors)
    return vectors


def build_centroids(embeddings: np.ndarray, labels: np.ndarray, family_count: int, seeds: np.ndarray) -> np.ndarray:
    centroids = np.zeros((family_count, embeddings.shape[1]), dtype="float32")
    for family in range(family_count):
        members = embeddings[labels == family]
        if len(members):
            centroids[family] = members.mean(axis=0)
        else:
            centroids[family] = seeds[family]
    return normalize(centroids)


def metrics(embeddings: np.ndarray, labels: np.ndarray, seeds: np.ndarray, name: str) -> dict:
    family_count = seeds.shape[0]
    centroids = build_centroids(embeddings, labels, family_count, seeds)
    sims = embeddings @ centroids.T
    order = np.argsort(-sims, axis=1)
    pos = (order == labels[:, None]).argmax(axis=1)
    top1 = sims.argmax(axis=1)
    sorted_sims = np.sort(sims, axis=1)
    margins = sims[np.arange(len(labels)), labels] - np.where(top1 == labels, sorted_sims[:, -2], sorted_sims[:, -1])

    result = {
        "condition": name,
        "cards": int(len(labels)),
        "families": int(family_count),
        "top1_containment": round(float((pos < 1).mean()) * 100, 1),
        "top2_containment": round(float((pos < 2).mean()) * 100, 1),
        "top3_containment": round(float((pos < 3).mean()) * 100, 1),
        "top5_containment": round(float((pos < 5).mean()) * 100, 1),
        "median_margin": round(float(np.median(margins)), 4),
        "negative_margin_share": round(float((margins < 0).mean()) * 100, 1),
    }

    rng = np.random.default_rng(SEED)
    for sigma in (0.01, 0.05):
        agreement = []
        for _ in range(200):
            perturbed = embeddings + rng.normal(0, sigma, embeddings.shape).astype("float32")
            perturbed = normalize(perturbed)
            agreement.append(float(((perturbed @ centroids.T).argmax(axis=1) == top1).mean()))
        result[f"perturb_agreement_sigma_{sigma}"] = round(float(np.mean(agreement)) * 100, 1)

    z = (embeddings @ seeds.T).argmax(axis=1)
    for iteration in range(60):
        em_centroids = build_centroids(embeddings, z, family_count, seeds)
        z_next = (embeddings @ em_centroids.T).argmax(axis=1)
        objective = float((embeddings @ em_centroids.T).max(axis=1).mean())
        if np.array_equal(z, z_next):
            z = z_next
            break
        z = z_next
    result["em_iterations"] = int(iteration + 1)
    result["em_final_objective"] = round(objective, 3)
    result["em_agreement"] = round(float((z == labels).mean()) * 100, 1)
    result["ari"] = round(float(adjusted_rand_score(labels, z)), 3)
    result["nmi"] = round(float(normalized_mutual_info_score(labels, z)), 3)
    return result


def simulate_assignment(
    cards: list[dict],
    embeddings: np.ndarray,
    existing_seeds: np.ndarray,
    baseline_labels: np.ndarray,
    family_ids: list[str],
    candidate_vectors: np.ndarray,
    candidates: list[Candidate],
) -> tuple[np.ndarray, list[dict]]:
    all_seed_vectors = np.vstack([existing_seeds, candidate_vectors])
    existing_scores = embeddings @ existing_seeds.T
    candidate_scores = embeddings @ candidate_vectors.T
    assigned = baseline_labels.copy()
    moves: list[dict] = []
    family_idx = {family_id: i for i, family_id in enumerate(family_ids)}

    for i, card in enumerate(cards):
        primary = card.get("primary_l3_id") or ""
        if primary.startswith("RAI3-P-"):
            continue
        current_index = baseline_labels[i]
        current_score = existing_scores[i, current_index]
        text = f"{card.get('label_en','')} {card.get('definition_en','')} {card.get('decision_reason','')} {card.get('stage2_hold_reason','')}"
        card_domain = "Agentic" if current_l3(card).startswith("RAI3-A-") else "General"
        best: tuple[float, int, Candidate] | None = None
        for j, candidate in enumerate(candidates):
            if candidate.domain == "Agentic" and card_domain != "Agentic":
                continue
            if candidate.domain == "General" and card_domain == "Agentic" and not card.get("decision_required"):
                continue
            if not re.search(candidate.pattern, text, re.IGNORECASE):
                continue
            score = float(candidate_scores[i, j])
            improvement = score - float(current_score)
            if improvement < 0.012:
                continue
            if best is None or improvement > best[0]:
                best = (improvement, j, candidate)
        if best is not None:
            improvement, j, candidate = best
            assigned[i] = len(family_ids) + j
            moves.append(
                {
                    "l4_id": card["l4_id"],
                    "label_en": card.get("label_en", ""),
                    "from_l3_id": family_ids[current_index],
                    "to_l3_id": candidate.node_id,
                    "to_l3_label_en": candidate.label_en,
                    "decision_required": bool(card.get("decision_required")),
                    "current_similarity": round(float(current_score), 4),
                    "candidate_similarity": round(float(candidate_scores[i, j]), 4),
                    "improvement": round(float(improvement), 4),
                }
            )
    return assigned, moves


def plot_results(rows: list[dict]) -> None:
    labels = [row["label"] for row in rows]
    metrics_to_plot = [
        ("top1_containment", "Top-1 containment (%)"),
        ("top5_containment", "Top-5 containment (%)"),
        ("negative_margin_share", "Negative-margin share (%)"),
        ("perturb_agreement_sigma_0.05", "Perturbation agreement, sigma 0.05 (%)"),
    ]
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.2), dpi=220)
    colors = ["#7B8794", "#3167D5", "#159276"]
    for ax, (metric, title) in zip(axes.ravel(), metrics_to_plot):
        values = [row[metric] for row in rows]
        ax.bar(labels, values, color=colors, edgecolor="#2F3A4A", linewidth=0.4)
        ax.set_title(title, loc="left")
        ax.grid(axis="y", color="#E6E9EF", linewidth=0.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        for tick in ax.get_xticklabels():
            tick.set_rotation(18)
            tick.set_ha("right")
        for i, value in enumerate(values):
            ax.text(i, value, f"{value:.1f}", ha="center", va="bottom", fontsize=7)
    fig.suptitle("Counterfactual reliability under candidate L3 expansion", x=0.02, ha="left", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(OUT_DIR / "candidate_l3_expansion_simulation.pdf", bbox_inches="tight")
    fig.savefig(OUT_DIR / "candidate_l3_expansion_simulation.png", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cards, nodes = load_release()
    index = json.loads((EMB_DIR / "index.json").read_text())
    embeddings = np.load(EMB_DIR / "card_embeddings.npy").astype("float32")
    existing_seed_vectors = np.load(EMB_DIR / "l3_seed_embeddings.npy").astype("float32")
    l4_ids = index["l4_ids"]
    card_by_id = {card["l4_id"]: card for card in cards}
    ordered_cards = [card_by_id[l4_id] for l4_id in l4_ids]
    family_ids = [node["node_id"] for node in nodes]
    family_idx = {family_id: i for i, family_id in enumerate(family_ids)}
    baseline_labels = np.array([family_idx[current_l3(card)] for card in ordered_cards])
    is_hold = np.array([bool(card.get("decision_required")) for card in ordered_cards])

    candidate_seed_vectors = encode_candidate_seeds()
    general_candidates = CANDIDATES[:4]
    all_candidates = CANDIDATES

    conditions = []
    for label, candidates in [
        ("Current v2.17.1", []),
        ("General +4", general_candidates),
        ("General +4, Agentic +2", all_candidates),
    ]:
        if not candidates:
            assigned = baseline_labels
            moves = []
            seeds = existing_seed_vectors
        else:
            assigned, moves = simulate_assignment(
                ordered_cards,
                embeddings,
                existing_seed_vectors,
                baseline_labels,
                family_ids,
                candidate_seed_vectors[: len(candidates)],
                candidates,
            )
            seeds = np.vstack([existing_seed_vectors, candidate_seed_vectors[: len(candidates)]])
        all_metrics = metrics(embeddings, assigned, seeds, label + " all")
        nonhold_metrics = metrics(embeddings[~is_hold], assigned[~is_hold], seeds, label + " non-HOLD")
        conditions.append(
            {
                "label": label,
                "candidate_count": len(candidates),
                "moved_cards": len(moves),
                "moved_hold_cards": sum(1 for move in moves if move["decision_required"]),
                "moved_nonhold_cards": sum(1 for move in moves if not move["decision_required"]),
                "all": all_metrics,
                "non_hold": nonhold_metrics,
                "moves": moves,
            }
        )

    rows = []
    for condition in conditions:
        row = {"label": condition["label"]}
        row.update(condition["all"])
        row["moved_cards"] = condition["moved_cards"]
        rows.append(row)
    plot_results(rows)

    summary = {
        "release_id": RELEASE,
        "model": MODEL_PATH,
        "seed": SEED,
        "rule": "Counterfactual movement requires candidate keyword support and at least 0.012 BGE-M3 similarity improvement over the current L3 seed. Physical source cards are locked.",
        "conditions": [
            {k: v for k, v in condition.items() if k != "moves"} for condition in conditions
        ],
        "candidate_definitions": [candidate.__dict__ for candidate in CANDIDATES],
        "outputs": {
            "summary": str(OUT_DIR / "candidate_l3_expansion_summary.json"),
            "moves": str(OUT_DIR / "candidate_l3_expansion_moves.json"),
            "figure_pdf": str(OUT_DIR / "candidate_l3_expansion_simulation.pdf"),
            "figure_png": str(OUT_DIR / "candidate_l3_expansion_simulation.png"),
        },
    }
    (OUT_DIR / "candidate_l3_expansion_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    (OUT_DIR / "candidate_l3_expansion_moves.json").write_text(
        json.dumps({condition["label"]: condition["moves"] for condition in conditions}, ensure_ascii=False, indent=2)
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
