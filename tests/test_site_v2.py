from __future__ import annotations

import json
import re
import unittest
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SiteV2Tests(unittest.TestCase):
    def test_site_bundle_matches_review_hold_policy(self) -> None:
        bundle = ROOT / "public/data/releases/v2.6.0"
        cards = json.loads((bundle / "cards.json").read_text())["cards"]
        manifest = json.loads((bundle / "manifest.json").read_text())
        self.assertEqual(len(cards), 1711)
        self.assertEqual(sum(row["primary_l3_id"] is not None for row in cards), 1711)
        self.assertEqual(sum(row["decision_required"] for row in cards), 76)
        self.assertEqual(sum(row["assignment_status"] == "stage3_forced" for row in cards), 165)
        self.assertEqual(manifest["counts"]["l3_nodes"], 50)

    def test_hold_marked_cards_remain_inside_the_l3_tree(self) -> None:
        cards = json.loads(
            (ROOT / "public/data/releases/v2.6.0/cards.json").read_text()
        )["cards"]
        holds = [row for row in cards if row["decision_required"]]
        self.assertEqual(len(holds), 76)
        self.assertTrue(all(row["primary_l3_id"] for row in holds))
        self.assertTrue(all(row["operational_bucket_id"] is None for row in holds))

    def test_physical_cards_and_duplicate_crosswalk_are_preserved(self) -> None:
        cards = json.loads((ROOT / "public/data/releases/v2.6.0/cards.json").read_text())["cards"]
        crosswalk = json.loads(
            (ROOT / "reports/data_quality/l4_deduplication_v2.1/retired_to_canonical.json").read_text()
        )
        self.assertEqual(sum(row["assignment_status"] == "locked_physical" for row in cards), 182)
        self.assertEqual(len(crosswalk), 1)
        self.assertTrue(all(row["retired_l4_id"] != row["canonical_l4_id"] for row in crosswalk))

    def test_no_exact_label_and_core_definition_duplicates_remain(self) -> None:
        cards = json.loads((ROOT / "public/data/releases/v2.6.0/cards.json").read_text())["cards"]

        def normalized(value: str) -> str:
            value = unicodedata.normalize("NFKC", value or "").casefold()
            return re.sub(r"[^a-z0-9가-힣]+", "", value)

        keys = []
        for card in cards:
            core = card["definition_en"].split("This L4 risk card treats")[0]
            keys.append((normalized(card["label_en"]), normalized(core)))
        self.assertEqual(len(keys), len(set(keys)))

    def test_two_reviewer_consensus_amendment_is_applied(self) -> None:
        cards = json.loads((ROOT / "public/data/releases/v2.6.0/cards.json").read_text())["cards"]
        card = next(row for row in cards if row["l4_id"] == "RAI4-0888")
        self.assertEqual(card["original_label_en"], "Privacy concerns")
        self.assertEqual(card["label_en"], "Anthropomorphic trust-induced privacy disclosure")
        self.assertEqual(card["primary_l3_id"], "RAI3-G-INT-10")
        self.assertTrue(card["expert_consensus_approved"])
        self.assertFalse(card["decision_required"])

    def test_physical_l3_labels_are_excluded_from_l4_pool(self) -> None:
        cards = json.loads((ROOT / "public/data/releases/v2.6.0/cards.json").read_text())["cards"]
        audit = json.loads((ROOT / "reports/data_quality/physical_l3_label_leakage_v2.3.json").read_text())
        excluded_ids = {row["l4_id"] for row in audit["excluded"]}
        self.assertEqual(len(excluded_ids), 14)
        self.assertIn("RAI4-0553", excluded_ids)
        self.assertTrue(excluded_ids.isdisjoint({row["l4_id"] for row in cards}))
        self.assertEqual(sum(row["primary_l3_id"].startswith("RAI3-P-") for row in cards), 182)

    def test_all_physical_cards_are_synced_from_authoritative_source(self) -> None:
        cards = json.loads((ROOT / "public/data/releases/v2.6.0/cards.json").read_text())["cards"]
        physical = [row for row in cards if row["assignment_status"] == "locked_physical"]
        self.assertEqual(len(physical), 182)
        self.assertTrue(all(row["physical_source_sync"] == "v2.4.0" for row in physical))
        self.assertTrue(all(row["metrics_source"] == "physical_ai_taxonomy_local_sync_v2.4" for row in physical))
        self.assertTrue(all(row["impact_score"] == round(row["severity_1to5"] * row["probability_0to1"], 6) for row in physical))
        self.assertTrue(all(row["impact_percentile"] is None for row in physical))
        self.assertEqual(sum(len(row["references"]) for row in physical), 360)
        self.assertEqual(sum(bool(ref.get("justification")) for row in physical for ref in row["references"]), 359)

    def test_percentile_is_not_rendered(self) -> None:
        script = (ROOT / "assets/site.js").read_text()
        self.assertNotIn("<span>Percentile</span>", script)

    def test_simplified_header_and_l1_to_l4_summary(self) -> None:
        page = (ROOT / "index.html").read_text()
        self.assertIn('class="hero__home" href="https://deep1003.github.io/RAI-Risk-Taxonomy-2.0/"', page)
        self.assertNotIn("hero__count", page)
        self.assertIn("전체 AI 리스크 분류 현황", page)
        self.assertNotIn("글로벌 AI 리스크 분류 현황", page)
        self.assertNotIn("coverage-note", page)
        for level, count in (("l1", "3"), ("l2", "4"), ("l3", "52"), ("l4", "1,711")):
            self.assertIn(f'id="stat-{level}">{count}', page)

    def test_domain_navigation_uses_links_without_counts(self) -> None:
        page = (ROOT / "index.html").read_text()
        self.assertIn('href="?domain=RAI1-G"', page)
        self.assertIn('href="?domain=RAI1-A"', page)
        self.assertIn('href="?domain=RAI1-P"', page)
        self.assertIn("General-purpose AI (범용 AI)", page)
        self.assertIn("Agentic AI (에이전틱 AI)", page)
        self.assertIn("Physical AI (피지컬 AI)", page)
        nav = page.split('<nav class="domain-nav"', 1)[1].split("</nav>", 1)[0]
        self.assertNotRegex(nav, r">\s*[\d,]+\s*<")

    def test_every_card_has_english_korean_bilingual_content(self) -> None:
        cards = json.loads((ROOT / "public/data/releases/v2.6.0/cards.json").read_text())["cards"]
        self.assertEqual(len(cards), 1711)
        self.assertTrue(all(row["label_en"].strip() and row["definition_en"].strip() for row in cards))
        self.assertTrue(all(re.search(r"[가-힣]", row["label_ko"]) for row in cards))
        self.assertTrue(all(re.search(r"[가-힣]", row["definition_ko"]) for row in cards))
        nonphysical = [row for row in cards if row["assignment_status"] != "locked_physical"]
        self.assertEqual(len(nonphysical), 1529)
        self.assertTrue(all(row["localization_review_status"] == "pending" for row in nonphysical))

    def test_all_levels_render_english_korean_labels(self) -> None:
        script = (ROOT / "assets/site.js").read_text()
        self.assertIn("function bilingualLabel(english, korean)", script)
        self.assertIn("bilingualLabel(card.label_en, card.label_ko)", script)
        self.assertIn("bilingualLabel(l3.label_en, l3.label_ko)", script)

    def test_l2_is_consolidated_to_three_canonical_categories(self) -> None:
        hierarchy = json.loads((ROOT / "public/data/releases/v2.6.0/hierarchy.json").read_text())
        categories = hierarchy["canonical_l2_categories"]
        self.assertEqual(len(categories), 3)
        self.assertEqual(
            {row["label_en"] for row in categories},
            {"Interaction Safety", "System Safety", "Societal Safety"},
        )
        l2_path_nodes = [row for row in hierarchy["nodes"] if row["level"] == 2]
        self.assertEqual(len(l2_path_nodes), 6)
        self.assertEqual({row["label_en"] for row in l2_path_nodes}, {row["label_en"] for row in categories})
        self.assertTrue(all(row["canonical_l2_id"] for row in l2_path_nodes))

    def test_hierarchy_width_and_l1_card_colors(self) -> None:
        css = (ROOT / "assets/site.css").read_text()
        script = (ROOT / "assets/site.js").read_text()
        self.assertIn("grid-template-columns: 312px minmax(0, 1fr)", css)
        self.assertIn("risk-id--domain", css)
        self.assertIn("domain-badge", css)
        self.assertIn('"RAI1-G": "#3867d6"', script)
        self.assertIn('"RAI1-A": "#148f77"', script)
        self.assertIn('"RAI1-P": "#c0392b"', script)
        self.assertIn("DOMAIN_COLORS[path.l1]", script)
        self.assertIn("DOMAIN_LABELS[path.l1]", script)

    def test_technical_report_draft_button(self) -> None:
        page = (ROOT / "index.html").read_text()
        css = (ROOT / "assets/site.css").read_text()
        self.assertIn('class="report-pill"', page)
        self.assertIn("Technical Report <b>DRAFT</b>", page)
        self.assertIn('href="reports/pdf/rai_risk_taxonomy_technical_report_2_0_en.pdf"', page)
        self.assertIn(".report-pill", css)

    def test_consistent_domain_and_level_icons(self) -> None:
        page = (ROOT / "index.html").read_text()
        script = (ROOT / "assets/site.js").read_text()
        self.assertIn("🧠</span>General-purpose AI", page)
        self.assertIn("🧭</span>Agentic AI", page)
        self.assertIn("🤖</span>Physical AI", page)
        self.assertIn('"RAI1-G": "🧠"', script)
        self.assertIn('"RAI1-A": "🧭"', script)
        self.assertIn('"RAI1-P": "🤖"', script)
        self.assertIn('"RAI2-INT": "↔"', script)
        self.assertIn('"RAI2-SYS": "⚙"', script)
        self.assertIn('"RAI2-SOC": "🏛"', script)


if __name__ == "__main__":
    unittest.main()
