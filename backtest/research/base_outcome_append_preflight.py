"""Preflight approved base outcome append rows before writing JSONL."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.research.ohlcv_capture_disabled_runtime_writer import SOURCE_LEDGER
from backtest.research.paper_evidence_loop_common import NO_EXECUTION_FLAGS, OUTCOME_LEDGER_PATH, iso_now, read_json, read_jsonl, write_json


RESULTS = Path("backtest/results")
DEFAULT_OUT = RESULTS / "base_outcome_append_preflight_latest.json"
DRY_RUN = RESULTS / "base_outcome_append_row_dry_run_builder_latest.json"
APPROVAL = RESULTS / "base_outcome_manual_approval_record_latest.json"
LINKAGE_LEDGER = RESULTS / "ohlcv_capture" / "ohlcv_window_source_reuse_linkages.jsonl"


def build_base_outcome_append_preflight(
    *,
    dry_run: dict[str, Any] | None = None,
    approval: dict[str, Any] | None = None,
    outcome_ledger_path: Path = OUTCOME_LEDGER_PATH,
    source_ledger_path: Path = SOURCE_LEDGER,
    linkage_ledger_path: Path = LINKAGE_LEDGER,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    dry_run = dry_run if dry_run is not None else read_json(DRY_RUN)
    approval = approval if approval is not None else read_json(APPROVAL)
    outcome_rows, read_errors = read_jsonl(outcome_ledger_path)
    source_rows, source_read_errors = read_jsonl(source_ledger_path)
    linkage_rows, linkage_read_errors = read_jsonl(linkage_ledger_path)
    existing_ids = {str(row.get("outcome_row_id") or "") for row in outcome_rows if isinstance(row, dict)}
    source_refs = _source_refs(source_rows, linkage_rows)
    approved_ids = {str(row.get("outcome_row_id") or "") for row in approval.get("approved_rows", []) if isinstance(row, dict)}
    dry_rows = dry_run.get("dry_run_rows") if isinstance(dry_run.get("dry_run_rows"), list) else []
    rows = [_row(row, approved_ids, existing_ids, source_refs) for row in dry_rows if isinstance(row, dict)]
    passed = [row for row in rows if row["preflight_passed"]]
    payload: dict[str, Any] = {
        "type": "base_outcome_append_preflight",
        "schema_version": "base_outcome_append_preflight_v1",
        "generated_at": iso_now(generated_at),
        **NO_EXECUTION_FLAGS,
        "status": "BASE_OUTCOME_APPEND_PREFLIGHT_READY" if passed else "BASE_OUTCOME_APPEND_PREFLIGHT_BLOCKED",
        "dry_run_status": dry_run.get("status"),
        "approval_status": approval.get("status"),
        "outcome_ledger_path": str(outcome_ledger_path),
        "source_ledger_path": str(source_ledger_path),
        "linkage_ledger_path": str(linkage_ledger_path),
        "rows": rows,
        "summary": {
            "dry_run_rows_seen": len(dry_rows),
            "approved_outcome_ids": len(approved_ids),
            "preflight_passed_rows": len(passed),
            "duplicate_existing_outcome_rows": sum(1 for row in rows if "outcome_row_already_exists" in row["blockers"]),
            "outcome_ledger_parse_errors": len(read_errors),
            "source_ledger_parse_errors": len(source_read_errors),
            "linkage_ledger_parse_errors": len(linkage_read_errors),
            "source_refs_missing_rows": sum(1 for row in rows if "source_row_not_in_current_source_ledger" in row["blockers"]),
            "append_execution_review_ready": bool(passed) and len(passed) == len(dry_rows) and not read_errors and not source_read_errors and not linkage_read_errors,
            "outcome_rows_appended": 0,
            "outcome_join_executed": False,
            "permission_opened_count": 0,
        },
        "read_errors": read_errors,
        "source_read_errors": source_read_errors,
        "operator_summary_ko": f"승인된 base outcome row {len(passed)}개가 append 직전 검사를 통과했습니다. 아직 outcome ledger에는 쓰지 않았습니다.",
        "recommended_next_action": "RUN_BASE_OUTCOME_APPEND_ONLY_WRITER_ONCE_IF_OPERATOR_APPROVES_PREFLIGHT",
        "artifact_contract_violations": [],
    }
    payload["artifact_contract_violations"] = validate_base_outcome_append_preflight(payload)
    if payload["artifact_contract_violations"]:
        payload["status"] = "BASE_OUTCOME_APPEND_PREFLIGHT_CONTRACT_BLOCKED"
    return payload


def validate_base_outcome_append_preflight(payload: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if payload.get("type") != "base_outcome_append_preflight":
        violations.append("type must be base_outcome_append_preflight")
    for flag, expected in NO_EXECUTION_FLAGS.items():
        if payload.get(flag) is not expected:
            violations.append(f"{flag} must be {str(expected).lower()}")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    if summary.get("outcome_rows_appended") != 0:
        violations.append("summary.outcome_rows_appended must be 0")
    if summary.get("outcome_join_executed") is not False:
        violations.append("summary.outcome_join_executed must be false")
    if summary.get("permission_opened_count") != 0:
        violations.append("summary.permission_opened_count must be 0")
    return violations


def write_base_outcome_append_preflight(out_json: Path = DEFAULT_OUT) -> dict[str, Any]:
    payload = build_base_outcome_append_preflight()
    write_json(out_json, payload)
    return payload


def _row(row: dict[str, Any], approved_ids: set[str], existing_ids: set[str], source_refs: set[tuple[str, str, str]]) -> dict[str, Any]:
    outcome_id = str(row.get("outcome_row_id") or "")
    source_ref = (
        str(row.get("paper_trade_id") or ""),
        str(row.get("source_row_id") or ""),
        str(row.get("source_row_hash") or ""),
    )
    blockers = []
    if outcome_id not in approved_ids:
        blockers.append("outcome_row_not_approved")
    if outcome_id in existing_ids:
        blockers.append("outcome_row_already_exists")
    if source_ref not in source_refs:
        blockers.append("source_row_not_in_current_source_ledger")
    if row.get("dry_run_only") is not True:
        blockers.append("dry_run_only_missing")
    if row.get("append_allowed_now") is not False:
        blockers.append("dry_run_append_flag_not_false")
    return {
        "paper_trade_id": row.get("paper_trade_id"),
        "source_row_id": row.get("source_row_id"),
        "outcome_row_id": outcome_id,
        "preflight_passed": not blockers,
        "blockers": blockers,
    }


def _source_refs(rows: list[dict[str, Any]], linkage_rows: list[dict[str, Any]] | None = None) -> set[tuple[str, str, str]]:
    refs: set[tuple[str, str, str]] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        refs.add(
            (
                str(row.get("paper_trade_id") or ""),
                str(row.get("source_row_id") or ""),
                str(row.get("source_row_hash") or ""),
            )
        )
    source_by_id = {str(row.get("source_row_id") or ""): row for row in rows if isinstance(row, dict) and row.get("source_row_id")}
    for row in linkage_rows or []:
        if not isinstance(row, dict):
            continue
        source = source_by_id.get(str(row.get("source_row_id") or ""))
        if not source:
            continue
        if str(source.get("source_row_hash") or "") != str(row.get("source_row_hash") or ""):
            continue
        refs.add(
            (
                str(row.get("target_paper_trade_id") or ""),
                str(row.get("source_row_id") or ""),
                str(row.get("source_row_hash") or ""),
            )
        )
    return refs


def main() -> int:
    parser = argparse.ArgumentParser(description="Build base outcome append preflight.")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    payload = write_base_outcome_append_preflight(Path(args.out_json))
    print(
        f"status={payload['status']} passed={payload['summary']['preflight_passed_rows']} "
        f"violations={len(payload['artifact_contract_violations'])}"
    )
    return 0 if not payload["artifact_contract_violations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
