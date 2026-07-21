from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "public/data/releases/v2.9.0"
REPORT = ROOT / "reports/data_quality/anthropomorphism_agentic_em_v2.9.0"


class AnthropomorphismAgenticEmV29Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cards = json.loads((RELEASE / "cards.json").read_text())["cards"]
        cls.summary = json.loads((REPORT / "summary.json").read_text())
        cls.audit = json.loads((REPORT / "remapping_audit.json").read_text())

    def test_population_and_uniqueness_are_preserved(self) -> None:
        self.assertEqual(len(self.cards), 1711)
        self.assertEqual(len({card["l4_id"] for card in self.cards}), 1711)

    def test_em_converged_and_only_anthropomorphism_moved(self) -> None:
        self.assertTrue(self.summary["converged"])
        self.assertEqual(self.summary["trace"][-1]["changes"], 0)
        self.assertTrue(all(row["from_l3_id"] == "RAI3-G-INT-10" for row in self.audit))
        allowed = {"RAI3-A-SYS-07", "RAI3-A-SYS-08", "RAI3-A-SYS-09", "RAI3-A-SYS-10"}
        self.assertTrue(all(row["to_l3_id"] in allowed for row in self.audit))

    def test_physical_locks_and_review_markers_are_preserved(self) -> None:
        self.assertEqual(sum(card["assignment_status"] == "locked_physical" for card in self.cards), 182)
        self.assertTrue(all(row["decision_required"] for row in self.audit))


if __name__ == "__main__":
    unittest.main()
