import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_ID = "v2.17.0"
OUT = ROOT / "reports" / "validation" / RELEASE_ID / "hold_reason_groups"
OUT.mkdir(parents=True, exist_ok=True)


def classify(card):
    reason = card.get("decision_reason")
    stage2 = card.get("stage2_hold_reason")
    mapping = card.get("mapping_review_method") or ""
    if not reason and card.get("hold_semantic_path"):
        return "Guarded BGE-M3 remap review"
    if isinstance(reason, str) and reason.startswith("TAXONOMY_GAP"):
        return "Taxonomy gap or missing L3 scope"
    if reason == "ANTHROPOMORPHISM_DIRECT_MECHANISM_NOT_ESTABLISHED":
        return "Anthropomorphism mechanism ambiguity"
    if reason == "OVERLOADED_L3_LOW_EVIDENCE_FIT":
        return "Overloaded L3 or weak evidence fit"
    if reason in {"EXPERT_REVIEW_NO_CONSENSUS", "FRONTIER_EXPERT_REJECTED", "FRONTIER_EXPERT_DISAGREEMENT"}:
        return "Expert disagreement or rejection"
    if reason == "RETIRED_SPARSE_AGENTIC_L3_FORCED_MIGRATION" or "retired_l3_forced_migration" in mapping:
        return "Retired sparse Agentic L3 migration"
    if reason == "CONSTRAINED_EM_REMAP_REQUIRES_HUMAN_REVIEW":
        return "Guarded BGE-M3 remap review"
    if reason == "PHYSICAL_OUTSIDE_LOCK" or stage2 == "PHYSICAL_OUTSIDE_LOCK":
        return "Physical AI lock-scope conflict"
    if reason in {"MULTI_MECHANISM", "LOW_ABSOLUTE_FIT", "CLOSEST_OPERATIONAL_FIT_HUMAN_OVERRIDE"}:
        return "Low-fit or multi-mechanism residual"
    if reason is None and stage2:
        return "Low-fit or multi-mechanism residual"
    return "Other residual review"


def gap_tags(card):
    reason = card.get("decision_reason")
    if not isinstance(reason, str):
        return []
    if not reason.startswith("TAXONOMY_GAP"):
        return []
    tail = reason.split(":", 1)[1] if ":" in reason else reason.replace("TAXONOMY_GAP_", "")
    return [tag for tag in tail.split(",") if tag]


cards = json.loads((ROOT / "public" / "data" / "releases" / RELEASE_ID / "cards.json").read_text())["cards"]
holds = [card for card in cards if card.get("decision_required")]
assert len(holds) == 734

group_counts = Counter(classify(card) for card in holds)
gap_counts = Counter(tag for card in holds for tag in gap_tags(card))

group_rows = [
    {
        "group": group,
        "count": count,
        "share_hold_percent": round(count / len(holds) * 100, 1),
        "share_all_l4_percent": round(count / len(cards) * 100, 1),
    }
    for group, count in group_counts.most_common()
]

gap_rows = [
    {
        "gap_tag": tag,
        "count": count,
        "share_taxonomy_gap_mentions_percent": round(count / sum(gap_counts.values()) * 100, 1),
    }
    for tag, count in gap_counts.most_common()
]

summary = {
    "release_id": RELEASE_ID,
    "l4_cards": len(cards),
    "hold_cards": len(holds),
    "hold_share_percent": round(len(holds) / len(cards) * 100, 1),
    "groups": group_rows,
    "taxonomy_gap_mentions": gap_rows,
}

(OUT / "hold_reason_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
with (OUT / "hold_reason_groups.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["group", "count", "share_hold_percent", "share_all_l4_percent"])
    writer.writeheader()
    writer.writerows(group_rows)
with (OUT / "hold_taxonomy_gap_mentions.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["gap_tag", "count", "share_taxonomy_gap_mentions_percent"])
    writer.writeheader()
    writer.writerows(gap_rows)

print(json.dumps(summary, ensure_ascii=False, indent=2))
