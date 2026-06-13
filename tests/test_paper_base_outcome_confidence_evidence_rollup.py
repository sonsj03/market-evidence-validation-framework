from __future__ import annotations

from backtest.research.paper_base_outcome_confidence_evidence_rollup import (
    build_paper_base_outcome_confidence_evidence_rollup,
)


def test_base_outcome_confidence_rollup_links_paper_source_and_outcome_without_edge_claims() -> None:
    payload = build_paper_base_outcome_confidence_evidence_rollup(
        paper_ledger={
            "status": "PAPER_LEDGER_AUDIT_READY",
            "rows": [
                {
                    "paper_trade_id": "paper_1",
                    "strategy_id": "LVOR",
                    "row_valid_for_delayed_outcome_contract": True,
                }
            ],
        },
        source_ledger={"status": "OHLCV_SOURCE_LEDGER_AUDIT_READY", "valid_paper_trade_ids": ["paper_1"]},
        outcome_ledger={
            "status": "PAPER_OUTCOME_LEDGER_AUDIT_READY",
            "summary": {"valid_unique_outcome_paper_trade_ids": 1, "duplicate_logical_outcome_rows": 0},
            "rows": [{"paper_trade_id": "paper_1", "row_violations": []}],
        },
    )

    assert payload["status"] == "PAPER_BASE_OUTCOME_CONFIDENCE_EVIDENCE_ACCUMULATING"
    assert payload["summary"]["complete_evidence_chain_rows"] == 1
    assert payload["summary"]["base_outcome_unique_linked_rows"] == 1
    assert payload["summary"]["duplicate_logical_outcome_rows"] == 0
    assert payload["summary"]["confidence_raise_allowed_now"] is False
    assert payload["summary"]["shadow_review_ready_now"] is False
    assert payload["summary"]["profit_or_edge_judgment_made"] is False
    assert payload["artifact_contract_violations"] == []
