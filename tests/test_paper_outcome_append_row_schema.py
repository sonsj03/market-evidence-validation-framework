from __future__ import annotations

from datetime import UTC, datetime

from backtest.research.paper_outcome_append_row_schema import (
    FORBIDDEN_OUTCOME_ROW_FIELDS,
    REQUIRED_OUTCOME_PAYLOAD_CONTRACT_FIELDS,
    REQUIRED_OUTCOME_ROW_FIELDS,
    build_paper_outcome_append_row_schema,
    validate_paper_outcome_append_row_schema,
)


def test_paper_outcome_append_row_schema_defines_disabled_append_only_contract() -> None:
    payload = build_paper_outcome_append_row_schema(generated_at=datetime(2026, 6, 2, tzinfo=UTC))

    assert payload["status"] == "PAPER_OUTCOME_APPEND_ROW_SCHEMA_READY_DISABLED"
    assert payload["required_outcome_row_fields"] == REQUIRED_OUTCOME_ROW_FIELDS
    assert payload["required_outcome_payload_contract_fields"] == REQUIRED_OUTCOME_PAYLOAD_CONTRACT_FIELDS
    assert set(FORBIDDEN_OUTCOME_ROW_FIELDS).issubset(set(payload["forbidden_outcome_row_fields"]))
    assert payload["outcome_join_allowed_now"] is False
    assert payload["outcome_row_append_allowed_now"] is False
    assert payload["original_row_mutation_allowed"] is False
    assert payload["summary"]["permission_opened_count"] == 0
    assert payload["artifact_contract_violations"] == []
    assert validate_paper_outcome_append_row_schema(payload) == []


def test_paper_outcome_append_row_schema_rejects_permission_and_forbidden_field_drift() -> None:
    payload = build_paper_outcome_append_row_schema()
    payload["outcome_row_append_allowed_now"] = True
    payload["summary"]["permission_opened_count"] = 1
    payload["payload_policy"]["profit_or_edge_claim_allowed"] = True
    payload["example_minimal_valid_row"]["pnl"] = 1.0

    violations = validate_paper_outcome_append_row_schema(payload)

    assert "outcome_row_append_allowed_now must be false" in violations
    assert "summary.permission_opened_count must be 0" in violations
    assert "payload_policy.profit_or_edge_claim_allowed must be false" in violations
    assert "example_minimal_valid_row must not include forbidden field pnl" in violations
