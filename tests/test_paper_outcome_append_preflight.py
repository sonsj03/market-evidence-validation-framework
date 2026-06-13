from __future__ import annotations

from datetime import UTC, datetime

from backtest.research.paper_outcome_append_preflight import (
    build_paper_outcome_append_preflight,
    validate_paper_outcome_append_preflight,
)


def test_preflight_blocks_when_required_sources_are_not_materialized() -> None:
    payload = build_paper_outcome_append_preflight(_artifacts(), generated_at=datetime(2026, 6, 2, tzinfo=UTC))

    assert payload["status"] == "PAPER_OUTCOME_APPEND_PREFLIGHT_READY_WITH_BLOCKERS"
    assert payload["summary"]["paper_rows_total"] == 1
    assert payload["summary"]["rows_delay_elapsed"] == 1
    assert payload["summary"]["rows_with_source_mapping"] == 1
    assert payload["summary"]["rows_with_all_required_sources_materialized"] == 0
    assert payload["summary"]["rows_ready_for_future_manual_append_review"] == 0
    assert payload["summary"]["outcome_rows_written"] == 0
    assert payload["summary"]["original_rows_mutated"] == 0
    assert payload["summary"]["source_types_missing_or_guarded"] == 1
    assert payload["source_gap_summary"]["missing_or_guarded_source_types"] == ["LOCAL_FORWARD_OHLCV_ARCHIVE"]
    assert payload["source_gap_summary"]["rows_waiting_for_sources"] == 1
    assert payload["operator_next_sources"][0]["source_type"] == "LOCAL_FORWARD_OHLCV_ARCHIVE"
    assert payload["artifact_contract_violations"] == []
    assert validate_paper_outcome_append_preflight(payload) == []
    assert "required_source_not_materialized:LOCAL_FORWARD_OHLCV_ARCHIVE" in payload["row_preflights"][0]["row_blockers"]


def test_preflight_can_be_ready_disabled_when_delay_and_sources_pass() -> None:
    artifacts = _artifacts()
    artifacts["paper_outcome_source_materialization_audit"]["source_states"]["LOCAL_FORWARD_OHLCV_ARCHIVE"][
        "materialized_for_outcome_join_now"
    ] = True

    payload = build_paper_outcome_append_preflight(artifacts)

    assert payload["status"] == "PAPER_OUTCOME_APPEND_PREFLIGHT_READY_DISABLED"
    assert payload["summary"]["rows_ready_for_future_manual_append_review"] == 1
    assert payload["source_gap_summary"]["missing_or_guarded_source_types"] == []
    assert payload["outcome_row_append_allowed_now"] is False
    assert payload["outcome_join_allowed_now"] is False


def test_preflight_rejects_permission_drift() -> None:
    payload = build_paper_outcome_append_preflight(_artifacts())
    payload["outcome_row_append_allowed_now"] = True
    payload["summary"]["outcome_rows_written"] = 1

    violations = validate_paper_outcome_append_preflight(payload)

    assert "outcome_row_append_allowed_now must be false" in violations
    assert "summary.outcome_rows_written must be 0" in violations


def _artifacts() -> dict:
    return {
        "paper_ledger_audit": {
            "status": "PAPER_LEDGER_AUDIT_READY",
            "rows": [
                {
                    "paper_trade_id": "paper-lefu-test",
                    "strategy_id": "LEFU",
                    "virtual_decision": "WOULD_STAY_FLAT",
                    "row_valid_for_delayed_outcome_contract": True,
                }
            ],
        },
        "paper_outcome_append_row_schema": {"status": "PAPER_OUTCOME_APPEND_ROW_SCHEMA_READY_DISABLED"},
        "paper_outcome_source_mapping": {
            "status": "PAPER_OUTCOME_SOURCE_MAPPING_READY_DISABLED",
            "rows": [
                {
                    "paper_trade_id": "paper-lefu-test",
                    "required_source_types": ["LOCAL_FORWARD_OHLCV_ARCHIVE"],
                }
            ],
        },
        "paper_outcome_source_materialization_audit": {
            "type": "paper_outcome_source_materialization_audit",
            "status": "PAPER_OUTCOME_SOURCE_MATERIALIZATION_WAIT_FOR_LOCAL_SOURCES",
            "source_states": {
                "LOCAL_FORWARD_OHLCV_ARCHIVE": {
                    "materialized_for_outcome_join_now": False,
                }
            },
        },
        "paper_outcome_join_row_eligibility": {
            "status": "PAPER_OUTCOME_JOIN_ROW_ELIGIBILITY_READY_DISABLED",
            "rows": [
                {
                    "paper_trade_id": "paper-lefu-test",
                    "minimum_delay_elapsed": True,
                }
            ],
        },
    }
