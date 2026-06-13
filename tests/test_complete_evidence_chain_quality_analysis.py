from __future__ import annotations

from datetime import UTC, datetime

from backtest.research.complete_evidence_chain_quality_analysis import (
    build_complete_evidence_chain_quality_analysis,
    validate_complete_evidence_chain_quality_analysis,
)


def test_complete_evidence_chain_quality_analysis_summarizes_reused_sources() -> None:
    payload = build_complete_evidence_chain_quality_analysis(
        artifacts=_artifacts(),
        ledgers=_ledgers(),
        generated_at=datetime(2026, 6, 13, tzinfo=UTC),
    )

    assert payload["status"] == "COMPLETE_EVIDENCE_CHAIN_QUALITY_ANALYSIS_READY_READ_ONLY"
    assert payload["summary"]["complete_chain_count"] == 2
    assert payload["summary"]["reused_window_source_linkage_count"] == 1
    assert payload["summary"]["confidence_delta_total"] == 0
    assert payload["summary"]["permission_opened_count"] == 0
    assert payload["strategy_summary"]["LEFU"]["complete_chain_count"] == 1
    assert payload["strategy_summary"]["LVOR"]["reused_window_source_linkage_count"] == 1
    assert payload["rows"][1]["source_quality_tier"] == "TIER_1_REPLAY_SAFE_REUSED_WINDOW_SOURCE"
    assert payload["artifact_contract_violations"] == []


def test_complete_evidence_chain_quality_analysis_rejects_permission_drift() -> None:
    payload = build_complete_evidence_chain_quality_analysis(artifacts=_artifacts(), ledgers=_ledgers())
    payload["summary"]["confidence_delta_total"] = 1
    payload["scope"]["confidence_update_allowed"] = True
    payload["rows"][0]["confidence_update_allowed"] = True

    violations = validate_complete_evidence_chain_quality_analysis(payload)

    assert "summary.confidence_delta_total must be 0" in violations
    assert "scope.confidence_update_allowed must be false" in violations
    assert any("confidence_update_allowed must be false" in violation for violation in violations)


def _artifacts() -> dict:
    return {
        "confidence_rollup": {
            "status": "READY",
            "rows": [
                {
                    "paper_trade_id": "paper-lefu-a",
                    "strategy_id": "LEFU",
                    "paper_source_outcome_chain_complete": True,
                },
                {
                    "paper_trade_id": "paper-lvor-b",
                    "strategy_id": "LVOR",
                    "paper_source_outcome_chain_complete": True,
                },
            ],
        },
        "decision_snapshot_layer": {
            "status": "READY",
            "snapshots": [
                _snapshot("paper-lefu-a", "LEFU", "decision-a"),
                _snapshot("paper-lvor-b", "LVOR", "decision-b"),
            ],
        },
        "source_ledger_audit": {"status": "READY"},
        "outcome_ledger_audit": {"status": "READY"},
        "postmortem_ledger_audit": {"status": "READY"},
        "context_summary": {
            "status": "READY",
            "rows": [
                {"strategy_id": "LEFU", "context_source_rows": 3, "explanation_linked_windows": 2, "remaining_ambiguity_count": 1},
                {"strategy_id": "LVOR", "context_source_rows": 3, "explanation_linked_windows": 2, "remaining_ambiguity_count": 1},
            ],
        },
        "regime_rollup": {
            "status": "READY",
            "rows": [
                {"strategy_id": "LEFU", "dominant_internal_regime_tag": "liquidation_cascade", "mapped_context_window_count": 2, "context_source_kinds": ["OI"], "direct_confidence_input_candidate_count": 0},
                {"strategy_id": "LVOR", "dominant_internal_regime_tag": "orderbook_fragility", "mapped_context_window_count": 2, "context_source_kinds": ["ORDERBOOK"], "direct_confidence_input_candidate_count": 0},
            ],
        },
        "candidate_queue": {"summary": {"remaining_dry_run_candidate_count": 0}},
        "ohlcv_coverage_inventory": {"summary": {"unavailable_gap_rows": 3}},
    }


def _ledgers() -> dict:
    return {
        "source_rows": [
            {
                "paper_trade_id": "paper-lefu-a",
                "source_row_id": "source-a",
                "source_row_hash": "sha256:a",
                "source_type": "PUBLIC_EXCHANGE_OHLCV_ONE_SHOT",
                "known_at_validated": True,
                "archive_written_ts": "2026-06-03T00:00:00+00:00",
                "outcome_window_start_ts": "2026-06-02T00:00:00+00:00",
                "outcome_window_end_ts": "2026-06-03T00:00:00+00:00",
            }
        ],
        "linkage_rows": [
            {
                "target_paper_trade_id": "paper-lvor-b",
                "strategy_id": "LVOR",
                "source_row_id": "source-a",
                "source_row_hash": "sha256:a",
                "window_source_id": "sha256:window-a",
                "source_owner_paper_trade_id": "paper-lefu-a",
            }
        ],
        "outcome_rows": [
            _outcome("paper-lefu-a", "source-a"),
            _outcome("paper-lvor-b", "source-a"),
        ],
        "postmortem_rows": [
            _postmortem("paper-lefu-a", "LEFU", "decision-a"),
            _postmortem("paper-lvor-b", "LVOR", "decision-b"),
        ],
    }


def _snapshot(paper_id: str, strategy: str, decision_id: str) -> dict:
    return {
        "paper_trade_id": paper_id,
        "strategy_id": strategy,
        "decision_id": decision_id,
        "decision_ts": "2026-06-02T00:00:00+00:00",
        "symbol": "BTC/USDT",
        "source_refs": [{"source_row_id": "source-a", "source_row_hash": "sha256:a"}],
        "outcome_refs": [{"outcome_row_id": f"outcome-{paper_id}", "source_ref_exact_match": True}],
        "missing_context": ["funding_ready_context"],
    }


def _outcome(paper_id: str, source_id: str) -> dict:
    return {
        "paper_trade_id": paper_id,
        "outcome_row_id": f"outcome-{paper_id}",
        "source_row_id": source_id,
        "outcome_payload_contract": {
            "observed_window_start_ts": "2026-06-02T00:00:00+00:00",
            "observed_window_end_ts": "2026-06-03T00:00:00+00:00",
            "no_profit_claim": True,
            "no_edge_claim": True,
            "no_threshold_update": True,
        },
        "outcome_recorded_at_ts": "2026-06-03T00:00:00+00:00",
    }


def _postmortem(paper_id: str, strategy: str, decision_id: str) -> dict:
    return {
        "paper_trade_id": paper_id,
        "strategy_id": strategy,
        "decision_id": decision_id,
        "postmortem_id": f"postmortem-{paper_id}",
        "decision_replayability": "REPLAYABLE",
        "confidence_update": False,
        "appended_at": "2026-06-04T00:00:00+00:00",
    }
