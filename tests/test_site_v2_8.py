from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V27 = ROOT / "public/data/releases/v2.7.0"
V28 = ROOT / "public/data/releases/v2.8.0"
NEW_IDS = {
    "RAI3-A-SYS-07": "Goal & Planning",
    "RAI3-A-SYS-08": "Tool Calling",
    "RAI3-A-SYS-09": "Memory",
    "RAI3-A-SYS-10": "Oversight & Control",
}


class SiteV28Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.before = json.loads((V27 / "cards.json").read_text())["cards"]
        cls.after = json.loads((V28 / "cards.json").read_text())["cards"]
        cls.hierarchy = json.loads((V28 / "hierarchy.json").read_text())["nodes"]
        cls.before_by_id = {row["l4_id"]: row for row in cls.before}
        cls.after_by_id = {row["l4_id"]: row for row in cls.after}

    def test_population_and_unique_ids(self) -> None:
        self.assertEqual(len(self.after), 1711)
        self.assertEqual(len({row["l4_id"] for row in self.after}), 1711)

    def test_four_new_agentic_l3_nodes(self) -> None:
        nodes = {row["node_id"]: row for row in self.hierarchy}
        for node_id, label in NEW_IDS.items():
            self.assertEqual(nodes[node_id]["label_en"], label)
            self.assertTrue(nodes[node_id]["definition_en"])
            self.assertTrue(nodes[node_id]["definition_ko"])
            self.assertTrue(nodes[node_id]["references"])

    def test_every_l3_is_bilingual_and_referenced(self) -> None:
        l3 = [row for row in self.hierarchy if row["level"] == 3]
        self.assertEqual(len(l3), 54)
        for row in l3:
            self.assertTrue(row.get("definition_en"), row["node_id"])
            self.assertTrue(row.get("definition_ko"), row["node_id"])
            self.assertTrue(row.get("references"), row["node_id"])
            self.assertTrue(all(ref.get("title") and ref.get("url") for ref in row["references"]))

    def test_physical_lock_placement_and_content_preserved(self) -> None:
        physical = [row for row in self.after if row["assignment_status"] == "locked_physical"]
        self.assertEqual(len(physical), 182)
        for row in physical:
            before = self.before_by_id[row["l4_id"]]
            comparable = {**row, "release_id": "v2.7.0"}
            self.assertEqual(comparable, before)

    def test_high_precision_anchor_assignments(self) -> None:
        expected = {
            "RAI4-0001": "RAI3-A-SYS-07",
            "RAI4-0037": "RAI3-A-SYS-08",
            "RAI4-0011": "RAI3-A-SYS-09",
            "RAI4-0003": "RAI3-A-SYS-10",
        }
        for card_id, node_id in expected.items():
            self.assertEqual(self.after_by_id[card_id]["primary_l3_id"], node_id)

    def test_conservative_exclusions(self) -> None:
        # General RAG, broad reasoning, and generic human override are not made
        # Agentic merely because those technologies or controls are mentioned.
        for card_id in ("RAI4-0034", "RAI4-0116"):
            self.assertEqual(
                self.after_by_id[card_id]["primary_l3_id"],
                self.before_by_id[card_id]["primary_l3_id"],
            )

    def test_fixed_point_was_reached(self) -> None:
        summary = json.loads(
            (ROOT / "reports/data_quality/agentic_l3_expansion_v2.8.0/summary.json").read_text()
        )
        self.assertTrue(summary["converged"])
        self.assertEqual(summary["iterations"][-1]["changes"], 0)


if __name__ == "__main__":
    unittest.main()
