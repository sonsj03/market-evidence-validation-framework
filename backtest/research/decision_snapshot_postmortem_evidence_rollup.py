"""Roll up decision snapshot postmortem evidence without changing confidence."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.research.decision_snapshot_input_adapters import CORE_STRATEGIES
from backtest.research.paper_evidence_loop_common import NO_EXECUTION_FLAGS, iso_now, read_json, write_json


RESULTS = Path("backtest/results")
DEFAULT_OUT = RESULTS / "decision_snapshot_postmortem_evidence_rollup_latest.json"
LEDGER_AUDIT = RESULTS / "decision_snapshot_postmortem_ledger_audit_latest.json"
SHADOW_REF_CLOSEOUT = RESULTS / "decision_snapshot_postmortem_shadow_ref_gap_closeout_latest.json"
COVERAGE_AUDIT = RESULTS / "decision_snapshot_coverage_audit_latest.json"

READINESS_READY_WITH_OPTIONAL_GAPS = "READY_WITH_OPTIONAL_GAPS"
READINESS_BLOCKED = "BLOCKED_BY_POSTMORTEM_EVIDENCE_ISSUES"
READINESS_NOT_READY = "NOT_READY_NO_VALID_POSTMORTEM_ROWS"
UNKNOWN_DISTRIBUTION_BUCKET = "UNKNOWN_NOT_AVAILABLE_IN_INPUT_ARTIFACTS"


def build_decision_snapshot_postmortem_evidence_rollup(
    *,
    ledger_audit: dict[str, Any] | None = None,
    shadow_ref_gap_closeout: dict[str, Any] | None = None,
    coverage_audit: dict[str, Any] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    ledger = ledger_audit if ledger_audit is not None else read_json(LEDGER_AUDIT)
    shadow_closeout = shadow_ref_gap_closeout if shadow_ref_gap_closeout is not None else read_json(SHADOW_REF_CLOSEOUT)
    coverage = coverage_audit if coverage_audit is not None else read_json(COVERAGE_AUDIT)
    ledger_summary = _dict_value(ledger.get("summary"))
    shadow_summary = _dict_value(shadow_closeout.get("summary"))
    coverage_summary = _dict_value(coverage.get("summary"))
    rows = [row for row in ledger.get("rows", []) if isinstance(row, dict)] if isinstance(ledger.get("rows"), list) else []
    strategy_rollup = _strategy_rollup(rows, coverage)
    relevance_distributions = _relevance_distributions(rows)
    confidence_discussion_ready = _confidence_discussion_ready(ledger_summary, shadow_summary, rows)
    readiness_state = _readiness_state(confidence_discussion_ready, ledger_summary, rows)
    payload: dict[str, Any] = {
        "type": "decision_snapshot_postmortem_evidence_rollup",
        "schema_version": "decision_snapshot_postmortem_evidence_rollup_v1",
        "generated_at": iso_now(generated_at),
        **NO_EXECUTION_FLAGS,
        "status": "DECISION_SNAPSHOT_POSTMORTEM_EVIDENCE_ROLLUP_READY",
        "input_status": {
            "decision_snapshot_postmortem_ledger_audit": ledger.get("status"),
            "decision_snapshot_postmortem_shadow_ref_gap_closeout": shadow_closeout.get("status"),
            "decision_snapshot_coverage_audit": coverage.get("status"),
        },
        "scope": {
            "confidence_update_allowed": False,
            "confidence_discussion_only": True,
            "profit_edge_judgment_allowed": False,
            "ledger_append_allowed": False,
            "shadow_ref_direct_backfill_allowed": False,
            "shadow_runtime_allowed": False,
        },
        "confidence_discussion": {
            "ready": confidence_discussion_ready,
            "readiness_state": readiness_state,
            "confidence_increase_count": 0,
            "reason_codes": _confidence_discussion_reason_codes(ledger_summary, shadow_summary, rows),
        },
        "strategy_postmortem_evidence": strategy_rollup,
        "relevance_distributions": relevance_distributions,
        "shadow_ref_optional_gap": {
            "count": int(shadow_summary.get("optional_shadow_ref_gap_rows") or shadow_summary.get("missing_shadow_ref_count") or 0),
            "classification": shadow_closeout.get("classification"),
            "kept_as_separate_gap": True,
            "invalid_row_count": int(shadow_summary.get("invalid_shadow_ref_gap_rows") or 0),
            "direct_backfill_allowed": False,
        },
        "major_remaining_gaps": _major_remaining_gaps(shadow_summary, coverage_summary, relevance_distributions),
        "summary": {
            "postmortem_rows_total": int(ledger_summary.get("ledger_rows_total") or len(rows)),
            "valid_postmortem_rows": int(ledger_summary.get("valid_rows") or 0),
            "invalid_postmortem_rows": int(ledger_summary.get("invalid_rows") or 0),
            "confidence_discussion_ready": confidence_discussion_ready,
            "confidence_increase_count": 0,
            "shadow_ref_optional_gap_count": int(shadow_summary.get("optional_shadow_ref_gap_rows") or shadow_summary.get("missing_shadow_ref_count") or 0),
            "permission_opened_count": 0,
            "profit_or_edge_judgment_count": 0,
            "shadow_live_scanner_executor_connected": False,
            "coverage_total_snapshots": int(coverage_summary.get("total_snapshots") or 0),
            "coverage_postmortem_ready_count": int(coverage_summary.get("postmortem_ready_count") or 0),
        },
        "operator_summary_ko": (
            "postmortem evidence를 strategy별로 rollup했습니다. 이 artifact는 confidence discussion readiness만 계산하며 "
            "confidence 상승, profit/edge 판단, shadow/live/scanner/executor 연결은 수행하지 않습니다."
        ),
        "recommended_next_action": "USE_ROLLUP_FOR_MANUAL_CONFIDENCE_DISCUSSION_ONLY_WITHOUT_CONFIDENCE_CHANGE",
        "artifact_contract_violations": [],
    }
    payload["artifact_contract_violations"] = validate_decision_snapshot_postmortem_evidence_rollup(payload)
    if payload["artifact_contract_violations"]:
        payload["status"] = "DECISION_SNAPSHOT_POSTMORTEM_EVIDENCE_ROLLUP_CONTRACT_BLOCKED"
    return payload


def validate_decision_snapshot_postmortem_evidence_rollup(payload: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if payload.get("type") != "decision_snapshot_postmortem_evidence_rollup":
        violations.append("type must be decision_snapshot_postmortem_evidence_rollup")
    if payload.get("schema_version") != "decision_snapshot_postmortem_evidence_rollup_v1":
        violations.append("schema_version must be decision_snapshot_postmortem_evidence_rollup_v1")
    for flag, expected in NO_EXECUTION_FLAGS.items():
        if payload.get(flag) is not expected:
            violations.append(f"{flag} must be {str(expected).lower()}")
    scope = _dict_value(payload.get("scope"))
    for key in ("confidence_update_allowed", "profit_edge_judgment_allowed", "ledger_append_allowed", "shadow_ref_direct_backfill_allowed", "shadow_runtime_allowed"):
        if scope.get(key) is not False:
            violations.append(f"scope.{key} must be false")
    if scope.get("confidence_discussion_only") is not True:
        violations.append("scope.confidence_discussion_only must be true")
    summary = _dict_value(payload.get("summary"))
    for key in ("confidence_increase_count", "permission_opened_count", "profit_or_edge_judgment_count"):
        if summary.get(key) != 0:
            violations.append(f"summary.{key} must be 0")
    if summary.get("shadow_live_scanner_executor_connected") is not False:
        violations.append("summary.shadow_live_scanner_executor_connected must be false")
    confidence = _dict_value(payload.get("confidence_discussion"))
    if confidence.get("confidence_increase_count") != 0:
        violations.append("confidence_discussion.confidence_increase_count must be 0")
    strategies = _dict_value(payload.get("strategy_postmortem_evidence"))
    for strategy in CORE_STRATEGIES:
        if strategy not in strategies:
            violations.append(f"strategy_postmortem_evidence.{strategy} must be present")
    total_strategy_rows = sum(int(_dict_value(row).get("postmortem_count") or 0) for row in strategies.values())
    if total_strategy_rows != summary.get("postmortem_rows_total"):
        violations.append("strategy postmortem counts must sum to summary.postmortem_rows_total")
    shadow_gap = _dict_value(payload.get("shadow_ref_optional_gap"))
    if shadow_gap.get("kept_as_separate_gap") is not True:
        violations.append("shadow_ref_optional_gap.kept_as_separate_gap must be true")
    if shadow_gap.get("direct_backfill_allowed") is not False:
        violations.append("shadow_ref_optional_gap.direct_backfill_allowed must be false")
    return violations


def write_decision_snapshot_postmortem_evidence_rollup(out_json: Path = DEFAULT_OUT) -> dict[str, Any]:
    payload = build_decision_snapshot_postmortem_evidence_rollup()
    write_json(out_json, payload)
    return payload


def _strategy_rollup(rows: list[dict[str, Any]], coverage: dict[str, Any]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("strategy_id") or "UNKNOWN")].append(row)
    coverage_by_strategy = _dict_value(coverage.get("strategy_coverage"))
    out: dict[str, dict[str, Any]] = {}
    for strategy in CORE_STRATEGIES:
        strategy_rows = grouped.get(strategy, [])
        strategy_coverage = _dict_value(coverage_by_strategy.get(strategy))
        out[strategy] = {
            "postmortem_count": len(strategy_rows),
            "valid_postmortem_count": sum(1 for row in strategy_rows if row.get("row_valid") is True),
            "invalid_postmortem_count": sum(1 for row in strategy_rows if row.get("row_valid") is False),
            "snapshot_count": int(strategy_coverage.get("snapshot_count") or 0),
            "coverage_postmortem_ready_count": int(strategy_coverage.get("postmortem_ready_count") or 0),
            "coverage_source_linked_count": int(strategy_coverage.get("source_linked_count") or 0),
            "coverage_outcome_linked_count": int(strategy_coverage.get("outcome_linked_count") or 0),
            "coverage_shadow_linked_count": int(strategy_coverage.get("shadow_linked_count") or 0),
            "shadow_ref_optional_gap_count": sum(1 for row in strategy_rows if "shadow_ref" in _list_value(row.get("missing_refs"))),
            "confidence_discussion_ready": bool(strategy_rows) and all(row.get("row_valid") is True for row in strategy_rows),
            "missing_context_by_class": _dict_value(strategy_coverage.get("missing_context_by_class")),
            "largest_missing_context": _dict_value(strategy_coverage.get("largest_missing_context")),
        }
    return out


def _relevance_distributions(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    distributions: dict[str, dict[str, Any]] = {}
    for field in ("missing_context_relevance", "blocker_relevance", "decision_replayability"):
        counts = Counter(str(row.get(field)) for row in rows if row.get(field))
        if not counts and rows:
            distributions[field] = {
                "distribution": {UNKNOWN_DISTRIBUTION_BUCKET: len(rows)},
                "source_status": "not_available_in_ledger_audit_input",
            }
        else:
            distributions[field] = {
                "distribution": dict(sorted(counts.items())),
                "source_status": "available",
            }
    return distributions


def _confidence_discussion_ready(ledger_summary: dict[str, Any], shadow_summary: dict[str, Any], rows: list[dict[str, Any]]) -> bool:
    return (
        bool(rows)
        and int(ledger_summary.get("valid_rows") or 0) == len(rows)
        and int(ledger_summary.get("invalid_rows") or 0) == 0
        and int(ledger_summary.get("permission_leak_count") or 0) == 0
        and int(ledger_summary.get("forbidden_field_count") or 0) == 0
        and int(shadow_summary.get("invalid_shadow_ref_gap_rows") or 0) == 0
    )


def _readiness_state(confidence_discussion_ready: bool, ledger_summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    if not rows or int(ledger_summary.get("valid_rows") or 0) == 0:
        return READINESS_NOT_READY
    if confidence_discussion_ready:
        return READINESS_READY_WITH_OPTIONAL_GAPS
    return READINESS_BLOCKED


def _confidence_discussion_reason_codes(ledger_summary: dict[str, Any], shadow_summary: dict[str, Any], rows: list[dict[str, Any]]) -> list[str]:
    reasons: list[str] = []
    if rows:
        reasons.append("valid_postmortem_evidence_rows_present")
    if int(ledger_summary.get("permission_leak_count") or 0) == 0:
        reasons.append("no_permission_leaks")
    if int(ledger_summary.get("forbidden_field_count") or 0) == 0:
        reasons.append("no_profit_edge_confidence_forbidden_fields")
    if int(shadow_summary.get("optional_shadow_ref_gap_rows") or 0) > 0:
        reasons.append("shadow_ref_optional_gap_kept_separate")
    if int(shadow_summary.get("invalid_shadow_ref_gap_rows") or 0) > 0:
        reasons.append("invalid_shadow_ref_gap_blocks_discussion")
    return reasons


def _major_remaining_gaps(shadow_summary: dict[str, Any], coverage_summary: dict[str, Any], relevance_distributions: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    shadow_gap_count = int(shadow_summary.get("optional_shadow_ref_gap_rows") or shadow_summary.get("missing_shadow_ref_count") or 0)
    if shadow_gap_count:
        gaps.append({"gap": "shadow_ref_optional_gap", "count": shadow_gap_count, "class": "optional_future_augmentation"})
    largest = coverage_summary.get("largest_missing_context")
    if isinstance(largest, dict) and largest.get("count"):
        gaps.append({"gap": str(largest.get("context")), "count": int(largest.get("count") or 0), "class": str(largest.get("class") or "unknown")})
    for field, distribution in relevance_distributions.items():
        if distribution.get("source_status") != "available":
            unknown_count = int(_dict_value(distribution.get("distribution")).get(UNKNOWN_DISTRIBUTION_BUCKET) or 0)
            gaps.append({"gap": f"{field}_distribution_unavailable_in_input", "count": unknown_count, "class": "rollup_input_gap"})
    return gaps


def _dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def main() -> int:
    parser = argparse.ArgumentParser(description="Build decision snapshot postmortem evidence rollup.")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    payload = write_decision_snapshot_postmortem_evidence_rollup(Path(args.out_json))
    summary = payload["summary"]
    print(
        f"status={payload['status']} rows={summary['postmortem_rows_total']} valid={summary['valid_postmortem_rows']} "
        f"confidence_discussion_ready={summary['confidence_discussion_ready']} "
        f"shadow_ref_optional_gap={summary['shadow_ref_optional_gap_count']} "
        f"violations={len(payload['artifact_contract_violations'])}"
    )
    return 0 if not payload["artifact_contract_violations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
