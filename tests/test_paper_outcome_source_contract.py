from __future__ import annotations

from datetime import UTC, datetime

from backtest.research.paper_outcome_source_contract import (
    REQUIRED_SOURCE_FIELDS,
    build_paper_outcome_source_contract,
    validate_paper_outcome_source_contract,
)


def test_paper_outcome_source_contract_defines_sources_without_fetch() -> None:
    payload = build_paper_outcome_source_contract(generated_at=datetime(2026, 6, 2, tzinfo=UTC))

    assert payload["status"] == "PAPER_OUTCOME_SOURCE_CONTRACT_READY_DISABLED"
    assert payload["required_source_fields"] == REQUIRED_SOURCE_FIELDS
    assert payload["network_call_allowed"] is False
    assert payload["market_outcome_fetch_allowed_now"] is False
    assert payload["outcome_join_allowed_now"] is False
    assert payload["artifact_contract_violations"] == []
    assert validate_paper_outcome_source_contract(payload) == []


def test_paper_outcome_source_contract_rejects_synthetic_or_permission_drift() -> None:
    payload = build_paper_outcome_source_contract()
    payload["source_quality_requirements"]["network_fetch_for_join_allowed_now"] = True
    payload["source_quality_requirements"]["synthetic_outcome_price_allowed"] = True
    payload["outcome_payload_requirements"]["profit_or_edge_claim_allowed"] = True

    violations = validate_paper_outcome_source_contract(payload)

    assert "source_quality_requirements.network_fetch_for_join_allowed_now must be false" in violations
    assert "source_quality_requirements.synthetic_outcome_price_allowed must be false" in violations
    assert "outcome_payload_requirements.profit_or_edge_claim_allowed must be false" in violations
