"""Preflight confidence updates without allowing any confidence change."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.research.decision_snapshot_input_adapters import CORE_STRATEGIES
from backtest.research.paper_evidence_loop_common import NO_EXECUTION_FLAGS, iso_now, read_json, write_json


RESULTS = Path("backtest/results")
DEFAULT_OUT = RESULTS / "confidence_update_preflight_latest.json"
RESULT_RECORD = RESULTS / "manual_confidence_discussion_result_record_latest.json"
DISCUSSION_ARTIFACT = RESULTS / "manual_confidence_discussion_artifact_latest.json"
POSTMORTEM_ROLLUP = RESULTS / "decision_snapshot_postmortem_evidence_rollup_latest.json"

RESULTS_THAT_BLOCK_UPDATE = {
    "HOLD_CONFIDENCE_NO_CHANGE",
    "REQUEST_MORE_EVIDENCE",
    "KEEP_DISCUSSION_OPEN",
    "KEEP_FILTER_ONLY",
}


def build_confidence_update_preflight(
    *,
    result_record: dict[str, Any] | None = None,
    discussion_artifact: dict[str, Any] | None = None,
    postmortem_rollup: dict[str, Any] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    result = result_record if result_record is not None else read_json(RESULT_RECORD)
    discussion = discussion_artifact if discussion_artifact is not None else read_json(DISCUSSION_ARTIFACT)
    rollup = postmortem_rollup if postmortem_rollup is not None else read_json(POSTMORTEM_ROLLUP)
    strategies = _strategy_preflights(result, discussion, rollup)
    payload: dict[str, Any] = {
        "type": "confidence_update_preflight",
        "schema_version": "confidence_update_preflight_v1",
        "generated_at": iso_now(generated_at),
        **NO_EXECUTION_FLAGS,
        "status": "CONFIDENCE_UPDATE_PREFLIGHT_BLOCKED_NO_CHANGE",
        "input_status": {
            "manual_confidence_discussion_result_record": result.get("status"),
            "manual_confidence_discussion_artifact": discussion.get("status"),
            "decision_snapshot_postmortem_evidence_rollup": rollup.get("status"),
        },
        "scope": {
            "preflight_only": True,
            "confidence_update_execution_allowed": False,
            "confidence_increase_allowed": False,
            "profit_edge_judgment_allowed": False,
            "ledger_append_allowed": False,
            "shadow_live_scanner_executor_allowed": False,
        },
        "strategy_preflight": strategies,
        "summary": {
            "strategy_count": len(strategies),
            "confidence_update_allowed_count": sum(1 for row in strategies.values() if row["confidence_update_allowed"]),
            "confidence_update_blocked_count": sum(1 for row in strategies.values() if not row["confidence_update_allowed"]),
            "confidence_delta_total": 0,
            "confidence_increase_count": 0,
            "profit_or_edge_judgment_count": 0,
            "permission_opened_count": 0,
            "shadow_live_scanner_executor_connected": False,
        },
        "operator_summary_ko": _operator_summary_ko(strategies),
        "artifact_contract_violations": [],
    }
    payload["artifact_contract_violations"] = validate_confidence_update_preflight(payload)
    if payload["artifact_contract_violations"]:
        payload["status"] = "CONFIDENCE_UPDATE_PREFLIGHT_CONTRACT_BLOCKED"
    return payload


def validate_confidence_update_preflight(payload: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if payload.get("type") != "confidence_update_preflight":
        violations.append("type must be confidence_update_preflight")
    if payload.get("schema_version") != "confidence_update_preflight_v1":
        violations.append("schema_version must be confidence_update_preflight_v1")
    for flag, expected in NO_EXECUTION_FLAGS.items():
        if payload.get(flag) is not expected:
            violations.append(f"{flag} must be {str(expected).lower()}")
    scope = _dict_value(payload.get("scope"))
    for key in (
        "confidence_update_execution_allowed",
        "confidence_increase_allowed",
        "profit_edge_judgment_allowed",
        "ledger_append_allowed",
        "shadow_live_scanner_executor_allowed",
    ):
        if scope.get(key) is not False:
            violations.append(f"scope.{key} must be false")
    if scope.get("preflight_only") is not True:
        violations.append("scope.preflight_only must be true")
    summary = _dict_value(payload.get("summary"))
    if summary.get("confidence_delta_total") != 0:
        violations.append("summary.confidence_delta_total must be 0")
    for key in ("confidence_increase_count", "profit_or_edge_judgment_count", "permission_opened_count"):
        if summary.get(key) != 0:
            violations.append(f"summary.{key} must be 0")
    if summary.get("shadow_live_scanner_executor_connected") is not False:
        violations.append("summary.shadow_live_scanner_executor_connected must be false")
    strategies = _dict_value(payload.get("strategy_preflight"))
    for strategy in CORE_STRATEGIES:
        if strategy not in strategies:
            violations.append(f"strategy_preflight.{strategy} must be present")
    if summary.get("strategy_count") != len(strategies):
        violations.append("summary.strategy_count must match strategy_preflight")
    allowed_count = 0
    blocked_count = 0
    for strategy, row in strategies.items():
        item = _dict_value(row)
        if item.get("confidence_update_allowed") is True:
            allowed_count += 1
        else:
            blocked_count += 1
        if item.get("confidence_delta") != 0:
            violations.append(f"{strategy}.confidence_delta must be 0")
        if item.get("confidence_increase_allowed") is not False:
            violations.append(f"{strategy}.confidence_increase_allowed must be false")
        if item.get("live_or_shadow_allowed") is not False:
            violations.append(f"{strategy}.live_or_shadow_allowed must be false")
        if not isinstance(item.get("blocked_reasons"), list):
            violations.append(f"{strategy}.blocked_reasons must be list")
        if not isinstance(item.get("required_next_evidence"), list):
            violations.append(f"{strategy}.required_next_evidence must be list")
        if item.get("source_discussion_result") == "HOLD_CONFIDENCE_NO_CHANGE" and item.get("confidence_update_allowed") is not False:
            violations.append(f"{strategy}.HOLD_CONFIDENCE_NO_CHANGE must block confidence update")
    if summary.get("confidence_update_allowed_count") != allowed_count:
        violations.append("summary.confidence_update_allowed_count must match rows")
    if summary.get("confidence_update_blocked_count") != blocked_count:
        violations.append("summary.confidence_update_blocked_count must match rows")
    return violations


def write_confidence_update_preflight(out_json: Path = DEFAULT_OUT) -> dict[str, Any]:
    payload = build_confidence_update_preflight()
    write_json(out_json, payload)
    return payload


def _strategy_preflights(result: dict[str, Any], discussion: dict[str, Any], rollup: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result_rows = _dict_value(result.get("strategy_results"))
    discussion_rows = _dict_value(discussion.get("strategy_discussions"))
    rollup_rows = _dict_value(rollup.get("strategy_postmortem_evidence"))
    out: dict[str, dict[str, Any]] = {}
    for strategy in CORE_STRATEGIES:
        result_row = _dict_value(result_rows.get(strategy))
        discussion_row = _dict_value(discussion_rows.get(strategy))
        rollup_row = _dict_value(rollup_rows.get(strategy))
        source_result = str(result_row.get("discussion_result") or "REQUEST_MORE_EVIDENCE")
        blocked_reasons = _blocked_reasons(source_result, result_row, discussion_row, rollup_row)
        out[strategy] = {
            "confidence_update_allowed": False,
            "confidence_delta": 0,
            "confidence_increase_allowed": False,
            "live_or_shadow_allowed": False,
            "source_discussion_result": source_result,
            "source_discussion_ready": result_row.get("discussion_ready") is True or discussion_row.get("discussion_ready") is True,
            "blocked_reasons": blocked_reasons,
            "required_next_evidence": _required_next_evidence(result_row, discussion_row),
            "future_update_conditions": _future_update_conditions(strategy, result_row, discussion_row, rollup_row),
            "operator_summary_ko": _strategy_summary_ko(strategy, source_result, blocked_reasons),
        }
    return out


def _blocked_reasons(source_result: str, result_row: dict[str, Any], discussion_row: dict[str, Any], rollup_row: dict[str, Any]) -> list[str]:
    reasons = ["confidence update execution is disabled by preflight scope"]
    if source_result in RESULTS_THAT_BLOCK_UPDATE:
        reasons.append(f"manual discussion result is {source_result}")
    if result_row.get("confidence_changed") is not False:
        reasons.append("source result record did not preserve confidence_changed=false")
    if result_row.get("confidence_delta") not in (None, 0):
        reasons.append("source result record has non-zero confidence_delta")
    blockers = result_row.get("confidence_change_blockers") if isinstance(result_row.get("confidence_change_blockers"), list) else []
    if blockers:
        reasons.append("confidence change blockers remain from manual discussion")
    if int(discussion_row.get("current_evidence_counts", {}).get("shadow_ref_optional_gap") or rollup_row.get("shadow_ref_optional_gap_count") or 0):
        reasons.append("shadow_ref optional gap remains")
    return reasons


def _required_next_evidence(result_row: dict[str, Any], discussion_row: dict[str, Any]) -> list[str]:
    evidence = result_row.get("next_required_evidence") if isinstance(result_row.get("next_required_evidence"), list) else []
    if not evidence:
        evidence = discussion_row.get("next_required_evidence") if isinstance(discussion_row.get("next_required_evidence"), list) else []
    if not evidence:
        evidence = ["manual discussion result must explicitly request evidence before confidence update"]
    return [str(item) for item in evidence]


def _future_update_conditions(strategy: str, result_row: dict[str, Any], discussion_row: dict[str, Any], rollup_row: dict[str, Any]) -> list[str]:
    return [
        f"{strategy} manual discussion result must change from HOLD_CONFIDENCE_NO_CHANGE to an explicitly approved update record in a future contract",
        "a separate confidence update writer/preflight must be approved with confidence_delta source and reviewer",
        "profit/edge/pnl fields must remain absent from the update request",
        "shadow/live/scanner/executor permissions must remain closed",
        "remaining blockers must be resolved or explicitly accepted as non-blocking by a future manual approval artifact",
        f"current valid postmortem rows available for discussion: {int(rollup_row.get('valid_postmortem_count') or discussion_row.get('current_evidence_counts', {}).get('valid_postmortem_rows') or 0)}",
        f"current result confidence_delta must remain 0 now: {int(result_row.get('confidence_delta') or 0)}",
    ]


def _strategy_summary_ko(strategy: str, source_result: str, blocked_reasons: list[str]) -> str:
    return f"{strategy}: confidence update는 현재 불가입니다. result={source_result}, confidence_delta=0, 차단 사유 {len(blocked_reasons)}개."


def _operator_summary_ko(strategies: dict[str, dict[str, Any]]) -> str:
    parts = [
        f"{strategy}=allowed:{str(row['confidence_update_allowed']).lower()}, delta:{row['confidence_delta']}, result:{row['source_discussion_result']}"
        for strategy, row in strategies.items()
    ]
    return (
        "Confidence Update Preflight입니다. "
        + "; ".join(parts)
        + ". 현재 HOLD_CONFIDENCE_NO_CHANGE 결과 때문에 confidence update는 모두 차단되며, confidence_delta는 항상 0입니다."
    )


def _dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build confidence update preflight.")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    payload = write_confidence_update_preflight(Path(args.out_json))
    summary = payload["summary"]
    print(
        f"status={payload['status']} strategies={summary['strategy_count']} "
        f"allowed={summary['confidence_update_allowed_count']} blocked={summary['confidence_update_blocked_count']} "
        f"delta={summary['confidence_delta_total']} violations={len(payload['artifact_contract_violations'])}"
    )
    return 0 if not payload["artifact_contract_violations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
