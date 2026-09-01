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
        self.assertEqual(len(self.cards), 623)
        self.assertEqual(self.manifest["counts"]["l3"], 50)
        self.assertEqual(self.manifest["counts"]["l3_master"], 47)
        self.assertEqual(self.manifest["counts"]["l3_immutable"], 46)
        self.assertEqual(self.manifest["counts"]["l3_others"], 3)
        self.assertEqual(Counter(card["mapping_method"] for card in self.cards), Counter({"EM": 321, "HD": 302}))
        self.assertEqual(
            Counter(card["primary_l3_id"].split("_")[0] for card in self.cards),
            Counter({"G": 492, "A": 66, "P": 65}),
        )

    def test_every_card_resolves_to_a_bilingual_l3_node(self) -> None:
        l3 = {node["node_id"]: node for node in self.hierarchy["nodes"] if node["level"] == 3}
        self.assertEqual(len(l3), 50)
        self.assertTrue(all(card["primary_l3_id"] in l3 for card in self.cards))
        self.assertTrue(all(card["label_en"] and card["label_ko"] for card in self.cards))
        self.assertTrue(all(card["definition_en"] and card["definition_ko"] for card in self.cards))

    def test_performance_reliability_l3_is_fully_propagated(self) -> None:
        nodes = [node for node in self.hierarchy["nodes"] if node["node_id"] == "G_SYS_PERF"]
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["parent_id"], "G_SYS")
        self.assertEqual(nodes[0]["label_ko"], "성능·신뢰성 실패")
        self.assertEqual(nodes[0]["label_en"], "Performance and Reliability Failure")
        cards = [card for card in self.cards if card["primary_l3_id"] == "G_SYS_PERF"]
        self.assertEqual([card["l4_id"] for card in cards], [f"G_SYS_PERF_{index:03d}" for index in range(1, 17)])

    def test_others_are_hd_assignments_without_equating_hd_and_others(self) -> None:
        others = {"G_Others", "A_Others", "P_Others"}
        routed = [card for card in self.cards if card["primary_l3_id"] in others]
        self.assertEqual(routed, [])
        self.assertGreater(sum(card["mapping_method"] == "HD" for card in self.cards), len(routed))

    def test_cleaning_reconciliation_and_validation_are_published(self) -> None:
        cleaning = self.manifest["cleaning"]
        self.assertEqual(cleaning["source_total"] - cleaning["deleted"] - cleaning["merged_away"] + cleaning["split_net_addition"], cleaning["final_total"])
        self.assertEqual(cleaning["source_total"], 798)
        self.assertEqual(cleaning["deleted"], 21)
        self.assertEqual(cleaning["merged_away"], 177)
        self.assertEqual(cleaning["split_net_addition"], 23)
        self.assertEqual(cleaning["final_total"], 623)
        self.assertEqual(cleaning["user_directed_operations"], 214)
        self.assertEqual(self.manifest["validation"], {"status": "PASS", "passed": 10, "failed": 0})

    def test_score_statuses_are_explicit_and_reconciled(self) -> None:
        forbidden = {"em_score", "em_margin", "hybrid_em_score", "hybrid_em_margin", "em_stability", "review_candidates", "definition_grounding_action", "definition_l3_anchor_score"}
        self.assertTrue(all(forbidden.isdisjoint(card) for card in self.cards))

    def test_site_points_to_master_bundle_and_downloads(self) -> None:
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "assets" / "site.js").read_text(encoding="utf-8")
        self.assertIn(f'public/data/releases/{RELEASE_ID}', script)
        self.assertIn("623 final L4 cards", page)
        self.assertIn("10/10 QA PASS", page)
        self.assertIn("현재 웹 리스크 카드에는 EM, Hybrid EM 또는 관련 점수를 표시하지 않습니다.", page)
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

    def test_round3_review_artifacts_are_published(self) -> None:
        for name in (
            "Human_Review_Round3_Decision_Ledger.csv",
            "Human_Review_Round3_Application_Log.csv",
            "Human_Review_Round3_Validation_Record.json",
            "Human_Review_Round3_Methodology_20260901.md",
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
        self.assertEqual(len(read_csv(SOURCE / "data" / "L1_L2_L3_Master.csv")), 50)


if __name__ == "__main__":
    unittest.main()
