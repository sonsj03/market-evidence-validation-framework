from __future__ import annotations

from pathlib import Path

from backtest.research.base_outcome_append_preflight import build_base_outcome_append_preflight


def test_base_outcome_append_preflight_passes_approved_dry_run_rows(tmp_path: Path) -> None:
    source_ledger = tmp_path / "source_rows.jsonl"
    source_ledger.write_text('{"paper_trade_id":"paper_1","source_row_id":"source_1","source_row_hash":"hash_1"}\n', encoding="utf-8")
    payload = build_base_outcome_append_preflight(
        dry_run={
            "dry_run_rows": [
                {
                    "paper_trade_id": "paper_1",
                    "source_row_id": "source_1",
                    "source_row_hash": "hash_1",
                    "outcome_row_id": "outcome_1",
                    "dry_run_only": True,
                    "append_allowed_now": False,
                }
            ]
        },
        approval={
            "status": "BASE_OUTCOME_MANUAL_APPROVAL_RECORD_APPROVED",
            "approved_rows": [{"paper_trade_id": "paper_1", "outcome_row_id": "outcome_1"}],
        },
        outcome_ledger_path=tmp_path / "paper_outcomes.jsonl",
        source_ledger_path=source_ledger,
    )

    assert payload["status"] == "BASE_OUTCOME_APPEND_PREFLIGHT_READY"
    assert payload["summary"]["preflight_passed_rows"] == 1
    assert payload["summary"]["append_execution_review_ready"] is True
    assert payload["summary"]["outcome_rows_appended"] == 0
    assert payload["artifact_contract_violations"] == []


def test_base_outcome_append_preflight_blocks_existing_outcome_id(tmp_path: Path) -> None:
    ledger = tmp_path / "paper_outcomes.jsonl"
    ledger.write_text('{"outcome_row_id":"outcome_1"}\n', encoding="utf-8")
    source_ledger = tmp_path / "source_rows.jsonl"
    source_ledger.write_text('{"paper_trade_id":"paper_1","source_row_id":"source_1","source_row_hash":"hash_1"}\n', encoding="utf-8")

    payload = build_base_outcome_append_preflight(
        dry_run={
            "dry_run_rows": [
                {
                    "paper_trade_id": "paper_1",
                    "source_row_id": "source_1",
                    "source_row_hash": "hash_1",
                    "outcome_row_id": "outcome_1",
                    "dry_run_only": True,
                    "append_allowed_now": False,
                }
            ]
        },
        approval={"approved_rows": [{"outcome_row_id": "outcome_1"}]},
        outcome_ledger_path=ledger,
        source_ledger_path=source_ledger,
    )

    assert payload["status"] == "BASE_OUTCOME_APPEND_PREFLIGHT_BLOCKED"
    assert payload["rows"][0]["blockers"] == ["outcome_row_already_exists"]


def test_base_outcome_append_preflight_blocks_source_ref_missing(tmp_path: Path) -> None:
    payload = build_base_outcome_append_preflight(
        dry_run={
            "dry_run_rows": [
                {
                    "paper_trade_id": "paper_1",
                    "source_row_id": "source_missing",
                    "source_row_hash": "hash_missing",
                    "outcome_row_id": "outcome_1",
                    "dry_run_only": True,
                    "append_allowed_now": False,
                }
            ]
        },
        approval={"approved_rows": [{"outcome_row_id": "outcome_1"}]},
        outcome_ledger_path=tmp_path / "paper_outcomes.jsonl",
        source_ledger_path=tmp_path / "source_rows.jsonl",
    )

    assert payload["status"] == "BASE_OUTCOME_APPEND_PREFLIGHT_BLOCKED"
    assert payload["rows"][0]["blockers"] == ["source_row_not_in_current_source_ledger"]
