from __future__ import annotations

from pathlib import Path

from backtest.research.paper_outcome_ledger_audit import build_paper_outcome_ledger_audit


def test_outcome_ledger_audit_accepts_missing_empty_ledger(tmp_path: Path) -> None:
    payload = build_paper_outcome_ledger_audit(outcome_ledger_path=tmp_path / "missing.jsonl")

    assert payload["status"] == "PAPER_OUTCOME_LEDGER_AUDIT_EMPTY_LEDGER"
    assert payload["summary"]["outcome_rows_total"] == 0
    assert payload["summary"]["original_paper_rows_mutated"] == 0
    assert payload["artifact_contract_violations"] == []


def test_outcome_ledger_audit_blocks_outcome_without_current_source_ref(tmp_path: Path) -> None:
    outcome = tmp_path / "paper_outcomes.jsonl"
    outcome.write_text(
        '{"outcome_row_id":"outcome_1","evidence_id":"outcome_1","paper_trade_id":"paper_1",'
        '"source_row_id":"source_missing","source_row_hash":"hash_missing",'
        '"known_at_ts":"2026-06-03T00:10:00+00:00","decision_ts":"2026-06-02T00:00:00+00:00",'
        '"outcome_recorded_at_ts":"2026-06-03T00:20:00+00:00",'
        '"permission_scope":{"outcome_join_allowed_now":false,"shadow_observe_allowed":false,'
        '"live_trading_allowed":false,"scanner_connection_allowed":false,"executor_connection_allowed":false},'
        '"artifact_hash":"sha256:abc"}\n',
        encoding="utf-8",
    )

    payload = build_paper_outcome_ledger_audit(
        outcome_ledger_path=outcome,
        source_ledger_path=tmp_path / "source_rows.jsonl",
    )

    assert payload["status"] == "PAPER_OUTCOME_LEDGER_AUDIT_BLOCKED"
    assert payload["summary"]["rows_with_missing_source_ref"] == 1
    assert "source_row_not_in_current_source_ledger" in payload["rows"][0]["row_violations"]


def test_outcome_ledger_audit_treats_older_row_as_superseded_by_newer_current_source_ref(tmp_path: Path) -> None:
    outcome = tmp_path / "paper_outcomes.jsonl"
    outcome.write_text(
        '{"outcome_row_id":"outcome_old","evidence_id":"outcome_old","paper_trade_id":"paper_1",'
        '"source_row_id":"source_1","source_row_hash":"sha256:old",'
        '"known_at_ts":"2026-06-03T00:10:00+00:00","decision_ts":"2026-06-02T00:00:00+00:00",'
        '"outcome_recorded_at_ts":"2026-06-03T00:20:00+00:00",'
        '"permission_scope":{"outcome_join_allowed_now":false,"shadow_observe_allowed":false,'
        '"live_trading_allowed":false,"scanner_connection_allowed":false,"executor_connection_allowed":false},'
        '"artifact_hash":"sha256:old"}\n'
        '{"outcome_row_id":"outcome_new","evidence_id":"outcome_new","paper_trade_id":"paper_1",'
        '"source_row_id":"source_1","source_row_hash":"sha256:new",'
        '"known_at_ts":"2026-06-03T00:10:00+00:00","decision_ts":"2026-06-02T00:00:00+00:00",'
        '"outcome_recorded_at_ts":"2026-06-03T00:20:00+00:00",'
        '"permission_scope":{"outcome_join_allowed_now":false,"shadow_observe_allowed":false,'
        '"live_trading_allowed":false,"scanner_connection_allowed":false,"executor_connection_allowed":false},'
        '"artifact_hash":"sha256:new"}\n',
        encoding="utf-8",
    )
    source = tmp_path / "source_rows.jsonl"
    source.write_text(
        '{"paper_trade_id":"paper_1","source_row_id":"source_1","source_row_hash":"sha256:new"}\n',
        encoding="utf-8",
    )

    payload = build_paper_outcome_ledger_audit(outcome_ledger_path=outcome, source_ledger_path=source)

    assert payload["summary"]["rows_with_missing_source_ref"] == 0
    assert payload["rows"][0]["superseded_by_correction"] is True
    assert "source_row_not_in_current_source_ledger" not in payload["rows"][0]["row_violations"]


def test_outcome_ledger_audit_reports_logical_duplicates_without_mutating_rows(tmp_path: Path) -> None:
    outcome = tmp_path / "paper_outcomes.jsonl"
    outcome.write_text(
        '{"outcome_row_id":"outcome_1","evidence_id":"outcome_1","paper_trade_id":"paper_1",'
        '"strategy_id":"LVOR","source_type":"OUTCOME_APPEND","schema_version":"unified_evidence_envelope_v1",'
        '"source_lineage":{"paper_trade_id":"paper_1","source_row_id":"source_1"},'
        '"source_row_id":"source_1","source_row_hash":"sha256:source",'
        '"known_at_ts":"2026-06-03T00:10:00+00:00","decision_ts":"2026-06-02T00:00:00+00:00",'
        '"outcome_recorded_at_ts":"2026-06-03T00:20:00+00:00",'
        '"permission_scope":{"source_write_allowed_now":false,"outcome_join_allowed_now":false,'
        '"outcome_row_append_allowed_now":false,"shadow_observe_allowed":false,"live_trading_allowed":false,'
        '"scanner_connection_allowed":false,"executor_connection_allowed":false},'
        '"artifact_hash":"sha256:one"}\n'
        '{"outcome_row_id":"outcome_2","evidence_id":"outcome_2","paper_trade_id":"paper_1",'
        '"strategy_id":"LVOR","source_type":"OUTCOME_APPEND","schema_version":"unified_evidence_envelope_v1",'
        '"source_lineage":{"paper_trade_id":"paper_1","source_row_id":"source_1"},'
        '"source_row_id":"source_1","source_row_hash":"sha256:source",'
        '"known_at_ts":"2026-06-03T00:10:00+00:00","decision_ts":"2026-06-02T00:00:00+00:00",'
        '"outcome_recorded_at_ts":"2026-06-03T00:20:00+00:00",'
        '"permission_scope":{"source_write_allowed_now":false,"outcome_join_allowed_now":false,'
        '"outcome_row_append_allowed_now":false,"shadow_observe_allowed":false,"live_trading_allowed":false,'
        '"scanner_connection_allowed":false,"executor_connection_allowed":false},'
        '"artifact_hash":"sha256:two"}\n',
        encoding="utf-8",
    )
    source = tmp_path / "source_rows.jsonl"
    source.write_text(
        '{"paper_trade_id":"paper_1","source_row_id":"source_1","source_row_hash":"sha256:source"}\n',
        encoding="utf-8",
    )

    payload = build_paper_outcome_ledger_audit(outcome_ledger_path=outcome, source_ledger_path=source)

    assert payload["status"] == "PAPER_OUTCOME_LEDGER_AUDIT_READY"
    assert payload["summary"]["outcome_rows_total"] == 2
    assert payload["summary"]["valid_unique_outcome_paper_trade_ids"] == 1
    assert payload["summary"]["valid_unique_outcome_source_refs"] == 1
    assert payload["summary"]["duplicate_logical_outcome_rows"] == 1
    assert payload["summary"]["original_paper_rows_mutated"] == 0
