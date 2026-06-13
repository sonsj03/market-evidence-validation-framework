"""Preflight for future append-only paper outcome rows.

The preflight checks ledger validity, per-row delay eligibility, source
materialization, and append-row schema status. It never writes outcome rows,
never mutates paper rows, and never opens shadow/live/scanner/executor paths.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


RESULTS = Path("backtest/results")
DEFAULT_OUT = RESULTS / "paper_outcome_append_preflight_latest.json"
INPUTS = {
    "paper_ledger_audit": RESULTS / "paper_ledger_audit_latest.json",
    "paper_outcome_append_row_schema": RESULTS / "paper_outcome_append_row_schema_latest.json",
    "paper_outcome_source_mapping": RESULTS / "paper_outcome_source_mapping_latest.json",
    "paper_outcome_source_materialization_audit": RESULTS / "paper_outcome_source_materialization_audit_latest.json",
    "paper_outcome_join_row_eligibility": RESULTS / "paper_outcome_join_row_eligibility_latest.json",
}

NO_EXECUTION_FLAGS = {
    "research_only": True,
    "read_only": True,
    "collection_trigger_allowed": False,
    "network_call_allowed": False,
    "market_outcome_fetch_allowed_now": False,
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
    "outcome_join_allowed_now": False,
    "outcome_row_append_allowed_now": False,
    "original_row_mutation_allowed": False,
}


def build_paper_outcome_append_preflight(
    artifacts: dict[str, dict[str, Any]] | None = None,
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    artifacts = artifacts if artifacts is not None else read_inputs()
    ledger = artifacts.get("paper_ledger_audit", {})
    schema = artifacts.get("paper_outcome_append_row_schema", {})
    mapping = artifacts.get("paper_outcome_source_mapping", {})
    materialization = artifacts.get("paper_outcome_source_materialization_audit", {})
    eligibility = artifacts.get("paper_outcome_join_row_eligibility", {})
    mapped_by_id = _by_id(mapping.get("rows"))
    eligible_by_id = _by_id(eligibility.get("rows"))
    source_states = materialization.get("source_states") if isinstance(materialization.get("source_states"), dict) else {}
    row_preflights = [
        _row_preflight(row, mapped_by_id, eligible_by_id, source_states)
        for row in ledger.get("rows", [])
        if isinstance(row, dict)
    ]
    global_blockers = _global_blockers(ledger, schema, mapping, materialization, eligibility)
    append_ready = [row for row in row_preflights if row["append_preflight_ready_for_manual_review"]]
    source_gap_summary = _source_gap_summary(row_preflights, source_states)
    operator_next_sources = _operator_next_sources(source_gap_summary)
    status = "PAPER_OUTCOME_APPEND_PREFLIGHT_WAIT_FOR_PAPER_ROWS"
    if global_blockers or row_preflights:
        status = "PAPER_OUTCOME_APPEND_PREFLIGHT_READY_WITH_BLOCKERS"
    if append_ready and not global_blockers:
        status = "PAPER_OUTCOME_APPEND_PREFLIGHT_READY_DISABLED"

    payload: dict[str, Any] = {
        "type": "paper_outcome_append_preflight",
        "schema_version": "paper_outcome_append_preflight_v1",
        "generated_at": (generated_at or datetime.now(UTC)).astimezone(UTC).isoformat(),
        **NO_EXECUTION_FLAGS,
        "status": status,
        "input_status": {name: artifacts.get(name, {}).get("status") for name in INPUTS},
        "global_blockers": global_blockers,
        "source_gap_summary": source_gap_summary,
        "operator_next_sources": operator_next_sources,
        "row_preflights": row_preflights,
        "summary": {
            "paper_rows_total": len(row_preflights),
            "rows_delay_elapsed": sum(1 for row in row_preflights if row["minimum_delay_elapsed"]),
            "rows_with_source_mapping": sum(1 for row in row_preflights if row["source_mapping_present"]),
            "rows_with_all_required_sources_materialized": sum(1 for row in row_preflights if row["all_required_sources_materialized"]),
            "rows_ready_for_future_manual_append_review": len(append_ready),
            "outcome_rows_written": 0,
            "original_rows_mutated": 0,
            "outcome_row_append_allowed_now": False,
            "outcome_join_allowed_now": False,
            "permission_opened_count": 0,
            "source_types_missing_or_guarded": len(source_gap_summary["missing_or_guarded_source_types"]),
        },
        "operator_summary_ko": (
            "paper 결과 row를 붙이기 전 사전점검입니다. 현재는 원본 row를 고치지 않고, outcome row도 쓰지 않으며, "
            "지연시간과 local source가 모두 준비됐는지만 확인합니다."
        ),
        "recommended_next_action": "WAIT_FOR_LOCAL_FORWARD_SOURCE_ROWS_BEFORE_APPEND_ONLY_OUTCOME_WRITER",
        "artifact_contract_violations": [],
    }
    payload["artifact_contract_violations"] = validate_paper_outcome_append_preflight(payload)
    if payload["artifact_contract_violations"]:
        payload["status"] = "PAPER_OUTCOME_APPEND_PREFLIGHT_BLOCKED"
    return payload


def validate_paper_outcome_append_preflight(payload: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if payload.get("type") != "paper_outcome_append_preflight":
        violations.append("type must be paper_outcome_append_preflight")
    if payload.get("schema_version") != "paper_outcome_append_preflight_v1":
        violations.append("schema_version must be paper_outcome_append_preflight_v1")
    for flag, expected in NO_EXECUTION_FLAGS.items():
        if payload.get(flag) is not expected:
            violations.append(f"{flag} must be {str(expected).lower()}")
    rows = payload.get("row_preflights")
    if not isinstance(rows, list):
        violations.append("row_preflights must be list")
        rows = []
    for row in rows:
        if not isinstance(row, dict):
            violations.append("row_preflight must be object")
            continue
        paper_trade_id = str(row.get("paper_trade_id") or "UNKNOWN")
        if row.get("outcome_row_append_allowed_now") is not False:
            violations.append(f"{paper_trade_id}.outcome_row_append_allowed_now must be false")
        if row.get("outcome_join_allowed_now") is not False:
            violations.append(f"{paper_trade_id}.outcome_join_allowed_now must be false")
        if not isinstance(row.get("row_blockers"), list):
            violations.append(f"{paper_trade_id}.row_blockers must be list")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    for key, expected in {
        "outcome_rows_written": 0,
        "original_rows_mutated": 0,
        "permission_opened_count": 0,
    }.items():
        if summary.get(key) != expected:
            violations.append(f"summary.{key} must be {expected}")
    for key in ("outcome_row_append_allowed_now", "outcome_join_allowed_now"):
        if summary.get(key) is not False:
            violations.append(f"summary.{key} must be false")
    source_gap = payload.get("source_gap_summary")
    if not isinstance(source_gap, dict):
        violations.append("source_gap_summary must be object")
    else:
        for key in ("required_source_types", "materialized_source_types", "missing_or_guarded_source_types"):
            if not isinstance(source_gap.get(key), list):
                violations.append(f"source_gap_summary.{key} must be list")
    if not isinstance(payload.get("operator_next_sources"), list):
        violations.append("operator_next_sources must be list")
    return violations


def write_paper_outcome_append_preflight(out_json: Path = DEFAULT_OUT) -> dict[str, Any]:
    payload = build_paper_outcome_append_preflight()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def read_inputs(paths: dict[str, Path] | None = None) -> dict[str, dict[str, Any]]:
    return {name: read_json(path) for name, path in (paths or INPUTS).items()}


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"_missing": True, "_path": str(path)}
    return payload if isinstance(payload, dict) else {"_invalid": True, "_path": str(path)}


def _row_preflight(
    ledger_row: dict[str, Any],
    mapped_by_id: dict[str, dict[str, Any]],
    eligible_by_id: dict[str, dict[str, Any]],
    source_states: dict[str, Any],
) -> dict[str, Any]:
    paper_trade_id = str(ledger_row.get("paper_trade_id") or "")
    mapped = mapped_by_id.get(paper_trade_id, {})
    eligible = eligible_by_id.get(paper_trade_id, {})
    required_sources = mapped.get("required_source_types") if isinstance(mapped.get("required_source_types"), list) else []
    source_blockers = _source_blockers(required_sources, source_states)
    row_blockers: list[str] = []
    if ledger_row.get("row_valid_for_delayed_outcome_contract") is not True:
        row_blockers.append("paper_ledger_row_not_valid_for_delayed_outcome_contract")
    if not mapped:
        row_blockers.append("paper_outcome_source_mapping_missing_for_row")
    if not eligible:
        row_blockers.append("paper_outcome_join_row_eligibility_missing_for_row")
    if eligible and eligible.get("minimum_delay_elapsed") is not True:
        row_blockers.append("minimum_delay_not_elapsed")
    if source_blockers:
        row_blockers.extend(source_blockers)
    ready = not row_blockers
    return {
        "paper_trade_id": paper_trade_id,
        "strategy_id": str(ledger_row.get("strategy_id") or ""),
        "virtual_decision": str(ledger_row.get("virtual_decision") or ""),
        "source_mapping_present": bool(mapped),
        "minimum_delay_elapsed": bool(eligible.get("minimum_delay_elapsed") is True),
        "required_source_types": required_sources,
        "all_required_sources_materialized": not source_blockers and bool(required_sources),
        "append_preflight_ready_for_manual_review": ready,
        "row_blockers": _dedupe(row_blockers),
        "outcome_row_append_allowed_now": False,
        "outcome_join_allowed_now": False,
    }


def _global_blockers(
    ledger: dict[str, Any],
    schema: dict[str, Any],
    mapping: dict[str, Any],
    materialization: dict[str, Any],
    eligibility: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if ledger.get("status") != "PAPER_LEDGER_AUDIT_READY":
        blockers.append("paper_ledger_audit_not_ready")
    if schema.get("status") != "PAPER_OUTCOME_APPEND_ROW_SCHEMA_READY_DISABLED":
        blockers.append("paper_outcome_append_row_schema_not_ready_disabled")
    if mapping.get("status") != "PAPER_OUTCOME_SOURCE_MAPPING_READY_DISABLED":
        blockers.append("paper_outcome_source_mapping_not_ready_disabled")
    if materialization.get("type") != "paper_outcome_source_materialization_audit":
        blockers.append("paper_outcome_source_materialization_audit_missing")
    if eligibility.get("status") != "PAPER_OUTCOME_JOIN_ROW_ELIGIBILITY_READY_DISABLED":
        blockers.append("paper_outcome_join_row_eligibility_not_ready_disabled")
    return blockers


def _source_blockers(required_sources: list[Any], source_states: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for source_type in sorted({str(source) for source in required_sources}):
        state = source_states.get(source_type) if isinstance(source_states.get(source_type), dict) else {}
        if state.get("materialized_for_outcome_join_now") is not True:
            blockers.append(f"required_source_not_materialized:{source_type}")
    return blockers


def _source_gap_summary(row_preflights: list[dict[str, Any]], source_states: dict[str, Any]) -> dict[str, Any]:
    required = sorted(
        {
            str(source)
            for row in row_preflights
            for source in row.get("required_source_types", [])
        }
    )
    materialized: list[str] = []
    missing_or_guarded: list[str] = []
    for source_type in required:
        state = source_states.get(source_type) if isinstance(source_states.get(source_type), dict) else {}
        if state.get("materialized_for_outcome_join_now") is True:
            materialized.append(source_type)
        else:
            missing_or_guarded.append(source_type)
    return {
        "required_source_types": required,
        "materialized_source_types": materialized,
        "missing_or_guarded_source_types": missing_or_guarded,
        "rows_waiting_for_sources": sum(1 for row in row_preflights if not row.get("all_required_sources_materialized")),
        "operator_summary_ko": _source_gap_summary_ko(missing_or_guarded),
    }


def _operator_next_sources(source_gap_summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    missing = set(source_gap_summary.get("missing_or_guarded_source_types") or [])
    source_labels = {
        "LOCAL_FORWARD_OHLCV_ARCHIVE": (
            "local forward OHLCV archive",
            "paper decision 이후 구간의 실제 OHLCV source row가 필요합니다.",
        ),
        "LOCAL_FORWARD_ORDERBOOK_ARCHIVE": (
            "local forward orderbook archive",
            "paper decision 이후 구간의 오더북/체결 context source row가 필요합니다.",
        ),
        "LOCAL_FORWARD_FUNDING_ARCHIVE": (
            "local forward funding archive",
            "paper decision 이후 구간의 funding context source row가 필요합니다.",
        ),
        "LOCAL_APPEND_ONLY_MARKET_CONTEXT_ARCHIVE": (
            "append-only market context archive",
            "paper decision 시점 이후 시장 context를 원본 수정 없이 별도 row로 확인해야 합니다.",
        ),
        "FORWARD_OBSERVATION_CAPTURE_METADATA": (
            "forward observation capture metadata",
            "decision 시점, known-at snapshot, source lineage가 필요합니다.",
        ),
        "APPEND_ONLY_OUTCOME_SOURCE_ROWS": (
            "append-only outcome source rows",
            "원본 paper row를 수정하지 않고 별도 outcome row로 붙일 source가 필요합니다.",
        ),
    }
    for source_type in sorted(missing):
        label, reason = source_labels.get(source_type, (source_type, "해당 source가 materialize되어야 outcome append 검토가 가능합니다."))
        rows.append(
            {
                "source_type": source_type,
                "label_ko": label,
                "why_needed_ko": reason,
                "ready_now": False,
            }
        )
    rows.append(
        {
            "source_type": "MANUAL_OUTCOME_APPEND_REVIEW",
            "label_ko": "수동 outcome append 검토",
            "why_needed_ko": "source가 준비되어도 자동 append는 금지되고, 수동 검토 후 별도 단계에서만 가능합니다.",
            "ready_now": False,
        }
    )
    return rows


def _source_gap_summary_ko(missing_or_guarded: list[str]) -> str:
    if not missing_or_guarded:
        return "필수 outcome source가 materialize되어 있지만 outcome append 권한은 여전히 닫혀 있습니다."
    return "결과를 붙이려면 먼저 local forward source가 paper decision window에 맞게 materialize되어야 합니다."


def _by_id(rows: Any) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return out
    for row in rows:
        if isinstance(row, dict) and row.get("paper_trade_id"):
            out[str(row["paper_trade_id"])] = row
    return out


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Build paper outcome append preflight.")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    payload = write_paper_outcome_append_preflight(Path(args.out_json))
    summary = payload["summary"]
    print(
        f"status={payload['status']} rows={summary['paper_rows_total']} "
        f"ready={summary['rows_ready_for_future_manual_append_review']} "
        f"outcome_append_allowed={summary['outcome_row_append_allowed_now']} "
        f"violations={len(payload['artifact_contract_violations'])}"
    )
    return 0 if not payload["artifact_contract_violations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
