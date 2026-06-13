"""Read-only quality analysis for complete paper evidence chains."""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backtest.research.paper_evidence_loop_common import NO_EXECUTION_FLAGS, iso_now, read_json, read_jsonl, write_json


RESULTS = Path("backtest/results")
DEFAULT_OUT = RESULTS / "complete_evidence_chain_quality_analysis_latest.json"
INPUTS = {
    "confidence_rollup": RESULTS / "paper_base_outcome_confidence_evidence_rollup_latest.json",
    "decision_snapshot_layer": RESULTS / "decision_snapshot_observation_layer_latest.json",
    "source_ledger_audit": RESULTS / "ohlcv_source_ledger_audit_latest.json",
    "outcome_ledger_audit": RESULTS / "paper_outcome_ledger_audit_latest.json",
    "postmortem_ledger_audit": RESULTS / "decision_snapshot_postmortem_ledger_audit_latest.json",
    "context_summary": RESULTS / "bybit_strategy_historical_forward_context_summary_latest.json",
    "regime_rollup": RESULTS / "bybit_internal_market_regime_rollup_latest.json",
    "candidate_queue": RESULTS / "local_normalized_source_candidate_queue_latest.json",
    "ohlcv_coverage_inventory": RESULTS / "ohlcv_coverage_gap_source_symbol_inventory_latest.json",
}
LEDGERS = {
    "source_rows": RESULTS / "ohlcv_capture" / "ohlcv_forward_source_rows.jsonl",
    "linkage_rows": RESULTS / "ohlcv_capture" / "ohlcv_window_source_reuse_linkages.jsonl",
    "outcome_rows": RESULTS / "paper_outcomes" / "paper_outcomes.jsonl",
    "postmortem_rows": RESULTS / "decision_postmortems" / "decision_snapshot_postmortem_rows.jsonl",
}
CORE_STRATEGIES = ("LEFU", "LVOR", "MQRF")


