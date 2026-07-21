import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/data/releases/v2.13.0"
RELEASE = ROOT / "public/data/releases/v2.14.0"
REPORT = ROOT / "reports/data_quality/agentic_l3_retirement_v2.14.0"
RETIRED = {
    "RAI3-A-SYS-07",
    "RAI3-A-SYS-08",
    "RAI3-A-SYS-09",
    "RAI3-A-SYS-10",
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class AgenticL3RetirementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_cards = load(SOURCE / "cards.json")["cards"]
        cls.cards = load(RELEASE / "cards.json")["cards"]
        cls.source_hierarchy = load(SOURCE / "hierarchy.json")
        cls.hierarchy = load(RELEASE / "hierarchy.json")
        cls.migrations = load(REPORT / "l4_migrations.json")
        cls.archive = load(REPORT / "retired_l3_nodes.json")

    def test_population_and_unique_ids(self):
        ids = [card["l4_id"] for card in self.cards]
        self.assertEqual(len(ids), 1711)
        self.assertEqual(len(ids), len(set(ids)))

    def test_retired_nodes_are_archived_not_active(self):
        active_l3 = {
            node["node_id"]
            for node in self.hierarchy["nodes"]
            if node["level"] == 3 and node["status"] == "active"
        }
        self.assertEqual(len(active_l3), 50)
        self.assertTrue(RETIRED.isdisjoint(active_l3))
        embedded_archive = self.hierarchy["retired_l3_archive"]
        self.assertEqual({node["node_id"] for node in embedded_archive}, RETIRED)
        self.assertEqual({node["node_id"] for node in self.archive}, RETIRED)
        self.assertTrue(all(node["id_reuse_prohibited"] for node in self.archive))

    def test_exactly_39_cards_migrated_and_all_are_hold(self):
        source_ids = {
            card["l4_id"]
            for card in self.source_cards
            if card["primary_l3_id"] in RETIRED
        }
        migration_ids = {row["l4_id"] for row in self.migrations}
        self.assertEqual(len(self.migrations), 39)
        self.assertEqual(migration_ids, source_ids)
        current = {card["l4_id"]: card for card in self.cards}
        for l4_id in migration_ids:
            card = current[l4_id]
            self.assertNotIn(card["primary_l3_id"], RETIRED)
            self.assertTrue(card["decision_required"])
            self.assertFalse(card["human_approved"])
            self.assertIsNotNone(card["retired_l3_migration"])

    def test_card_identity_evidence_and_metrics_are_preserved(self):
        source = {card["l4_id"]: card for card in self.source_cards}
        preserved = (
            "l4_id",
            "label_en",
            "label_ko",
            "definition_en",
            "definition_ko",
            "references",
            "severity_1to5",
            "probability_0to1",
            "impact_score",
            "metrics_source",
        )
        for card in self.cards:
            before = source[card["l4_id"]]
            for field in preserved:
                self.assertEqual(card.get(field), before.get(field), (card["l4_id"], field))

    def test_physical_lock_is_preserved(self):
        source = {
            card["l4_id"]: card
            for card in self.source_cards
            if card["primary_l3_id"].startswith("RAI3-P-")
        }
        current = {
            card["l4_id"]: card
            for card in self.cards
            if card["primary_l3_id"].startswith("RAI3-P-")
        }
        self.assertEqual(len(source), 182)
        self.assertEqual(set(current), set(source))
        for l4_id, card in current.items():
            comparable = {k: v for k, v in card.items() if k != "release_id"}
            baseline = {k: v for k, v in source[l4_id].items() if k != "release_id"}
            self.assertEqual(comparable, baseline, l4_id)

    def test_counts_and_active_family_coverage(self):
        domain_counts = Counter(card["primary_l3_id"].split("-")[1] for card in self.cards)
        self.assertEqual(domain_counts, Counter({"G": 1193, "A": 336, "P": 182}))
        self.assertEqual(sum(bool(card["decision_required"]) for card in self.cards), 720)
        family_counts = Counter(card["primary_l3_id"] for card in self.cards)
        active_l3 = [
            node for node in self.hierarchy["nodes"]
            if node["level"] == 3 and node["status"] == "active"
        ]
        self.assertTrue(all(family_counts[node["node_id"]] > 0 for node in active_l3))
        self.assertTrue(
            all(node["l4_count"] == family_counts[node["node_id"]] for node in active_l3)
        )


if __name__ == "__main__":
    unittest.main()
