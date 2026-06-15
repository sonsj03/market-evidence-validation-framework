"""Disabled OHLCV capture surface for public research-only builds.

Only path constants are exposed here. No writer, collector, network call, or
runtime enablement exists in the public repository.
"""

from __future__ import annotations

from pathlib import Path


SOURCE_LEDGER = Path("backtest/results/ohlcv_capture/ohlcv_forward_source_rows.jsonl")
