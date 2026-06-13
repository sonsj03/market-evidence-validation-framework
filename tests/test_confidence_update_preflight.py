from __future__ import annotations

from backtest.research.confidence_update_preflight import (
    build_confidence_update_preflight,
    validate_confidence_update_preflight,
)


def test_confidence_update_preflight_blocks_hold_no_change_results() -> None:
    payload = build_confidence_update_preflight(
        result_record=_result_record(),
        discussion_artifact=_discussion_artifact(),
        postmortem_rollup=_rollup(),
    )

    assert payload["status"] == "CONFIDENCE_UPDATE_PREFLIGHT_BLOCKED_NO_CHANGE"
    assert payload["summary"]["strategy_count"] == 3
    assert payload["summary"]["confidence_update_allowed_count"] == 0
    assert payload["summary"]["confidence_update_blocked_count"] == 3
    assert payload["summary"]["confidence_delta_total"] == 0
    assert payload["summary"]["confidence_increase_count"] == 0
    assert payload["strategy_preflight"]["LEFU"]["confidence_update_allowed"] is False
    assert payload["strategy_preflight"]["LEFU"]["confidence_delta"] == 0
    assert "manual discussion result is HOLD_CONFIDENCE_NO_CHANGE" in payload["strategy_preflight"]["LEFU"]["blocked_reasons"]
    assert payload["artifact_contract_violations"] == []


def test_confidence_update_preflight_carries_next_evidence_and_future_conditions() -> None:
    payload = build_confidence_update_preflight(
        result_record=_result_record(),
        discussion_artifact=_discussion_artifact(),
        postmortem_rollup=_rollup(),
    )
    lefu = payload["strategy_preflight"]["LEFU"]

    assert lefu["required_next_evidence"] == ["LEFU next evidence"]
    assert any("future contract" in item for item in lefu["future_update_conditions"])
    assert any("profit/edge/pnl" in item for item in lefu["future_update_conditions"])
    assert any("valid postmortem rows" in item for item in lefu["future_update_conditions"])


def test_confidence_update_preflight_blocks_request_more_evidence_result() -> None:
    result = _result_record()
    result["strategy_results"]["MQRF"]["discussion_result"] = "REQUEST_MORE_EVIDENCE"

    payload = build_confidence_update_preflight(
        result_record=result,
        discussion_artifact=_discussion_artifact(),
        postmortem_rollup=_rollup(),
    )

    assert payload["strategy_preflight"]["MQRF"]["confidence_update_allowed"] is False
    assert "manual discussion result is REQUEST_MORE_EVIDENCE" in payload["strategy_preflight"]["MQRF"]["blocked_reasons"]


def test_confidence_update_preflight_contract_rejects_update_or_permission_drift() -> None:
    payload = build_confidence_update_preflight(
        result_record=_result_record(),
        discussion_artifact=_discussion_artifact(),
        postmortem_rollup=_rollup(),
    )
    payload["scope"]["confidence_update_execution_allowed"] = True
    payload["summary"]["confidence_delta_total"] = 1
    payload["live_trading_allowed"] = True
    payload["strategy_preflight"]["LEFU"]["confidence_update_allowed"] = True
    payload["strategy_preflight"]["LEFU"]["confidence_delta"] = 1

    violations = validate_confidence_update_preflight(payload)

    assert "scope.confidence_update_execution_allowed must be false" in violations
    assert "summary.confidence_delta_total must be 0" in violations
    assert "live_trading_allowed must be false" in violations
    assert "LEFU.confidence_delta must be 0" in violations
    assert "LEFU.HOLD_CONFIDENCE_NO_CHANGE must block confidence update" in violations


def _result_record() -> dict:
    return {
        "status": "MANUAL_CONFIDENCE_DISCUSSION_RESULT_RECORD_READY",
        "strategy_results": {
            "LEFU": _result_row("LEFU", "LEFU next evidence"),
            "LVOR": _result_row("LVOR", "LVOR next evidence"),
            "MQRF": _result_row("MQRF", "MQRF next evidence"),
        },
    }


def _discussion_artifact() -> dict:
    return {
        "status": "MANUAL_CONFIDENCE_DISCUSSION_ARTIFACT_READY",
        "strategy_discussions": {
            "LEFU": _discussion_row("LEFU", 2),
            "LVOR": _discussion_row("LVOR", 1),
            "MQRF": _discussion_row("MQRF", 1),
        },
    }


def _rollup() -> dict:
    return {
        "status": "DECISION_SNAPSHOT_POSTMORTEM_EVIDENCE_ROLLUP_READY",
        "strategy_postmortem_evidence": {
            "LEFU": {"valid_postmortem_count": 2, "shadow_ref_optional_gap_count": 2},
            "LVOR": {"valid_postmortem_count": 1, "shadow_ref_optional_gap_count": 1},
            "MQRF": {"valid_postmortem_count": 1, "shadow_ref_optional_gap_count": 1},
        },
    }


def _result_row(strategy: str, next_evidence: str) -> dict:
    return {
        "discussion_result": "HOLD_CONFIDENCE_NO_CHANGE",
        "discussion_ready": True,
        "confidence_changed": False,
        "confidence_delta": 0,
        "confidence_change_blockers": [f"{strategy} blocker"],
        "next_required_evidence": [next_evidence],
    }


def _discussion_row(strategy: str, shadow_gap: int) -> dict:
    return {
        "discussion_ready": True,
        "current_evidence_counts": {
            "valid_postmortem_rows": 2,
            "shadow_ref_optional_gap": shadow_gap,
        },
        "next_required_evidence": [f"{strategy} discussion evidence"],
    }
