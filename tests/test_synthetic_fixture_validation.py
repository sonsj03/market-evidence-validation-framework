from __future__ import annotations

from pathlib import Path
from unittest import TestCase

from scripts.validate_synthetic_fixture import validate_fixture, validate_rows


class SyntheticFixtureValidationTest(TestCase):
    def test_public_synthetic_fixture_passes_contract(self) -> None:
        report = validate_fixture(Path("fixtures/synthetic_market_observations.jsonl"))

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["row_count"], 2)
        self.assertEqual(report["violations"], [])

    def test_validator_rejects_missing_source_lineage(self) -> None:
        row = self._valid_row()
        del row["source_lineage"]

        violations = validate_rows([row])

        self.assertIn("row 1: missing fields: source_lineage", violations)

    def test_validator_rejects_invalid_known_at_ordering(self) -> None:
        row = self._valid_row()
        row["known_at"] = "2025-12-31T23:59:00Z"

        violations = validate_rows([row])

        self.assertIn("row 1: known_at must not be earlier than observed_at", violations)

    def test_validator_rejects_malformed_confidence_score(self) -> None:
        row = self._valid_row()
        row["confidence_evidence_score"] = 1.2

        violations = validate_rows([row])

        self.assertIn(
            "row 1: confidence_evidence_score must be a number from 0 to 1",
            violations,
        )

    def test_validator_rejects_unexpected_schema_field(self) -> None:
        row = self._valid_row()
        row["runtime_hint"] = "not allowed"

        violations = validate_rows([row])

        self.assertIn("row 1: unexpected fields: runtime_hint", violations)

    def test_validator_rejects_lineage_mismatch(self) -> None:
        row = self._valid_row()
        row["source_lineage"]["source_ref"] = "src_OTHER"

        violations = validate_rows([row])

        self.assertIn("row 1: source_lineage.source_ref must match source_ref", violations)

    def test_validator_rejects_missing_source_identity(self) -> None:
        row = self._valid_row()
        del row["source_lineage"]["source_identity_key"]

        violations = validate_rows([row])

        self.assertIn(
            "row 1: source_lineage missing fields: source_identity_key",
            violations,
        )

    def test_validator_rejects_venue_mismatch(self) -> None:
        row = self._valid_row()
        row["source_lineage"]["venue"] = "other_venue"

        violations = validate_rows([row])

        self.assertIn("row 1: source_lineage.venue must match venue", violations)

    def test_validator_rejects_source_known_at_before_source_observed_at(self) -> None:
        row = self._valid_row()
        row["source_lineage"]["source_known_at"] = "2025-12-31T23:59:00Z"

        violations = validate_rows([row])

        self.assertIn(
            "row 1: source_lineage.source_known_at must not be earlier than source_observed_at",
            violations,
        )

    def test_validator_rejects_row_known_at_before_source_known_at(self) -> None:
        row = self._valid_row()
        row["known_at"] = "2026-01-01T00:00:30Z"
        row["source_lineage"]["source_known_at"] = "2026-01-01T00:01:00Z"

        violations = validate_rows([row])

        self.assertIn(
            "row 1: known_at must not be earlier than source_lineage.source_known_at",
            violations,
        )

    def _valid_row(self) -> dict[str, object]:
        return {
            "observation_id": "obs_TEST_001",
            "symbol": "BTCUSDT",
            "venue": "synthetic_exchange",
            "market_type": "synthetic_spot",
            "quote_currency": "USDT",
            "observed_at": "2026-01-01T00:00:00Z",
            "known_at": "2026-01-01T00:01:00Z",
            "source_ref": "src_TEST_001",
            "source_lineage": {
                "source_ref": "src_TEST_001",
                "source_type": "synthetic_fixture",
                "venue": "synthetic_exchange",
                "market_type": "synthetic_spot",
                "source_identity_key": "synthetic_exchange:synthetic_spot:BTCUSDT:USDT",
                "source_observed_at": "2026-01-01T00:00:00Z",
                "source_known_at": "2026-01-01T00:01:00Z",
            },
            "hypothesis": "synthetic_context",
            "confidence_evidence_score": 0.5,
            "direct_trading_allowed": False,
            "order_execution_allowed": False,
            "private_exchange_api_allowed": False,
        }
