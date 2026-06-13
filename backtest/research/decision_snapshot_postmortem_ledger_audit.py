"""Audit the append-only decision snapshot postmortem ledger."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.research.paper_evidence_loop_common import NO_EXECUTION_FLAGS, iso_now, read_json, read_jsonl, write_json


RESULTS = Path("backtest/results")
DEFAULT_OUT = RESULTS / "decision_snapshot_postmortem_ledger_audit_latest.json"
POSTMORTEM_LEDGER = RESULTS / "decision_postmortems" / "decision_snapshot_postmortem_rows.jsonl"
CONTRACT = RESULTS / "decision_snapshot_postmortem_row_contract_latest.json"

PROFIT_EDGE_CONFIDENCE_PROMOTION_FIELDS = {
    "profit",
    "pnl",
    "edge",
    "alpha",
    "sharpe",
    "win_rate",
    "expected_value",
    "confidence_delta",
    "confidence_upgrade",
    "confidence_update",
    "promotion_decision",
    "promotion_allowed",
    "profit_or_edge_judgment",
    "live_trade_decision",
}

PERMISSION_LEAK_FLAGS = {
    "append_allowed_now",
    "source_write_allowed_now",
    "outcome_join_allowed_now",
    "shadow_observe_allowed",
    "live_trading_allowed",
    "scanner_connection_allowed",
    "executor_connection_allowed",
    "stage4_entry_allowed",
    "strategy_execution_allowed",
    "promotion_allowed",
    "limited_live_allowed",
}


def build_decision_snapshot_postmortem_ledger_audit(
    *,
    contract: dict[str, Any] | None = None,
    ledger_rows: list[dict[str, Any]] | None = None,
    ledger_errors: list[str] | None = None,
    ledger_path: Path = POSTMORTEM_LEDGER,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    contract_payload = contract if contract is not None else read_json(CONTRACT)
    rows, read_errors = (ledger_rows, ledger_errors or []) if ledger_rows is not None else read_jsonl(ledger_path)
    required_fields = _string_list(_row_contract(contract_payload).get("required_fields"))
    forbidden_fields = _string_list(_row_contract(contract_payload).get("forbidden_fields"))
    postmortem_id_counts = Counter(_row_id(row, "postmortem_id") for row in rows if _row_id(row, "postmortem_id"))
    decision_id_counts = Counter(_row_id(row, "decision_id") for row in rows if _row_id(row, "decision_id"))
    duplicate_postmortem_ids = {item for item, count in postmortem_id_counts.items() if count > 1}
    duplicate_decision_ids = {item for item, count in decision_id_counts.items() if count > 1}

    audited_rows = [
        _audit_row(index, row, required_fields, forbidden_fields, duplicate_postmortem_ids, duplicate_decision_ids)
        for index, row in enumerate(rows, start=1)
    ]
    summary = _summary(audited_rows, rows, read_errors, duplicate_postmortem_ids, duplicate_decision_ids)
    payload: dict[str, Any] = {
        "type": "decision_snapshot_postmortem_ledger_audit",
        "schema_version": "decision_snapshot_postmortem_ledger_audit_v1",
        "generated_at": iso_now(generated_at),
        **NO_EXECUTION_FLAGS,
        "status": "DECISION_SNAPSHOT_POSTMORTEM_LEDGER_AUDIT_READY",
        "input_status": {
            "decision_snapshot_postmortem_row_contract": contract_payload.get("status"),
        },
        "ledger_path": str(ledger_path),
        "ledger_present": ledger_path.exists() if ledger_rows is None else True,
        "contract_required_fields": required_fields,
        "contract_forbidden_fields": forbidden_fields,
        "duplicate_postmortem_ids": sorted(duplicate_postmortem_ids),
        "duplicate_decision_ids": sorted(duplicate_decision_ids),
        "rows": audited_rows,
        "summary": summary,
        "ledger_read_errors": read_errors,
        "ref_audit_policy": {
            "decision_ref_required": True,
            "source_ref_required": True,
            "outcome_ref_required": True,
            "shadow_ref_required_by_current_row_contract": False,
            "missing_shadow_ref_is_audit_gap_not_row_invalid": True,
        },
        "operator_summary_ko": (
            "append-only decision snapshot postmortem ledger를 읽기 전용으로 감사했습니다. "
            "required/forbidden field, 중복 id, 참조 누락, 권한 누수, profit/edge/confidence/promotion "
            "관련 필드를 검사했으며 원본 ledger는 수정하지 않았습니다."
        ),
        "artifact_contract_violations": [],
    }
    payload["artifact_contract_violations"] = validate_decision_snapshot_postmortem_ledger_audit(payload)
    if payload["artifact_contract_violations"] or read_errors:
        payload["status"] = "DECISION_SNAPSHOT_POSTMORTEM_LEDGER_AUDIT_CONTRACT_BLOCKED"
    return payload


def validate_decision_snapshot_postmortem_ledger_audit(payload: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if payload.get("type") != "decision_snapshot_postmortem_ledger_audit":
        violations.append("type must be decision_snapshot_postmortem_ledger_audit")
    if payload.get("schema_version") != "decision_snapshot_postmortem_ledger_audit_v1":
        violations.append("schema_version must be decision_snapshot_postmortem_ledger_audit_v1")
    for flag, expected in NO_EXECUTION_FLAGS.items():
        if payload.get(flag) is not expected:
            violations.append(f"{flag} must be {str(expected).lower()}")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
    if summary.get("ledger_rows_total") != len(rows):
        violations.append("summary.ledger_rows_total must match rows")
    if summary.get("valid_rows") != sum(1 for row in rows if isinstance(row, dict) and row.get("row_valid") is True):
        violations.append("summary.valid_rows must match rows")
    if summary.get("invalid_rows") != sum(1 for row in rows if isinstance(row, dict) and row.get("row_valid") is False):
        violations.append("summary.invalid_rows must match rows")
    for key in ("original_ledgers_mutated", "confidence_increase_count", "profit_or_edge_judgment_count", "permission_opened_count"):
        if summary.get(key) != 0:
            violations.append(f"summary.{key} must be 0")
    if summary.get("shadow_live_scanner_executor_connected") is not False:
        violations.append("summary.shadow_live_scanner_executor_connected must be false")
    if summary.get("permission_leak_count") != sum(len(_list_value(row.get("permission_leaks"))) for row in rows if isinstance(row, dict)):
        violations.append("summary.permission_leak_count must match rows")
    if summary.get("forbidden_field_count") != sum(len(_list_value(row.get("forbidden_fields_present"))) for row in rows if isinstance(row, dict)):
        violations.append("summary.forbidden_field_count must match rows")
    if summary.get("missing_ref_count") != sum(len(_list_value(row.get("missing_refs"))) for row in rows if isinstance(row, dict)):
        violations.append("summary.missing_ref_count must match rows")
    for row in rows:
        if not isinstance(row, dict):
            violations.append("audit row must be object")
            continue
        if row.get("row_valid") is True and row.get("hard_violations"):
            violations.append(f"{row.get('postmortem_id', 'UNKNOWN')}.valid row must not have hard violations")
        if row.get("permission_leaks"):
            violations.append(f"{row.get('postmortem_id', 'UNKNOWN')}.permission leak must stay blocked")
    return violations


def write_decision_snapshot_postmortem_ledger_audit(out_json: Path = DEFAULT_OUT, *, ledger_path: Path = POSTMORTEM_LEDGER) -> dict[str, Any]:
    payload = build_decision_snapshot_postmortem_ledger_audit(ledger_path=ledger_path)
    write_json(out_json, payload)
    return payload


def _audit_row(
    index: int,
    row: dict[str, Any],
    required_fields: list[str],
    forbidden_fields: list[str],
    duplicate_postmortem_ids: set[str],
    duplicate_decision_ids: set[str],
) -> dict[str, Any]:
    postmortem_id = _row_id(row, "postmortem_id")
    decision_id = _row_id(row, "decision_id")
    required_missing = [field for field in required_fields if field not in row or row.get(field) in (None, "")]
    forbidden_present = [field for field in forbidden_fields if field in row]
    duplicate_violations = []
    if postmortem_id in duplicate_postmortem_ids:
        duplicate_violations.append("duplicate_postmortem_id")
    if decision_id in duplicate_decision_ids:
        duplicate_violations.append("duplicate_decision_id")
    missing_refs = _missing_refs(row)
    hard_ref_violations = [ref for ref in missing_refs if ref != "shadow_ref"]
    permission_leaks = _permission_leaks(row)
    semantic_fields = _profit_edge_confidence_promotion_fields(row)
    hard_violations = (
        [f"required_field_missing:{field}" for field in required_missing]
        + [f"forbidden_field_present:{field}" for field in forbidden_present]
        + duplicate_violations
        + [f"missing_ref:{ref}" for ref in hard_ref_violations]
        + [f"permission_leak:{field}" for field in permission_leaks]
        + [f"profit_edge_confidence_promotion_field:{field}" for field in semantic_fields]
    )
    return {
        "line_number": index,
        "postmortem_id": postmortem_id,
        "decision_id": decision_id,
        "paper_trade_id": _row_id(row, "paper_trade_id"),
        "strategy_id": _row_id(row, "strategy_id"),
        "required_missing_fields": required_missing,
        "forbidden_fields_present": forbidden_present,
        "duplicate_violations": duplicate_violations,
        "missing_refs": missing_refs,
        "hard_ref_violations": hard_ref_violations,
        "permission_leaks": permission_leaks,
        "profit_edge_confidence_promotion_fields": semantic_fields,
        "hard_violations": hard_violations,
        "row_valid": not hard_violations,
    }


def _summary(
    audited_rows: list[dict[str, Any]],
    raw_rows: list[dict[str, Any]],
    read_errors: list[str],
    duplicate_postmortem_ids: set[str],
    duplicate_decision_ids: set[str],
) -> dict[str, Any]:
    return {
        "ledger_rows_total": len(raw_rows),
        "valid_rows": sum(1 for row in audited_rows if row["row_valid"]),
        "invalid_rows": sum(1 for row in audited_rows if not row["row_valid"]),
        "duplicate_postmortem_id_count": len(duplicate_postmortem_ids),
        "duplicate_decision_id_count": len(duplicate_decision_ids),
        "missing_ref_count": sum(len(row["missing_refs"]) for row in audited_rows),
        "permission_leak_count": sum(len(row["permission_leaks"]) for row in audited_rows),
        "forbidden_field_count": sum(len(row["forbidden_fields_present"]) for row in audited_rows),
        "profit_edge_confidence_promotion_field_count": sum(len(row["profit_edge_confidence_promotion_fields"]) for row in audited_rows),
        "ledger_read_error_count": len(read_errors),
        "original_ledgers_mutated": 0,
        "confidence_increase_count": 0,
        "profit_or_edge_judgment_count": 0,
        "permission_opened_count": 0,
        "shadow_live_scanner_executor_connected": False,
    }


def _missing_refs(row: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not row.get("decision_id"):
        missing.append("decision_ref")
    outcome_ref = row.get("observation_only_outcome_ref")
    if not isinstance(outcome_ref, dict) or not outcome_ref.get("outcome_row_id"):
        missing.append("outcome_ref")
    if not isinstance(outcome_ref, dict) or not outcome_ref.get("source_row_id"):
        missing.append("source_ref")
    if not row.get("shadow_ref") and not row.get("shadow_refs"):
        missing.append("shadow_ref")
    return missing


def _permission_leaks(row: dict[str, Any]) -> list[str]:
    leaks = [field for field in sorted(PERMISSION_LEAK_FLAGS) if row.get(field) is True]
    if row.get("original_ledgers_mutated") not in (None, 0, False):
        leaks.append("original_ledgers_mutated")
    return leaks


def _profit_edge_confidence_promotion_fields(row: dict[str, Any]) -> list[str]:
    fields: list[str] = []
    for field in sorted(PROFIT_EDGE_CONFIDENCE_PROMOTION_FIELDS):
        if field not in row:
            continue
        value = row.get(field)
        if field in {"confidence_update", "profit_or_edge_judgment", "promotion_allowed"}:
            if value is True:
                fields.append(field)
        else:
            fields.append(field)
    return fields


def _row_contract(contract: dict[str, Any]) -> dict[str, Any]:
    value = contract.get("row_schema_contract")
    return value if isinstance(value, dict) else {}


def _row_id(row: dict[str, Any], field: str) -> str:
    value = row.get(field)
    return str(value) if value not in (None, "") else ""


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value if item] if isinstance(value, list) else []


def _list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit decision snapshot postmortem append-only ledger.")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT))
    parser.add_argument("--ledger-path", default=str(POSTMORTEM_LEDGER))
    args = parser.parse_args()
    payload = write_decision_snapshot_postmortem_ledger_audit(Path(args.out_json), ledger_path=Path(args.ledger_path))
    summary = payload["summary"]
    print(
        f"status={payload['status']} rows={summary['ledger_rows_total']} valid={summary['valid_rows']} "
        f"invalid={summary['invalid_rows']} duplicate_postmortem_ids={summary['duplicate_postmortem_id_count']} "
        f"duplicate_decision_ids={summary['duplicate_decision_id_count']} missing_refs={summary['missing_ref_count']} "
        f"permission_leaks={summary['permission_leak_count']} forbidden_fields={summary['forbidden_field_count']} "
        f"violations={len(payload['artifact_contract_violations'])}"
    )
    return 0 if not payload["artifact_contract_violations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
