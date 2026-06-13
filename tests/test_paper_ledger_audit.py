from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from backtest.research.low_confidence_paper_trade_writer import build_example_paper_trade_row_from_schema
from backtest.research.paper_ledger_audit import build_paper_ledger_audit, validate_paper_ledger_audit


def test_paper_ledger_audit_empty_missing_ledger_is_valid_wait_state(tmp_path: Path) -> None:
    payload = build_paper_ledger_audit(
        ledger_path=tmp_path / "missing.jsonl",
        generated_at=datetime(2026, 6, 2, tzinfo=UTC),
    )

    assert payload["status"] == "PAPER_LEDGER_AUDIT_EMPTY_LEDGER"
    assert payload["empty_ledger_ok"] is True
    assert payload["summary"]["rows_total"] == 0
    assert payload["summary"]["permission_opened_count"] == 0
    assert payload["outcome_join_allowed_now"] is False
    assert payload["artifact_contract_violations"] == []
    assert validate_paper_ledger_audit(payload) == []


def test_paper_ledger_audit_accepts_valid_rows(tmp_path: Path) -> None:
    ledger = tmp_path / "paper.jsonl"
    row = build_example_paper_trade_row_from_schema("LEFU")
    row.update(
        {
            "exchange": "binance",
            "market_type": "perp",
            "replay_decision_ts": row["recorded_at_ts"],
            "outcome_window_start_ts": row["recorded_at_ts"],
            "outcome_window_end_ts": "2026-06-02T00:00:00+00:00",
            "required_outcome_source_types": ["FUNDING", "OHLCV"],
            "source_selection_hints": {"exchange": "binance"},
            "known_at_snapshot_hash": "sha256:" + "0" * 64,
            "blocker_snapshot_hash": "sha256:" + "1" * 64,
            "source_mode": "CURRENT_ARTIFACT_CONTEXT",
        }
    )
    ledger.write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")

    payload = build_paper_ledger_audit(ledger_path=ledger)

    assert payload["status"] == "PAPER_LEDGER_AUDIT_READY"
    assert payload["summary"]["rows_total"] == 1
    assert payload["summary"]["schema_violation_rows"] == 0
    assert payload["rows"][0]["row_valid_for_delayed_outcome_contract"] is True
    assert payload["rows"][0]["symbol"] == "BTC/USDT"
    assert payload["rows"][0]["exchange"] == "binance"
    assert payload["rows"][0]["market_type"] == "perp"
    assert payload["rows"][0]["replay_decision_ts"] == row["recorded_at_ts"]
    assert payload["rows"][0]["outcome_window_start_ts"] == row["recorded_at_ts"]
    assert payload["rows"][0]["required_outcome_source_types"] == ["FUNDING", "OHLCV"]
    assert payload["rows"][0]["source_selection_hints"] == {"exchange": "binance"}
    assert payload["rows"][0]["known_at_snapshot_hash"].startswith("sha256:")
    assert payload["rows"][0]["blocker_snapshot_hash"].startswith("sha256:")
    assert payload["rows"][0]["source_mode"] == "CURRENT_ARTIFACT_CONTEXT"
    assert payload["rows"][0]["max_holding_window"] == "24h"
    assert payload["rows"][0]["decision_ts"] == row["recorded_at_ts"]


def test_paper_ledger_audit_blocks_duplicate_permission_real_order_and_outcome(tmp_path: Path) -> None:
    ledger = tmp_path / "paper.jsonl"
    row1 = build_example_paper_trade_row_from_schema("LVOR")
    row2 = dict(row1)
    row2["no_execution_flags"] = dict(row1["no_execution_flags"])
    row2["no_execution_flags"]["shadow_observe_allowed"] = True
    row2["real_order_id"] = "real-1"
    row2["outcome_return_pct"] = 1.23
    ledger.write_text(
        json.dumps(row1, sort_keys=True) + "\n" + json.dumps(row2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    payload = build_paper_ledger_audit(ledger_path=ledger)

    assert payload["status"] == "PAPER_LEDGER_AUDIT_BLOCKED"
    assert payload["summary"]["duplicate_paper_trade_id_rows"] == 2
    assert payload["summary"]["permission_leak_rows"] == 1
    assert payload["summary"]["real_order_leak_rows"] == 1
    assert payload["summary"]["outcome_contamination_rows"] == 1
    assert "shadow_observe_allowed" in payload["rows"][1]["permission_leaks"]
    assert "real_order_id" in payload["rows"][1]["real_order_field_leaks"]
    assert "outcome_return_pct" in payload["rows"][1]["outcome_contamination"]


def test_paper_ledger_audit_reports_invalid_json(tmp_path: Path) -> None:
    ledger = tmp_path / "paper.jsonl"
    ledger.write_text('{"paper_trade_id": "x"}\nnot-json\n', encoding="utf-8")

    payload = build_paper_ledger_audit(ledger_path=ledger)

    assert payload["status"] == "PAPER_LEDGER_AUDIT_BLOCKED"
    assert payload["summary"]["invalid_json_rows"] == 1
    assert payload["read_errors"][0].startswith("line 2: invalid json")
