"""Roll up paper/source/base-outcome evidence without profit or edge claims."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.research.paper_evidence_loop_common import NO_EXECUTION_FLAGS, iso_now, read_json, write_json


RESULTS = Path("backtest/results")
DEFAULT_OUT = RESULTS / "paper_base_outcome_confidence_evidence_rollup_latest.json"
PAPER_LEDGER = RESULTS / "paper_ledger_audit_latest.json"
SOURCE_LEDGER = RESULTS / "ohlcv_source_ledger_audit_latest.json"
BYBIT_ORDERBOOK_SOURCE_LEDGER = RESULTS / "bybit_orderbook_source_ledger_audit_latest.json"
OUTCOME_LEDGER = RESULTS / "paper_outcome_ledger_audit_latest.json"
LINKAGE_LEDGER = RESULTS / "ohlcv_capture" / "ohlcv_window_source_reuse_linkages.jsonl"


def build_paper_base_outcome_confidence_evidence_rollup(
    *,
    paper_ledger: dict[str, Any] | None = None,
    source_ledger: dict[str, Any] | None = None,
    bybit_orderbook_source_ledger: dict[str, Any] | None = None,
    outcome_ledger: dict[str, Any] | None = None,
    linkage_rows: list[dict[str, Any]] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    source_ledger_was_supplied = source_ledger is not None
    paper_ledger = paper_ledger if paper_ledger is not None else read_json(PAPER_LEDGER)
    source_ledger = source_ledger if source_ledger is not None else read_json(SOURCE_LEDGER)
    bybit_orderbook_source_ledger = (
        bybit_orderbook_source_ledger
        if bybit_orderbook_source_ledger is not None
        else ({} if source_ledger_was_supplied else read_json(BYBIT_ORDERBOOK_SOURCE_LEDGER))
    )
    outcome_ledger = outcome_ledger if outcome_ledger is not None else read_json(OUTCOME_LEDGER)
    if linkage_rows is None:
        from backtest.research.paper_evidence_loop_common import read_jsonl

        linkage_rows = read_jsonl(LINKAGE_LEDGER)[0]
    paper_rows = paper_ledger.get("rows") if isinstance(paper_ledger.get("rows"), list) else []
    source_ids = set(source_ledger.get("valid_paper_trade_ids") or [])
    source_ids.update(str(row.get("target_paper_trade_id") or "") for row in linkage_rows if isinstance(row, dict) and row.get("target_paper_trade_id"))
    source_ids.update(str(item) for item in bybit_orderbook_source_ledger.get("valid_paper_trade_ids", []) if item)
    outcome_rows = outcome_ledger.get("rows") if isinstance(outcome_ledger.get("rows"), list) else []
    outcome_ids = {str(row.get("paper_trade_id") or "") for row in outcome_rows if isinstance(row, dict) and not row.get("row_violations")}
    rows = [_row(row, source_ids, outcome_ids) for row in paper_rows if isinstance(row, dict)]
    strategies = sorted({str(row.get("strategy_id") or "UNKNOWN") for row in rows})
    complete_rows = [row for row in rows if row["paper_source_outcome_chain_complete"]]
    payload: dict[str, Any] = {
        "type": "paper_base_outcome_confidence_evidence_rollup",
        "schema_version": "paper_base_outcome_confidence_evidence_rollup_v1",
        "generated_at": iso_now(generated_at),
        **NO_EXECUTION_FLAGS,
        "status": "PAPER_BASE_OUTCOME_CONFIDENCE_EVIDENCE_ACCUMULATING" if complete_rows else "PAPER_BASE_OUTCOME_CONFIDENCE_WAIT_FOR_OUTCOME_ROWS",
        "input_status": {
            "paper_ledger": paper_ledger.get("status"),
            "source_ledger": source_ledger.get("status"),
            "bybit_orderbook_source_ledger": bybit_orderbook_source_ledger.get("status"),
            "outcome_ledger": outcome_ledger.get("status"),
        },
        "rows": rows,
        "summary": {
            "paper_rows_total": len(rows),
            "valid_paper_rows": sum(1 for row in rows if row["valid_paper_row"]),
            "source_linked_rows": sum(1 for row in rows if row["ohlcv_source_present"]),
            "bybit_orderbook_source_linked_rows": len(set(bybit_orderbook_source_ledger.get("valid_paper_trade_ids") or [])),
            "base_outcome_linked_rows": sum(1 for row in rows if row["base_outcome_present"]),
            "base_outcome_unique_linked_rows": int(_summary(outcome_ledger).get("valid_unique_outcome_paper_trade_ids") or len(outcome_ids)),
            "duplicate_logical_outcome_rows": int(_summary(outcome_ledger).get("duplicate_logical_outcome_rows") or 0),
            "complete_evidence_chain_rows": len(complete_rows),
            "strategies_total": len(strategies),
            "strategies_with_complete_chain": len({row["strategy_id"] for row in complete_rows}),
            "confidence_raise_allowed_now": False,
            "shadow_review_ready_now": False,
            "profit_or_edge_judgment_made": False,
            "threshold_update_made": False,
            "permission_opened_count": 0,
        },
        "strategy_summary": _strategy_summary(rows),
        "operator_summary_ko": (
            f"paper/source/base outcome이 모두 연결된 관찰 row {len(complete_rows)}개를 확인했습니다. "
            "이는 신뢰도 누적 재료일 뿐 수익성/edge 판단은 아닙니다."
        ),
        "recommended_next_action": "UPDATE_PAPER_TO_SHADOW_REVIEW_READINESS_WITH_BASE_OUTCOME_COVERAGE",
        "artifact_contract_violations": [],
    }
    payload["artifact_contract_violations"] = validate_paper_base_outcome_confidence_evidence_rollup(payload)
    if payload["artifact_contract_violations"]:
        payload["status"] = "PAPER_BASE_OUTCOME_CONFIDENCE_EVIDENCE_CONTRACT_BLOCKED"
    return payload


def validate_paper_base_outcome_confidence_evidence_rollup(payload: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if payload.get("type") != "paper_base_outcome_confidence_evidence_rollup":
        violations.append("type must be paper_base_outcome_confidence_evidence_rollup")
    for flag, expected in NO_EXECUTION_FLAGS.items():
        if payload.get(flag) is not expected:
            violations.append(f"{flag} must be {str(expected).lower()}")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    for key in ("confidence_raise_allowed_now", "shadow_review_ready_now", "profit_or_edge_judgment_made", "threshold_update_made"):
        if summary.get(key) is not False:
            violations.append(f"summary.{key} must be false")
    if summary.get("permission_opened_count") != 0:
        violations.append("summary.permission_opened_count must be 0")
    return violations


def write_paper_base_outcome_confidence_evidence_rollup(out_json: Path = DEFAULT_OUT) -> dict[str, Any]:
    payload = build_paper_base_outcome_confidence_evidence_rollup()
    write_json(out_json, payload)
    return payload


def _summary(payload: dict[str, Any]) -> dict[str, Any]:
    return payload.get("summary") if isinstance(payload.get("summary"), dict) else {}


def _row(row: dict[str, Any], source_ids: set[str], outcome_ids: set[str]) -> dict[str, Any]:
    paper_trade_id = str(row.get("paper_trade_id") or "")
    valid_paper = row.get("row_valid_for_delayed_outcome_contract") is True
    source_present = paper_trade_id in source_ids
    outcome_present = paper_trade_id in outcome_ids
    blockers = []
    if not valid_paper:
        blockers.append("paper_row_not_valid")
    if not source_present:
        blockers.append("ohlcv_source_missing")
    if not outcome_present:
        blockers.append("base_outcome_missing")
    return {
        "paper_trade_id": paper_trade_id,
        "strategy_id": str(row.get("strategy_id") or "UNKNOWN"),
        "valid_paper_row": valid_paper,
        "ohlcv_source_present": source_present,
        "base_outcome_present": outcome_present,
        "paper_source_outcome_chain_complete": valid_paper and source_present and outcome_present,
        "confidence_interpretation": "OBSERVATION_QUALITY_ONLY",
        "profit_or_edge_judgment_made": False,
        "blockers": blockers,
    }


def _strategy_summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = {}
    for row in rows:
        strategy = str(row.get("strategy_id") or "UNKNOWN")
        entry = summary.setdefault(strategy, {"paper_rows": 0, "complete_evidence_chain_rows": 0})
        entry["paper_rows"] += 1
        if row.get("paper_source_outcome_chain_complete") is True:
            entry["complete_evidence_chain_rows"] += 1
    return dict(sorted(summary.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build paper base outcome confidence evidence rollup.")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    payload = write_paper_base_outcome_confidence_evidence_rollup(Path(args.out_json))
    print(
        f"status={payload['status']} complete={payload['summary']['complete_evidence_chain_rows']} "
        f"violations={len(payload['artifact_contract_violations'])}"
    )
    return 0 if not payload["artifact_contract_violations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
