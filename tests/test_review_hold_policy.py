from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReviewHoldPolicyTests(unittest.TestCase):
    def test_decision_required_cards_remain_in_l3_taxonomy(self) -> None:
        rows = json.loads((ROOT / "data/experiments/stage3-forced-policy-v2/placements.json").read_text())
        holds = [row for row in rows if row["decision_required"]]
        self.assertEqual(len(rows), 1726)
        self.assertEqual(len(holds), 55)
        self.assertEqual(sum(row["policy_l3_id"] is not None for row in rows), 1726)
        self.assertTrue(all(row["policy_l3_id"] for row in holds))
        self.assertTrue(all(not row["excluded_from_taxonomy_distribution"] for row in holds))
        self.assertTrue(all(row["operational_bucket_id"] is None for row in holds))
        self.assertTrue(all(not row["human_approved"] for row in holds))

    def test_only_hard_holds_receive_decision_marker(self) -> None:
        rows = json.loads((ROOT / "data/experiments/stage3-forced-policy-v2/placements.json").read_text())
        hard_reasons = {
            "PHYSICAL_OUTSIDE_LOCK", "FRONTIER_EXPERT_REJECTED",
            "FRONTIER_EXPERT_DISAGREEMENT", "MULTI_MECHANISM", "LOW_ABSOLUTE_FIT",
        }
        moved = {row["l4_id"] for row in rows if row["decision_required"]}
        expected = {
            row["l4_id"] for row in rows
            if row["forced_from_stage2_hold_reason"] in hard_reasons
        }
        self.assertEqual(moved, expected)
        self.assertEqual(sum(row["policy_status"] == "forced_match_stage3" for row in rows), 173)


if __name__ == "__main__":
    unittest.main()
