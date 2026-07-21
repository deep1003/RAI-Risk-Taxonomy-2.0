from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "public/data/releases/v2.12.0"
RELEASE = ROOT / "public/data/releases/v2.13.0"
REPORT = ROOT / "reports/data_quality/memory_card_differentiation_v2.13.0"
TARGETS = {"RAI4-0011", "RAI4-0484", "RAI4-1670"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class MemoryCardDifferentiationV213Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.before = load(SOURCE / "cards.json")["cards"]
        cls.after = load(RELEASE / "cards.json")["cards"]
        cls.summary = load(REPORT / "summary.json")
        cls.audit = load(REPORT / "scope_differentiation_audit.json")

    def test_population_and_grain_are_preserved(self) -> None:
        self.assertEqual(len(self.after), 1711)
        self.assertEqual(len({card["l4_id"] for card in self.after}), 1711)
        self.assertEqual(self.summary["counts"]["l3"], 54)
        self.assertEqual(self.summary["counts"]["physical_locked"], 182)

    def test_exactly_three_cards_change_beyond_release_id(self) -> None:
        before = {card["l4_id"]: card for card in self.before}
        changed = set()
        for card in self.after:
            comparable = {**card, "release_id": "v2.12.0"}
            if comparable != before[card["l4_id"]]:
                changed.add(card["l4_id"])
        self.assertEqual(changed, TARGETS)
        self.assertEqual({row["l4_id"] for row in self.audit}, TARGETS)

    def test_identity_evidence_metrics_and_path_are_preserved(self) -> None:
        before = {card["l4_id"]: card for card in self.before}
        after = {card["l4_id"]: card for card in self.after}
        protected = (
            "l4_id", "primary_l3_id", "references", "severity_1to5",
            "probability_0to1", "impact_score", "breadcrumb",
        )
        for l4_id in TARGETS:
            for field in protected:
                self.assertEqual(before[l4_id].get(field), after[l4_id].get(field))

    def test_names_and_mechanisms_are_distinct_and_held(self) -> None:
        cards = {card["l4_id"]: card for card in self.after}
        self.assertEqual(cards["RAI4-0011"]["label_en"], "Agent context poisoning")
        self.assertEqual(cards["RAI4-0484"]["label_en"], "Unsafe memory accumulation")
        self.assertEqual(cards["RAI4-1670"]["label_en"], "Persistent agent-memory poisoning")
        self.assertEqual(len({cards[l4_id]["label_ko"] for l4_id in TARGETS}), 3)
        self.assertTrue(all(cards[l4_id]["decision_required"] for l4_id in TARGETS))
        self.assertTrue(all(cards[l4_id]["human_approved"] is False for l4_id in TARGETS))
        self.assertEqual(self.summary["counts"]["decision_required"], 692)

    def test_physical_cards_are_unchanged(self) -> None:
        before = {card["l4_id"]: card for card in self.before}
        for card in self.after:
            if card.get("assignment_status") != "locked_physical":
                continue
            comparable = {**card, "release_id": "v2.12.0"}
            self.assertEqual(comparable, before[card["l4_id"]])


if __name__ == "__main__":
    unittest.main()
