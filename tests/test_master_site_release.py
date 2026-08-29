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
        self.assertEqual(len(self.cards), 798)
        self.assertEqual(self.manifest["counts"]["l3"], 49)
        self.assertEqual(self.manifest["counts"]["l3_immutable"], 46)
        self.assertEqual(self.manifest["counts"]["l3_others"], 3)
        self.assertEqual(Counter(card["mapping_method"] for card in self.cards), Counter({"EM": 440, "HD": 358}))
        self.assertEqual(
            Counter(card["primary_l3_id"].split("_")[0] for card in self.cards),
            Counter({"G": 630, "P": 94, "A": 74}),
        )

    def test_every_card_resolves_to_a_bilingual_l3_node(self) -> None:
        l3 = {node["node_id"]: node for node in self.hierarchy["nodes"] if node["level"] == 3}
        self.assertEqual(len(l3), 49)
        self.assertTrue(all(card["primary_l3_id"] in l3 for card in self.cards))
        self.assertTrue(all(card["label_en"] and card["label_ko"] for card in self.cards))
        self.assertTrue(all(card["definition_en"] and card["definition_ko"] for card in self.cards))

    def test_others_are_hd_assignments_without_equating_hd_and_others(self) -> None:
        others = {"G_Others", "A_Others", "P_Others"}
        routed = [card for card in self.cards if card["primary_l3_id"] in others]
        self.assertEqual(Counter(card["primary_l3_id"] for card in routed), Counter({"G_Others": 117, "P_Others": 8, "A_Others": 4}))
        self.assertTrue(all(card["mapping_method"] == "HD" for card in routed))
        self.assertGreater(sum(card["mapping_method"] == "HD" for card in self.cards), len(routed))

    def test_cleaning_reconciliation_and_validation_are_published(self) -> None:
        cleaning = self.manifest["cleaning"]
        self.assertEqual(cleaning["source_total"] - cleaning["deleted"] - cleaning["merged_away"] + cleaning["split_net_addition"], cleaning["final_total"])
        self.assertEqual(cleaning["source_total"], 808)
        self.assertEqual(cleaning["deleted"], 4)
        self.assertEqual(cleaning["merged_away"], 37)
        self.assertEqual(cleaning["split_net_addition"], 31)
        self.assertEqual(cleaning["final_total"], 798)
        self.assertEqual(cleaning["user_directed_operations"], 10)
        self.assertEqual(cleaning["korean_copyedit_operations"], 518)
        self.assertEqual(cleaning["english_copyedit_operations"], 319)
        self.assertEqual(self.manifest["validation"], {"status": "PASS", "passed": 30, "failed": 0})

    def test_score_statuses_are_explicit_and_reconciled(self) -> None:
        statuses = Counter(card["definition_grounding_action"] for card in self.cards)
        self.assertNotIn(None, statuses)
        self.assertEqual(dict(statuses), self.manifest["score_status_counts"])
        self.assertEqual(sum(statuses.values()), 798)

    def test_site_points_to_master_bundle_and_downloads(self) -> None:
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "assets" / "site.js").read_text(encoding="utf-8")
        self.assertIn(f'public/data/releases/{RELEASE_ID}', script)
        self.assertIn("798 final L4 cards", page)
        self.assertIn("30/30 QA PASS", page)
        self.assertIn("이번 라운드에서는 EM 또는 Hybrid EM을 재실행하지 않았습니다", page)
        for name in ("L1_Master.csv", "L1_L2_L3_Master.csv", "L4_General.csv", "L4_Agentic.csv", "L4_Physical.csv"):
            self.assertIn(f"releases/{RELEASE_ID}/data/{name}", page)
        self.assertIn(f"releases/{RELEASE_ID}/manifest.html", page)
        self.assertIn(f"releases/{RELEASE_ID}/validation.html", page)

    def test_round2_review_artifacts_are_published(self) -> None:
        for name in (
            "Human_Review_Round2_Decision_Ledger.csv",
            "L3_Human_Review_Round2_Decision_Ledger.csv",
            "user_directed_operations.csv",
            "L4_Korean_Copyedit_Approved_20260829.csv",
            "L4_English_Copyedit_Approved_20260829.csv",
            "L4_Final_Terminology_L3_Alignment_Approved_20260829.csv",
            "Expert_Language_Review_Final_20260829.json",
            "L4_Top20_Similar_Pairs.csv",
        ):
            self.assertTrue((SOURCE / "validation" / name).is_file(), name)

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
