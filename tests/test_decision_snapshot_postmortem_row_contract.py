from __future__ import annotations

from backtest.research.decision_snapshot_postmortem_row_contract import (
    FORBIDDEN_POSTMORTEM_FIELDS,
    REQUIRED_POSTMORTEM_FIELDS,
    build_decision_snapshot_postmortem_row_contract,
    validate_decision_snapshot_postmortem_row_contract,
)


def test_builds_postmortem_row_contract_from_coverage_audit() -> None:
    payload = build_decision_snapshot_postmortem_row_contract(_fixture_coverage())

    assert payload["status"] == "DECISION_SNAPSHOT_POSTMORTEM_ROW_CONTRACT_READY_DISABLED"
    assert payload["shadow_observe_allowed"] is False
    assert payload["live_trading_allowed"] is False
    assert payload["scope"]["contract_only"] is True
    assert payload["scope"]["append_allowed_now"] is False
    assert payload["scope"]["postmortem_row_append_executed"] is False
    assert payload["scope"]["outcome_interpretation_scope"] == "observation_only"
    assert payload["postmortem_candidate_counts"]["total"] == 3
    assert payload["postmortem_candidate_counts"]["by_strategy"] == {"LEFU": 1, "LVOR": 2, "MQRF": 0}
    assert payload["summary"]["postmortem_ready_snapshot_count"] == 3
    assert payload["summary"]["append_allowed_now"] is False
    assert payload["summary"]["postmortem_rows_appended"] == 0
    assert payload["summary"]["confidence_increase_count"] == 0
    assert payload["summary"]["profit_or_edge_judgment_count"] == 0
    assert payload["artifact_contract_violations"] == []

    required = payload["row_schema_contract"]["required_fields"]
    forbidden = payload["row_schema_contract"]["forbidden_fields"]
    for field in REQUIRED_POSTMORTEM_FIELDS:
        assert field in required
    for field in FORBIDDEN_POSTMORTEM_FIELDS:
        assert field in forbidden
        assert field not in payload["example_row_shape"]

    assert payload["row_schema_contract"]["field_contract"]["favorable_movement"]["profit_or_edge_allowed"] is False
    assert "confidence_delta" in forbidden
    assert "profit" in forbidden
    assert "pnl" in forbidden
    assert "entry_order" in forbidden


def test_contract_rejects_append_confidence_and_profit_leaks() -> None:
    payload = build_decision_snapshot_postmortem_row_contract(_fixture_coverage())
    payload["scope"]["append_allowed_now"] = True
    payload["summary"]["confidence_increase_count"] = 1
    payload["example_row_shape"]["profit"] = 10

    violations = validate_decision_snapshot_postmortem_row_contract(payload)

    assert "scope.append_allowed_now must be false" in violations
    assert "summary.confidence_increase_count must be 0" in violations
    assert "example_row_shape must not include forbidden field profit" in violations


def test_contract_requires_candidate_counts_to_match() -> None:
    payload = build_decision_snapshot_postmortem_row_contract(_fixture_coverage())
    payload["postmortem_candidate_counts"]["by_strategy"]["MQRF"] = 9

    violations = validate_decision_snapshot_postmortem_row_contract(payload)

    assert "postmortem_candidate_counts.by_strategy must sum to total" in violations


def _fixture_coverage() -> dict:
    return {
        "status": "DECISION_SNAPSHOT_COVERAGE_AUDIT_READY",
        "summary": {
            "postmortem_ready_count": 3,
        },
        "strategy_coverage": {
            "LEFU": {"postmortem_ready_count": 1},
            "LVOR": {"postmortem_ready_count": 2},
            "MQRF": {"postmortem_ready_count": 0},
        },
    }
