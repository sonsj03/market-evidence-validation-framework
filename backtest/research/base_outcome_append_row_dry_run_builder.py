"""Build dry-run append-only base outcome rows without writing them."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.research.ohlcv_capture_disabled_runtime_writer import SOURCE_LEDGER
from backtest.research.paper_evidence_loop_common import OUTCOME_LEDGER_PATH, hash_payload, iso_now, read_json, read_jsonl, write_json
from backtest.research.paper_outcome_append_row_schema import (
    FORBIDDEN_OUTCOME_ROW_FIELDS,
    NO_EXECUTION_FLAGS as SCHEMA_NO_EXECUTION_FLAGS,
    REQUIRED_OUTCOME_PAYLOAD_CONTRACT_FIELDS,
    REQUIRED_OUTCOME_ROW_FIELDS,
)


RESULTS = Path("backtest/results")
DEFAULT_OUT = RESULTS / "base_outcome_append_row_dry_run_builder_latest.json"
GATE = RESULTS / "base_outcome_manual_review_gate_latest.json"
PAPER_LEDGER_AUDIT = RESULTS / "paper_ledger_audit_latest.json"
SOURCE_LEDGER_AUDIT = RESULTS / "ohlcv_source_ledger_audit_latest.json"
SCHEMA = RESULTS / "paper_outcome_append_row_schema_latest.json"
LINKAGE_LEDGER = RESULTS / "ohlcv_capture" / "ohlcv_window_source_reuse_linkages.jsonl"

NO_EXECUTION_FLAGS = {
    "research_only": True,
    "read_only": True,
    "collection_trigger_allowed": False,
    "network_call_allowed": False,
    "market_outcome_fetch_allowed_now": False,
    "source_write_allowed_now": False,
    "strategy_execution_allowed": False,
    "scanner_connection_allowed": False,
    "executor_connection_allowed": False,
    "stage4_entry_allowed": False,
    "shadow_observe_allowed": False,
    "promotion_allowed": False,
    "limited_live_allowed": False,
    "live_trading_allowed": False,
    "cost_adjusted_replay_allowed": False,
    "edge_evidence_allowed": False,
    "profit_forecast_allowed": False,
    "threshold_optimization_allowed": False,
    "outcome_join_allowed_now": False,
    "outcome_row_append_allowed_now": False,
}


def build_base_outcome_append_row_dry_run_builder(
    *,
    gate: dict[str, Any] | None = None,
    paper_ledger_audit: dict[str, Any] | None = None,
    source_ledger_audit: dict[str, Any] | None = None,
    schema: dict[str, Any] | None = None,
    source_ledger_path: Path = SOURCE_LEDGER,
    linkage_ledger_path: Path = LINKAGE_LEDGER,
    outcome_ledger_path: Path = OUTCOME_LEDGER_PATH,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    gate = gate if gate is not None else read_json(GATE)
    paper_ledger_audit = paper_ledger_audit if paper_ledger_audit is not None else read_json(PAPER_LEDGER_AUDIT)
    source_ledger_audit = source_ledger_audit if source_ledger_audit is not None else read_json(SOURCE_LEDGER_AUDIT)
    schema = schema if schema is not None else read_json(SCHEMA)
    source_rows, source_errors = read_jsonl(source_ledger_path)
    linkage_rows, linkage_errors = read_jsonl(linkage_ledger_path)
    outcome_rows, outcome_errors = read_jsonl(outcome_ledger_path)
    source_by_id = _source_by_paper_trade_id(source_rows, linkage_rows)
    existing_outcome_by_paper = _existing_outcome_by_paper_trade_id(outcome_rows)
    paper_by_id = _by_paper_trade_id(paper_ledger_audit.get("rows"))
    gate_rows = gate.get("rows") if isinstance(gate.get("rows"), list) else []
    candidates = [row for row in gate_rows if isinstance(row, dict) and row.get("base_outcome_review_candidate") is True]
    dry_run_rows = [
        _build_row(candidate, paper_by_id, source_by_id, existing_outcome_by_paper, generated_at)
        for candidate in candidates
    ]
    shape_valid_rows = sum(1 for row in dry_run_rows if _row_shape_violations(row) == [])
    payload: dict[str, Any] = {
        "type": "base_outcome_append_row_dry_run_builder",
        "schema_version": "base_outcome_append_row_dry_run_builder_v1",
        "generated_at": iso_now(generated_at),
        **NO_EXECUTION_FLAGS,
        "status": "BASE_OUTCOME_APPEND_ROW_DRY_RUN_READY" if dry_run_rows else "BASE_OUTCOME_APPEND_ROW_DRY_RUN_WAIT_FOR_REVIEW_CANDIDATES",
        "gate_status": gate.get("status"),
        "source_ledger_status": source_ledger_audit.get("status"),
        "schema_status": schema.get("status"),
        "source_ledger_path": str(source_ledger_path),
        "linkage_ledger_path": str(linkage_ledger_path),
        "outcome_ledger_path": str(outcome_ledger_path),
        "dry_run_rows": dry_run_rows,
        "row_shape_violations": {row.get("paper_trade_id", ""): _row_shape_violations(row) for row in dry_run_rows},
        "source_ledger_errors": source_errors,
        "summary": {
            "base_review_candidate_rows": len(candidates),
            "dry_run_rows": len(dry_run_rows),
            "dry_run_shape_valid_rows": shape_valid_rows,
            "source_ledger_parse_errors": len(source_errors),
            "linkage_ledger_parse_errors": len(linkage_errors),
            "outcome_ledger_parse_errors": len(outcome_errors),
            "missing_source_rows": sum(1 for row in dry_run_rows if row.get("_missing_source_row") is True),
            "missing_paper_rows": sum(1 for row in dry_run_rows if row.get("_missing_paper_row") is True),
            "correction_rows": sum(1 for row in dry_run_rows if row.get("supersedes_outcome_row_id")),
            "outcome_rows_written": 0,
            "outcome_rows_appended": 0,
            "outcome_join_executed": False,
            "permission_opened_count": 0,
        },
        "operator_summary_ko": (
            f"base outcome 후보 {len(dry_run_rows)}개의 append row 형식을 dry-run으로 만들었습니다. "
            "실제 outcome ledger에는 아무것도 쓰지 않았습니다."
        ),
        "recommended_next_action": "REVIEW_BASE_OUTCOME_DRY_RUN_ROWS_BEFORE_ANY_APPEND_ONLY_OUTCOME_WRITER",
        "artifact_contract_violations": [],
    }
    payload["artifact_contract_violations"] = validate_base_outcome_append_row_dry_run_builder(payload)
    if payload["artifact_contract_violations"]:
        payload["status"] = "BASE_OUTCOME_APPEND_ROW_DRY_RUN_CONTRACT_BLOCKED"
    return payload


def validate_base_outcome_append_row_dry_run_builder(payload: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if payload.get("type") != "base_outcome_append_row_dry_run_builder":
        violations.append("type must be base_outcome_append_row_dry_run_builder")
    if payload.get("schema_version") != "base_outcome_append_row_dry_run_builder_v1":
        violations.append("schema_version must be base_outcome_append_row_dry_run_builder_v1")
    for flag, expected in NO_EXECUTION_FLAGS.items():
        if payload.get(flag) is not expected:
            violations.append(f"{flag} must be {str(expected).lower()}")
    rows = payload.get("dry_run_rows")
    if not isinstance(rows, list):
        violations.append("dry_run_rows must be list")
        rows = []
    for row in rows:
        if not isinstance(row, dict):
            violations.append("dry_run_row must be object")
            continue
        violations.extend(_row_shape_violations(row))
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    if summary.get("outcome_rows_written") != 0:
        violations.append("summary.outcome_rows_written must be 0")
    if summary.get("outcome_rows_appended") != 0:
        violations.append("summary.outcome_rows_appended must be 0")
    if summary.get("outcome_join_executed") is not False:
        violations.append("summary.outcome_join_executed must be false")
    if summary.get("permission_opened_count") != 0:
        violations.append("summary.permission_opened_count must be 0")
    return sorted(set(violations))


def write_base_outcome_append_row_dry_run_builder(out_json: Path = DEFAULT_OUT) -> dict[str, Any]:
    payload = build_base_outcome_append_row_dry_run_builder()
    write_json(out_json, payload)
    return payload


def _build_row(
    candidate: dict[str, Any],
    paper_by_id: dict[str, dict[str, Any]],
    source_by_id: dict[str, dict[str, Any]],
    existing_outcome_by_paper: dict[str, dict[str, Any]],
    generated_at: datetime | None,
) -> dict[str, Any]:
    paper_trade_id = str(candidate.get("paper_trade_id") or "")
    paper = paper_by_id.get(paper_trade_id, {})
    source = source_by_id.get(paper_trade_id, {})
    existing_outcome = existing_outcome_by_paper.get(paper_trade_id, {})
    supersedes_outcome_row_id = _superseded_outcome_id(existing_outcome, source)
    payload_contract = {
        "observed_price_ref": source.get("source_payload_ref") or source.get("source_url_or_endpoint_id") or "",
        "observed_window_start_ts": source.get("outcome_window_start_ts") or paper.get("outcome_window_start_ts") or "",
        "observed_window_end_ts": source.get("outcome_window_end_ts") or paper.get("outcome_window_end_ts") or "",
        "source_type": source.get("source_type") or "PUBLIC_EXCHANGE_OHLCV_ONE_SHOT",
        "source_trust_level": "FORWARD_LOCAL_APPEND_ONLY",
        "outcome_interpretation": "OBSERVATION_ONLY_BASE_OHLCV",
        "no_profit_claim": True,
        "no_edge_claim": True,
        "no_threshold_update": True,
    }
    payload_hash = hash_payload(payload_contract)
    outcome_row = {
        "outcome_row_id": "base-outcome-dry-run-" + hash_payload({"paper_trade_id": paper_trade_id, "source_row_hash": source.get("source_row_hash")})[-16:],
        "record_type": "PAPER_OUTCOME_APPEND_DRY_RUN",
        "paper_trade_id": paper_trade_id,
        "strategy_id": paper.get("strategy_id") or source.get("strategy_id") or candidate.get("strategy_id") or "",
        "original_lineage_hash": paper.get("lineage_hash") or source.get("lineage_hash") or "",
        "outcome_recorded_at_ts": iso_now(generated_at),
        "outcome_window": paper.get("max_holding_window") or "24h",
        "outcome_source_ref": source.get("source_payload_ref") or "",
        "join_candidate_ts": source.get("archive_written_ts") or source.get("artifact_created_at") or "",
        "replay_decision_ts": paper.get("replay_decision_ts") or paper.get("decision_ts") or paper.get("recorded_at_ts") or "",
        "known_at_boundary_ts": source.get("archive_written_ts") or source.get("artifact_created_at") or "",
        "correction_reason": "source_ref_repair_current_ledger" if supersedes_outcome_row_id else "dry_run_base_ohlcv_outcome_shape_only",
        "supersedes_outcome_row_id": supersedes_outcome_row_id,
        "outcome_payload_hash": payload_hash,
        "outcome_payload_contract": payload_contract,
        "no_execution_flags": {
            "real_order_intent_allowed": False,
            "scanner_connection_allowed": False,
            "executor_connection_allowed": False,
            "stage4_entry_allowed": False,
            "shadow_observe_allowed": False,
            "limited_live_allowed": False,
            "live_trading_allowed": False,
            "cost_adjusted_replay_allowed": False,
            "outcome_join_allowed_now": False,
        },
        "dry_run_only": True,
        "append_allowed_now": False,
        "source_row_hash": source.get("source_row_hash") or "",
        "source_row_id": source.get("source_row_id") or "",
        "source_ohlcv_summary": {
            "open": source.get("open"),
            "high": source.get("high"),
            "low": source.get("low"),
            "close": source.get("close"),
            "volume": source.get("volume"),
            "bars_count": source.get("bars_count"),
        },
        "_missing_source_row": not bool(source),
        "_missing_paper_row": not bool(paper),
    }
    return outcome_row


def _row_shape_violations(row: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    for field in REQUIRED_OUTCOME_ROW_FIELDS:
        if field not in row:
            violations.append(f"missing_required_field:{field}")
    for field in FORBIDDEN_OUTCOME_ROW_FIELDS:
        if field in row:
            violations.append(f"forbidden_field_present:{field}")
    contract = row.get("outcome_payload_contract") if isinstance(row.get("outcome_payload_contract"), dict) else {}
    for field in REQUIRED_OUTCOME_PAYLOAD_CONTRACT_FIELDS:
        if field not in contract:
            violations.append(f"missing_payload_contract_field:{field}")
    for key, expected in SCHEMA_NO_EXECUTION_FLAGS.items():
        if key in {"read_only_contract", "original_row_mutation_allowed"}:
            continue
        if row.get("no_execution_flags", {}).get(key) is True and expected is False:
            violations.append(f"no_execution_flags.{key} must not be true")
    if row.get("dry_run_only") is not True:
        violations.append("dry_run_only must be true")
    if row.get("append_allowed_now") is not False:
        violations.append("append_allowed_now must be false")
    if row.get("_missing_source_row") is True:
        violations.append("source_row_missing")
    if row.get("_missing_paper_row") is True:
        violations.append("paper_row_missing")
    return sorted(set(violations))


def _by_paper_trade_id(rows: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("paper_trade_id"):
                out[str(row["paper_trade_id"])] = row
    return out


def _source_by_paper_trade_id(source_rows: list[dict[str, Any]], linkage_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out = _by_paper_trade_id(source_rows)
    source_by_row_id = {str(row.get("source_row_id") or ""): row for row in source_rows if isinstance(row, dict) and row.get("source_row_id")}
    for linkage in linkage_rows:
        if not isinstance(linkage, dict):
            continue
        target = str(linkage.get("target_paper_trade_id") or "")
        source = source_by_row_id.get(str(linkage.get("source_row_id") or ""))
        if not target or not source or target in out:
            continue
        if str(source.get("source_row_hash") or "") != str(linkage.get("source_row_hash") or ""):
            continue
        synthetic = dict(source)
        synthetic["paper_trade_id"] = target
        synthetic["strategy_id"] = linkage.get("strategy_id") or synthetic.get("strategy_id")
        synthetic["source_lineage_mode"] = "WINDOW_LEVEL_REUSE_EXPLICIT_LINKAGE"
        synthetic["window_source_id"] = linkage.get("window_source_id")
        synthetic["source_owner_paper_trade_id"] = linkage.get("source_owner_paper_trade_id")
        out[target] = synthetic
    return out


def _existing_outcome_by_paper_trade_id(rows: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    superseded = _superseded_outcome_ids(rows)
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict) or not row.get("paper_trade_id"):
                continue
            outcome_id = str(row.get("outcome_row_id") or row.get("evidence_id") or "")
            if outcome_id in superseded:
                continue
            out[str(row["paper_trade_id"])] = row
    return out


def _superseded_outcome_ids(rows: Any) -> set[str]:
    ids: set[str] = set()
    if not isinstance(rows, list):
        return ids
    for row in rows:
        if isinstance(row, dict) and row.get("supersedes_outcome_row_id"):
            ids.add(str(row["supersedes_outcome_row_id"]))
    return ids


def _superseded_outcome_id(existing_outcome: dict[str, Any], source: dict[str, Any]) -> str | None:
    if not existing_outcome or not source:
        return None
    existing_ref = (
        str(existing_outcome.get("source_row_id") or ""),
        str(existing_outcome.get("source_row_hash") or ""),
    )
    source_ref = (
        str(source.get("source_row_id") or ""),
        str(source.get("source_row_hash") or ""),
    )
    if existing_ref == source_ref:
        return None
    outcome_id = str(existing_outcome.get("outcome_row_id") or existing_outcome.get("evidence_id") or "")
    return outcome_id or None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build base outcome append row dry-run artifact.")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    payload = write_base_outcome_append_row_dry_run_builder(Path(args.out_json))
    print(
        f"status={payload['status']} dry_run_rows={payload['summary']['dry_run_rows']} "
        f"shape_valid={payload['summary']['dry_run_shape_valid_rows']} violations={len(payload['artifact_contract_violations'])}"
    )
    return 0 if not payload["artifact_contract_violations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
