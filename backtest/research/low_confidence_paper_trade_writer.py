"""Schema helpers for synthetic low-confidence paper trade rows.

The public repository does not write paper trades. These helpers only build and
validate in-memory rows used by read-only audit tests.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


REQUIRED_FIELDS = (
    "paper_trade_id",
    "strategy_id",
    "symbol",
    "recorded_at_ts",
    "lineage_hash",
    "known_at_snapshot_ref",
    "known_at_snapshot_hash",
    "blocker_snapshot",
    "blocker_snapshot_hash",
    "no_execution_flags",
)

FORBIDDEN_TRUE_FLAGS = (
    "real_order_intent_allowed",
    "scanner_connection_allowed",
    "executor_connection_allowed",
    "stage4_entry_allowed",
    "replay_candidate",
    "shadow_observe_allowed",
    "limited_live_allowed",
    "live_trading_allowed",
    "cost_adjusted_replay_allowed",
    "outcome_join_allowed_now",
)


def build_example_paper_trade_row_from_schema(strategy_id: str = "LEFU") -> dict[str, Any]:
    recorded_at = datetime(2026, 6, 1, tzinfo=UTC).isoformat()
    return {
        "paper_trade_id": f"paper_{strategy_id.lower()}_example",
        "strategy_id": strategy_id,
        "symbol": "BTC/USDT",
        "recorded_at_ts": recorded_at,
        "decision_ts": recorded_at,
        "known_at_ts": recorded_at,
        "lineage_hash": "sha256:" + "a" * 64,
        "known_at_snapshot_ref": f"synthetic://known-at/{strategy_id}",
        "known_at_snapshot_hash": "sha256:" + "b" * 64,
        "blocker_snapshot": {"source_mode": "CURRENT_ARTIFACT_CONTEXT"},
        "blocker_snapshot_hash": "sha256:" + "c" * 64,
        "max_holding_window": "24h",
        "virtual_decision": "OBSERVE_ONLY",
        "virtual_side": "none",
        "virtual_exit_plan": {"max_holding_window": "24h"},
        "feature_snapshot_hash": "sha256:" + "d" * 64,
        "no_execution_flags": {flag: False for flag in FORBIDDEN_TRUE_FLAGS},
    }


def validate_paper_trade_row_before_append(row: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in row:
            violations.append(f"missing required field {field}")
    if not str(row.get("paper_trade_id") or ""):
        violations.append("paper_trade_id must be non-empty")
    if not str(row.get("strategy_id") or ""):
        violations.append("strategy_id must be non-empty")
    for field in ("lineage_hash", "known_at_snapshot_hash", "blocker_snapshot_hash"):
        if field in row and not str(row.get(field) or "").startswith("sha256:"):
            violations.append(f"{field} must start with sha256:")
    flags = row.get("no_execution_flags")
    if not isinstance(flags, dict):
        violations.append("no_execution_flags must be object")
    else:
        for flag in FORBIDDEN_TRUE_FLAGS:
            if flags.get(flag) is not False:
                violations.append(f"no_execution_flags.{flag} must be false")
    return violations
