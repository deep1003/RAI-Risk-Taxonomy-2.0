from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/data/releases/v2.11.0"
RELEASE = ROOT / "public/data/releases/v2.12.0"
REPORT = ROOT / "reports/data_quality/anthropomorphism_all_l3_em_v2.12.0"


class AnthropomorphismAllL3EmV212Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.before = json.loads((SOURCE / "cards.json").read_text())["cards"]
        cls.after = json.loads((RELEASE / "cards.json").read_text())["cards"]
        cls.summary = json.loads((REPORT / "summary.json").read_text())
        cls.audit = json.loads((REPORT / "remapping_audit.json").read_text())

    def test_population_and_unique_ids(self) -> None:
        self.assertEqual(len(self.after), 1711)
        self.assertEqual(len({card["l4_id"] for card in self.after}), 1711)

    def test_convergence_and_source_scope(self) -> None:
        self.assertTrue(self.summary["converged"])
        self.assertEqual(self.summary["trace"][-1]["changes"], 0)
        self.assertTrue(all(row["from_l3_id"] == "RAI3-G-INT-10" for row in self.audit))
        self.assertTrue(all(not row["to_l3_id"].startswith("RAI3-P-") for row in self.audit))

    def test_only_audited_paths_change(self) -> None:
        before = {card["l4_id"]: card for card in self.before}
        changed = {card["l4_id"] for card in self.after if card["primary_l3_id"] != before[card["l4_id"]]["primary_l3_id"]}
        self.assertEqual(changed, {row["l4_id"] for row in self.audit})

    def test_physical_lock_and_reference_preservation(self) -> None:
        before = {card["l4_id"]: card for card in self.before}
        physical = [card for card in self.after if card["assignment_status"] == "locked_physical"]
        self.assertEqual(len(physical), 182)
        self.assertTrue(all(card["primary_l3_id"] == before[card["l4_id"]]["primary_l3_id"] for card in physical))
        self.assertTrue(all(card["references"] == before[card["l4_id"]]["references"] for card in self.after))

    def test_all_remaps_are_marked_for_review(self) -> None:
        self.assertEqual(len(self.audit), 8)
        self.assertTrue(all(row["decision_required"] for row in self.audit))


if __name__ == "__main__":
    unittest.main()
