from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V26 = ROOT / "public/data/releases/v2.6.0"
V27 = ROOT / "public/data/releases/v2.7.0"
BANNED = (
    "This L4 risk card treats",
    "under the broader L1 domain",
    "It should be interpreted as a specific risk mechanism",
    "The definition is anchored to the listed evidence source",
)


class SiteV27Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.before = json.loads((V26 / "cards.json").read_text())["cards"]
        cls.after = json.loads((V27 / "cards.json").read_text())["cards"]
        cls.by_id = {row["l4_id"]: row for row in cls.after}

    def test_population_and_complete_operational_assignment(self) -> None:
        self.assertEqual(len(self.after), 1711)
        self.assertEqual(len({row["l4_id"] for row in self.after}), 1711)
        self.assertTrue(all(row["primary_l3_id"] for row in self.after))

    def test_physical_lock_is_unchanged_except_release_id(self) -> None:
        before = {
            row["l4_id"]: {**row, "release_id": "v2.7.0"}
            for row in self.before if row["assignment_status"] == "locked_physical"
        }
        after = {
            row["l4_id"]: row
            for row in self.after if row["assignment_status"] == "locked_physical"
        }
        self.assertEqual(len(after), 182)
        self.assertEqual(before, after)

    def test_no_legacy_taxonomy_scaffold_in_nonphysical_definitions(self) -> None:
        nonphysical = [row for row in self.after if row["assignment_status"] != "locked_physical"]
        self.assertEqual(len(nonphysical), 1529)
        for row in nonphysical:
            self.assertTrue(row["definition_en"].strip())
            self.assertFalse(any(phrase in row["definition_en"] for phrase in BANNED), row["l4_id"])

    def test_confirmed_mapping_corrections(self) -> None:
        expected = {
            "RAI4-0109": "RAI3-G-SYS-09",
            "RAI4-0116": "RAI3-G-SYS-09",
            "RAI4-0709": "RAI3-G-INT-04",
            "RAI4-1002": "RAI3-G-INT-04",
            "RAI4-1073": "RAI3-G-INT-06",
            "RAI4-1221": "RAI3-G-INT-04",
            "RAI4-1302": "RAI3-G-SYS-08",
            "RAI4-1431": "RAI3-G-SYS-08",
            "RAI4-1581": "RAI3-G-SYS-03",
        }
        for l4_id, l3_id in expected.items():
            self.assertEqual(self.by_id[l4_id]["primary_l3_id"], l3_id)
        self.assertNotEqual(self.by_id["RAI4-1431"]["label_en"], "Goal misalignment")

    def test_taxonomy_gap_cards_are_marked_hold(self) -> None:
        scores = {
            row["l4_id"]: row
            for row in json.loads((ROOT / "data/releases/v1.0.0/algorithm_scores.json").read_text())
        }
        for row in self.after:
            if row["assignment_status"] == "locked_physical":
                continue
            if scores.get(row["l4_id"], {}).get("gap_sentinels"):
                self.assertTrue(row["decision_required"], row["l4_id"])

    def test_unsupported_anthropomorphism_assignments_are_hold(self) -> None:
        scores = {
            row["l4_id"]: row
            for row in json.loads((ROOT / "data/releases/v1.0.0/algorithm_scores.json").read_text())
        }
        for row in self.after:
            if row["primary_l3_id"] != "RAI3-G-INT-10":
                continue
            eligible = scores.get(row["l4_id"], {}).get("eligible_l3_ids", [])
            if "RAI3-G-INT-10" not in eligible:
                self.assertTrue(row["decision_required"], row["l4_id"])

    def test_compute_governance_definition_and_evidence_are_specific(self) -> None:
        card = self.by_id["RAI4-0109"]
        self.assertNotIn("Anthropomorphism", card["definition_en"])
        self.assertTrue(card["decision_required"])
        self.assertEqual(card["references"][0]["url"], "https://arxiv.org/abs/2402.08797")

    def test_default_card_order_starts_with_general_purpose_ai(self) -> None:
        script = (ROOT / "assets/site.js").read_text()
        self.assertIn('"RAI1-G": 0', script)
        self.assertIn('"RAI1-A": 1', script)
        self.assertIn('"RAI1-P": 2', script)
        self.assertIn("}).sort(compareCardsByDomain);", script)


if __name__ == "__main__":
    unittest.main()
