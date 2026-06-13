"""Audit provenance fields for long-term research artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


RESULTS = Path("backtest/results")
DEFAULT_OUT = RESULTS / "artifact_provenance_integrity_audit_latest.json"
INPUTS = {
    "evidence_reliability": RESULTS / "evidence_reliability_model_contract_latest.json",
    "conflict_gate": RESULTS / "historical_forward_conflict_gate_latest.json",
    "regime_contract": RESULTS / "regime_similarity_evidence_contract_latest.json",
    "stage4_evidence": RESULTS / "stage4_evidence_preflight_latest.json",
    "historical_proxy": RESULTS / "historical_proxy_stage4_preflight_latest.json",
    "collector_maturity": RESULTS / "collector_side_maturity_report_latest.json",
    "evidence_source_registry": RESULTS / "evidence_source_registry_latest.json",
    "evidence_tier_decay_model": RESULTS / "evidence_tier_decay_model_latest.json",
    "evidence_feature_provenance_contract": RESULTS / "evidence_feature_provenance_contract_latest.json",
    "sovereign_evidence_engine": RESULTS / "sovereign_evidence_engine_latest.json",
    "historical_tier_b_usage_gate": RESULTS / "historical_tier_b_usage_gate_latest.json",
    "forward_observation_confidence_accumulator": RESULTS / "forward_observation_confidence_accumulator_latest.json",
    "evidence_recheck_sequence_closeout": RESULTS / "evidence_recheck_sequence_closeout_latest.json",
    "forward_observation_row_contract": RESULTS / "forward_observation_row_contract_latest.json",
    "forward_observation_dry_run_builder": RESULTS / "forward_observation_dry_run_builder_latest.json",
    "forward_observation_row_validator": RESULTS / "forward_observation_row_validator_latest.json",
    "forward_observation_outcome_join_preparation": RESULTS / "forward_observation_outcome_join_preparation_latest.json",
    "replay_safe_evidence_transition_layer": RESULTS / "replay_safe_evidence_transition_layer_latest.json",
    "historical_forward_comparability_audit": RESULTS / "historical_forward_comparability_audit_latest.json",
    "forward_observation_writer_enablement_contract": RESULTS / "forward_observation_writer_enablement_contract_latest.json",
    "evidence_provenance_graph": RESULTS / "evidence_provenance_graph_latest.json",
    "orderbook_event_trigger_feasibility": RESULTS / "orderbook_event_trigger_feasibility_latest.json",
    "mechanical_replay_pipeline_smoke_test": RESULTS / "mechanical_replay_pipeline_smoke_test_latest.json",
    "cost_fill_conservative_envelope_contract": RESULTS / "cost_fill_conservative_envelope_contract_latest.json",
    "historical_tier_b_bootstrap_feasibility": RESULTS / "historical_tier_b_bootstrap_feasibility_latest.json",
    "orderbook_adaptive_trigger_design_closeout": RESULTS / "orderbook_adaptive_trigger_design_closeout_latest.json",
    "public_funding_guarded_source_ready_closeout": RESULTS / "public_funding_guarded_source_ready_closeout_latest.json",
    "stage4_fee_funding_source_closeout_guarded_update": RESULTS
    / "stage4_fee_funding_source_closeout_guarded_update_latest.json",
    "stage4_cost_fill_replay_blocker_rollup_guarded_funding_update": RESULTS
    / "stage4_cost_fill_replay_blocker_rollup_guarded_funding_update_latest.json",
    "public_funding_lookahead_guard_test_pack": RESULTS / "public_funding_lookahead_guard_test_pack_latest.json",
    "sync_gap_master_audit": RESULTS / "sync_gap_master_audit_latest.json",
    "replay_acceleration_master_board": RESULTS / "replay_acceleration_master_board_latest.json",
    "service_shadow_policy_blocker_audit": RESULTS / "service_shadow_policy_blocker_audit_latest.json",
    "cross_exchange_dependency_risk_audit": RESULTS / "cross_exchange_dependency_risk_audit_latest.json",
    "strategy_status_debt_audit": RESULTS / "strategy_status_debt_audit_latest.json",
    "monitoring_blind_spot_audit": RESULTS / "monitoring_blind_spot_audit_latest.json",
    "service_shadow_policy_diagnosis": RESULTS / "service_shadow_policy_diagnosis_latest.json",
    "oi_second_exchange_visibility_contract": RESULTS / "oi_second_exchange_visibility_contract_latest.json",
    "strategy_deferred_archive_stub_plan": RESULTS / "strategy_deferred_archive_stub_plan_latest.json",
    "replay_acceleration_gui_panel_decision": RESULTS / "replay_acceleration_gui_panel_decision_latest.json",
    "service_shadow_policy_journal_summary": RESULTS / "service_shadow_policy_journal_summary_latest.json",
    "oi_second_exchange_feasibility_matrix": RESULTS / "oi_second_exchange_feasibility_matrix_latest.json",
    "strategy_deferred_archive_stub_closeout": RESULTS / "strategy_deferred_archive_stub_closeout_latest.json",
    "telegram_blind_spot_dry_run_verifier": RESULTS / "telegram_blind_spot_dry_run_verifier_latest.json",
    "operational_resolution_sequence_closeout": RESULTS / "operational_resolution_sequence_closeout_latest.json",
    "service_restart_policy_fix_plan": RESULTS / "service_restart_policy_fix_plan_latest.json",
    "operational_next_action_board": RESULTS / "operational_next_action_board_latest.json",
    "service_restart_policy_pending_check": RESULTS / "service_restart_policy_pending_check_latest.json",
    "oi_bybit_visibility_preflight": RESULTS / "oi_bybit_visibility_preflight_latest.json",
    "oi_bybit_source_policy_review": RESULTS / "oi_bybit_source_policy_review_latest.json",
    "oi_bybit_normalization_comparability_plan": RESULTS / "oi_bybit_normalization_comparability_plan_latest.json",
    "oi_binance_bybit_visibility_diff_audit": RESULTS / "oi_binance_bybit_visibility_diff_audit_latest.json",
    "oi_bybit_normalized_dry_run_schema_contract": RESULTS / "oi_bybit_normalized_dry_run_schema_contract_latest.json",
    "oi_bybit_normalized_row_dry_run_builder": RESULTS / "oi_bybit_normalized_row_dry_run_builder_latest.json",
    "oi_bybit_normalized_row_validator": RESULTS / "oi_bybit_normalized_row_validator_latest.json",
    "oi_bybit_normalized_validation_closeout": RESULTS / "oi_bybit_normalized_validation_closeout_latest.json",
    "oi_binance_bybit_overlap_window_comparability_audit": RESULTS
    / "oi_binance_bybit_overlap_window_comparability_audit_latest.json",
    "oi_binance_bybit_comparability_scoring_contract": RESULTS
    / "oi_binance_bybit_comparability_scoring_contract_latest.json",
    "oi_provider_delay_density_review": RESULTS / "oi_provider_delay_density_review_latest.json",
    "oi_unit_notional_blocker_closeout": RESULTS / "oi_unit_notional_blocker_closeout_latest.json",
    "oi_price_join_or_quote_source_preflight": RESULTS / "oi_price_join_or_quote_source_preflight_latest.json",
    "oi_price_join_contract": RESULTS / "oi_price_join_contract_latest.json",
    "oi_price_join_dry_run_feasibility_audit": RESULTS / "oi_price_join_dry_run_feasibility_audit_latest.json",
    "oi_price_source_known_at_gap_closeout": RESULTS / "oi_price_source_known_at_gap_closeout_latest.json",
    "future_price_capture_contract": RESULTS / "future_price_capture_contract_latest.json",
    "future_price_capture_validator_contract": RESULTS / "future_price_capture_validator_contract_latest.json",
    "oi_notional_comparability_blocker_rollup": RESULTS
    / "oi_notional_comparability_blocker_rollup_latest.json",
    "strategy_deferred_archive_stub_manifest": RESULTS / "strategy_deferred_archive_stub_manifest_latest.json",
    "strategy_deferred_active_surface_review": RESULTS / "strategy_deferred_active_surface_review_latest.json",
    "operational_blocker_closeout_board": RESULTS / "operational_blocker_closeout_board_latest.json",
    "stage4_tiered_replay_contract": RESULTS / "stage4_tiered_replay_contract_latest.json",
    "historical_evidence_tier_gate": RESULTS / "historical_evidence_tier_gate_latest.json",
    "preliminary_replay_permission_contract": RESULTS / "preliminary_replay_permission_contract_latest.json",
    "account_fee_truth_source_validator": RESULTS / "account_fee_truth_source_validator_latest.json",
}

NO_EXECUTION_FLAGS = {
    "research_only": True,
    "read_only": True,
    "collection_triggered": False,
    "network_call_allowed": False,
    "strategy_execution_allowed": False,
    "scanner_connection_allowed": False,
    "executor_connection_allowed": False,
    "stage4_entry_allowed": False,
    "shadow_observe_allowed": False,
    "promotion_allowed": False,
    "live_trading_allowed": False,
    "cost_adjusted_replay_allowed": False,
}


def build_artifact_provenance_integrity_audit(
    artifacts: dict[str, dict[str, Any]] | None = None,
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    artifacts = artifacts if artifacts is not None else read_inputs()
    rows = [_row(name, payload) for name, payload in artifacts.items()]
    weak = [row for row in rows if row["provenance_state"] != "BASIC_PROVENANCE_OK"]
    payload: dict[str, Any] = {
        "type": "artifact_provenance_integrity_audit",
        "schema_version": "artifact_provenance_integrity_audit_v1",
        "generated_at": (generated_at or datetime.now(UTC)).astimezone(UTC).isoformat(),
        **NO_EXECUTION_FLAGS,
        "status": "ARTIFACT_PROVENANCE_INTEGRITY_AUDIT_READY_WITH_WARNINGS" if weak else "ARTIFACT_PROVENANCE_INTEGRITY_AUDIT_READY",
        "summary": {
            "artifacts_total": len(rows),
            "weak_provenance_count": len(weak),
            "missing_generated_at_count": sum(1 for row in rows if not row["has_generated_at"]),
            "contract_violations_count": sum(row["contract_violations"] for row in rows),
        },
        "rows": rows,
        "required_future_fields": [
            "source_artifact_paths",
            "source_hash",
            "generated_at",
            "known_at_basis",
            "collector_role",
            "main_or_minipc_origin",
        ],
        "artifact_contract_violations": [],
    }
    payload["artifact_contract_violations"] = validate_artifact_provenance_integrity_audit(payload)
    return payload


def validate_artifact_provenance_integrity_audit(payload: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if payload.get("type") != "artifact_provenance_integrity_audit":
        violations.append("type must be artifact_provenance_integrity_audit")
    for flag, expected in NO_EXECUTION_FLAGS.items():
        if payload.get(flag) is not expected:
            violations.append(f"{flag} must be {str(expected).lower()}")
    if not isinstance(payload.get("rows"), list) or not payload["rows"]:
        violations.append("rows must be non-empty")
    return violations


def write_artifact_provenance_integrity_audit(out_json: Path = DEFAULT_OUT) -> dict[str, Any]:
    payload = build_artifact_provenance_integrity_audit()
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


def _row(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    has_generated = bool(payload.get("generated_at") or payload.get("created_at"))
    has_type = bool(payload.get("type"))
    has_status = bool(payload.get("status"))
    state = "BASIC_PROVENANCE_OK" if has_generated and has_type and has_status else "BASIC_PROVENANCE_WEAK"
    return {
        "artifact_name": name,
        "type": str(payload.get("type") or ""),
        "status": str(payload.get("status") or ""),
        "has_generated_at": has_generated,
        "has_type": has_type,
        "has_status": has_status,
        "contract_violations": len(payload.get("artifact_contract_violations") or []),
        "provenance_state": state,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build artifact provenance integrity audit.")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    payload = write_artifact_provenance_integrity_audit(Path(args.out_json))
    print(
        f"status={payload['status']} artifacts={payload['summary']['artifacts_total']} "
        f"weak={payload['summary']['weak_provenance_count']} violations={len(payload['artifact_contract_violations'])}"
    )
    return 0 if not payload["artifact_contract_violations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
