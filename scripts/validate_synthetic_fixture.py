"""Validate the public synthetic observation fixture.

This script uses only the Python standard library and never reads private
configuration, raw market archives, account data, or network resources.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "observation_id",
    "symbol",
    "observed_at",
    "known_at",
    "source_ref",
    "source_lineage",
    "hypothesis",
    "confidence_evidence_score",
    "direct_trading_allowed",
    "order_execution_allowed",
    "private_exchange_api_allowed",
}

ALLOWED_FIELDS = REQUIRED_FIELDS

FORBIDDEN_TRUE_FLAGS = {
    "direct_trading_allowed",
    "order_execution_allowed",
    "private_exchange_api_allowed",
}

ALLOWED_SOURCE_TYPES = {"synthetic_fixture"}


def parse_utc_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"line {line_no}: row must be an object")
            rows.append(row)
    return rows


def validate_rows(rows: list[dict[str, Any]]) -> list[str]:
    violations: list[str] = []
    if not rows:
        return ["fixture must contain at least one row"]

    seen_ids: set[str] = set()
    for index, row in enumerate(rows, start=1):
        missing = sorted(REQUIRED_FIELDS - set(row))
        if missing:
            violations.append(f"row {index}: missing fields: {', '.join(missing)}")
        unexpected = sorted(set(row) - ALLOWED_FIELDS)
        if unexpected:
            violations.append(f"row {index}: unexpected fields: {', '.join(unexpected)}")

        observation_id = str(row.get("observation_id") or "")
        if not observation_id:
            violations.append(f"row {index}: observation_id must be non-empty")
        elif observation_id in seen_ids:
            violations.append(f"row {index}: duplicate observation_id {observation_id}")
        seen_ids.add(observation_id)

        source_ref = row.get("source_ref")
        if not isinstance(source_ref, str) or not source_ref:
            violations.append(f"row {index}: source_ref must be a non-empty string")

        source_lineage = row.get("source_lineage")
        if not isinstance(source_lineage, dict):
            violations.append(f"row {index}: source_lineage must be an object")
        else:
            if source_lineage.get("source_ref") != source_ref:
                violations.append(f"row {index}: source_lineage.source_ref must match source_ref")
            if source_lineage.get("source_type") not in ALLOWED_SOURCE_TYPES:
                violations.append(f"row {index}: source_lineage.source_type must be synthetic_fixture")

        observed_at = parse_utc_timestamp(row.get("observed_at"))
        known_at = parse_utc_timestamp(row.get("known_at"))
        if observed_at is None:
            violations.append(f"row {index}: observed_at must be an ISO-8601 UTC timestamp")
        if known_at is None:
            violations.append(f"row {index}: known_at must be an ISO-8601 UTC timestamp")
        if observed_at is not None and known_at is not None and known_at < observed_at:
            violations.append(f"row {index}: known_at must not be earlier than observed_at")

        confidence = row.get("confidence_evidence_score")
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not 0 <= confidence <= 1
        ):
            violations.append(f"row {index}: confidence_evidence_score must be a number from 0 to 1")

        for field in FORBIDDEN_TRUE_FLAGS:
            if row.get(field) is not False:
                violations.append(f"row {index}: {field} must be false")

    return violations


def validate_fixture(path: Path) -> dict[str, Any]:
    rows = load_jsonl(path)
    violations = validate_rows(rows)
    return {
        "fixture": str(path),
        "row_count": len(rows),
        "status": "PASS" if not violations else "FAIL",
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate synthetic fixture rows")
    parser.add_argument(
        "fixture",
        nargs="?",
        default="fixtures/synthetic_market_observations.jsonl",
        help="Path to the synthetic JSONL fixture",
    )
    args = parser.parse_args()

    report = validate_fixture(Path(args.fixture))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
