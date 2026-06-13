"""Market outcome source contract for future paper outcome joins.

The contract defines acceptable source properties only. It does not fetch
market data, calculate outcomes, mutate paper rows, or enable shadow/live.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


RESULTS = Path("backtest/results")
DEFAULT_OUT = RESULTS / "paper_outcome_source_contract_latest.json"

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
    "original_row_mutation_allowed": False,
}

REQUIRED_SOURCE_FIELDS = [
    "source_id",
    "source_type",
    "symbol",
    "exchange",
    "timeframe",
    "source_time_start_ts",
    "source_time_end_ts",
    "source_captured_at_ts",
    "source_trust_level",
    "known_at_boundary_ts",
    "append_only_source_ref",
]


def build_paper_outcome_source_contract(*, generated_at: datetime | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "paper_outcome_source_contract",
        "schema_version": "paper_outcome_source_contract_v1",
        "generated_at": (generated_at or datetime.now(UTC)).astimezone(UTC).isoformat(),
        **NO_EXECUTION_FLAGS,
        "status": "PAPER_OUTCOME_SOURCE_CONTRACT_READY_DISABLED",
        "purpose": "define_future_market_outcome_source_requirements_without_fetching_market_data",
        "allowed_source_types": [
            "LOCAL_FORWARD_OHLCV_ARCHIVE",
            "LOCAL_FORWARD_ORDERBOOK_ARCHIVE",
            "LOCAL_FORWARD_FUNDING_ARCHIVE",
            "LOCAL_APPEND_ONLY_MARKET_CONTEXT_ARCHIVE",
        ],
        "required_source_fields": REQUIRED_SOURCE_FIELDS,
        "source_quality_requirements": {
            "source_must_be_local_or_preexisting": True,
            "network_fetch_for_join_allowed_now": False,
            "source_time_must_cover_outcome_window": True,
            "source_captured_at_ts_must_not_be_before_source_time_end_ts": True,
            "known_at_boundary_must_be_after_original_decision_ts": True,
            "source_ref_must_be_append_only": True,
            "synthetic_outcome_price_allowed": False,
            "missing_price_imputation_allowed": False,
        },
        "outcome_payload_requirements": {
            "outcome_price_reference_required": True,
            "outcome_window_required": True,
            "paper_trade_id_required": True,
            "original_lineage_hash_required": True,
            "outcome_payload_hash_required": True,
            "profit_or_edge_claim_allowed": False,
            "threshold_update_allowed": False,
        },
        "recommended_next_action": "BUILD_PAPER_OUTCOME_JOIN_ROW_ELIGIBILITY",
        "artifact_contract_violations": [],
    }
    payload["artifact_contract_violations"] = validate_paper_outcome_source_contract(payload)
    if payload["artifact_contract_violations"]:
        payload["status"] = "PAPER_OUTCOME_SOURCE_CONTRACT_BLOCKED"
    return payload


def validate_paper_outcome_source_contract(payload: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if payload.get("type") != "paper_outcome_source_contract":
        violations.append("type must be paper_outcome_source_contract")
    if payload.get("schema_version") != "paper_outcome_source_contract_v1":
        violations.append("schema_version must be paper_outcome_source_contract_v1")
    for flag, expected in NO_EXECUTION_FLAGS.items():
        if payload.get(flag) is not expected:
            violations.append(f"{flag} must be {str(expected).lower()}")
    if payload.get("required_source_fields") != REQUIRED_SOURCE_FIELDS:
        violations.append("required_source_fields must match contract")
    quality = payload.get("source_quality_requirements") if isinstance(payload.get("source_quality_requirements"), dict) else {}
    if quality.get("network_fetch_for_join_allowed_now") is not False:
        violations.append("source_quality_requirements.network_fetch_for_join_allowed_now must be false")
    if quality.get("synthetic_outcome_price_allowed") is not False:
        violations.append("source_quality_requirements.synthetic_outcome_price_allowed must be false")
    outcome = payload.get("outcome_payload_requirements") if isinstance(payload.get("outcome_payload_requirements"), dict) else {}
    for key in ("profit_or_edge_claim_allowed", "threshold_update_allowed"):
        if outcome.get(key) is not False:
            violations.append(f"outcome_payload_requirements.{key} must be false")
    return violations


def write_paper_outcome_source_contract(out_json: Path = DEFAULT_OUT) -> dict[str, Any]:
    payload = build_paper_outcome_source_contract()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build paper outcome source contract.")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    payload = write_paper_outcome_source_contract(Path(args.out_json))
    print(
        f"status={payload['status']} required_fields={len(payload['required_source_fields'])} "
        f"outcome_join_allowed_now={payload['outcome_join_allowed_now']} violations={len(payload['artifact_contract_violations'])}"
    )
    return 0 if not payload["artifact_contract_violations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
