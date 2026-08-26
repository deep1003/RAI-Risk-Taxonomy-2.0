from __future__ import annotations

import csv
import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_ID = "RAI-Risk-Taxonomy-2.0-master"
SOURCE = ROOT / "releases" / RELEASE_ID
PUBLIC = ROOT / "public" / "data" / "releases" / RELEASE_ID


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class MasterSiteReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((PUBLIC / "manifest.json").read_text(encoding="utf-8"))
        cls.hierarchy = json.loads((PUBLIC / "hierarchy.json").read_text(encoding="utf-8"))
        cls.cards = json.loads((PUBLIC / "cards.json").read_text(encoding="utf-8"))["cards"]

    def test_canonical_csv_package_has_exactly_five_files(self) -> None:
        names = sorted(path.name for path in (SOURCE / "data").glob("*.csv"))
        self.assertEqual(
            names,
            [
                "L1_L2_L3_Master.csv",
                "L1_Master.csv",
                "L4_Agentic.csv",
                "L4_General.csv",
                "L4_Physical.csv",
            ],
        )

    def test_public_counts_match_reviewed_release(self) -> None:
        self.assertEqual(len(self.cards), 834)
        self.assertEqual(self.manifest["counts"]["l3"], 49)
        self.assertEqual(self.manifest["counts"]["l3_immutable"], 46)
        self.assertEqual(self.manifest["counts"]["l3_others"], 3)
        self.assertEqual(Counter(card["mapping_method"] for card in self.cards), Counter({"EM": 769, "HD": 65}))
        self.assertEqual(
            Counter(card["primary_l3_id"].split("_")[0] for card in self.cards),
            Counter({"G": 618, "P": 131, "A": 85}),
        )

    def test_every_card_resolves_to_a_bilingual_l3_node(self) -> None:
        l3 = {node["node_id"]: node for node in self.hierarchy["nodes"] if node["level"] == 3}
        self.assertEqual(len(l3), 49)
        self.assertTrue(all(card["primary_l3_id"] in l3 for card in self.cards))
        self.assertTrue(all(card["label_en"] and card["label_ko"] for card in self.cards))
        self.assertTrue(all(card["definition_en"] and card["definition_ko"] for card in self.cards))

    def test_others_are_exclusively_hd_assignments(self) -> None:
        others = {"G_Others", "A_Others", "P_Others"}
        routed = [card for card in self.cards if card["primary_l3_id"] in others]
        self.assertEqual(len(routed), 65)
        self.assertTrue(all(card["mapping_method"] == "HD" for card in routed))
        self.assertTrue(all(card["primary_l3_id"] in others for card in self.cards if card["mapping_method"] == "HD"))

    def test_cleaning_reconciliation_and_validation_are_published(self) -> None:
        cleaning = self.manifest["cleaning"]
        self.assertEqual(cleaning["source_total"] - cleaning["deleted"] - cleaning["merged_away"] + cleaning["split_net_addition"], cleaning["final_total"])
        self.assertEqual(cleaning["final_total"], 834)
        self.assertEqual(self.manifest["validation"], {"status": "PASS", "passed": 18, "failed": 0})

    def test_site_points_to_master_bundle_and_downloads(self) -> None:
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "assets" / "site.js").read_text(encoding="utf-8")
        self.assertIn(f'public/data/releases/{RELEASE_ID}', script)
        self.assertIn("834 final L4 cards", page)
        self.assertIn("18/18 QA PASS", page)
        for name in ("L1_Master.csv", "L1_L2_L3_Master.csv", "L4_General.csv", "L4_Agentic.csv", "L4_Physical.csv"):
            self.assertIn(f"releases/{RELEASE_ID}/data/{name}", page)
        self.assertIn(f"releases/{RELEASE_ID}/manifest.html", page)
        self.assertIn(f"releases/{RELEASE_ID}/validation.html", page)

    def test_manifest_and_validation_have_html_tables_and_charts(self) -> None:
        manifest_page = (SOURCE / "manifest.html").read_text(encoding="utf-8")
        validation_page = (SOURCE / "validation.html").read_text(encoding="utf-8")
        report_script = (ROOT / "assets" / "release-report.js").read_text(encoding="utf-8")
        report_style = (ROOT / "assets" / "release-report.css").read_text(encoding="utf-8")
        self.assertIn('data-report="manifest"', manifest_page)
        self.assertIn('data-report="validation"', validation_page)
        self.assertIn('href="manifest.json" download', manifest_page)
        self.assertIn('href="validation/final_release_qa.json" download', validation_page)
        self.assertIn('<table>', report_script)
        self.assertIn('class="bar-chart"', report_script)
        self.assertIn('class="stack-chart"', report_script)
        self.assertIn('class="validation-bar"', report_script)
        self.assertIn(".table-shell", report_style)

    def test_manifest_hashes_match_distribution_manifest(self) -> None:
        source_manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(self.manifest["artifacts"], source_manifest["primary_outputs"])
        self.assertEqual(len(read_csv(SOURCE / "data" / "L1_L2_L3_Master.csv")), 49)


if __name__ == "__main__":
    unittest.main()
