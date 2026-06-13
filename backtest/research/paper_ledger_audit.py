"""Audit low-confidence paper trade ledger rows.

This read-only audit inspects the dedicated append-only JSONL ledger, validates
each row against the low-confidence virtual trade schema, and reports duplicate
paper_trade_id, execution-permission leaks, real-order fields, and outcome
contamination. It does not append, mutate, join outcomes, or open shadow/live
permissions.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backtest.research.low_confidence_paper_trade_writer import validate_paper_trade_row_before_append
from backtest.research.paper_writer_enablement_contract import PAPER_LEDGER_PATH


RESULTS = Path("backtest/results")
DEFAULT_OUT = RESULTS / "paper_ledger_audit_latest.json"
DEFAULT_LEDGER = PAPER_LEDGER_PATH

NO_EXECUTION_FLAGS = {
    "research_only": True,
    "read_only": True,
    "collection_trigger_allowed": False,
    "network_call_allowed": False,
    "strategy_execution_allowed": False,
    "scanner_connection_allowed": False,
    "executor_connection_allowed": False,
    "stage4_entry_allowed": False,
    "preliminary_replay_allowed": False,
    "historical_preliminary_replay_allowed_now": False,
    "shadow_observe_allowed": False,
    "promotion_allowed": False,
    "limited_live_allowed": False,
    "live_trading_allowed": False,
    "cost_adjusted_replay_allowed": False,
    "edge_evidence_allowed": False,
    "profit_forecast_allowed": False,
    "threshold_optimization_allowed": False,
    "real_order_intent_allowed": False,
    "outcome_join_allowed_now": False,
    "ledger_mutation_allowed": False,
}

FORBIDDEN_ROW_FLAGS = (
    "real_order_intent_allowed",
    "scanner_connection_allowed",
    "executor_connection_allowed",
    "stage4_entry_allowed",
    "replay_candidate",
    "shadow_observe_allowed",
    "limited_live_allowed",
    "live_trading_allowed",
    "cost_adjusted_replay_allowed",
    "outcome_join_allowed_now",
)

OUTCOME_CONTAMINATION_KEYS = (
    "outcome",
    "outcome_ts",
    "outcome_price",
    "outcome_return",
    "outcome_return_pct",
    "pnl",
    "pnl_pct",
    "profit",
    "edge",
    "win_loss",
)


def build_paper_ledger_audit(
    *,
    ledger_path: Path = DEFAULT_LEDGER,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    loaded_rows, read_errors = _read_jsonl_rows(ledger_path)
    duplicate_ids = _duplicate_ids(loaded_rows)
    row_audits = [
        _audit_row(line_number, row, duplicate_ids)
        for line_number, row in loaded_rows
        if isinstance(row, dict)
    ]
    invalid_json_count = sum(1 for error in read_errors if error.startswith("line "))
    schema_violation_count = sum(1 for row in row_audits if row["schema_violations"])
    duplicate_row_count = sum(1 for row in row_audits if row["duplicate_paper_trade_id"])
    permission_leak_count = sum(1 for row in row_audits if row["permission_leaks"])
    real_order_leak_count = sum(1 for row in row_audits if row["real_order_field_leaks"])
    outcome_contamination_count = sum(1 for row in row_audits if row["outcome_contamination"])
    missing_lineage_hash_count = sum(1 for row in row_audits if not row["lineage_hash_present"])
    missing_known_at_ref_count = sum(1 for row in row_audits if not row["known_at_snapshot_ref_present"])
    missing_blocker_snapshot_count = sum(1 for row in row_audits if not row["blocker_snapshot_present"])
    ledger_present = ledger_path.exists()
    status = "PAPER_LEDGER_AUDIT_EMPTY_LEDGER"
    if read_errors or schema_violation_count or duplicate_row_count or permission_leak_count or real_order_leak_count or outcome_contamination_count:
        status = "PAPER_LEDGER_AUDIT_BLOCKED"
    elif row_audits:
        status = "PAPER_LEDGER_AUDIT_READY"

    payload: dict[str, Any] = {
        "type": "paper_ledger_audit",
        "schema_version": "paper_ledger_audit_v1",
        "generated_at": (generated_at or datetime.now(UTC)).astimezone(UTC).isoformat(),
        **NO_EXECUTION_FLAGS,
        "status": status,
        "ledger_path": str(ledger_path),
        "ledger_present": ledger_present,
        "empty_ledger_ok": not ledger_present or not row_audits,
        "rows": row_audits,
        "read_errors": read_errors,
        "summary": {
            "ledger_present": ledger_present,
            "rows_total": len(row_audits),
            "invalid_json_rows": invalid_json_count,
            "schema_violation_rows": schema_violation_count,
            "duplicate_paper_trade_id_rows": duplicate_row_count,
            "permission_leak_rows": permission_leak_count,
            "real_order_leak_rows": real_order_leak_count,
            "outcome_contamination_rows": outcome_contamination_count,
            "missing_lineage_hash_rows": missing_lineage_hash_count,
            "missing_known_at_snapshot_ref_rows": missing_known_at_ref_count,
            "missing_blocker_snapshot_rows": missing_blocker_snapshot_count,
            "valid_rows": sum(1 for row in row_audits if row["row_valid_for_delayed_outcome_contract"]),
            "invalid_rows": sum(1 for row in row_audits if not row["row_valid_for_delayed_outcome_contract"]),
            "outcome_join_allowed_now": False,
            "permission_opened_count": 0,
        },
        "operator_summary_ko": (
            "paper ledger가 없거나 비어 있으면 정상 대기 상태입니다. row가 있으면 schema, duplicate id, "
            "실주문 필드, outcome 오염, no-execution flag leak만 검사합니다."
        ),
        "recommended_next_action": "BUILD_OUTCOME_JOIN_DELAYED_CONTRACT",
        "artifact_contract_violations": [],
    }
    payload["artifact_contract_violations"] = validate_paper_ledger_audit(payload)
    if payload["artifact_contract_violations"]:
        payload["status"] = "PAPER_LEDGER_AUDIT_BLOCKED"
    return payload


def validate_paper_ledger_audit(payload: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if payload.get("type") != "paper_ledger_audit":
        violations.append("type must be paper_ledger_audit")
    if payload.get("schema_version") != "paper_ledger_audit_v1":
        violations.append("schema_version must be paper_ledger_audit_v1")
    if payload.get("status") not in {"PAPER_LEDGER_AUDIT_EMPTY_LEDGER", "PAPER_LEDGER_AUDIT_READY", "PAPER_LEDGER_AUDIT_BLOCKED"}:
        violations.append("status must be a known paper ledger audit status")
    for flag, expected in NO_EXECUTION_FLAGS.items():
        if payload.get(flag) is not expected:
            violations.append(f"{flag} must be {str(expected).lower()}")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        violations.append("rows must be list")
        rows = []
    for row in rows:
        if not isinstance(row, dict):
            violations.append("row audit must be object")
            continue
        if not isinstance(row.get("schema_violations"), list):
            violations.append("row.schema_violations must be list")
        if not isinstance(row.get("permission_leaks"), list):
            violations.append("row.permission_leaks must be list")
        if not isinstance(row.get("outcome_contamination"), list):
            violations.append("row.outcome_contamination must be list")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    expected_zero_flags = {
        "outcome_join_allowed_now": False,
        "permission_opened_count": 0,
    }
    for key, expected in expected_zero_flags.items():
        if summary.get(key) != expected:
            violations.append(f"summary.{key} must be {expected}")
    if "private secret config" in json.dumps(payload, ensure_ascii=True, sort_keys=True).lower():
        violations.append("artifact must not reference private secret config")
    return violations


def write_paper_ledger_audit(
    out_json: Path = DEFAULT_OUT,
    *,
    ledger_path: Path = DEFAULT_LEDGER,
) -> dict[str, Any]:
    payload = build_paper_ledger_audit(ledger_path=ledger_path)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _read_jsonl_rows(path: Path) -> tuple[list[tuple[int, Any]], list[str]]:
    if not path.exists():
        return [], []
    rows: list[tuple[int, Any]] = []
    errors: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append((line_number, json.loads(line)))
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_number}: invalid json: {exc.msg}")
    return rows, errors


def _duplicate_ids(rows: list[tuple[int, Any]]) -> set[str]:
    counts: dict[str, int] = {}
    for _, row in rows:
        if isinstance(row, dict):
            paper_trade_id = str(row.get("paper_trade_id") or "")
            if paper_trade_id:
                counts[paper_trade_id] = counts.get(paper_trade_id, 0) + 1
    return {paper_trade_id for paper_trade_id, count in counts.items() if count > 1}


def _audit_row(line_number: int, row: dict[str, Any], duplicate_ids: set[str]) -> dict[str, Any]:
    paper_trade_id = str(row.get("paper_trade_id") or "")
    schema_violations = validate_paper_trade_row_before_append(row)
    flags = row.get("no_execution_flags") if isinstance(row.get("no_execution_flags"), dict) else {}
    permission_leaks = [key for key in FORBIDDEN_ROW_FLAGS if flags.get(key) is not False]
    real_order_field_leaks = [key for key in ("real_order_id", "order_id", "exchange_order_id") if key in row and row.get(key) is not None]
    outcome_contamination = [key for key in OUTCOME_CONTAMINATION_KEYS if key in row and row.get(key) is not None]
    return {
        "line_number": line_number,
        "paper_trade_id": paper_trade_id,
        "strategy_id": row.get("strategy_id"),
        "symbol": row.get("symbol"),
        "exchange": row.get("exchange"),
        "market_type": row.get("market_type"),
        "recorded_at_ts": row.get("recorded_at_ts"),
        "decision_ts": row.get("decision_ts") or row.get("replay_decision_ts") or row.get("recorded_at_ts"),
        "replay_decision_ts": row.get("replay_decision_ts") or row.get("decision_ts") or row.get("recorded_at_ts"),
        "known_at_ts": row.get("known_at_ts") or row.get("recorded_at_ts"),
        "known_at_snapshot_ref": row.get("known_at_snapshot_ref"),
        "known_at_snapshot_hash": row.get("known_at_snapshot_hash"),
        "blocker_snapshot_hash": row.get("blocker_snapshot_hash"),
        "lineage_hash": row.get("lineage_hash"),
        "max_holding_window": row.get("max_holding_window"),
        "outcome_window_start_ts": row.get("outcome_window_start_ts"),
        "outcome_window_end_ts": row.get("outcome_window_end_ts"),
        "required_outcome_source_types": row.get("required_outcome_source_types"),
        "source_selection_hints": row.get("source_selection_hints"),
        "source_mode": row.get("source_mode") or (row.get("blocker_snapshot") or {}).get("source_mode") if isinstance(row.get("blocker_snapshot"), dict) else row.get("source_mode"),
        "virtual_exit_plan": row.get("virtual_exit_plan"),
        "feature_snapshot_hash": row.get("feature_snapshot_hash"),
        "virtual_decision": row.get("virtual_decision"),
        "virtual_side": row.get("virtual_side"),
        "schema_violations": sorted(set(schema_violations)),
        "duplicate_paper_trade_id": paper_trade_id in duplicate_ids,
        "lineage_hash_present": str(row.get("lineage_hash") or "").startswith("sha256:"),
        "known_at_snapshot_ref_present": bool(row.get("known_at_snapshot_ref")),
        "blocker_snapshot_present": isinstance(row.get("blocker_snapshot"), dict),
        "no_execution_flags_all_false": not permission_leaks,
        "permission_leaks": permission_leaks,
        "real_order_field_leaks": real_order_field_leaks,
        "outcome_contamination": outcome_contamination,
        "row_valid_for_delayed_outcome_contract": (
            not schema_violations
            and paper_trade_id not in duplicate_ids
            and not permission_leaks
            and not real_order_field_leaks
            and not outcome_contamination
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the low-confidence paper trade JSONL ledger.")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT))
    parser.add_argument("--ledger-path", default=str(DEFAULT_LEDGER))
    args = parser.parse_args()
    payload = write_paper_ledger_audit(Path(args.out_json), ledger_path=Path(args.ledger_path))
    summary = payload["summary"]
    print(
        f"status={payload['status']} rows={summary['rows_total']} "
        f"schema_violations={summary['schema_violation_rows']} duplicates={summary['duplicate_paper_trade_id_rows']} "
        f"permission_leaks={summary['permission_leak_rows']} outcome_contamination={summary['outcome_contamination_rows']}"
    )
    return 0 if not payload["artifact_contract_violations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
