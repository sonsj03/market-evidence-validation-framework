"""Audit append-only paper outcome ledger rows."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.research.ohlcv_capture_disabled_runtime_writer import SOURCE_LEDGER
from backtest.research.paper_evidence_loop_common import NO_EXECUTION_FLAGS, OUTCOME_LEDGER_PATH, iso_now, parse_ts, read_jsonl, write_json
from backtest.research.unified_evidence_envelope_contract import REQUIRED_ENVELOPE_FIELDS, validate_evidence_envelope


DEFAULT_OUT = Path("backtest/results/paper_outcome_ledger_audit_latest.json")
LINKAGE_LEDGER = Path("backtest/results/ohlcv_capture/ohlcv_window_source_reuse_linkages.jsonl")


def build_paper_outcome_ledger_audit(
    *,
    outcome_ledger_path: Path = OUTCOME_LEDGER_PATH,
    source_ledger_path: Path = SOURCE_LEDGER,
    linkage_ledger_path: Path = LINKAGE_LEDGER,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    rows, read_errors = read_jsonl(outcome_ledger_path)
    source_rows, source_read_errors = read_jsonl(source_ledger_path)
    linkage_rows, linkage_read_errors = read_jsonl(linkage_ledger_path)
    source_refs = _source_refs(source_rows, linkage_rows)
    source_ids = _source_ids(source_rows, linkage_rows)
    duplicate_ids = _duplicates([str(row.get("outcome_row_id") or row.get("evidence_id") or "") for row in rows])
    superseded_ids = _superseded_ids(rows, source_refs, source_ids)
    audits = [_audit_row(row, duplicate_ids, source_refs, source_ids, superseded_ids) for row in rows]
    valid_unique_paper_ids = _valid_unique_paper_trade_ids(audits)
    valid_unique_source_refs = _valid_unique_source_refs(audits)
    status = "PAPER_OUTCOME_LEDGER_AUDIT_EMPTY_LEDGER"
    if read_errors or source_read_errors or any(row["row_violations"] for row in audits):
        status = "PAPER_OUTCOME_LEDGER_AUDIT_BLOCKED"
    elif audits:
        status = "PAPER_OUTCOME_LEDGER_AUDIT_READY"
    payload: dict[str, Any] = {
        "type": "paper_outcome_ledger_audit",
        "schema_version": "paper_outcome_ledger_audit_v1",
        "generated_at": iso_now(generated_at),
        **NO_EXECUTION_FLAGS,
        "status": status,
        "outcome_ledger_path": str(outcome_ledger_path),
        "source_ledger_path": str(source_ledger_path),
        "linkage_ledger_path": str(linkage_ledger_path),
        "ledger_present": outcome_ledger_path.exists(),
        "rows": audits,
        "read_errors": read_errors,
        "source_read_errors": source_read_errors,
        "summary": {
            "outcome_rows_total": len(audits),
            "valid_unique_outcome_paper_trade_ids": len(valid_unique_paper_ids),
            "valid_unique_outcome_source_refs": len(valid_unique_source_refs),
            "duplicate_logical_outcome_rows": max(0, len([row for row in audits if not row["row_violations"]]) - len(valid_unique_paper_ids)),
            "duplicate_outcome_id_rows": sum(1 for row in audits if row["duplicate_outcome_id"]),
            "rows_with_timestamp_order_violations": sum(1 for row in audits if "timestamp_order_invalid" in row["row_violations"]),
            "rows_with_permission_leak": sum(1 for row in audits if "permission_leak" in row["row_violations"]),
            "rows_with_missing_source_ref": sum(1 for row in audits if "source_row_not_in_current_source_ledger" in row["row_violations"]),
            "source_ledger_parse_errors": len(source_read_errors),
            "linkage_ledger_parse_errors": len(linkage_read_errors),
            "original_paper_rows_mutated": 0,
            "permission_opened_count": 0,
        },
        "summary_ko": "outcome ledger가 없거나 비어 있어도 정상 audit artifact를 생성합니다. 원본 paper row mutation은 허용하지 않습니다.",
        "artifact_contract_violations": [],
    }
    payload["artifact_contract_violations"] = validate_paper_outcome_ledger_audit(payload)
    if payload["artifact_contract_violations"]:
        payload["status"] = "PAPER_OUTCOME_LEDGER_AUDIT_BLOCKED"
    return payload


def validate_paper_outcome_ledger_audit(payload: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if payload.get("type") != "paper_outcome_ledger_audit":
        violations.append("type must be paper_outcome_ledger_audit")
    for flag, expected in NO_EXECUTION_FLAGS.items():
        if payload.get(flag) is not expected:
            violations.append(f"{flag} must be {str(expected).lower()}")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    if summary.get("original_paper_rows_mutated") != 0:
        violations.append("summary.original_paper_rows_mutated must be 0")
    if summary.get("permission_opened_count") != 0:
        violations.append("summary.permission_opened_count must be 0")
    return violations


def write_paper_outcome_ledger_audit(out_json: Path = DEFAULT_OUT) -> dict[str, Any]:
    payload = build_paper_outcome_ledger_audit()
    write_json(out_json, payload)
    return payload


def _audit_row(
    row: dict[str, Any],
    duplicate_ids: set[str],
    source_refs: set[tuple[str, str, str]],
    source_ids: set[tuple[str, str]],
    superseded_ids: set[str],
) -> dict[str, Any]:
    violations = []
    envelope_violations = validate_evidence_envelope(row)
    if envelope_violations:
        violations.append("required_evidence_envelope_fields_invalid")
    outcome_id = str(row.get("outcome_row_id") or row.get("evidence_id") or "")
    if outcome_id in duplicate_ids:
        violations.append("duplicate_outcome_id")
    known = parse_ts(row.get("known_at_ts"))
    decision = parse_ts(row.get("decision_ts"))
    recorded = parse_ts(row.get("outcome_recorded_at_ts") or row.get("known_at_ts"))
    if not (decision and known and recorded and decision <= known <= recorded):
        violations.append("timestamp_order_invalid")
    scope = row.get("permission_scope") if isinstance(row.get("permission_scope"), dict) else {}
    if any(scope.get(key) is True for key in ("outcome_join_allowed_now", "shadow_observe_allowed", "live_trading_allowed", "scanner_connection_allowed", "executor_connection_allowed")):
        violations.append("permission_leak")
    if not str(row.get("artifact_hash") or "").startswith("sha256:"):
        violations.append("lineage_hash_missing")
    source_ref = (
        str(row.get("paper_trade_id") or ""),
        str(row.get("source_row_id") or ""),
        str(row.get("source_row_hash") or ""),
    )
    stable_source_id = (source_ref[0], source_ref[1])
    superseded_by_correction = outcome_id in superseded_ids
    source_ref_found = source_ref in source_refs or stable_source_id in source_ids
    if not source_ref_found and not superseded_by_correction:
        violations.append("source_row_not_in_current_source_ledger")
    return {
        "outcome_row_id": outcome_id,
        "paper_trade_id": row.get("paper_trade_id"),
        "source_row_id": row.get("source_row_id"),
        "evidence_id": row.get("evidence_id"),
        "duplicate_outcome_id": outcome_id in duplicate_ids,
        "source_ref_exact_match": source_ref in source_refs,
        "source_ref_stable_id_match": stable_source_id in source_ids,
        "superseded_by_correction": superseded_by_correction,
        "row_violations": sorted(set(violations)),
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


def _source_ids(rows: list[dict[str, Any]], linkage_rows: list[dict[str, Any]] | None = None) -> set[tuple[str, str]]:
    ids: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        ids.add(
            (
                str(row.get("paper_trade_id") or ""),
                str(row.get("source_row_id") or ""),
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
        ids.add(
            (
                str(row.get("target_paper_trade_id") or ""),
                str(row.get("source_row_id") or ""),
            )
        )
    return ids


def _superseded_ids(
    rows: list[dict[str, Any]],
    source_refs: set[tuple[str, str, str]],
    source_ids: set[tuple[str, str]],
) -> set[str]:
    ids: set[str] = set()
    latest_current_source_ref_by_paper: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("supersedes_outcome_row_id"):
            ids.add(str(row["supersedes_outcome_row_id"]))
        outcome_id = str(row.get("outcome_row_id") or row.get("evidence_id") or "")
        source_ref = (
            str(row.get("paper_trade_id") or ""),
            str(row.get("source_row_id") or ""),
            str(row.get("source_row_hash") or ""),
        )
        stable_source_id = (source_ref[0], source_ref[1])
        if outcome_id and (source_ref in source_refs or stable_source_id in source_ids):
            latest_current_source_ref_by_paper[source_ref[0]] = outcome_id
    for row in rows:
        if not isinstance(row, dict):
            continue
        outcome_id = str(row.get("outcome_row_id") or row.get("evidence_id") or "")
        paper_trade_id = str(row.get("paper_trade_id") or "")
        latest_current_id = latest_current_source_ref_by_paper.get(paper_trade_id)
        if outcome_id and latest_current_id and outcome_id != latest_current_id:
            ids.add(outcome_id)
    return ids


def _duplicates(values: list[str]) -> set[str]:
    counts: dict[str, int] = {}
    for value in values:
        if value:
            counts[value] = counts.get(value, 0) + 1
    return {value for value, count in counts.items() if count > 1}


def _valid_unique_paper_trade_ids(rows: list[dict[str, Any]]) -> set[str]:
    return {
        str(row.get("paper_trade_id") or "")
        for row in rows
        if isinstance(row, dict) and not row.get("row_violations") and row.get("paper_trade_id")
    }


def _valid_unique_source_refs(rows: list[dict[str, Any]]) -> set[tuple[str, str]]:
    return {
        (str(row.get("paper_trade_id") or ""), str(row.get("source_row_id") or ""))
        for row in rows
        if isinstance(row, dict) and not row.get("row_violations") and row.get("paper_trade_id") and row.get("source_row_id")
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build paper outcome ledger audit.")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    payload = write_paper_outcome_ledger_audit(Path(args.out_json))
    print(f"status={payload['status']} rows={payload['summary']['outcome_rows_total']} violations={len(payload['artifact_contract_violations'])}")
    return 0 if not payload["artifact_contract_violations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
