"""Minimal unified evidence envelope contract for public audits."""

from __future__ import annotations

from typing import Any


REQUIRED_ENVELOPE_FIELDS = (
    "evidence_id",
    "paper_trade_id",
    "strategy_id",
    "source_type",
    "schema_version",
    "source_lineage",
    "known_at_ts",
    "permission_scope",
    "artifact_hash",
)


def validate_evidence_envelope(row: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    for field in REQUIRED_ENVELOPE_FIELDS:
        if field not in row:
            violations.append(f"missing required envelope field {field}")
    if "permission_scope" in row and not isinstance(row.get("permission_scope"), dict):
        violations.append("permission_scope must be object")
    if "source_lineage" in row and not isinstance(row.get("source_lineage"), dict):
        violations.append("source_lineage must be object")
    if "artifact_hash" in row and not str(row.get("artifact_hash") or "").startswith("sha256:"):
        violations.append("artifact_hash must start with sha256:")
    return violations
