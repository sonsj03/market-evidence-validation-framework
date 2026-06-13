"""Helpers for future source row reference fields.

This module is intentionally runtime-free. It prepares deterministic row
reference and validation helpers for future collector patches without reading
or mutating collector artifacts.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence


HASH_PREFIX = "sha256:"
SOURCE_ROW_ID_PREFIX = "srcrow:"
SOURCE_ROW_ID_HEX_LENGTH = 24

COMMON_SOURCE_ROW_ID_FIELDS = (
    "source_name",
    "exchange",
    "market_type",
    "source_type",
    "symbol",
    "source_event_ts",
    "source_row_index_or_offset",
)

COMMON_REQUIRED_FIELDS = (
    "source_row_id",
    "source_row_index_or_offset",
    "source_artifact_path",
    "source_artifact_hash",
    "source_name",
    "exchange",
    "symbol",
    "market_type",
    "source_type",
    "source_trust_level",
    "source_event_ts",
    "collector_seen_ts",
    "archive_written_ts",
)

LIQUIDATION_REQUIRED_FIELDS = (
    *COMMON_REQUIRED_FIELDS,
    "liquidation_event_ts",
    "exchange_event_id_or_hash",
    "side",
    "price",
    "quantity",
    "symbol_native",
    "symbol_normalized",
)

ORDERBOOK_REQUIRED_FIELDS = (
    *COMMON_REQUIRED_FIELDS,
    "snapshot_ts",
    "depth_limit",
    "bid_levels_hash",
    "ask_levels_hash",
    "best_bid",
    "best_ask",
    "spread_bps",
)


def canonical_json(value: Any) -> str:
    return json.dumps(
        _jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def sha256_hex(value: bytes | str) -> str:
    payload = value.encode("utf-8") if isinstance(value, str) else value
    return f"{HASH_PREFIX}{hashlib.sha256(payload).hexdigest()}"


def source_artifact_hash(value: Any) -> str:
    if isinstance(value, bytes):
        return sha256_hex(value)
    if isinstance(value, str):
        return sha256_hex(value)
    return sha256_hex(canonical_json(value))


def source_artifact_file_hash(path: str | Path) -> str:
    payload = Path(path).read_bytes()
    return sha256_hex(payload)


def deterministic_source_row_id(
    row: Mapping[str, Any],
    *,
    canonical_payload_hash: str | None = None,
) -> str:
    material = {field: row.get(field) for field in COMMON_SOURCE_ROW_ID_FIELDS}
    material["canonical_payload_hash"] = canonical_payload_hash or source_artifact_hash(
        row.get("raw_payload", row.get("payload", row))
    )
    digest = hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()
    return f"{SOURCE_ROW_ID_PREFIX}{digest[:SOURCE_ROW_ID_HEX_LENGTH]}"


def levels_hash(levels: Sequence[Any]) -> str:
    return source_artifact_hash(_canonical_levels(levels))


def bid_levels_hash(levels: Sequence[Any]) -> str:
    return levels_hash(levels)


def ask_levels_hash(levels: Sequence[Any]) -> str:
    return levels_hash(levels)


def best_bid(levels: Sequence[Any]) -> float | None:
    if not levels:
        return None
    return _float_or_none(_level_price(levels[0]))


def best_ask(levels: Sequence[Any]) -> float | None:
    if not levels:
        return None
    return _float_or_none(_level_price(levels[0]))


def spread_bps(bid: Any, ask: Any) -> float | None:
    bid_value = _float_or_none(bid)
    ask_value = _float_or_none(ask)
    if bid_value is None or ask_value is None:
        return None
    mid = (bid_value + ask_value) / 2.0
    if mid <= 0:
        return None
    return ((ask_value - bid_value) / mid) * 10_000.0


def exchange_event_id_or_hash(payload: Mapping[str, Any]) -> str:
    for field in ("exchange_event_id", "event_id", "id", "trade_id", "T", "time", "updatedTime"):
        value = payload.get(field)
        if value not in (None, ""):
            return str(value)
    return source_artifact_hash(payload)


def validate_required_fields(
    row: Mapping[str, Any],
    required_fields: Sequence[str],
) -> list[str]:
    return [
        f"missing_required_field:{field}"
        for field in required_fields
        if _missing(row.get(field))
    ]


def validate_timestamp_order(
    row: Mapping[str, Any],
    *,
    check_snapshot: bool = False,
) -> list[str]:
    reasons: list[str] = []
    source_event_ts = _parse_ts(row.get("source_event_ts"))
    collector_seen_ts = _parse_ts(row.get("collector_seen_ts"))
    archive_written_ts = _parse_ts(row.get("archive_written_ts"))

    if source_event_ts and collector_seen_ts and source_event_ts > collector_seen_ts:
        reasons.append("timestamp_order_violation:source_event_after_collector_seen")
    if collector_seen_ts and archive_written_ts and collector_seen_ts > archive_written_ts:
        reasons.append("timestamp_order_violation:collector_seen_after_archive_written")

    if check_snapshot:
        snapshot_ts = _parse_ts(row.get("snapshot_ts"))
        if snapshot_ts and collector_seen_ts and snapshot_ts > collector_seen_ts:
            reasons.append("timestamp_order_violation:snapshot_after_collector_seen")
    return reasons


def validate_no_backfill_guard(row: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    if row.get("historical_backfill_attempt") is True:
        reasons.append("historical_backfill_forbidden")
    if row.get("synthetic_timestamp_used") is True:
        reasons.append("synthetic_timestamp_forbidden")
    if row.get("mutates_existing_row") is True:
        reasons.append("existing_row_mutation_forbidden")
    return reasons


def validate_append_only_guard(row: Mapping[str, Any]) -> list[str]:
    return validate_no_backfill_guard(row)


def validate_source_row_reference(
    row: Mapping[str, Any],
    required_fields: Sequence[str],
    *,
    check_snapshot: bool = False,
) -> list[str]:
    reasons = validate_required_fields(row, required_fields)
    reasons.extend(validate_timestamp_order(row, check_snapshot=check_snapshot))
    reasons.extend(validate_append_only_guard(row))
    return reasons


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _canonical_levels(levels: Sequence[Any]) -> list[list[str]]:
    canonical: list[list[str]] = []
    for level in levels:
        price = _level_price(level)
        quantity = _level_quantity(level)
        canonical.append([_decimal_text(price), _decimal_text(quantity)])
    return canonical


def _level_price(level: Any) -> Any:
    if isinstance(level, Mapping):
        for field in ("price", "p", "bid", "ask"):
            if field in level:
                return level[field]
    if isinstance(level, Sequence) and not isinstance(level, (str, bytes)) and level:
        return level[0]
    return None


def _level_quantity(level: Any) -> Any:
    if isinstance(level, Mapping):
        for field in ("quantity", "qty", "size", "q"):
            if field in level:
                return level[field]
    if isinstance(level, Sequence) and not isinstance(level, (str, bytes)) and len(level) > 1:
        return level[1]
    return None


def _decimal_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        return format(Decimal(str(value)).normalize(), "f")
    except (InvalidOperation, ValueError):
        return str(value)


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _missing(value: Any) -> bool:
    return value is None or value == ""


def _parse_ts(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
