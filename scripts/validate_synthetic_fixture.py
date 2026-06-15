"""Validate the public synthetic observation fixture."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.synthetic_fixture_contracts import (
    build_domain_extension_readiness,
    load_jsonl,
    parse_utc_timestamp,
    validate_fixture,
    validate_rows,
)


__all__ = [
    "build_domain_extension_readiness",
    "load_jsonl",
    "parse_utc_timestamp",
    "validate_fixture",
    "validate_rows",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate synthetic fixture rows")
    parser.add_argument(
        "fixture",
        nargs="?",
        default=None,
        help="Path to the synthetic JSONL fixture",
    )
    args = parser.parse_args()

    fixture = Path(args.fixture) if args.fixture else ROOT / "fixtures" / "synthetic_market_observations.jsonl"
    report = validate_fixture(fixture)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
