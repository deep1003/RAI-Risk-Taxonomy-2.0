from __future__ import annotations

import hashlib
import json
import sys
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data" / "releases" / "v1.0.0"
PUBLIC = ROOT / "public" / "data" / "releases" / "v1.0.0"
SOURCES = ROOT / "data" / "source_snapshots" / "v1.0.0"
sys.path.insert(0, str(ROOT / "src"))

from rai_taxonomy.codebook import PHYSICAL_ALIAS_TO_GLOBAL, PHYSICAL_LEGACY_TO_NEW  # noqa: E402


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class ReleaseSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.nodes = load(RELEASE / "taxonomy_nodes.json")
        cls.registry = load(RELEASE / "l4_registry.json")
        cls.crosswalk = load(RELEASE / "source_crosswalk.json")
        cls.locks = load(RELEASE / "physical_lock.json")
        cls.placements = load(RELEASE / "placements.json")
        cls.site_cards = load(PUBLIC / "cards.json")["cards"]
        cls.source_global = load(SOURCES / "global_ai_risk_l4_overlay_nodes.json")
        cls.source_physical = load(SOURCES / "physical_l4_cards.json")
        cls.source_physical_references = load(SOURCES / "physical_l4_references.json")

    def test_expected_grain(self) -> None:
        self.assertEqual(Counter(row["level"] for row in self.nodes), {0: 1, 1: 3, 2: 6, 3: 50})
        self.assertEqual(len(self.registry), 1726)
        self.assertEqual(len(self.placements), 1726)
        self.assertEqual(len(self.site_cards), 1726)

    def test_l4_ids_are_contiguous_and_unique(self) -> None:
        expected = [f"RAI4-{number:04d}" for number in range(1, 1727)]
        self.assertEqual([row["l4_id"] for row in self.registry], expected)
        self.assertEqual(len({row["l4_id"] for row in self.registry}), 1726)

    def test_crosswalk_counts(self) -> None:
        physical = [row for row in self.crosswalk if row["source_system"] == "physical_182"]
        self.assertEqual(len(self.crosswalk), 1908)
        self.assertEqual(
            Counter(row["relationship"] for row in physical),
            {"exact_id": 169, "explicit_alias": 13},
        )

    def test_crosswalk_matches_every_source_card(self) -> None:
        expected_global = {
            row["id"]: f"RAI4-{number:04d}"
            for number, row in enumerate(sorted(self.source_global, key=lambda item: item["id"]), start=1)
        }
        global_xw = {
            row["source_id"]: row
            for row in self.crosswalk
            if row["source_system"] == "global_1726"
        }
        self.assertEqual(set(global_xw), set(expected_global))
        for source_id, l4_id in expected_global.items():
            self.assertEqual(global_xw[source_id]["l4_id"], l4_id)
            self.assertEqual(global_xw[source_id]["canonical_source_id"], source_id)
        physical_xw = {
            row["source_id"]: row
            for row in self.crosswalk
            if row["source_system"] == "physical_182"
        }
        for card in self.source_physical:
            physical_id = card["card_id"]
            canonical_id = PHYSICAL_ALIAS_TO_GLOBAL.get(physical_id, physical_id)
            self.assertEqual(physical_xw[physical_id]["canonical_source_id"], canonical_id)
            self.assertEqual(physical_xw[physical_id]["l4_id"], expected_global[canonical_id])

    def test_physical_lock_is_preserved(self) -> None:
        placement_by_l4 = {row["l4_id"]: row for row in self.placements}
        self.assertEqual(len(self.locks), 182)
        self.assertEqual(Counter(row["legacy_l2_id"] for row in self.locks), {"P2": 91, "I2": 62, "S2": 29})
        for lock in self.locks:
            placement = placement_by_l4[lock["l4_id"]]
            self.assertEqual(placement["assignment_status"], "locked_physical")
            self.assertEqual(placement["primary_l3_id"], lock["new_l3_id"])

    def test_physical_chain_references_and_3h_are_preserved(self) -> None:
        expected_global = {
            row["id"]: f"RAI4-{number:04d}"
            for number, row in enumerate(sorted(self.source_global, key=lambda item: item["id"]), start=1)
        }
        lock_by_physical = {row["physical_card_id"]: row for row in self.locks}
        registry_by_l4 = {row["l4_id"]: row for row in self.registry}
        reference_counts = Counter(row["card_id"] for row in self.source_physical_references)
        for card in self.source_physical:
            physical_id = card["card_id"]
            canonical_id = PHYSICAL_ALIAS_TO_GLOBAL.get(physical_id, physical_id)
            l4_id = expected_global[canonical_id]
            lock = lock_by_physical[physical_id]
            self.assertEqual(lock["l4_id"], l4_id)
            self.assertEqual(lock["legacy_l2_id"], card["l2_id"])
            self.assertEqual(lock["legacy_l3_id"], card["l3_id"])
            self.assertEqual(lock["new_l3_id"], PHYSICAL_LEGACY_TO_NEW[card["l3_id"]])
            registry_card = registry_by_l4[l4_id]
            physical_refs = [
                row for row in registry_card["references"] if row["source_system"] == "physical_182"
            ]
            self.assertEqual(len(physical_refs), reference_counts[physical_id])
            self.assertEqual(registry_card["three_h_one_r_raw"], card["three_h_one_r"])
            self.assertEqual(
                len(registry_card["three_h_one_r"]),
                len([token for token in card["three_h_one_r"].split("|") if token.strip()]),
            )

    def test_open_set_contract(self) -> None:
        for row in self.placements:
            if row["assignment_status"] == "needs_taxonomy_decision":
                self.assertIsNone(row["primary_l3_id"])
                self.assertIsNotNone(row["decision_id"])
            else:
                self.assertIsNotNone(row["primary_l3_id"])
            self.assertFalse(row["legacy_hierarchy_used_as_feature"])

    def test_every_algorithm_proposal_has_frontier_consensus(self) -> None:
        for row in self.placements:
            if row["assignment_status"] != "algorithm_proposed":
                continue
            reviews = row.get("frontier_expert_reviews", [])
            self.assertEqual(len(reviews), 2)
            self.assertEqual({review["decision"] for review in reviews}, {"APPROVE"})
            self.assertTrue(all(review["hierarchy_blind"] for review in reviews))
            self.assertFalse(row["confidence_calibrated"])

    def test_pinned_algorithm_configuration(self) -> None:
        config = load(RELEASE / "algorithm_config.json")
        run = load(RELEASE / "algorithm_run.json")
        manifest = load(RELEASE / "manifest.json")
        expected_revision = "5617a9f61b028005a4858fdac845db406aefb181"
        self.assertEqual(config["model_revision"], expected_revision)
        self.assertEqual(run["model_revision"], expected_revision)
        self.assertEqual(manifest["algorithm"]["model_revision"], expected_revision)
        payload = json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        self.assertEqual(run["configuration_sha256"], digest)
        self.assertEqual(manifest["algorithm"]["configuration_sha256"], digest)

    def test_site_cards_are_exact_canonical_joins(self) -> None:
        registry_by_l4 = {row["l4_id"]: row for row in self.registry}
        placement_by_l4 = {row["l4_id"]: row for row in self.placements}
        self.assertEqual({row["l4_id"] for row in self.site_cards}, set(registry_by_l4))
        for site_card in self.site_cards:
            l4_id = site_card["l4_id"]
            self.assertTrue(all(site_card[key] == value for key, value in registry_by_l4[l4_id].items()))
            self.assertEqual(site_card["primary_l3_id"], placement_by_l4[l4_id]["primary_l3_id"])
            self.assertEqual(site_card["assignment_status"], placement_by_l4[l4_id]["assignment_status"])

    def test_static_html_explorer_targets_the_release_bundle(self) -> None:
        index_path = ROOT / "index.html"
        css_path = ROOT / "assets" / "site.css"
        js_path = ROOT / "assets" / "site.js"
        self.assertTrue(index_path.is_file())
        self.assertTrue(css_path.is_file())
        self.assertTrue(js_path.is_file())
        index = index_path.read_text(encoding="utf-8")
        script = js_path.read_text(encoding="utf-8")
        self.assertIn('href="assets/site.css"', index)
        self.assertIn('src="assets/site.js"', index)
        self.assertIn('const DATA_ROOT = "public/data/releases/v2.0.0"', script)
        self.assertNotIn("RAI4-1726", script)


if __name__ == "__main__":
    unittest.main()
