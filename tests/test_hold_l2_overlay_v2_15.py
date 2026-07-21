import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/data/releases/v2.14.0"
RELEASE = ROOT / "public/data/releases/v2.15.0"
REPORT = ROOT / "reports/data_quality/hold_l2_overlay_v2.15.0"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class HoldL2OverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = load(SOURCE / "cards.json")["cards"]
        cls.cards = load(RELEASE / "cards.json")["cards"]
        cls.hierarchy = load(RELEASE / "hierarchy.json")
        cls.moves = load(REPORT / "hold_path_moves.json")

    def test_hold_population_is_complete(self):
        self.assertEqual(len(self.cards), 1711)
        self.assertEqual(len({card["l4_id"] for card in self.cards}), 1711)
        self.assertEqual(len(self.moves), 720)
        self.assertEqual(
            Counter(move["l1_id"] for move in self.moves),
            Counter({"RAI1-G": 626, "RAI1-A": 94}),
        )

    def test_hold_cards_use_domain_specific_review_paths(self):
        for card in self.cards:
            if not card["decision_required"]:
                continue
            expected = "RAI3-G-HLD-01" if card["hold_review_l2_id"] == "RAI2-G-HLD" else "RAI3-A-HLD-01"
            self.assertEqual(card["primary_l3_id"], expected)
            self.assertEqual(card["hold_review_l3_id"], expected)
            self.assertIn("l3_id", card["hold_semantic_path"])
            self.assertNotIn("HLD", card["hold_semantic_path"]["l3_id"])

    def test_non_hold_and_physical_content_is_preserved(self):
        before = {card["l4_id"]: card for card in self.source}
        for card in self.cards:
            source = before[card["l4_id"]]
            changed = {
                "release_id", "primary_l3_id", "breadcrumb", "hold_semantic_path",
                "hold_review_l2_id", "hold_review_l3_id",
            } if source["decision_required"] else {"release_id"}
            comparable = {key: value for key, value in card.items() if key not in changed}
            baseline = {key: value for key, value in source.items() if key not in changed}
            self.assertEqual(comparable, baseline, card["l4_id"])
        physical = [card for card in self.cards if card["primary_l3_id"].startswith("RAI3-P-")]
        self.assertEqual(len(physical), 182)
        self.assertTrue(all(not card["decision_required"] for card in physical))

    def test_hierarchy_has_four_l2_categories_and_two_hold_paths(self):
        categories = {row["category_id"] for row in self.hierarchy["canonical_l2_categories"]}
        self.assertEqual(categories, {"RAI2-INT", "RAI2-SYS", "RAI2-SOC", "RAI2-HLD"})
        nodes = {node["node_id"]: node for node in self.hierarchy["nodes"]}
        self.assertEqual(nodes["RAI2-G-HLD"]["parent_id"], "RAI1-G")
        self.assertEqual(nodes["RAI2-A-HLD"]["parent_id"], "RAI1-A")
        self.assertEqual(nodes["RAI3-G-HLD-01"]["l4_count"], 626)
        self.assertEqual(nodes["RAI3-A-HLD-01"]["l4_count"], 94)
        self.assertEqual(sum(node["level"] == 3 for node in nodes.values()), 52)

    def test_non_hold_validation_population_is_991(self):
        summary = load(ROOT / "reports/validation/v2.15.0/non_hold_reliability/reliability_summary.json")
        self.assertEqual(summary["population"]["assessed_non_hold_cards"], 991)
        self.assertEqual(summary["population"]["excluded_hold_cards"], 720)
        self.assertEqual(summary["population"]["semantic_l3_families"], 50)
        self.assertEqual(summary["population"]["empty_semantic_l3_families"], 0)


if __name__ == "__main__":
    unittest.main()
