"""Shared read-only helpers for public evidence validation contracts."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


RESULTS = Path("backtest/results")
PAPER_LEDGER_PATH = RESULTS / "paper_trades" / "paper_trades.jsonl"
OUTCOME_LEDGER_PATH = RESULTS / "paper_outcomes" / "paper_outcomes.jsonl"

NO_EXECUTION_FLAGS = {
    "research_only": True,
    "read_only": True,
    "collection_trigger_allowed": False,
    "network_call_allowed": False,
    "market_outcome_fetch_allowed_now": False,
    "source_write_allowed_now": False,
    "strategy_execution_allowed": False,
    "scanner_connection_allowed": False,
    "executor_connection_allowed": False,
    "stage4_entry_allowed": False,
    "preliminary_replay_allowed": False,
    "historical_preliminary_replay_allowed_now": False,
    "shadow_observe_allowed": False,
    "promotion_allowed": False,
    "limited_live_allowed": False,
    "live_trading_allowed": False,
    "cost_adjusted_replay_allowed": False,
    "edge_evidence_allowed": False,
    "profit_forecast_allowed": False,
    "threshold_optimization_allowed": False,
    "real_order_intent_allowed": False,
    "outcome_join_allowed_now": False,
    "outcome_row_append_allowed_now": False,
    "original_row_mutation_allowed": False,
    "ledger_mutation_allowed": False,
    "confidence_update_allowed": False,
}


def iso_now(value: datetime | None = None) -> str:
    return (value or datetime.now(UTC)).astimezone(UTC).isoformat()


def parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.exists():
        return [], []
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_no}: invalid json: {exc.msg}")
            continue
        if not isinstance(row, dict):
            errors.append(f"line {line_no}: row must be object")
            continue
        rows.append(row)
    return rows, errors


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
