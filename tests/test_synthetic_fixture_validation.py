from __future__ import annotations

from pathlib import Path
from unittest import TestCase

from scripts.validate_synthetic_fixture import validate_fixture


class SyntheticFixtureValidationTest(TestCase):
    def test_public_synthetic_fixture_passes_contract(self) -> None:
        report = validate_fixture(Path("fixtures/synthetic_market_observations.jsonl"))

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["row_count"], 2)
        self.assertEqual(report["violations"], [])

