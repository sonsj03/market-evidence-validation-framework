from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TradeEvent:
    bot: str
    action: str
    symbol: str
    side: str
    ts: float
    price: float
    trade_id: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class TradeCase:
    bot: str
    symbol: str
    side: str
    entry_ts: float
    entry_price: float
    exit_ts: float
    exit_price: float
    actual_exit_reason: str
    actual_pnl_usdt: float
    actual_pnl_pct: float
    session: str
    mfe_pct: float
    mae_pct: float
    hold_sec: float
    fees_pct: float = 0.08
    matched_by: str = "unknown"
    data_quality: str = "medium"
    dirty_reasons: tuple[str, ...] = ()
    trade_id: str = ""
    raw_open: dict[str, Any] = field(default_factory=dict)
    raw_close: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PriceBar:
    symbol: str
    ts: float
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(frozen=True)
class ReplayResult:
    bot: str
    symbol: str
    side: str
    session: str
    actual_exit_reason: str
    sim_exit_reason: str
    actual_pnl_usdt: float
    actual_pnl_pct: float
    sim_pnl_pct_net: float
    sim_pnl_usdt_est: float
    r_multiple: float
    matched_by: str
    data_quality: str
    dirty_reasons: tuple[str, ...]
    price_path_quality: str = "mfe_mae_approx"
    trade_id: str = ""
    details: dict[str, Any] = field(default_factory=dict)
