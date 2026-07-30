import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "public/data/releases/v2.18.0-rc"


class V218SynchronizationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cards = json.loads(
            (RELEASE / "cards.json").read_text(encoding="utf-8")
        )["cards"]
        cls.hierarchy = json.loads(
            (RELEASE / "hierarchy.json").read_text(encoding="utf-8")
        )
        cls.manifest = json.loads(
            (RELEASE / "manifest.json").read_text(encoding="utf-8")
        )

    def test_registry_and_review_counts(self):
        active = [card for card in self.cards if card.get("status") == "active"]
        retired = [card for card in self.cards if card.get("status") == "retired"]
        hold = [card for card in active if card.get("decision_required")]
        self.assertEqual(len(self.cards), 1711)
        self.assertEqual(len({card["l4_id"] for card in self.cards}), 1711)
        self.assertEqual(len(active), 1660)
        self.assertEqual(len(retired), 51)
        self.assertEqual(len(hold), 614)

    def test_semantic_hierarchy_counts(self):
        semantic_l3 = [
            node
            for node in self.hierarchy["nodes"]
            if node.get("level") == 3 and node.get("status") == "active"
        ]
        review_l3 = [
            node
            for node in self.hierarchy["nodes"]
            if node.get("level") == 3
            and node.get("status") == "active_review_path"
        ]
        counts = Counter(node["node_id"].split("-")[1] for node in semantic_l3)
        self.assertEqual(len(semantic_l3), 54)
        self.assertEqual(len(review_l3), 2)
        self.assertEqual(counts, {"G": 33, "A": 6, "P": 15})
        semantic_l2 = [
            row
            for row in self.hierarchy["canonical_l2_categories"]
            if not row.get("review_overlay")
        ]
        self.assertEqual(len(semantic_l2), 3)

    def test_card_paths_are_referentially_valid(self):
        node_ids = {node["node_id"] for node in self.hierarchy["nodes"]}
        for card in self.cards:
            self.assertIn(card["primary_l3_id"], node_ids)
            if card.get("status") != "active":
                continue
            breadcrumb = card.get("breadcrumb") or []
            self.assertEqual(breadcrumb[-1]["node_id"], card["primary_l3_id"])

    def test_space_and_network_match_release(self):
        space = json.loads(
            (RELEASE / "risk_space.json").read_text(encoding="utf-8")
        )
        network = json.loads(
            (RELEASE / "semantic_proximity_network.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(space["metadata"]["release_id"], "v2.18.0-rc")
        self.assertEqual(space["metadata"]["active_cards"], 1660)
        self.assertEqual(space["metadata"]["hold_cards"], 614)
        self.assertEqual(space["metadata"]["l3_count"], 54)
        self.assertEqual(len(space["points"]), 1660)
        self.assertEqual(network["metadata"]["release"], "v2.18.0-rc")
        self.assertEqual(network["metadata"]["cluster_count"], 54)
        self.assertEqual(len(network["nodes"]), 1660)

    def test_report_hierarchy_coverage_is_data_derived(self):
        report = (
            ROOT
            / "reports/latex/rai_risk_taxonomy_technical_report_2_0_en.tex"
        ).read_text(encoding="utf-8")
        nodes = {
            node["node_id"]: node for node in self.hierarchy["nodes"]
        }
        active = [
            card for card in self.cards if card.get("status") == "active"
        ]
        primary_domain = Counter(
            card["primary_l3_id"].split("-")[1] for card in active
        )
        semantic_l2 = Counter()
        semantic_l3 = Counter()
        for card in active:
            l3_id = card["primary_l3_id"]
            if "HLD" in l3_id:
                l3_id = card["hold_semantic_path"]["l3_id"]
            l3 = nodes[l3_id]
            l2 = nodes[l3["parent_id"]]
            semantic_l3[l3_id] += 1
            semantic_l2[l2["label_en"]] += 1
        self.assertEqual(primary_domain, {"G": 1221, "A": 281, "P": 158})
        self.assertEqual(
            semantic_l2,
            {
                "System Safety": 847,
                "Interaction Safety": 705,
                "Societal Impact": 108,
            },
        )
        self.assertEqual(max(semantic_l3.values()), 160)
        self.assertIn("Total & 705 & 847 & 108 & 1,660", report)
        self.assertIn("(160,Anthropomorphism)", report)

    def test_site_and_report_references_are_current(self):
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        site_js = (ROOT / "assets/site.js").read_text(encoding="utf-8")
        space_js = (ROOT / "assets/risk-space.js").read_text(encoding="utf-8")
        report = (
            ROOT
            / "reports/latex/rai_risk_taxonomy_technical_report_2_0_en.tex"
        ).read_text(encoding="utf-8")
        self.assertIn("v2.18.0-rc", index)
        self.assertIn("614 active HOLD", index)
        self.assertIn('public/data/releases/v2.18.0-rc', site_js)
        self.assertIn('public/data/releases/v2.18.0-rc', space_js)
        self.assertIn("release candidate v2.18.0-rc", report)
        self.assertIn("Current hierarchy coverage by L1 domain", report)
        self.assertIn("Top-1 containment & 71.9\\% & 81.6\\%", report)
        self.assertIn("General-purpose AI & 33 & 1,221 & 73.6\\%", report)

    def test_physical_master_sync(self):
        by_source = {
            card.get("physical_source_card_id"): card
            for card in self.cards
            if card.get("physical_source_card_id")
        }
        self.assertEqual(len(by_source), 182)
        self.assertEqual(
            by_source["PHYSBENCH-REF-0065"]["primary_l3_id"],
            "RAI3-P-SYS-02",
        )
        self.assertEqual(
            by_source["PHYSBENCH-REF-0107"]["primary_l3_id"],
            "RAI3-G-SOC-06",
        )
        self.assertTrue(
            by_source["PHYSBENCH-REF-0065"]["human_approved"]
        )
        self.assertEqual(
            self.manifest["physical_master_sync"]["cards_synced"],
            182,
        )


if __name__ == "__main__":
    unittest.main()
