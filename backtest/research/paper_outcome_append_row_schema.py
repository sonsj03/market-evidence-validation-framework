"""Append-only outcome row schema for future paper observation review.

This module defines the row shape only. It does not append outcome rows, fetch
market data, calculate PnL, mutate paper rows, or enable shadow/live paths.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


RESULTS = Path("backtest/results")
DEFAULT_OUT = RESULTS / "paper_outcome_append_row_schema_latest.json"

REQUIRED_OUTCOME_ROW_FIELDS = [
    "outcome_row_id",
    "record_type",
    "paper_trade_id",
    "original_lineage_hash",
    "outcome_recorded_at_ts",
    "outcome_window",
    "outcome_source_ref",
    "join_candidate_ts",
    "replay_decision_ts",
    "known_at_boundary_ts",
    "correction_reason",
    "supersedes_outcome_row_id",
    "outcome_payload_hash",
    "outcome_payload_contract",
    "no_execution_flags",
]

REQUIRED_OUTCOME_PAYLOAD_CONTRACT_FIELDS = [
    "observed_price_ref",
    "observed_window_start_ts",
    "observed_window_end_ts",
    "source_type",
    "source_trust_level",
    "outcome_interpretation",
    "no_profit_claim",
    "no_edge_claim",
    "no_threshold_update",
]

FORBIDDEN_OUTCOME_ROW_FIELDS = [
    "profit",
    "pnl",
    "pnl_pct",
    "edge",
    "win_loss",
    "entry_signal",
    "exit_signal",
    "position_size",
    "shadow_candidate",
    "promotion_candidate",
    "threshold_update",
    "real_order_id",
    "exchange_order_id",
]

NO_EXECUTION_FLAGS = {
    "research_only": True,
    "read_only_contract": True,
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


def build_paper_outcome_append_row_schema(*, generated_at: datetime | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "paper_outcome_append_row_schema",
        "schema_version": "paper_outcome_append_row_schema_v1",
        "generated_at": (generated_at or datetime.now(UTC)).astimezone(UTC).isoformat(),
        **NO_EXECUTION_FLAGS,
        "status": "PAPER_OUTCOME_APPEND_ROW_SCHEMA_READY_DISABLED",
        "purpose": "define_future_append_only_outcome_rows_without_writing_or_joining_outcomes",
        "required_outcome_row_fields": REQUIRED_OUTCOME_ROW_FIELDS,
        "required_outcome_payload_contract_fields": REQUIRED_OUTCOME_PAYLOAD_CONTRACT_FIELDS,
        "forbidden_outcome_row_fields": FORBIDDEN_OUTCOME_ROW_FIELDS,
        "append_only_policy": {
            "append_only_outcome_rows_required": True,
            "original_paper_row_mutation_allowed": False,
            "delete_or_rewrite_original_row_allowed": False,
            "multiple_outcomes_require_supersedes_outcome_row_id": True,
            "correction_rows_must_preserve_original_lineage_hash": True,
        },
        "payload_policy": {
            "outcome_interpretation_must_be_observation_only": True,
            "profit_or_edge_claim_allowed": False,
            "threshold_update_allowed": False,
            "entry_exit_or_sizing_signal_allowed": False,
            "synthetic_price_allowed": False,
        },
        "example_minimal_valid_row": _example_minimal_valid_row(),
        "summary": {
            "required_fields_total": len(REQUIRED_OUTCOME_ROW_FIELDS),
            "payload_contract_fields_total": len(REQUIRED_OUTCOME_PAYLOAD_CONTRACT_FIELDS),
            "forbidden_fields_total": len(FORBIDDEN_OUTCOME_ROW_FIELDS),
            "example_rows_valid": 1,
            "permission_opened_count": 0,
            "outcome_join_allowed_now": False,
            "outcome_row_append_allowed_now": False,
        },
        "operator_summary_ko": (
            "나중에 paper 결과를 붙일 때 원본 row를 고치지 않고 별도 outcome row만 append하기 위한 형식입니다. "
            "아직 outcome join이나 수익/edge 판단은 허용하지 않습니다."
        ),
        "recommended_next_action": "BUILD_PAPER_OUTCOME_SOURCE_MAPPING_WITHOUT_FETCHING_MARKET_DATA",
        "artifact_contract_violations": [],
    }
    payload["artifact_contract_violations"] = validate_paper_outcome_append_row_schema(payload)
    if payload["artifact_contract_violations"]:
        payload["status"] = "PAPER_OUTCOME_APPEND_ROW_SCHEMA_BLOCKED"
    return payload


def validate_paper_outcome_append_row_schema(payload: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if payload.get("type") != "paper_outcome_append_row_schema":
        violations.append("type must be paper_outcome_append_row_schema")
    if payload.get("schema_version") != "paper_outcome_append_row_schema_v1":
        violations.append("schema_version must be paper_outcome_append_row_schema_v1")
    for flag, expected in NO_EXECUTION_FLAGS.items():
        if payload.get(flag) is not expected:
            violations.append(f"{flag} must be {str(expected).lower()}")
    if payload.get("required_outcome_row_fields") != REQUIRED_OUTCOME_ROW_FIELDS:
        violations.append("required_outcome_row_fields must match contract")
    if payload.get("required_outcome_payload_contract_fields") != REQUIRED_OUTCOME_PAYLOAD_CONTRACT_FIELDS:
        violations.append("required_outcome_payload_contract_fields must match contract")
    forbidden = set(payload.get("forbidden_outcome_row_fields") or [])
    for field in FORBIDDEN_OUTCOME_ROW_FIELDS:
        if field not in forbidden:
            violations.append(f"forbidden_outcome_row_fields must include {field}")
    append_policy = payload.get("append_only_policy") if isinstance(payload.get("append_only_policy"), dict) else {}
    if append_policy.get("original_paper_row_mutation_allowed") is not False:
        violations.append("append_only_policy.original_paper_row_mutation_allowed must be false")
    payload_policy = payload.get("payload_policy") if isinstance(payload.get("payload_policy"), dict) else {}
    for key in ("profit_or_edge_claim_allowed", "threshold_update_allowed", "entry_exit_or_sizing_signal_allowed", "synthetic_price_allowed"):
        if payload_policy.get(key) is not False:
            violations.append(f"payload_policy.{key} must be false")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    if summary.get("permission_opened_count") != 0:
        violations.append("summary.permission_opened_count must be 0")
    if summary.get("outcome_join_allowed_now") is not False:
        violations.append("summary.outcome_join_allowed_now must be false")
    if summary.get("outcome_row_append_allowed_now") is not False:
        violations.append("summary.outcome_row_append_allowed_now must be false")
    example = payload.get("example_minimal_valid_row") if isinstance(payload.get("example_minimal_valid_row"), dict) else {}
    for field in REQUIRED_OUTCOME_ROW_FIELDS:
        if field not in example:
            violations.append(f"example_minimal_valid_row must include {field}")
    for field in FORBIDDEN_OUTCOME_ROW_FIELDS:
        if field in example:
            violations.append(f"example_minimal_valid_row must not include forbidden field {field}")
    return violations


def write_paper_outcome_append_row_schema(out_json: Path = DEFAULT_OUT) -> dict[str, Any]:
    payload = build_paper_outcome_append_row_schema()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _example_minimal_valid_row() -> dict[str, Any]:
    return {
        "outcome_row_id": "paper-outcome-example",
        "record_type": "PAPER_OUTCOME_APPEND",
        "paper_trade_id": "paper-example",
        "original_lineage_hash": "sha256:original-paper-row-lineage",
        "outcome_recorded_at_ts": "2026-06-02T01:30:00+00:00",
        "outcome_window": "24h",
        "outcome_source_ref": "local_forward_archive://example",
        "join_candidate_ts": "2026-06-02T01:00:00+00:00",
        "replay_decision_ts": "2026-06-02T00:00:00+00:00",
        "known_at_boundary_ts": "2026-06-02T01:30:00+00:00",
        "correction_reason": "first_append_only_observation",
        "supersedes_outcome_row_id": None,
        "outcome_payload_hash": "sha256:outcome-payload-hash",
        "outcome_payload_contract": {
            "observed_price_ref": "local_forward_archive://example/price_ref",
            "observed_window_start_ts": "2026-06-02T00:00:00+00:00",
            "observed_window_end_ts": "2026-06-03T00:00:00+00:00",
            "source_type": "LOCAL_FORWARD_OHLCV_ARCHIVE",
            "source_trust_level": "FORWARD_LOCAL_APPEND_ONLY",
            "outcome_interpretation": "OBSERVATION_ONLY",
            "no_profit_claim": True,
            "no_edge_claim": True,
            "no_threshold_update": True,
        },
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
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build paper outcome append row schema.")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    payload = write_paper_outcome_append_row_schema(Path(args.out_json))
    summary = payload["summary"]
    print(
        f"status={payload['status']} required_fields={summary['required_fields_total']} "
        f"forbidden_fields={summary['forbidden_fields_total']} outcome_join_allowed_now={payload['outcome_join_allowed_now']} "
        f"violations={len(payload['artifact_contract_violations'])}"
    )
    return 0 if not payload["artifact_contract_violations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
