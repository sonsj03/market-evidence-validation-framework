"""Postmortem row contract for decision snapshot observations.

This artifact defines the future row schema only. It does not append
postmortem rows, interpret profit/edge, or update confidence.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.research.decision_snapshot_input_adapters import CORE_STRATEGIES
from backtest.research.paper_evidence_loop_common import NO_EXECUTION_FLAGS, iso_now, read_json, write_json


RESULTS = Path("backtest/results")
DEFAULT_OUT = RESULTS / "decision_snapshot_postmortem_row_contract_latest.json"
COVERAGE_AUDIT = RESULTS / "decision_snapshot_coverage_audit_latest.json"

REQUIRED_POSTMORTEM_FIELDS = [
    "postmortem_id",
    "decision_id",
    "paper_trade_id",
    "strategy_id",
    "observation_only_outcome_ref",
    "favorable_movement",
    "adverse_movement",
    "missing_context_relevance",
    "blocker_relevance",
    "decision_replayability",
    "repeated_failure_pattern_candidate",
    "reviewer",
    "reviewed_at",
]

FORBIDDEN_POSTMORTEM_FIELDS = [
    "profit",
    "pnl",
    "edge",
    "alpha",
    "sharpe",
    "win_rate",
    "expected_value",
    "confidence_delta",
    "confidence_upgrade",
    "promotion_decision",
    "live_trade_decision",
    "position_size",
    "entry_order",
    "exit_order",
]

FIELD_CONTRACT = {
    "favorable_movement": {
        "type": "observation_bucket",
        "allowed_values": ["NOT_REVIEWED", "NONE_OBSERVED", "LOW", "MEDIUM", "HIGH", "UNKNOWN"],
        "profit_or_edge_allowed": False,
    },
    "adverse_movement": {
        "type": "observation_bucket",
        "allowed_values": ["NOT_REVIEWED", "NONE_OBSERVED", "LOW", "MEDIUM", "HIGH", "UNKNOWN"],
        "profit_or_edge_allowed": False,
    },
    "missing_context_relevance": {
        "type": "classification",
        "allowed_values": ["NOT_REVIEWED", "NOT_RELEVANT", "POSSIBLY_RELEVANT", "LIKELY_RELEVANT", "UNKNOWN"],
    },
    "blocker_relevance": {
        "type": "classification",
        "allowed_values": ["NOT_REVIEWED", "NOT_RELEVANT", "POSSIBLY_RELEVANT", "LIKELY_RELEVANT", "UNKNOWN"],
    },
    "decision_replayability": {
        "type": "classification",
        "allowed_values": ["NOT_REVIEWED", "REPLAYABLE", "PARTIALLY_REPLAYABLE", "NOT_REPLAYABLE", "UNKNOWN"],
    },
    "repeated_failure_pattern_candidate": {
        "type": "classification",
        "allowed_values": ["NOT_REVIEWED", "NO", "POSSIBLE", "LIKELY", "UNKNOWN"],
    },
}


def build_decision_snapshot_postmortem_row_contract(
    coverage_audit: dict[str, Any] | None = None,
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    coverage = coverage_audit if coverage_audit is not None else read_json(COVERAGE_AUDIT)
    strategy_coverage = coverage.get("strategy_coverage") if isinstance(coverage.get("strategy_coverage"), dict) else {}
    strategy_candidates = {
        strategy: int((strategy_coverage.get(strategy) if isinstance(strategy_coverage.get(strategy), dict) else {}).get("postmortem_ready_count") or 0)
        for strategy in CORE_STRATEGIES
    }
    summary = coverage.get("summary") if isinstance(coverage.get("summary"), dict) else {}
    postmortem_ready_count = int(summary.get("postmortem_ready_count") or 0)
    payload: dict[str, Any] = {
        "type": "decision_snapshot_postmortem_row_contract",
        "schema_version": "decision_snapshot_postmortem_row_contract_v1",
        "generated_at": iso_now(generated_at),
        **NO_EXECUTION_FLAGS,
        "status": "DECISION_SNAPSHOT_POSTMORTEM_ROW_CONTRACT_READY_DISABLED",
        "input_status": {
            "decision_snapshot_coverage_audit": coverage.get("status"),
        },
        "scope": {
            "source_artifact": str(COVERAGE_AUDIT),
            "contract_only": True,
            "append_allowed_now": False,
            "postmortem_row_append_executed": False,
            "confidence_update_allowed": False,
            "profit_or_edge_judgment_allowed": False,
            "outcome_interpretation_scope": "observation_only",
        },
        "postmortem_candidate_counts": {
            "total": postmortem_ready_count,
            "by_strategy": strategy_candidates,
        },
        "row_schema_contract": {
            "required_fields": REQUIRED_POSTMORTEM_FIELDS,
            "forbidden_fields": FORBIDDEN_POSTMORTEM_FIELDS,
            "field_contract": FIELD_CONTRACT,
            "required_links": [
                "decision_id",
                "paper_trade_id",
                "observation_only_outcome_ref",
            ],
            "append_target": "future_separate_postmortem_review_artifact_only",
            "ledger_mutation_allowed": False,
        },
        "example_row_shape": _example_row_shape(),
        "summary": {
            "postmortem_ready_snapshot_count": postmortem_ready_count,
            "strategy_postmortem_candidate_counts": strategy_candidates,
            "required_field_count": len(REQUIRED_POSTMORTEM_FIELDS),
            "forbidden_field_count": len(FORBIDDEN_POSTMORTEM_FIELDS),
            "append_allowed_now": False,
            "postmortem_rows_appended": 0,
            "permission_opened_count": 0,
            "confidence_increase_count": 0,
            "profit_or_edge_judgment_count": 0,
        },
        "operator_summary_ko": (
            "postmortem-ready decision snapshot에 나중에 붙일 row 계약만 정의했습니다. "
            "실제 append, 수익률/edge 판단, confidence 상승, shadow/live 연결은 수행하지 않았습니다."
        ),
        "recommended_next_action": "IMPLEMENT_SEPARATE_DRY_RUN_POSTMORTEM_BUILDER_ONLY_AFTER_OPERATOR_APPROVES_REVIEW_SCOPE",
        "artifact_contract_violations": [],
    }
    payload["artifact_contract_violations"] = validate_decision_snapshot_postmortem_row_contract(payload)
    if payload["artifact_contract_violations"]:
        payload["status"] = "DECISION_SNAPSHOT_POSTMORTEM_ROW_CONTRACT_BLOCKED"
    return payload


def validate_decision_snapshot_postmortem_row_contract(payload: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if payload.get("type") != "decision_snapshot_postmortem_row_contract":
        violations.append("type must be decision_snapshot_postmortem_row_contract")
    if payload.get("schema_version") != "decision_snapshot_postmortem_row_contract_v1":
        violations.append("schema_version must be decision_snapshot_postmortem_row_contract_v1")
    for flag, expected in NO_EXECUTION_FLAGS.items():
        if payload.get(flag) is not expected:
            violations.append(f"{flag} must be {str(expected).lower()}")
    scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else {}
    for key in ("append_allowed_now", "postmortem_row_append_executed", "confidence_update_allowed", "profit_or_edge_judgment_allowed"):
        if scope.get(key) is not False:
            violations.append(f"scope.{key} must be false")
    if scope.get("outcome_interpretation_scope") != "observation_only":
        violations.append("scope.outcome_interpretation_scope must be observation_only")
    row_contract = payload.get("row_schema_contract") if isinstance(payload.get("row_schema_contract"), dict) else {}
    required = row_contract.get("required_fields") if isinstance(row_contract.get("required_fields"), list) else []
    forbidden = row_contract.get("forbidden_fields") if isinstance(row_contract.get("forbidden_fields"), list) else []
    for field in REQUIRED_POSTMORTEM_FIELDS:
        if field not in required:
            violations.append(f"row_schema_contract.required_fields missing {field}")
    for field in FORBIDDEN_POSTMORTEM_FIELDS:
        if field not in forbidden:
            violations.append(f"row_schema_contract.forbidden_fields missing {field}")
    if row_contract.get("ledger_mutation_allowed") is not False:
        violations.append("row_schema_contract.ledger_mutation_allowed must be false")
    example = payload.get("example_row_shape") if isinstance(payload.get("example_row_shape"), dict) else {}
    for forbidden_field in forbidden:
        if forbidden_field in example:
            violations.append(f"example_row_shape must not include forbidden field {forbidden_field}")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    for key in ("append_allowed_now",):
        if summary.get(key) is not False:
            violations.append(f"summary.{key} must be false")
    for key in ("postmortem_rows_appended", "permission_opened_count", "confidence_increase_count", "profit_or_edge_judgment_count"):
        if summary.get(key) != 0:
            violations.append(f"summary.{key} must be 0")
    candidates = payload.get("postmortem_candidate_counts") if isinstance(payload.get("postmortem_candidate_counts"), dict) else {}
    by_strategy = candidates.get("by_strategy") if isinstance(candidates.get("by_strategy"), dict) else {}
    if sum(int(by_strategy.get(strategy) or 0) for strategy in CORE_STRATEGIES) != candidates.get("total"):
        violations.append("postmortem_candidate_counts.by_strategy must sum to total")
    if summary.get("postmortem_ready_snapshot_count") != candidates.get("total"):
        violations.append("summary.postmortem_ready_snapshot_count must match candidate total")
    return violations


def write_decision_snapshot_postmortem_row_contract(out_json: Path = DEFAULT_OUT) -> dict[str, Any]:
    payload = build_decision_snapshot_postmortem_row_contract()
    write_json(out_json, payload)
    return payload


def _example_row_shape() -> dict[str, Any]:
    return {
        "postmortem_id": "postmortem://decision-snapshot/<decision_id>",
        "decision_id": "<decision_id>",
        "paper_trade_id": "<paper_trade_id>",
        "strategy_id": "<LEFU|LVOR|MQRF>",
        "observation_only_outcome_ref": "<outcome_ref>",
        "favorable_movement": "NOT_REVIEWED",
        "adverse_movement": "NOT_REVIEWED",
        "missing_context_relevance": "NOT_REVIEWED",
        "blocker_relevance": "NOT_REVIEWED",
        "decision_replayability": "NOT_REVIEWED",
        "repeated_failure_pattern_candidate": "NOT_REVIEWED",
        "reviewer": "operator_or_deterministic_reviewer",
        "reviewed_at": "<iso8601>",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build decision snapshot postmortem row contract.")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    payload = write_decision_snapshot_postmortem_row_contract(Path(args.out_json))
    summary = payload["summary"]
    print(
        f"status={payload['status']} postmortem_ready={summary['postmortem_ready_snapshot_count']} "
        f"required_fields={summary['required_field_count']} forbidden_fields={summary['forbidden_field_count']} "
        f"append_allowed_now={summary['append_allowed_now']} violations={len(payload['artifact_contract_violations'])}"
    )
    return 0 if not payload["artifact_contract_violations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
