from __future__ import annotations

import json
from pathlib import Path

from backtest.research.base_outcome_append_row_dry_run_builder import (
    build_base_outcome_append_row_dry_run_builder,
)


def test_base_outcome_append_row_dry_run_builder_makes_schema_shaped_rows_without_appending(tmp_path: Path) -> None:
    source_ledger = tmp_path / "source_rows.jsonl"
    source_ledger.write_text(
        json.dumps(
            {
                "paper_trade_id": "paper_1",
                "strategy_id": "LVOR",
                "source_payload_ref": "public_ohlcv://binance/perp/BTC/USDT/1m/window",
                "source_type": "PUBLIC_EXCHANGE_OHLCV_ONE_SHOT",
                "source_row_hash": "sha256:source",
                "source_row_id": "source_1",
                "archive_written_ts": "2026-06-05T00:10:00+00:00",
                "artifact_created_at": "2026-06-05T00:10:00+00:00",
                "outcome_window_start_ts": "2026-06-04T00:00:00+00:00",
                "outcome_window_end_ts": "2026-06-05T00:00:00+00:00",
                "open": 100.0,
                "high": 110.0,
                "low": 90.0,
                "close": 105.0,
                "volume": 123.0,
                "bars_count": 1441,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = build_base_outcome_append_row_dry_run_builder(
        gate={
            "status": "BASE_OUTCOME_MANUAL_REVIEW_GATE_READY",
            "rows": [
                {
                    "paper_trade_id": "paper_1",
                    "strategy_id": "LVOR",
                    "base_outcome_review_candidate": True,
                }
            ],
        },
        paper_ledger_audit={
            "rows": [
                {
                    "paper_trade_id": "paper_1",
                    "strategy_id": "LVOR",
                    "lineage_hash": "sha256:paper",
                    "replay_decision_ts": "2026-06-04T00:00:00+00:00",
                    "max_holding_window": "24h",
                }
            ]
        },
        source_ledger_audit={"status": "OHLCV_SOURCE_LEDGER_AUDIT_READY"},
        schema={"status": "PAPER_OUTCOME_APPEND_ROW_SCHEMA_READY_DISABLED"},
        source_ledger_path=source_ledger,
    )

    assert payload["status"] == "BASE_OUTCOME_APPEND_ROW_DRY_RUN_READY"
    assert payload["summary"]["dry_run_rows"] == 1
    assert payload["summary"]["dry_run_shape_valid_rows"] == 1
    assert payload["summary"]["outcome_rows_appended"] == 0
    assert payload["summary"]["outcome_join_executed"] is False
    row = payload["dry_run_rows"][0]
    assert row["record_type"] == "PAPER_OUTCOME_APPEND_DRY_RUN"
    assert row["dry_run_only"] is True
    assert row["append_allowed_now"] is False
    assert row["outcome_payload_contract"]["no_profit_claim"] is True
    assert row["outcome_payload_contract"]["no_edge_claim"] is True
    assert payload["artifact_contract_violations"] == []


def test_base_outcome_append_row_dry_run_builder_supersedes_latest_active_correction(tmp_path: Path) -> None:
    source_ledger = tmp_path / "source_rows.jsonl"
    source_ledger.write_text(
        json.dumps(
            {
                "paper_trade_id": "paper_1",
                "strategy_id": "LVOR",
                "source_payload_ref": "public_ohlcv://binance/perp/BTC/USDT/1m/window",
                "source_type": "PUBLIC_EXCHANGE_OHLCV_ONE_SHOT",
                "source_row_hash": "sha256:new-source",
                "source_row_id": "source_1",
                "archive_written_ts": "2026-06-05T00:10:00+00:00",
                "artifact_created_at": "2026-06-05T00:10:00+00:00",
                "outcome_window_start_ts": "2026-06-04T00:00:00+00:00",
                "outcome_window_end_ts": "2026-06-05T00:00:00+00:00",
                "open": 100.0,
                "high": 110.0,
                "low": 90.0,
                "close": 105.0,
                "volume": 123.0,
                "bars_count": 1441,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    outcome_ledger = tmp_path / "paper_outcomes.jsonl"
    outcome_ledger.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "paper_trade_id": "paper_1",
                        "outcome_row_id": "old_outcome",
                        "source_row_id": "source_1",
                        "source_row_hash": "sha256:old-source",
                    }
                ),
                json.dumps(
                    {
                        "paper_trade_id": "paper_1",
                        "outcome_row_id": "old_correction",
                        "source_row_id": "source_1",
                        "source_row_hash": "sha256:stale-correction-source",
                        "supersedes_outcome_row_id": "old_outcome",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    payload = build_base_outcome_append_row_dry_run_builder(
        gate={
            "status": "BASE_OUTCOME_MANUAL_REVIEW_GATE_READY",
            "rows": [
                {
                    "paper_trade_id": "paper_1",
                    "strategy_id": "LVOR",
                    "base_outcome_review_candidate": True,
                }
            ],
        },
        paper_ledger_audit={
            "rows": [
                {
                    "paper_trade_id": "paper_1",
                    "strategy_id": "LVOR",
                    "lineage_hash": "sha256:paper",
                    "replay_decision_ts": "2026-06-04T00:00:00+00:00",
                    "max_holding_window": "24h",
                }
            ]
        },
        source_ledger_audit={"status": "OHLCV_SOURCE_LEDGER_AUDIT_READY"},
        schema={"status": "PAPER_OUTCOME_APPEND_ROW_SCHEMA_READY_DISABLED"},
        source_ledger_path=source_ledger,
        outcome_ledger_path=outcome_ledger,
    )

    row = payload["dry_run_rows"][0]
    assert row["correction_reason"] == "source_ref_repair_current_ledger"
    assert row["supersedes_outcome_row_id"] == "old_correction"
