from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class RemapWorkflowIntegrationTest(unittest.TestCase):
    def test_successor_write_validate_and_stable_decision_ids(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rai-remap-smoke-") as temp_dir:
            clone = Path(temp_dir) / "repo"
            shutil.copytree(
                ROOT,
                clone,
                ignore=shutil.ignore_patterns(".git", "tmp", "build", "__pycache__", "*.pyc"),
            )
            command = [
                sys.executable,
                "scripts/create_remap_release.py",
                "--from-release",
                "v1.0.0",
                "--to-release",
                "v1.0.1",
                "--decisions",
                "tests/fixtures/remap_decisions.example.json",
                "--approved-by",
                "Test Taxonomy Board",
                "--approved-at",
                "2026-07-21T00:00:00+09:00",
                "--reviewer",
                "Smoke Reviewer A",
                "--reviewer",
                "Smoke Reviewer B",
                "--allow-prepublication-source",
            ]
            subprocess.run(command, cwd=clone, check=True, capture_output=True, text=True)
            result = subprocess.run(
                [sys.executable, "scripts/validate_release.py", "--release-id", "v1.0.1"],
                cwd=clone,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn('"status": "PASS_WITH_WARNINGS"', result.stdout)

            source = load(clone / "data/releases/v1.0.0/placements.json")
            successor = load(clone / "data/releases/v1.0.1/placements.json")
            source_by_id = {row["l4_id"]: row for row in source}
            successor_by_id = {row["l4_id"]: row for row in successor}
            changed_id = "RAI4-0001"
            for l4_id, before in source_by_id.items():
                if l4_id != changed_id:
                    self.assertEqual(before.get("decision_id"), successor_by_id[l4_id].get("decision_id"))

            migrations = load(clone / "data/releases/v1.0.1/placement_migrations.json")
            validation = load(clone / "reports/validation/v1.0.1/validation_summary.json")
            self.assertEqual(len(migrations), 1)
            self.assertEqual(migrations[0]["l4_id"], changed_id)
            self.assertEqual(validation["failed_checks"], 0)
            checks = {row["check_id"]: row["status"] for row in validation["checks"]}
            self.assertEqual(checks["REL-004"], "PASS")
            self.assertEqual(checks["REL-005"], "PASS")
            self.assertEqual(checks["REL-006"], "PASS")


if __name__ == "__main__":
    unittest.main()
