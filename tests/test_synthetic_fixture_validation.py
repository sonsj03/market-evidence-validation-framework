from __future__ import annotations

from pathlib import Path
from unittest import TestCase

from scripts.validate_synthetic_fixture import (
    build_domain_extension_readiness,
    load_jsonl,
    validate_fixture,
    validate_rows,
)


class SyntheticFixtureValidationTest(TestCase):
    def test_public_synthetic_fixture_passes_contract(self) -> None:
        report = validate_fixture(Path("fixtures/synthetic_market_observations.jsonl"))

        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["row_count"], 2)
        self.assertEqual(report["domain_extension_readiness"]["status"], "READY")
        self.assertEqual(report["violations"], [])

    def test_public_synthetic_fixture_includes_spot_and_funding_domains(self) -> None:
        rows = load_jsonl(Path("fixtures/synthetic_market_observations.jsonl"))
        domains = {row["source_lineage"]["evidence_domain"] for row in rows}
        market_types = {row["market_type"] for row in rows}

        self.assertEqual(domains, {"offchain_exchange", "offchain_funding"})
        self.assertEqual(market_types, {"synthetic_spot", "funding"})

    def test_domain_extension_readiness_blocks_missing_funding_coverage(self) -> None:
        row = self._valid_row()

        readiness = build_domain_extension_readiness([row], [])

        self.assertEqual(readiness["status"], "BLOCKED")
        self.assertIn(
            "public_fixture_must_cover_offchain_exchange_and_funding",
            readiness["blockers"],
        )

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

    def test_validator_rejects_normalized_symbol_mismatch(self) -> None:
        row = self._valid_row()
        row["normalized_symbol"] = "BTC-USDT"

        violations = validate_rows([row])

        self.assertIn("row 1: normalized_symbol must equal base_asset/quote_asset", violations)

    def test_validator_rejects_quote_asset_mismatch(self) -> None:
        row = self._valid_row()
        row["quote_asset"] = "USD"

        violations = validate_rows([row])

        self.assertIn("row 1: quote_asset must match quote_currency", violations)

    def test_validator_rejects_non_continuous_session_model(self) -> None:
        row = self._valid_row()
        row["session_model"] = "regular_market_hours"

        violations = validate_rows([row])

        self.assertIn("row 1: session_model must be continuous_24_7", violations)

    def test_validator_rejects_session_assumption_fields(self) -> None:
        row = self._valid_row()
        row["market_open"] = "09:30"

        violations = validate_rows([row])

        self.assertIn("row 1: forbidden session assumption fields: market_open", violations)

    def test_validator_rejects_financial_advice_policy_drift(self) -> None:
        row = self._valid_row()
        row["research_policy"]["financial_advice_allowed"] = True

        violations = validate_rows([row])

        self.assertIn("row 1: research_policy.financial_advice_allowed must be false", violations)

    def test_validator_rejects_jurisdiction_instruction_policy_drift(self) -> None:
        row = self._valid_row()
        row["research_policy"]["jurisdiction_specific_instruction_allowed"] = True

        violations = validate_rows([row])

        self.assertIn(
            "row 1: research_policy.jurisdiction_specific_instruction_allowed must be false",
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

    def test_validator_rejects_adapter_contract_with_network_enabled(self) -> None:
        row = self._valid_row()
        row["source_lineage"]["adapter_contract"]["network_allowed"] = True

        violations = validate_rows([row])

        self.assertIn(
            "row 1: source_lineage.adapter_contract.network_allowed must be false",
            violations,
        )

    def test_validator_rejects_adapter_contract_requiring_credentials(self) -> None:
        row = self._valid_row()
        row["source_lineage"]["adapter_contract"]["credential_required"] = True

        violations = validate_rows([row])

        self.assertIn(
            "row 1: source_lineage.adapter_contract.credential_required must be false",
            violations,
        )

    def test_validator_rejects_adapter_contract_missing_provider_version(self) -> None:
        row = self._valid_row()
        del row["source_lineage"]["adapter_contract"]["provider_contract_version"]

        violations = validate_rows([row])

        self.assertIn(
            "row 1: source_lineage.adapter_contract missing fields: provider_contract_version",
            violations,
        )

    def test_validator_rejects_adapter_contract_without_fail_closed_deprecation_policy(self) -> None:
        row = self._valid_row()
        row["source_lineage"]["adapter_contract"]["deprecation_policy"] = "best_effort"

        violations = validate_rows([row])

        self.assertIn(
            "row 1: source_lineage.adapter_contract.deprecation_policy must be fail_closed_on_unknown_change",
            violations,
        )

    def test_validator_rejects_invalid_evidence_domain(self) -> None:
        row = self._valid_row()
        row["source_lineage"]["evidence_domain"] = "mixed_unknown"

        violations = validate_rows([row])

        self.assertIn(
            "row 1: source_lineage.evidence_domain must be one of: offchain_exchange, offchain_funding, onchain_block, onchain_mempool",
            violations,
        )

    def test_validator_rejects_onchain_block_without_finality_fields(self) -> None:
        row = self._valid_row()
        row["source_lineage"]["evidence_domain"] = "onchain_block"

        violations = validate_rows([row])

        self.assertIn(
            "row 1: onchain_block source_lineage missing fields: block_hash, block_number, chain_id, evidence_usage, finality_state, reorg_invalidated",
            violations,
        )

    def test_validator_rejects_reorg_invalidated_block_without_reorg_flag(self) -> None:
        row = self._valid_onchain_block_row()
        row["source_lineage"]["finality_state"] = "reorg_invalidated"
        row["source_lineage"]["reorg_invalidated"] = False

        violations = validate_rows([row])

        self.assertIn(
            "row 1: source_lineage.reorg_invalidated must be true when finality_state is reorg_invalidated",
            violations,
        )

    def test_validator_rejects_reorg_invalidated_block_as_stable_evidence(self) -> None:
        row = self._valid_onchain_block_row()
        row["source_lineage"]["finality_state"] = "reorg_invalidated"
        row["source_lineage"]["reorg_invalidated"] = True
        row["source_lineage"]["evidence_usage"] = "stable_evidence"

        violations = validate_rows([row])

        self.assertIn(
            "row 1: reorg_invalidated onchain_block source_lineage must use evidence_usage invalidation_record",
            violations,
        )

    def test_validator_rejects_invalidation_record_without_superseding_block_hash(self) -> None:
        row = self._valid_onchain_block_row()
        row["source_lineage"]["finality_state"] = "reorg_invalidated"
        row["source_lineage"]["reorg_invalidated"] = True
        row["source_lineage"]["evidence_usage"] = "invalidation_record"

        violations = validate_rows([row])

        self.assertIn(
            "row 1: invalidation_record onchain_block source_lineage requires superseded_by_block_hash",
            violations,
        )

    def test_validator_rejects_finalized_reorg_invalidated_block(self) -> None:
        row = self._valid_onchain_block_row()
        row["source_lineage"]["finality_state"] = "finalized"
        row["source_lineage"]["reorg_invalidated"] = True

        violations = validate_rows([row])

        self.assertIn(
            "row 1: finalized onchain_block source_lineage must not be reorg_invalidated",
            violations,
        )

    def test_validator_rejects_joined_reorg_invalidated_onchain_block(self) -> None:
        row = self._valid_cross_source_row()
        row["source_lineage"]["joined_source_refs"][1].update(
            {
                "evidence_domain": "onchain_block",
                "finality_state": "reorg_invalidated",
                "reorg_invalidated": True,
            }
        )

        violations = validate_rows([row])

        self.assertIn(
            "row 1: joined_source_refs[2] must not use reorg-invalidated onchain_block evidence",
            violations,
        )

    def test_validator_rejects_mempool_without_mempool_fields(self) -> None:
        row = self._valid_row()
        row["source_lineage"]["evidence_domain"] = "onchain_mempool"

        violations = validate_rows([row])

        self.assertIn(
            "row 1: onchain_mempool source_lineage missing fields: chain_id, confirmed_in_block, mempool_observation_id, mempool_state, tx_hash",
            violations,
        )

    def test_validator_rejects_mempool_with_confirmed_block_fields(self) -> None:
        row = self._valid_onchain_mempool_row()
        row["source_lineage"]["block_hash"] = "0xblock"
        row["source_lineage"]["finality_state"] = "finalized"

        violations = validate_rows([row])

        self.assertIn(
            "row 1: onchain_mempool source_lineage must not include confirmed block fields: block_hash, finality_state",
            violations,
        )

    def test_validator_rejects_pending_mempool_marked_confirmed(self) -> None:
        row = self._valid_onchain_mempool_row()
        row["source_lineage"]["mempool_state"] = "pending"
        row["source_lineage"]["confirmed_in_block"] = True

        violations = validate_rows([row])

        self.assertIn(
            "row 1: source_lineage.confirmed_in_block must be false when mempool_state is pending",
            violations,
        )

    def test_validator_rejects_included_mempool_without_inclusion_block_ref(self) -> None:
        row = self._valid_onchain_mempool_row()
        row["source_lineage"]["mempool_state"] = "included"
        row["source_lineage"]["confirmed_in_block"] = True

        violations = validate_rows([row])

        self.assertIn(
            "row 1: source_lineage.included_block_number must be a non-negative integer when mempool_state is included",
            violations,
        )
        self.assertIn(
            "row 1: source_lineage.included_block_hash must be non-empty when mempool_state is included",
            violations,
        )

    def test_validator_rejects_boolean_included_mempool_block_number(self) -> None:
        row = self._valid_onchain_mempool_row()
        row["source_lineage"]["mempool_state"] = "included"
        row["source_lineage"]["confirmed_in_block"] = True
        row["source_lineage"]["included_block_number"] = True
        row["source_lineage"]["included_block_hash"] = "0xincludedblock"

        violations = validate_rows([row])

        self.assertIn(
            "row 1: source_lineage.included_block_number must be a non-negative integer when mempool_state is included",
            violations,
        )

    def test_validator_rejects_joined_source_without_source_known_at(self) -> None:
        row = self._valid_cross_source_row()
        del row["source_lineage"]["joined_source_refs"][1]["source_known_at"]

        violations = validate_rows([row])

        self.assertIn(
            "row 1: joined_source_refs[2] missing fields: source_known_at",
            violations,
        )

    def test_validator_rejects_row_known_at_before_joined_source_known_at(self) -> None:
        row = self._valid_cross_source_row()
        row["known_at"] = "2026-01-01T00:01:30Z"

        violations = validate_rows([row])

        self.assertIn(
            "row 1: known_at must not be earlier than any joined_source_refs.source_known_at",
            violations,
        )

    def test_validator_rejects_settled_funding_without_settlement_known_at(self) -> None:
        row = self._valid_funding_row()
        row["source_lineage"]["settlement_state"] = "settled"

        violations = validate_rows([row])

        self.assertIn(
            "row 1: settled offchain_funding source_lineage requires settlement_known_at",
            violations,
        )

    def test_validator_rejects_settled_funding_known_before_settlement_known_at(self) -> None:
        row = self._valid_funding_row()
        row["source_lineage"]["settlement_state"] = "settled"
        row["source_lineage"]["settlement_known_at"] = "2026-01-01T08:01:00Z"

        violations = validate_rows([row])

        self.assertIn(
            "row 1: source_lineage.source_known_at must not be earlier than settlement_known_at for settled offchain_funding",
            violations,
        )

    def test_validator_rejects_estimated_funding_with_settlement_known_at(self) -> None:
        row = self._valid_funding_row()
        row["source_lineage"]["settlement_state"] = "estimated"
        row["source_lineage"]["settlement_known_at"] = "2026-01-01T08:01:00Z"

        violations = validate_rows([row])

        self.assertIn(
            "row 1: estimated offchain_funding source_lineage must not include settlement_known_at",
            violations,
        )

    def test_validator_rejects_initial_listing_without_thin_market_flag(self) -> None:
        row = self._valid_listing_context_row()
        row["source_lineage"]["listing_context"]["listing_phase"] = "initial_listing"
        row["source_lineage"]["listing_context"]["thin_market_flag"] = False

        violations = validate_rows([row])

        self.assertIn(
            "row 1: initial_listing listing_context requires thin_market_flag true",
            violations,
        )

    def test_validator_rejects_seasoned_listing_with_too_little_age(self) -> None:
        row = self._valid_listing_context_row()
        row["source_lineage"]["listing_context"]["listing_phase"] = "seasoned"
        row["source_lineage"]["listing_context"]["listing_age_seconds"] = 3600

        violations = validate_rows([row])

        self.assertIn(
            "row 1: seasoned listing_context requires listing_age_seconds of at least 86400",
            violations,
        )

    def test_validator_rejects_source_known_before_listing_time(self) -> None:
        row = self._valid_listing_context_row()
        row["source_lineage"]["listing_context"]["listed_at"] = "2026-01-01T00:02:00Z"

        violations = validate_rows([row])

        self.assertIn(
            "row 1: source_lineage.source_known_at must not be earlier than listing_context.listed_at",
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
            "venue_symbol": "BTCUSDT",
            "normalized_symbol": "BTC/USDT",
            "base_asset": "BTC",
            "quote_asset": "USDT",
            "venue": "synthetic_exchange",
            "market_type": "synthetic_spot",
            "quote_currency": "USDT",
            "normalization_version": "synthetic_symbol_normalization_v1",
            "session_model": "continuous_24_7",
            "observed_at": "2026-01-01T00:00:00Z",
            "known_at": "2026-01-01T00:01:00Z",
            "source_ref": "src_TEST_001",
            "research_policy": self._research_policy(),
            "source_lineage": {
                "source_ref": "src_TEST_001",
                "source_type": "synthetic_fixture",
                "evidence_domain": "offchain_exchange",
                "adapter_contract": self._adapter_contract(),
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

    def _research_policy(self) -> dict[str, object]:
        return {
            "policy_id": "research_only_no_advice_no_execution",
            "research_only": True,
            "financial_advice_allowed": False,
            "execution_guidance_allowed": False,
            "jurisdiction_specific_instruction_allowed": False,
        }

    def _valid_onchain_block_row(self) -> dict[str, object]:
        row = self._valid_row()
        row["symbol"] = "BTC"
        row["venue_symbol"] = "BTC"
        row["normalized_symbol"] = "BTC/NATIVE"
        row["base_asset"] = "BTC"
        row["quote_asset"] = "NATIVE"
        row["venue"] = "synthetic_chain"
        row["market_type"] = "onchain_block"
        row["quote_currency"] = "NATIVE"
        row["source_lineage"].update(
            {
                "evidence_domain": "onchain_block",
                "venue": "synthetic_chain",
                "market_type": "onchain_block",
                "source_identity_key": "synthetic_chain:onchain_block:BTC:NATIVE",
                "chain_id": "synthetic-chain-1",
                "block_number": 100,
                "block_hash": "0xsyntheticblockhash",
                "finality_state": "finalized",
                "reorg_invalidated": False,
                "evidence_usage": "stable_evidence",
            }
        )
        return row

    def _adapter_contract(self) -> dict[str, object]:
        return {
            "adapter_type": "synthetic_fixture_adapter",
            "adapter_schema_version": "synthetic_adapter_contract_v1",
            "provider_contract_version": "synthetic_provider_contract_v1",
            "deprecation_policy": "fail_closed_on_unknown_change",
            "read_only": True,
            "fixture_only": True,
            "network_allowed": False,
            "credential_required": False,
            "private_api_allowed": False,
        }

    def _valid_listing_context_row(self) -> dict[str, object]:
        row = self._valid_row()
        row["source_lineage"]["listing_context"] = {
            "listed_at": "2026-01-01T00:00:00Z",
            "listing_phase": "initial_listing",
            "listing_age_seconds": 60,
            "thin_market_flag": True,
        }
        return row

    def _valid_cross_source_row(self) -> dict[str, object]:
        row = self._valid_row()
        row["known_at"] = "2026-01-01T00:02:00Z"
        row["source_lineage"]["joined_source_refs"] = [
            {
                "source_ref": "src_TEST_A",
                "evidence_domain": "offchain_exchange",
                "venue": "synthetic_exchange_a",
                "source_known_at": "2026-01-01T00:01:00Z",
            },
            {
                "source_ref": "src_TEST_B",
                "evidence_domain": "offchain_exchange",
                "venue": "synthetic_exchange_b",
                "source_known_at": "2026-01-01T00:02:00Z",
            },
        ]
        return row

    def _valid_funding_row(self) -> dict[str, object]:
        row = self._valid_row()
        row["venue_symbol"] = "BTCUSDT"
        row["normalized_symbol"] = "BTC/USDT"
        row["base_asset"] = "BTC"
        row["quote_asset"] = "USDT"
        row["venue"] = "synthetic_exchange"
        row["market_type"] = "funding"
        row["quote_currency"] = "USDT"
        row["observed_at"] = "2026-01-01T08:00:00Z"
        row["known_at"] = "2026-01-01T08:00:30Z"
        row["source_lineage"].update(
            {
                "evidence_domain": "offchain_funding",
                "venue": "synthetic_exchange",
                "market_type": "funding",
                "source_identity_key": "synthetic_exchange:funding:BTCUSDT:USDT",
                "source_observed_at": "2026-01-01T08:00:00Z",
                "source_known_at": "2026-01-01T08:00:30Z",
                "funding_period_start": "2026-01-01T00:00:00Z",
                "funding_period_end": "2026-01-01T08:00:00Z",
                "settlement_state": "estimated",
            }
        )
        return row

    def _valid_onchain_mempool_row(self) -> dict[str, object]:
        row = self._valid_row()
        row["symbol"] = "BTC"
        row["venue_symbol"] = "BTC"
        row["normalized_symbol"] = "BTC/NATIVE"
        row["base_asset"] = "BTC"
        row["quote_asset"] = "NATIVE"
        row["venue"] = "synthetic_chain"
        row["market_type"] = "onchain_mempool"
        row["quote_currency"] = "NATIVE"
        row["source_lineage"].update(
            {
                "evidence_domain": "onchain_mempool",
                "venue": "synthetic_chain",
                "market_type": "onchain_mempool",
                "source_identity_key": "synthetic_chain:onchain_mempool:BTC:NATIVE",
                "chain_id": "synthetic-chain-1",
                "tx_hash": "0xsynthetictxhash",
                "mempool_observation_id": "mempool_obs_1",
                "mempool_state": "pending",
                "confirmed_in_block": False,
            }
        )
        return row
