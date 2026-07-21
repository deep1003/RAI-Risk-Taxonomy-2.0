from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SiteV2Tests(unittest.TestCase):
    def test_site_bundle_matches_review_hold_policy(self) -> None:
        bundle = ROOT / "public/data/releases/v2.0.0"
        cards = json.loads((bundle / "cards.json").read_text())["cards"]
        manifest = json.loads((bundle / "manifest.json").read_text())
        self.assertEqual(len(cards), 1726)
        self.assertEqual(sum(row["primary_l3_id"] is not None for row in cards), 1726)
        self.assertEqual(sum(row["decision_required"] for row in cards), 55)
        self.assertEqual(sum(row["assignment_status"] == "stage3_forced" for row in cards), 173)
        self.assertEqual(manifest["counts"]["l3_nodes"], 50)

    def test_hold_marked_cards_remain_inside_the_l3_tree(self) -> None:
        cards = json.loads(
            (ROOT / "public/data/releases/v2.0.0/cards.json").read_text()
        )["cards"]
        holds = [row for row in cards if row["decision_required"]]
        self.assertEqual(len(holds), 55)
        self.assertTrue(all(row["primary_l3_id"] for row in holds))
        self.assertTrue(all(row["operational_bucket_id"] is None for row in holds))


if __name__ == "__main__":
    unittest.main()
