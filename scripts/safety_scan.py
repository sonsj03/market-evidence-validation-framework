"""Dependency-free safety scan for the public research-only repository."""

from __future__ import annotations

import argparse
from pathlib import Path


FORBIDDEN_PATH_PARTS = {
    ".env",
    "secret",
    "credential",
    "session",
    "wallet",
    "account",
}
FORBIDDEN_SUFFIXES = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".parquet",
    ".pkl",
    ".pickle",
    ".log",
}
ALLOWED_JSONL = {Path("fixtures/synthetic_market_observations.jsonl")}
ROOT = Path(__file__).resolve().parents[1]


def scan(root: Path) -> list[str]:
    violations: list[str] = []
    for path in sorted(root.rglob("*")):
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        rel_text = rel.as_posix().lower()
        if path.suffix.lower() == ".jsonl" and rel not in ALLOWED_JSONL:
            violations.append(f"unexpected jsonl artifact: {rel}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            violations.append(f"forbidden artifact suffix: {rel}")
        if any(part in rel_text for part in FORBIDDEN_PATH_PARTS):
            violations.append(f"forbidden path marker: {rel}")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan for public safety-boundary artifact drift.")
    parser.add_argument("root", nargs="?", default=None)
    args = parser.parse_args()
    root = Path(args.root).resolve() if args.root else ROOT
    violations = scan(root)
    if violations:
        for violation in violations:
            print(violation)
        return 1
    print("safety scan: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
