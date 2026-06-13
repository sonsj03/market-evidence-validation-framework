from __future__ import annotations

from backtest.research.decision_snapshot_postmortem_evidence_rollup import (
    READINESS_BLOCKED,
    READINESS_READY_WITH_OPTIONAL_GAPS,
    UNKNOWN_DISTRIBUTION_BUCKET,
    build_decision_snapshot_postmortem_evidence_rollup,
    validate_decision_snapshot_postmortem_evidence_rollup,
)


def test_postmortem_evidence_rollup_summarizes_strategy_counts_and_ready_discussion() -> None:
    payload = build_decision_snapshot_postmortem_evidence_rollup(
        ledger_audit=_ledger_audit(),
        shadow_ref_gap_closeout=_shadow_closeout(),
        coverage_audit=_coverage_audit(),
    )

    assert payload["status"] == "DECISION_SNAPSHOT_POSTMORTEM_EVIDENCE_ROLLUP_READY"
    assert payload["summary"]["postmortem_rows_total"] == 4
    assert payload["summary"]["valid_postmortem_rows"] == 4
    assert payload["summary"]["confidence_discussion_ready"] is True
    assert payload["confidence_discussion"]["readiness_state"] == READINESS_READY_WITH_OPTIONAL_GAPS
    assert payload["confidence_discussion"]["confidence_increase_count"] == 0
    assert payload["summary"]["confidence_increase_count"] == 0
    assert payload["summary"]["shadow_ref_optional_gap_count"] == 4
    assert payload["strategy_postmortem_evidence"]["LEFU"]["postmortem_count"] == 2
    assert payload["strategy_postmortem_evidence"]["LVOR"]["postmortem_count"] == 1
    assert payload["strategy_postmortem_evidence"]["MQRF"]["postmortem_count"] == 1
    assert payload["shadow_ref_optional_gap"]["kept_as_separate_gap"] is True
    assert payload["artifact_contract_violations"] == []


def test_postmortem_evidence_rollup_marks_relevance_distributions_unavailable_from_inputs() -> None:
    payload = build_decision_snapshot_postmortem_evidence_rollup(
        ledger_audit=_ledger_audit(),
        shadow_ref_gap_closeout=_shadow_closeout(),
        coverage_audit=_coverage_audit(),
    )

    for field in ("missing_context_relevance", "blocker_relevance", "decision_replayability"):
        distribution = payload["relevance_distributions"][field]
        assert distribution["source_status"] == "not_available_in_ledger_audit_input"
        assert distribution["distribution"][UNKNOWN_DISTRIBUTION_BUCKET] == 4

    gap_names = {gap["gap"] for gap in payload["major_remaining_gaps"]}
    assert "shadow_ref_optional_gap" in gap_names
    assert "funding_ready_context" in gap_names
    assert "missing_context_relevance_distribution_unavailable_in_input" in gap_names


def test_postmortem_evidence_rollup_blocks_discussion_on_invalid_rows_or_permission_leak() -> None:
    ledger = _ledger_audit()
    ledger["summary"]["valid_rows"] = 3
    ledger["summary"]["invalid_rows"] = 1
    ledger["summary"]["permission_leak_count"] = 1
    ledger["rows"][0]["row_valid"] = False

    payload = build_decision_snapshot_postmortem_evidence_rollup(
        ledger_audit=ledger,
        shadow_ref_gap_closeout=_shadow_closeout(),
        coverage_audit=_coverage_audit(),
    )

    assert payload["summary"]["confidence_discussion_ready"] is False
    assert payload["confidence_discussion"]["readiness_state"] == READINESS_BLOCKED
    assert payload["strategy_postmortem_evidence"]["LEFU"]["invalid_postmortem_count"] == 1


def test_postmortem_evidence_rollup_contract_rejects_confidence_or_execution_drift() -> None:
    payload = build_decision_snapshot_postmortem_evidence_rollup(
        ledger_audit=_ledger_audit(),
        shadow_ref_gap_closeout=_shadow_closeout(),
        coverage_audit=_coverage_audit(),
    )
    payload["scope"]["confidence_update_allowed"] = True
    payload["summary"]["confidence_increase_count"] = 1
    payload["shadow_ref_optional_gap"]["direct_backfill_allowed"] = True
    payload["live_trading_allowed"] = True

    violations = validate_decision_snapshot_postmortem_evidence_rollup(payload)

    assert "scope.confidence_update_allowed must be false" in violations
    assert "summary.confidence_increase_count must be 0" in violations
    assert "shadow_ref_optional_gap.direct_backfill_allowed must be false" in violations
    assert "live_trading_allowed must be false" in violations


def _ledger_audit() -> dict:
    rows = [
        _ledger_row("pm-1", "decision-1", "paper-1", "LEFU"),
        _ledger_row("pm-2", "decision-2", "paper-2", "LEFU"),
        _ledger_row("pm-3", "decision-3", "paper-3", "LVOR"),
        _ledger_row("pm-4", "decision-4", "paper-4", "MQRF"),
    ]
    return {
        "status": "DECISION_SNAPSHOT_POSTMORTEM_LEDGER_AUDIT_READY",
        "summary": {
            "ledger_rows_total": 4,
            "valid_rows": 4,
            "invalid_rows": 0,
            "permission_leak_count": 0,
            "forbidden_field_count": 0,
        },
        "rows": rows,
    }


def _shadow_closeout() -> dict:
    return {
        "status": "DECISION_SNAPSHOT_POSTMORTEM_SHADOW_REF_GAP_CLOSEOUT_READY",
        "classification": "OPTIONAL_GAP_FUTURE_AUGMENTATION",
        "summary": {
            "missing_shadow_ref_count": 4,
            "optional_shadow_ref_gap_rows": 4,
            "invalid_shadow_ref_gap_rows": 0,
        },
    }


def _coverage_audit() -> dict:
    return {
        "status": "DECISION_SNAPSHOT_COVERAGE_AUDIT_READY",
        "summary": {
            "total_snapshots": 6,
            "postmortem_ready_count": 4,
            "largest_missing_context": {"context": "funding_ready_context", "count": 6, "class": "optional_context"},
        },
        "strategy_coverage": {
            "LEFU": {
                "snapshot_count": 2,
                "postmortem_ready_count": 2,
                "source_linked_count": 2,
                "outcome_linked_count": 2,
                "shadow_linked_count": 2,
                "missing_context_by_class": {"optional_context": 2},
                "largest_missing_context": {"context": "funding_ready_context", "count": 2, "class": "optional_context"},
            },
            "LVOR": {
                "snapshot_count": 2,
                "postmortem_ready_count": 1,
                "source_linked_count": 1,
                "outcome_linked_count": 1,
                "shadow_linked_count": 2,
                "missing_context_by_class": {"optional_context": 2},
                "largest_missing_context": {"context": "funding_ready_context", "count": 2, "class": "optional_context"},
            },
            "MQRF": {
                "snapshot_count": 2,
                "postmortem_ready_count": 1,
                "source_linked_count": 1,
                "outcome_linked_count": 1,
                "shadow_linked_count": 1,
                "missing_context_by_class": {"optional_context": 2},
                "largest_missing_context": {"context": "funding_ready_context", "count": 2, "class": "optional_context"},
            },
        },
    }


def _ledger_row(postmortem_id: str, decision_id: str, paper_trade_id: str, strategy_id: str) -> dict:
    return {
        "postmortem_id": postmortem_id,
        "decision_id": decision_id,
        "paper_trade_id": paper_trade_id,
        "strategy_id": strategy_id,
        "row_valid": True,
        "missing_refs": ["shadow_ref"],
        "hard_violations": [],
    }