def build_complete_evidence_chain_quality_analysis(
    *,
    artifacts: dict[str, dict[str, Any]] | None = None,
    ledgers: dict[str, list[dict[str, Any]]] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    artifacts = artifacts if artifacts is not None else {name: read_json(path) for name, path in INPUTS.items()}
    ledgers = ledgers if ledgers is not None else {name: read_jsonl(path)[0] for name, path in LEDGERS.items()}
    snapshots = {
        str(row.get("paper_trade_id") or ""): row
        for row in _rows(artifacts.get("decision_snapshot_layer", {}).get("snapshots"))
    }
    rollup_rows = [
        row
        for row in _rows(artifacts.get("confidence_rollup", {}).get("rows"))
        if row.get("paper_source_outcome_chain_complete") is True
    ]
    source_by_paper = _source_by_paper(ledgers)
    outcome_by_paper = _latest_by_paper(ledgers.get("outcome_rows", []), "paper_trade_id", "outcome_recorded_at_ts")
    postmortem_by_paper = _latest_by_paper(ledgers.get("postmortem_rows", []), "paper_trade_id", "appended_at")
    regime_by_strategy = _regime_by_strategy(artifacts.get("regime_rollup", {}))
    context_by_strategy = _context_by_strategy(artifacts.get("context_summary", {}))
    rows = [
        _chain_row(
            rollup_row,
            snapshots.get(str(rollup_row.get("paper_trade_id") or ""), {}),
            source_by_paper.get(str(rollup_row.get("paper_trade_id") or ""), {}),
            outcome_by_paper.get(str(rollup_row.get("paper_trade_id") or ""), {}),
            postmortem_by_paper.get(str(rollup_row.get("paper_trade_id") or ""), {}),
            regime_by_strategy,
            context_by_strategy,
        )
        for rollup_row in rollup_rows
    ]
    source_counts = Counter(row["source_identity_key"] for row in rows if row.get("source_identity_key"))
    window_counts = Counter(row["outcome_window_key"] for row in rows if row.get("outcome_window_key"))
    for row in rows:
        row["shared_source_count_for_identity"] = source_counts.get(row.get("source_identity_key"), 0)
        row["shared_outcome_window_count"] = window_counts.get(row.get("outcome_window_key"), 0)
        row["duplicate_hypothesis_risk"] = _duplicate_hypothesis_risk(row)
    strategy_summary = _strategy_summary(rows)
    summary = _summary(rows, artifacts)
    payload: dict[str, Any] = {
        "type": "complete_evidence_chain_quality_analysis",
        "schema_version": "complete_evidence_chain_quality_analysis_v1",
        "generated_at": iso_now(generated_at),
        **NO_EXECUTION_FLAGS,
        "status": "COMPLETE_EVIDENCE_CHAIN_QUALITY_ANALYSIS_READY_READ_ONLY",
        "scope": {
            "read_only": True,
            "paper_or_shadow_observation_append_allowed": False,
            "source_ledger_append_allowed": False,
            "outcome_append_allowed": False,
            "postmortem_append_allowed": False,
            "confidence_update_allowed": False,
            "profit_or_edge_judgment_allowed": False,
            "gui_or_closeout_created": False,
            "shadow_live_scanner_executor_promotion_allowed": False,
        },
        "input_status": {name: artifact.get("status") for name, artifact in artifacts.items()},
        "rows": rows,
        "strategy_summary": strategy_summary,
        "top_blockers": _top_blockers(rows, artifacts),
        "top_opportunities": _top_opportunities(rows),
        "summary": summary,
        "operator_summary_ko": (
            f"complete evidence chain {summary['complete_chain_count']}개를 source/outcome/postmortem/context 품질 기준으로 read-only 분석했습니다. "
            "수익성/edge 판단이나 confidence 상승은 수행하지 않았습니다."
        ),
        "artifact_contract_violations": [],
    }
    payload["artifact_contract_violations"] = validate_complete_evidence_chain_quality_analysis(payload)
    if payload["artifact_contract_violations"]:
        payload["status"] = "COMPLETE_EVIDENCE_CHAIN_QUALITY_ANALYSIS_CONTRACT_BLOCKED"
    return payload


def validate_complete_evidence_chain_quality_analysis(payload: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if payload.get("type") != "complete_evidence_chain_quality_analysis":
        violations.append("type must be complete_evidence_chain_quality_analysis")
    if payload.get("schema_version") != "complete_evidence_chain_quality_analysis_v1":
        violations.append("schema_version must be complete_evidence_chain_quality_analysis_v1")
    for key, expected in NO_EXECUTION_FLAGS.items():
        if payload.get(key) is not expected:
            violations.append(f"{key} must be {str(expected).lower()}")
    scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else {}
    for key in (
        "paper_or_shadow_observation_append_allowed",
        "source_ledger_append_allowed",
        "outcome_append_allowed",
        "postmortem_append_allowed",
        "confidence_update_allowed",
        "profit_or_edge_judgment_allowed",
        "gui_or_closeout_created",
        "shadow_live_scanner_executor_promotion_allowed",
    ):
        if scope.get(key) is not False:
            violations.append(f"scope.{key} must be false")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    for key in ("confidence_delta_total", "permission_opened_count", "source_rows_appended", "outcome_rows_appended", "postmortem_rows_appended"):
        if summary.get(key) != 0:
            violations.append(f"summary.{key} must be 0")
    for row in _rows(payload.get("rows")):
        if row.get("complete_chain") is not True:
            violations.append(f"{row.get('paper_trade_id')}.complete_chain must be true")
        if row.get("profit_or_edge_judgment") is not False:
            violations.append(f"{row.get('paper_trade_id')}.profit_or_edge_judgment must be false")
        if row.get("confidence_update_allowed") is not False:
            violations.append(f"{row.get('paper_trade_id')}.confidence_update_allowed must be false")
    return violations


def write_complete_evidence_chain_quality_analysis(out_json: Path = DEFAULT_OUT) -> dict[str, Any]:
    payload = build_complete_evidence_chain_quality_analysis()
    write_json(out_json, payload)
    return payload


def _chain_row(
    rollup_row: dict[str, Any],
    snapshot: dict[str, Any],
    source: dict[str, Any],
    outcome: dict[str, Any],
    postmortem: dict[str, Any],
    regime_by_strategy: dict[str, dict[str, Any]],
    context_by_strategy: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    paper_id = str(rollup_row.get("paper_trade_id") or "")
    strategy = str(rollup_row.get("strategy_id") or "UNKNOWN")
    source_refs = _rows(snapshot.get("source_refs"))
    outcome_refs = _rows(snapshot.get("outcome_refs"))
    source_type = _source_type(source, source_refs)
    outcome_contract = outcome.get("outcome_payload_contract") if isinstance(outcome.get("outcome_payload_contract"), dict) else {}
    window_start = outcome_contract.get("observed_window_start_ts") or source.get("outcome_window_start_ts")
    window_end = outcome_contract.get("observed_window_end_ts") or source.get("outcome_window_end_ts")
    source_key = str(source.get("window_source_id") or source.get("source_row_id") or (source_refs[0].get("window_source_id") if source_refs else ""))
    source_completeness = _source_completeness(source, source_refs)
    outcome_quality = _outcome_quality(outcome, outcome_refs)
    postmortem_quality = _postmortem_quality(postmortem)
    regime = regime_by_strategy.get(strategy, {})
    context = context_by_strategy.get(strategy, {})
    blockers = _confidence_blockers(snapshot, source_completeness, outcome_quality, postmortem_quality, regime, context)
    return {
        "paper_trade_id": paper_id,
        "strategy_id": strategy,
        "decision_ts": snapshot.get("decision_ts"),
        "symbol": snapshot.get("symbol"),
        "complete_chain": True,
        "source_type": source_type,
        "source_quality_tier": _source_quality_tier(source_type, source_completeness),
        "source_completeness": source_completeness,
        "source_identity_key": source_key,
        "source_row_id": source.get("source_row_id") or (source_refs[0].get("source_row_id") if source_refs else None),
        "window_source_id": source.get("window_source_id") or (source_refs[0].get("window_source_id") if source_refs else None),
        "shared_or_reused_source": source_type == "OHLCV_WINDOW_SOURCE_REUSE_LINKAGE",
        "outcome_window_start_ts": window_start,
        "outcome_window_end_ts": window_end,
        "outcome_window_key": f"{snapshot.get('symbol')}|{window_start}|{window_end}",
        "outcome_quality": outcome_quality,
        "postmortem_quality": postmortem_quality,
        "postmortem_available": bool(postmortem),
        "regime_tag_coverage": {
            "dominant_internal_regime_tag": regime.get("dominant_internal_regime_tag"),
            "mapped_context_window_count": int(regime.get("mapped_context_window_count") or 0),
            "context_source_kinds": list(regime.get("context_source_kinds") or []),
            "regime_context_only": True,
        },
        "context_coverage": {
            "context_source_rows": int(context.get("context_source_rows") or 0),
            "explanation_linked_windows": int(context.get("explanation_linked_windows") or 0),
            "remaining_ambiguity_count": int(context.get("remaining_ambiguity_count") or 0),
            "direct_confidence_input_candidate_count": int(context.get("direct_confidence_input_candidate_count") or 0),
        },
        "unresolved_ambiguity": list(context.get("remaining_ambiguities") or []),
        "confidence_blockers": blockers,
        "next_evidence_needed": _next_evidence_needed(strategy, blockers),
        "profit_or_edge_judgment": False,
        "confidence_update_allowed": False,
    }


def _source_by_paper(ledgers: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    direct = {str(row.get("paper_trade_id") or ""): dict(row) for row in _rows(ledgers.get("source_rows")) if row.get("paper_trade_id")}
    source_by_id = {str(row.get("source_row_id") or ""): row for row in _rows(ledgers.get("source_rows")) if row.get("source_row_id")}
    for linkage in _rows(ledgers.get("linkage_rows")):
        target = str(linkage.get("target_paper_trade_id") or "")
        source = source_by_id.get(str(linkage.get("source_row_id") or ""))
        if not target or not source or str(source.get("source_row_hash") or "") != str(linkage.get("source_row_hash") or ""):
            continue
        synthetic = dict(source)
        synthetic.update(
            {
                "paper_trade_id": target,
                "strategy_id": linkage.get("strategy_id") or source.get("strategy_id"),
                "source_type": "OHLCV_WINDOW_SOURCE_REUSE_LINKAGE",
                "window_source_id": linkage.get("window_source_id"),
                "source_owner_paper_trade_id": linkage.get("source_owner_paper_trade_id"),
            }
        )
        direct[target] = synthetic
    return direct


def _source_type(source: dict[str, Any], source_refs: list[dict[str, Any]]) -> str:
    if source.get("source_type") == "OHLCV_WINDOW_SOURCE_REUSE_LINKAGE":
        return "OHLCV_WINDOW_SOURCE_REUSE_LINKAGE"
    if any(ref.get("source_type") == "ohlcv_window_source_reuse_linkage" for ref in source_refs):
        return "OHLCV_WINDOW_SOURCE_REUSE_LINKAGE"
    return "OHLCV_DIRECT_APPEND_ONLY_SOURCE"


def _source_completeness(source: dict[str, Any], source_refs: list[dict[str, Any]]) -> str:
    if not source and not source_refs:
        return "MISSING"
    has_hash = bool(source.get("source_row_hash") or any(ref.get("source_row_hash") for ref in source_refs))
    has_known_at = source.get("known_at_validated") is True or bool(source.get("archive_written_ts"))
    has_window = bool(source.get("outcome_window_start_ts") and source.get("outcome_window_end_ts"))
    if has_hash and has_known_at and has_window:
        return "COMPLETE_REPLAY_SAFE"
    if has_hash and has_known_at:
        return "PARTIAL_WINDOW_METADATA"
    return "PARTIAL_SOURCE_METADATA"


def _source_quality_tier(source_type: str, completeness: str) -> str:
    if completeness != "COMPLETE_REPLAY_SAFE":
        return "TIER_2_REPLAY_SAFE_WITH_METADATA_GAP"
    if source_type == "OHLCV_WINDOW_SOURCE_REUSE_LINKAGE":
        return "TIER_1_REPLAY_SAFE_REUSED_WINDOW_SOURCE"
    return "TIER_1_REPLAY_SAFE_DIRECT_SOURCE"


def _outcome_quality(outcome: dict[str, Any], outcome_refs: list[dict[str, Any]]) -> str:
    if not outcome and not outcome_refs:
        return "MISSING"
    contract = outcome.get("outcome_payload_contract") if isinstance(outcome.get("outcome_payload_contract"), dict) else {}
    no_claims = contract.get("no_profit_claim") is True and contract.get("no_edge_claim") is True and contract.get("no_threshold_update") is True
    if outcome.get("source_row_id") and contract.get("observed_window_start_ts") and contract.get("observed_window_end_ts") and no_claims:
        return "BASE_OHLCV_OBSERVATION_ONLY_COMPLETE"
    if outcome_refs:
        return "BASE_OHLCV_AUDIT_REF_PRESENT"
    return "PARTIAL_OUTCOME_METADATA"


def _postmortem_quality(postmortem: dict[str, Any]) -> str:
    if not postmortem:
        return "MISSING"
    if postmortem.get("decision_replayability") == "REPLAYABLE" and postmortem.get("confidence_update") is False:
        return "OBSERVATION_ONLY_REPLAYABLE_POSTMORTEM"
    return "OBSERVATION_ONLY_POSTMORTEM_PRESENT"


def _confidence_blockers(snapshot: dict[str, Any], source_quality: str, outcome_quality: str, postmortem_quality: str, regime: dict[str, Any], context: dict[str, Any]) -> list[str]:
    blockers = []
    if source_quality != "COMPLETE_REPLAY_SAFE":
        blockers.append("source_metadata_gap")
    if outcome_quality != "BASE_OHLCV_OBSERVATION_ONLY_COMPLETE":
        blockers.append("outcome_quality_gap")
    if postmortem_quality != "OBSERVATION_ONLY_REPLAYABLE_POSTMORTEM":
        blockers.append("postmortem_quality_gap")
    if "funding_ready_context" in (snapshot.get("missing_context") or []):
        blockers.append("funding_ready_context_missing")
    if "orderbook_market_ready_context" in (snapshot.get("missing_context") or []):
        blockers.append("orderbook_market_ready_context_missing")
    if int(context.get("direct_confidence_input_candidate_count") or 0) == 0:
        blockers.append("context_not_direct_confidence_input")
    if int(regime.get("direct_confidence_input_candidate_count") or 0) == 0:
        blockers.append("regime_context_only")
    for item in regime.get("blockers") or []:
        blocker = str(item)
        if blocker == "source_outcome_postmortem_chain_not_complete":
            blockers.append("regime_context_not_reconciled_with_latest_complete_chains")
        else:
            blockers.append(blocker)
    return sorted(set(blockers))


def _next_evidence_needed(strategy: str, blockers: list[str]) -> dict[str, Any]:
    target = 3
    if strategy == "LVOR":
        target = 3
    elif strategy == "LEFU":
        target = 4
    elif strategy == "MQRF":
        target = 4
    conditions = ["keep confidence_delta at 0 until predeclared confidence gate is run"]
    if "funding_ready_context_missing" in blockers:
        conditions.append("attach funding/regime context to the same paper windows")
    if "orderbook_market_ready_context_missing" in blockers:
        conditions.append("attach orderbook/market context to the same paper windows")
    if "context_not_direct_confidence_input" in blockers:
        conditions.append("convert context sources only through approved source/outcome/postmortem linkage")
    return {"additional_complete_chains_target_before_confidence_discussion": target, "data_conditions": conditions}


def _strategy_summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for strategy in CORE_STRATEGIES:
        items = [row for row in rows if row.get("strategy_id") == strategy]
        windows = {row.get("outcome_window_key") for row in items if row.get("outcome_window_key")}
        shared = [row for row in items if int(row.get("shared_source_count_for_identity") or 0) > 1]
        reused = [row for row in items if row.get("source_type") == "OHLCV_WINDOW_SOURCE_REUSE_LINKAGE"]
        blocker_counts = Counter(blocker for row in items for blocker in row.get("confidence_blockers", []))
        regime_tags = Counter(row.get("regime_tag_coverage", {}).get("dominant_internal_regime_tag") or "UNKNOWN" for row in items)
        out[strategy] = {
            "complete_chain_count": len(items),
            "unique_outcome_window_count": len(windows),
            "shared_source_count": len(shared),
            "reused_window_source_linkage_count": len(reused),
            "source_quality_tier_counts": dict(Counter(row.get("source_quality_tier") for row in items)),
            "regime_tag_coverage": dict(regime_tags),
            "outcome_quality_counts": dict(Counter(row.get("outcome_quality") for row in items)),
            "postmortem_quality_counts": dict(Counter(row.get("postmortem_quality") for row in items)),
            "duplicate_hypothesis_risk_counts": dict(Counter(row.get("duplicate_hypothesis_risk") for row in items)),
            "confidence_blocker_counts": dict(blocker_counts.most_common()),
            "next_evidence_goal_count": max((row.get("next_evidence_needed", {}).get("additional_complete_chains_target_before_confidence_discussion") or 0) for row in items) if items else 0,
        }
    return out


def _summary(rows: list[dict[str, Any]], artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    coverage = artifacts.get("ohlcv_coverage_inventory", {}).get("summary", {})
    queue = artifacts.get("candidate_queue", {}).get("summary", {})
    return {
        "complete_chain_count": len(rows),
        "strategy_complete_chain_count": dict(Counter(row.get("strategy_id") for row in rows)),
        "unique_outcome_window_count": len({row.get("outcome_window_key") for row in rows if row.get("outcome_window_key")}),
        "shared_source_count": sum(1 for row in rows if int(row.get("shared_source_count_for_identity") or 0) > 1),
        "reused_window_source_linkage_count": sum(1 for row in rows if row.get("source_type") == "OHLCV_WINDOW_SOURCE_REUSE_LINKAGE"),
        "remaining_ohlcv_unavailable_gap": int(coverage.get("unavailable_gap_rows") or 0),
        "remaining_dry_run_candidates": int(queue.get("remaining_dry_run_candidate_count") or 0),
        "confidence_delta_total": 0,
        "permission_opened_count": 0,
        "source_rows_appended": 0,
        "outcome_rows_appended": 0,
        "postmortem_rows_appended": 0,
    }


def _top_blockers(rows: list[dict[str, Any]], artifacts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    blockers = Counter(blocker for row in rows for blocker in row.get("confidence_blockers", []))
    coverage = artifacts.get("ohlcv_coverage_inventory", {}).get("summary", {})
    out = [{"blocker": name, "count": count} for name, count in blockers.most_common(6)]
    out.append({"blocker": "remaining_ohlcv_unavailable_gap", "count": int(coverage.get("unavailable_gap_rows") or 0)})
    return out


def _top_opportunities(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"opportunity": "diversify outcome windows beyond shared 2026-06-02 window", "current_unique_windows": len({row.get("outcome_window_key") for row in rows if row.get("outcome_window_key")})},
        {"opportunity": "attach same-window funding/orderbook context where missing", "affected_rows": sum(1 for row in rows if "funding_ready_context_missing" in row.get("confidence_blockers", []) or "orderbook_market_ready_context_missing" in row.get("confidence_blockers", []))},
        {"opportunity": "run separate confidence discussion only after context directness and duplicate risk are reduced", "current_complete_chains": len(rows)},
    ]


def _duplicate_hypothesis_risk(row: dict[str, Any]) -> str:
    shared_source = int(row.get("shared_source_count_for_identity") or 0)
    shared_window = int(row.get("shared_outcome_window_count") or 0)
    if shared_source >= 4 or shared_window >= 6:
        return "HIGH_SHARED_WINDOW_OR_SOURCE"
    if shared_source > 1 or shared_window > 1:
        return "MEDIUM_SHARED_WINDOW_OR_SOURCE"
    return "LOW_UNIQUE_WINDOW_SOURCE"


def _regime_by_strategy(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("strategy_id") or ""): row for row in _rows(payload.get("rows"))}


def _context_by_strategy(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("strategy_id") or ""): row for row in _rows(payload.get("rows"))}


def _latest_by_paper(rows: list[dict[str, Any]], paper_key: str, ts_key: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in _rows(rows):
        paper_id = str(row.get(paper_key) or "")
        if not paper_id:
            continue
        if paper_id not in out or str(row.get(ts_key) or "") >= str(out[paper_id].get(ts_key) or ""):
            out[paper_id] = row
    return out


def _rows(value: Any) -> list[dict[str, Any]]:
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def main() -> int:
    parser = argparse.ArgumentParser(description="Build complete evidence chain quality analysis.")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    payload = write_complete_evidence_chain_quality_analysis(Path(args.out_json))
    summary = payload["summary"]
    print(
        f"status={payload['status']} chains={summary['complete_chain_count']} "
        f"windows={summary['unique_outcome_window_count']} shared_source={summary['shared_source_count']} "
        f"reused_linkage={summary['reused_window_source_linkage_count']} "
        f"ohlcv_gap={summary['remaining_ohlcv_unavailable_gap']} "
        f"confidence_delta={summary['confidence_delta_total']} permission_opened={summary['permission_opened_count']} "
        f"violations={len(payload['artifact_contract_violations'])}"
    )
    return 0 if not payload["artifact_contract_violations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
