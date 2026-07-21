from __future__ import annotations

import json
import re
import unittest
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SiteV2Tests(unittest.TestCase):
    def test_site_bundle_matches_review_hold_policy(self) -> None:
        bundle = ROOT / "public/data/releases/v2.2.0"
        cards = json.loads((bundle / "cards.json").read_text())["cards"]
        manifest = json.loads((bundle / "manifest.json").read_text())
        self.assertEqual(len(cards), 1725)
        self.assertEqual(sum(row["primary_l3_id"] is not None for row in cards), 1725)
        self.assertEqual(sum(row["decision_required"] for row in cards), 83)
        self.assertEqual(sum(row["assignment_status"] == "stage3_forced" for row in cards), 173)
        self.assertEqual(manifest["counts"]["l3_nodes"], 50)

    def test_hold_marked_cards_remain_inside_the_l3_tree(self) -> None:
        cards = json.loads(
            (ROOT / "public/data/releases/v2.2.0/cards.json").read_text()
        )["cards"]
        holds = [row for row in cards if row["decision_required"]]
        self.assertEqual(len(holds), 83)
        self.assertTrue(all(row["primary_l3_id"] for row in holds))
        self.assertTrue(all(row["operational_bucket_id"] is None for row in holds))

    def test_physical_cards_and_duplicate_crosswalk_are_preserved(self) -> None:
        cards = json.loads((ROOT / "public/data/releases/v2.2.0/cards.json").read_text())["cards"]
        crosswalk = json.loads(
            (ROOT / "reports/data_quality/l4_deduplication_v2.1/retired_to_canonical.json").read_text()
        )
        self.assertEqual(sum(row["assignment_status"] == "locked_physical" for row in cards), 182)
        self.assertEqual(len(crosswalk), 1)
        self.assertTrue(all(row["retired_l4_id"] != row["canonical_l4_id"] for row in crosswalk))

    def test_no_exact_label_and_core_definition_duplicates_remain(self) -> None:
        cards = json.loads((ROOT / "public/data/releases/v2.2.0/cards.json").read_text())["cards"]

        def normalized(value: str) -> str:
            value = unicodedata.normalize("NFKC", value or "").casefold()
            return re.sub(r"[^a-z0-9가-힣]+", "", value)

        keys = []
        for card in cards:
            core = card["definition_en"].split("This L4 risk card treats")[0]
            keys.append((normalized(card["label_en"]), normalized(core)))
        self.assertEqual(len(keys), len(set(keys)))

    def test_two_reviewer_consensus_amendment_is_applied(self) -> None:
        cards = json.loads((ROOT / "public/data/releases/v2.2.0/cards.json").read_text())["cards"]
        card = next(row for row in cards if row["l4_id"] == "RAI4-0888")
        self.assertEqual(card["original_label_en"], "Privacy concerns")
        self.assertEqual(card["label_en"], "Anthropomorphic trust-induced privacy disclosure")
        self.assertEqual(card["primary_l3_id"], "RAI3-G-INT-10")
        self.assertTrue(card["expert_consensus_approved"])
        self.assertFalse(card["decision_required"])


if __name__ == "__main__":
    unittest.main()
