from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class ClassificationStageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage2 = load(ROOT / "data/experiments/stage2-v1/stage2_placements.json")
        cls.stage3 = load(ROOT / "data/experiments/stage3-v1/stage3_placements.json")
        cls.scores = {
            row["l4_id"]: row
            for row in load(ROOT / "data/releases/v1.0.0/algorithm_scores.json")
        }

    def test_stage2_preserves_protected_sets_and_leaves_ten_percent(self) -> None:
        counts = Counter(row["stage2_status"] for row in self.stage2)
        self.assertEqual(len(self.stage2), 1726)
        self.assertEqual(len({row["l4_id"] for row in self.stage2}), 1726)
        self.assertEqual(counts["locked_physical"], 182)
        self.assertEqual(counts["stage1_algorithm_proposed"], 37)
        self.assertEqual(counts["algorithm_proposed_stage2"], 1334)
        self.assertEqual(counts["needs_taxonomy_decision"], 173)
        self.assertAlmostEqual(counts["needs_taxonomy_decision"] / 1726, 0.10, delta=0.001)
        self.assertFalse(any(row["human_approved"] for row in self.stage2))

    def test_stage3_force_matches_only_stage2_holds_to_recorded_top1(self) -> None:
        stage2_by_l4 = {row["l4_id"]: row for row in self.stage2}
        forced = [row for row in self.stage3 if row["forced_match"]]
        self.assertEqual(len(self.stage3), 1726)
        self.assertTrue(all(row["stage3_l3_id"] for row in self.stage3))
        self.assertEqual(len(forced), 173)
        for row in self.stage3:
            before = stage2_by_l4[row["l4_id"]]
            if row["forced_match"]:
                self.assertEqual(before["stage2_status"], "needs_taxonomy_decision")
                self.assertEqual(row["stage3_l3_id"], self.scores[row["l4_id"]]["top1_l3_id"])
                self.assertEqual(row["forced_from_stage2_hold_reason"], before["stage2_hold_reason"])
            else:
                self.assertEqual(row["stage3_l3_id"], before["stage2_l3_id"])
        self.assertFalse(any(row["human_approved"] for row in self.stage3))


if __name__ == "__main__":
    unittest.main()
