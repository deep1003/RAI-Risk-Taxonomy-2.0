import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "v2.17.0"
TARGET = "v2.17.1"

MOVES = {
    "RAI4-0520": ("RAI3-P-SOC-02", "Direct EAI physical labor displacement mechanism."),
    "RAI4-0640": ("RAI3-P-INT-01", "Embodied AI systems designed or deployed for malicious physical harm."),
    "RAI4-0797": ("RAI3-P-INT-05", "Embodied AI misinformation grounded in physical perception and action."),
    "RAI4-1294": ("RAI3-P-INT-01", "Autonomous vehicles or drones used as weapons."),
    "RAI4-1410": ("RAI3-P-SYS-02", "Robot control failure through specification gaming in a physical task."),
    "RAI4-1549": ("RAI3-P-SYS-04", "AI failure in cyber-physical critical infrastructure."),
    "RAI4-1678": ("RAI3-P-INT-03", "Backdoor attack causing unsafe robotic manipulation."),
}


def load(path):
    return json.loads(path.read_text())


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def breadcrumb(node_id, nodes):
    by_id = {node["node_id"]: node for node in nodes}
    parts = []
    current = node_id
    while current:
        node = by_id[current]
        if node.get("level", 0) >= 1:
            parts.append(
                {
                    "node_id": node["node_id"],
                    "label_en": node.get("label_en"),
                    "label_ko": node.get("label_ko"),
                    "level": node.get("level"),
                }
            )
        current = node.get("parent_id")
    return list(reversed(parts))


def main():
    source_dir = ROOT / "public" / "data" / "releases" / SOURCE
    target_dir = ROOT / "public" / "data" / "releases" / TARGET
    if target_dir.exists():
        raise FileExistsError(target_dir)

    cards_payload = load(source_dir / "cards.json")
    hierarchy = load(source_dir / "hierarchy.json")
    manifest = load(source_dir / "manifest.json")
    changelog = load(source_dir / "revision_changelog.json")
    nodes = hierarchy["nodes"]
    node_by_id = {node["node_id"]: node for node in nodes}

    moved = []
    for card in cards_payload["cards"]:
        card["release_id"] = TARGET
        if card["l4_id"] not in MOVES:
            continue
        target_l3, rationale = MOVES[card["l4_id"]]
        if target_l3 not in node_by_id:
            raise KeyError(target_l3)
        old_primary = card["primary_l3_id"]
        old_hold_path = card.get("hold_semantic_path")
        if "HLD" not in old_primary:
            raise ValueError(f"expected HOLD card: {card['l4_id']} {old_primary}")
        card["primary_l3_id"] = target_l3
        card["breadcrumb"] = breadcrumb(target_l3, nodes)
        card["decision_required"] = False
        card["decision_reason"] = None
        card["assignment_status"] = "published_physical_minimal_transfer"
        card["review_status"] = "physical_transfer_pending_final_human_review"
        card["previous_primary_l3_id"] = old_primary
        card["previous_hold_semantic_path"] = old_hold_path
        card["hold_semantic_path"] = None
        card["hold_review_l2_id"] = None
        card["hold_review_l3_id"] = None
        card["physical_transfer_v2_17_1"] = {
            "from_release": SOURCE,
            "to_release": TARGET,
            "target_l3_id": target_l3,
            "target_l3_label_en": node_by_id[target_l3].get("label_en"),
            "rationale": rationale,
            "policy": "minimal conservative transfer from HOLD to existing Physical AI L3; protected 182 Physical source cards remain unchanged",
        }
        moved.append(
            {
                "l4_id": card["l4_id"],
                "label_en": card["label_en"],
                "from_primary_l3_id": old_primary,
                "from_hold_semantic_path": old_hold_path,
                "to_l3_id": target_l3,
                "to_l3_label_en": node_by_id[target_l3].get("label_en"),
                "rationale": rationale,
            }
        )

    cards = cards_payload["cards"]
    hierarchy["release_id"] = TARGET
    cards_payload["release_id"] = TARGET
    changelog["release_id"] = TARGET
    changelog["source_release"] = SOURCE
    changelog["minimal_physical_transfer_v2_17_1"] = moved

    by_path = {"HOLD-path": 0, "Agentic": 0, "General": 0, "Physical": 0}
    for card in cards:
        l3 = card["primary_l3_id"]
        if "HLD" in l3:
            by_path["HOLD-path"] += 1
        elif l3.startswith("RAI3-A"):
            by_path["Agentic"] += 1
        elif l3.startswith("RAI3-G"):
            by_path["General"] += 1
        elif l3.startswith("RAI3-P"):
            by_path["Physical"] += 1

    manifest.update(
        {
            "release_id": TARGET,
            "source_release": SOURCE,
            "status": "published_minimal_physical_transfer",
            "method": "minimal conservative transfer of directly embodied HOLD cards to existing Physical AI L3 nodes",
        }
    )
    manifest["counts"]["decision_required"] = sum(1 for card in cards if card.get("decision_required"))
    manifest["counts"]["minimal_physical_transfer_from_hold"] = len(moved)
    manifest["counts"]["by_path"] = by_path
    manifest["policy"] = (
        "Only HOLD cards with direct embodied, robotic, autonomous-vehicle, drone, "
        "cyber-physical, or physical-labor mechanisms were transferred. The protected "
        "182 Physical AI source cards remain unchanged."
    )

    write(target_dir / "cards.json", cards_payload)
    write(target_dir / "hierarchy.json", hierarchy)
    write(target_dir / "manifest.json", manifest)
    write(target_dir / "revision_changelog.json", changelog)

    out_dir = ROOT / "reports" / "validation" / TARGET / "minimal_physical_transfer"
    write(out_dir / "transfer_decisions.json", moved)
    write(
        out_dir / "summary.json",
        {
            "release_id": TARGET,
            "source_release": SOURCE,
            "moved": len(moved),
            "by_path": by_path,
            "decision_required": manifest["counts"]["decision_required"],
        },
    )
    print(json.dumps({"moved": moved, "by_path": by_path}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
