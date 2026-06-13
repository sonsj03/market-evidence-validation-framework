from __future__ import annotations

from backtest.research.decision_snapshot_postmortem_ledger_audit import (
    build_decision_snapshot_postmortem_ledger_audit,
    validate_decision_snapshot_postmortem_ledger_audit,
)


def test_ledger_audit_accepts_contract_valid_rows_with_shadow_gap() -> None:
    payload = build_decision_snapshot_postmortem_ledger_audit(
        contract=_fixture_contract(),
        ledger_rows=[
            _row("pm-1", "decision-1", "paper-1", "LEFU"),
            _row("pm-2", "decision-2", "paper-2", "LVOR"),
        ],
    )

    assert payload["summary"]["ledger_rows_total"] == 2
    assert payload["summary"]["valid_rows"] == 2
    assert payload["summary"]["invalid_rows"] == 0
    assert payload["summary"]["duplicate_postmortem_id_count"] == 0
    assert payload["summary"]["duplicate_decision_id_count"] == 0
    assert payload["summary"]["missing_ref_count"] == 2
    assert payload["summary"]["permission_leak_count"] == 0
    assert payload["summary"]["forbidden_field_count"] == 0
    assert payload["artifact_contract_violations"] == []
    assert all(row["missing_refs"] == ["shadow_ref"] for row in payload["rows"])


def test_ledger_audit_blocks_duplicates_forbidden_fields_and_permission_leaks() -> None:
    row_1 = _row("pm-1", "decision-1", "paper-1", "LEFU")
    row_1["profit"] = 12.3
    row_1["append_allowed_now"] = True
    row_1["confidence_update"] = True
    row_2 = _row("pm-1", "decision-1", "paper-2", "MQRF")

    payload = build_decision_snapshot_postmortem_ledger_audit(
        contract=_fixture_contract(),
        ledger_rows=[row_1, row_2],
    )

    assert payload["summary"]["valid_rows"] == 0
    assert payload["summary"]["invalid_rows"] == 2
    assert payload["summary"]["duplicate_postmortem_id_count"] == 1
    assert payload["summary"]["duplicate_decision_id_count"] == 1
    assert payload["summary"]["permission_leak_count"] == 1
    assert payload["summary"]["forbidden_field_count"] == 1
    assert payload["summary"]["profit_edge_confidence_promotion_field_count"] == 2
    assert "profit" in payload["rows"][0]["forbidden_fields_present"]
    assert "append_allowed_now" in payload["rows"][0]["permission_leaks"]
    assert "confidence_update" in payload["rows"][0]["profit_edge_confidence_promotion_fields"]
    assert payload["artifact_contract_violations"]


def test_ledger_audit_detects_missing_required_and_core_refs() -> None:
    row = _row("pm-1", "decision-1", "paper-1", "LEFU")
    row.pop("reviewer")
    row["observation_only_outcome_ref"] = {"outcome_row_id": "outcome-1"}

    payload = build_decision_snapshot_postmortem_ledger_audit(
        contract=_fixture_contract(),
        ledger_rows=[row],
    )

    assert payload["summary"]["valid_rows"] == 0
    assert payload["summary"]["invalid_rows"] == 1
    assert payload["summary"]["missing_ref_count"] == 2
    assert "reviewer" in payload["rows"][0]["required_missing_fields"]
    assert "source_ref" in payload["rows"][0]["hard_ref_violations"]
    assert "shadow_ref" in payload["rows"][0]["missing_refs"]


def test_contract_validator_rejects_summary_mismatch_and_execution_flags() -> None:
    payload = build_decision_snapshot_postmortem_ledger_audit(
        contract=_fixture_contract(),
        ledger_rows=[_row("pm-1", "decision-1", "paper-1", "LEFU")],
    )
    payload["summary"]["valid_rows"] = 99
    payload["summary"]["original_ledgers_mutated"] = 1
    payload["live_trading_allowed"] = True

    violations = validate_decision_snapshot_postmortem_ledger_audit(payload)

    assert "summary.valid_rows must match rows" in violations
    assert "summary.original_ledgers_mutated must be 0" in violations
    assert "live_trading_allowed must be false" in violations


def _fixture_contract() -> dict:
    return {
        "status": "DECISION_SNAPSHOT_POSTMORTEM_ROW_CONTRACT_READY_DISABLED",
        "row_schema_contract": {
            "required_fields": [
                "postmortem_id",
                "decision_id",
                "paper_trade_id",
                "strategy_id",
                "observation_only_outcome_ref",
                "favorable_movement",
                "adverse_movement",
                "missing_context_relevance",
                "blocker_relevance",
                "decision_replayability",
                "repeated_failure_pattern_candidate",
                "reviewer",
                "reviewed_at",
            ],
            "forbidden_fields": [
                "profit",
                "pnl",
                "edge",
                "confidence_delta",
                "confidence_upgrade",
                "promotion_decision",
                "live_trade_decision",
            ],
        },
    }


def _row(postmortem_id: str, decision_id: str, paper_trade_id: str, strategy_id: str) -> dict:
    return {
        "postmortem_id": postmortem_id,
        "decision_id": decision_id,
        "paper_trade_id": paper_trade_id,
        "strategy_id": strategy_id,
        "observation_only_outcome_ref": {
            "outcome_row_id": f"outcome-{paper_trade_id}",
            "source_row_id": f"source-{paper_trade_id}",
        },
        "favorable_movement": "NOT_REVIEWED",
        "adverse_movement": "NOT_REVIEWED",
        "missing_context_relevance": "POSSIBLY_RELEVANT",
        "blocker_relevance": "NOT_RELEVANT",
        "decision_replayability": "REPLAYABLE",
        "repeated_failure_pattern_candidate": "NOT_REVIEWED",
        "reviewer": "dry_run_builder",
        "reviewed_at": "DRY_RUN_NOT_REVIEWED",
        "append_allowed_now": False,
        "profit_or_edge_judgment": False,
        "confidence_update": False,
        "original_ledgers_mutated": 0,
    }
