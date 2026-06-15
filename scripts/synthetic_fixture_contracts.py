"""Validate the public synthetic observation fixture.

This script uses only the Python standard library and never reads private
configuration, raw market archives, account data, or network resources.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "observation_id",
    "symbol",
    "venue_symbol",
    "normalized_symbol",
    "base_asset",
    "quote_asset",
    "venue",
    "market_type",
    "quote_currency",
    "normalization_version",
    "session_model",
    "observed_at",
    "known_at",
    "source_ref",
    "source_lineage",
    "research_policy",
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
ALLOWED_SESSION_MODELS = {"continuous_24_7"}
ALLOWED_ADAPTER_TYPES = {
    "synthetic_fixture_adapter",
}
ALLOWED_ADAPTER_DEPRECATION_POLICIES = {
    "fail_closed_on_unknown_change",
}
ALLOWED_EVIDENCE_DOMAINS = {
    "offchain_exchange",
    "offchain_funding",
    "onchain_block",
    "onchain_mempool",
}
ALLOWED_FINALITY_STATES = {
    "pending",
    "finalized",
    "reorg_invalidated",
}
ALLOWED_MEMPOOL_STATES = {
    "pending",
    "dropped",
    "included",
}
ALLOWED_FUNDING_SETTLEMENT_STATES = {
    "estimated",
    "settled",
}
ALLOWED_LISTING_PHASES = {
    "pre_listing",
    "initial_listing",
    "seasoned",
}
ALLOWED_ONCHAIN_BLOCK_EVIDENCE_USAGES = {
    "stable_evidence",
    "invalidation_record",
}
LISTING_CONTEXT_FIELDS = {
    "listed_at",
    "listing_phase",
    "listing_age_seconds",
    "thin_market_flag",
}
FORBIDDEN_SESSION_ASSUMPTION_FIELDS = {
    "market_open",
    "market_close",
    "regular_session_open",
    "regular_session_close",
    "trading_session",
}
REQUIRED_RESEARCH_POLICY_FIELDS = {
    "policy_id",
    "research_only",
    "financial_advice_allowed",
    "execution_guidance_allowed",
    "jurisdiction_specific_instruction_allowed",
}
ONCHAIN_BLOCK_LINEAGE_FIELDS = {
    "chain_id",
    "block_number",
    "block_hash",
    "finality_state",
    "reorg_invalidated",
    "evidence_usage",
}
ONCHAIN_MEMPOOL_LINEAGE_FIELDS = {
    "chain_id",
    "tx_hash",
    "mempool_observation_id",
    "mempool_state",
    "confirmed_in_block",
}
MEMPOOL_FORBIDDEN_BLOCK_FIELDS = {
    "block_number",
    "block_hash",
    "finality_state",
    "reorg_invalidated",
}
OFFCHAIN_FUNDING_LINEAGE_FIELDS = {
    "funding_period_start",
    "funding_period_end",
    "settlement_state",
}
REQUIRED_SOURCE_LINEAGE_FIELDS = {
    "source_ref",
    "source_type",
    "evidence_domain",
    "adapter_contract",
    "venue",
    "market_type",
    "source_identity_key",
    "source_observed_at",
    "source_known_at",
}


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
        joined_source_known_ats: list[datetime] = []
        missing = sorted(REQUIRED_FIELDS - set(row))
        if missing:
            violations.append(f"row {index}: missing fields: {', '.join(missing)}")
        unexpected = sorted(set(row) - ALLOWED_FIELDS)
        if unexpected:
            violations.append(f"row {index}: unexpected fields: {', '.join(unexpected)}")
        forbidden_session_fields = sorted(FORBIDDEN_SESSION_ASSUMPTION_FIELDS & set(row))
        if forbidden_session_fields:
            violations.append(
                f"row {index}: forbidden session assumption fields: {', '.join(forbidden_session_fields)}"
            )

        observation_id = str(row.get("observation_id") or "")
        if not observation_id:
            violations.append(f"row {index}: observation_id must be non-empty")
        elif observation_id in seen_ids:
            violations.append(f"row {index}: duplicate observation_id {observation_id}")
        seen_ids.add(observation_id)

        source_ref = row.get("source_ref")
        if not isinstance(source_ref, str) or not source_ref:
            violations.append(f"row {index}: source_ref must be a non-empty string")

        violations.extend(validate_symbol_normalization(row, index))
        if row.get("session_model") not in ALLOWED_SESSION_MODELS:
            violations.append(f"row {index}: session_model must be continuous_24_7")
        violations.extend(validate_research_policy(row, index))

        source_lineage = row.get("source_lineage")
        source_observed_at = None
        source_known_at = None
        if not isinstance(source_lineage, dict):
            violations.append(f"row {index}: source_lineage must be an object")
        else:
            missing_lineage = sorted(REQUIRED_SOURCE_LINEAGE_FIELDS - set(source_lineage))
            if missing_lineage:
                violations.append(
                    f"row {index}: source_lineage missing fields: {', '.join(missing_lineage)}"
                )
            if source_lineage.get("source_ref") != source_ref:
                violations.append(f"row {index}: source_lineage.source_ref must match source_ref")
            if source_lineage.get("source_type") not in ALLOWED_SOURCE_TYPES:
                violations.append(f"row {index}: source_lineage.source_type must be synthetic_fixture")
            if source_lineage.get("evidence_domain") not in ALLOWED_EVIDENCE_DOMAINS:
                violations.append(
                    f"row {index}: source_lineage.evidence_domain must be one of: "
                    f"{', '.join(sorted(ALLOWED_EVIDENCE_DOMAINS))}"
                )
            if source_lineage.get("evidence_domain") == "onchain_block":
                violations.extend(validate_onchain_block_lineage(source_lineage, index))
            if source_lineage.get("evidence_domain") == "onchain_mempool":
                violations.extend(validate_onchain_mempool_lineage(source_lineage, index))
            if source_lineage.get("evidence_domain") == "offchain_funding":
                violations.extend(validate_offchain_funding_lineage(source_lineage, index))
            violations.extend(validate_adapter_contract(source_lineage, index))
            joined_violations, joined_source_known_ats = validate_joined_source_refs(
                source_lineage,
                index,
            )
            violations.extend(joined_violations)
            violations.extend(validate_listing_context(source_lineage, index))
            if source_lineage.get("venue") != row.get("venue"):
                violations.append(f"row {index}: source_lineage.venue must match venue")
            if source_lineage.get("market_type") != row.get("market_type"):
                violations.append(f"row {index}: source_lineage.market_type must match market_type")
            identity_key = source_lineage.get("source_identity_key")
            if not isinstance(identity_key, str) or not identity_key:
                violations.append(f"row {index}: source_lineage.source_identity_key must be non-empty")
            source_observed_at = parse_utc_timestamp(source_lineage.get("source_observed_at"))
            source_known_at = parse_utc_timestamp(source_lineage.get("source_known_at"))
            if source_observed_at is None:
                violations.append(
                    f"row {index}: source_lineage.source_observed_at must be an ISO-8601 UTC timestamp"
                )
            if source_known_at is None:
                violations.append(
                    f"row {index}: source_lineage.source_known_at must be an ISO-8601 UTC timestamp"
                )
            if (
                source_observed_at is not None
                and source_known_at is not None
                and source_known_at < source_observed_at
            ):
                violations.append(
                    f"row {index}: source_lineage.source_known_at must not be earlier than source_observed_at"
                )

        observed_at = parse_utc_timestamp(row.get("observed_at"))
        known_at = parse_utc_timestamp(row.get("known_at"))
        if observed_at is None:
            violations.append(f"row {index}: observed_at must be an ISO-8601 UTC timestamp")
        if known_at is None:
            violations.append(f"row {index}: known_at must be an ISO-8601 UTC timestamp")
        if observed_at is not None and known_at is not None and known_at < observed_at:
            violations.append(f"row {index}: known_at must not be earlier than observed_at")
        if known_at is not None and source_known_at is not None and known_at < source_known_at:
            violations.append(f"row {index}: known_at must not be earlier than source_lineage.source_known_at")
        for joined_known_at in joined_source_known_ats:
            if known_at is not None and known_at < joined_known_at:
                violations.append(
                    f"row {index}: known_at must not be earlier than any joined_source_refs.source_known_at"
                )
                break

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


def validate_symbol_normalization(row: dict[str, Any], row_index: int) -> list[str]:
    violations: list[str] = []
    for field in (
        "venue_symbol",
        "normalized_symbol",
        "base_asset",
        "quote_asset",
        "quote_currency",
        "normalization_version",
    ):
        if not isinstance(row.get(field), str) or not row.get(field):
            violations.append(f"row {row_index}: {field} must be a non-empty string")
    base_asset = row.get("base_asset")
    quote_asset = row.get("quote_asset")
    normalized_symbol = row.get("normalized_symbol")
    if isinstance(base_asset, str) and isinstance(quote_asset, str) and isinstance(normalized_symbol, str):
        expected = f"{base_asset}/{quote_asset}"
        if normalized_symbol != expected:
            violations.append(f"row {row_index}: normalized_symbol must equal base_asset/quote_asset")
    if row.get("quote_asset") != row.get("quote_currency"):
        violations.append(f"row {row_index}: quote_asset must match quote_currency")
    if row.get("symbol") != row.get("venue_symbol"):
        violations.append(f"row {row_index}: symbol must match venue_symbol in synthetic fixture rows")
    return violations


def validate_research_policy(row: dict[str, Any], row_index: int) -> list[str]:
    policy = row.get("research_policy")
    if not isinstance(policy, dict):
        return [f"row {row_index}: research_policy must be an object"]
    violations: list[str] = []
    missing = sorted(REQUIRED_RESEARCH_POLICY_FIELDS - set(policy))
    if missing:
        violations.append(f"row {row_index}: research_policy missing fields: {', '.join(missing)}")
    if policy.get("policy_id") != "research_only_no_advice_no_execution":
        violations.append(
            f"row {row_index}: research_policy.policy_id must be research_only_no_advice_no_execution"
        )
    expected_flags = {
        "research_only": True,
        "financial_advice_allowed": False,
        "execution_guidance_allowed": False,
        "jurisdiction_specific_instruction_allowed": False,
    }
    for field, expected in expected_flags.items():
        if policy.get(field) is not expected:
            violations.append(f"row {row_index}: research_policy.{field} must be {str(expected).lower()}")
    return violations


def validate_adapter_contract(source_lineage: dict[str, Any], row_index: int) -> list[str]:
    adapter = source_lineage.get("adapter_contract")
    if not isinstance(adapter, dict):
        return [f"row {row_index}: source_lineage.adapter_contract must be an object"]
    violations: list[str] = []
    required = {
        "adapter_type",
        "adapter_schema_version",
        "provider_contract_version",
        "deprecation_policy",
        "read_only",
        "fixture_only",
        "network_allowed",
        "credential_required",
        "private_api_allowed",
    }
    missing = sorted(required - set(adapter))
    if missing:
        violations.append(
            f"row {row_index}: source_lineage.adapter_contract missing fields: {', '.join(missing)}"
        )
    if adapter.get("adapter_type") not in ALLOWED_ADAPTER_TYPES:
        violations.append(
            f"row {row_index}: source_lineage.adapter_contract.adapter_type must be synthetic_fixture_adapter"
        )
    for field in ("adapter_schema_version", "provider_contract_version"):
        if not isinstance(adapter.get(field), str) or not adapter.get(field):
            violations.append(f"row {row_index}: source_lineage.adapter_contract.{field} must be non-empty")
    if adapter.get("deprecation_policy") not in ALLOWED_ADAPTER_DEPRECATION_POLICIES:
        violations.append(
            "row "
            f"{row_index}: source_lineage.adapter_contract.deprecation_policy must be fail_closed_on_unknown_change"
        )
    expected_flags = {
        "read_only": True,
        "fixture_only": True,
        "network_allowed": False,
        "credential_required": False,
        "private_api_allowed": False,
    }
    for field, expected in expected_flags.items():
        if adapter.get(field) is not expected:
            violations.append(
                f"row {row_index}: source_lineage.adapter_contract.{field} must be {str(expected).lower()}"
            )
    return violations


def validate_onchain_block_lineage(source_lineage: dict[str, Any], row_index: int) -> list[str]:
    violations: list[str] = []
    missing = sorted(ONCHAIN_BLOCK_LINEAGE_FIELDS - set(source_lineage))
    if missing:
        violations.append(
            f"row {row_index}: onchain_block source_lineage missing fields: {', '.join(missing)}"
        )
    chain_id = source_lineage.get("chain_id")
    if not isinstance(chain_id, str) or not chain_id:
        violations.append(f"row {row_index}: source_lineage.chain_id must be non-empty for onchain_block")
    block_number = source_lineage.get("block_number")
    if isinstance(block_number, bool) or not isinstance(block_number, int) or block_number < 0:
        violations.append(f"row {row_index}: source_lineage.block_number must be a non-negative integer for onchain_block")
    block_hash = source_lineage.get("block_hash")
    if not isinstance(block_hash, str) or not block_hash:
        violations.append(f"row {row_index}: source_lineage.block_hash must be non-empty for onchain_block")
    finality_state = source_lineage.get("finality_state")
    if finality_state not in ALLOWED_FINALITY_STATES:
        violations.append(
            f"row {row_index}: source_lineage.finality_state must be one of: "
            f"{', '.join(sorted(ALLOWED_FINALITY_STATES))}"
        )
    reorg_invalidated = source_lineage.get("reorg_invalidated")
    if not isinstance(reorg_invalidated, bool):
        violations.append(f"row {row_index}: source_lineage.reorg_invalidated must be boolean for onchain_block")
    if finality_state == "reorg_invalidated" and reorg_invalidated is not True:
        violations.append(
            f"row {row_index}: source_lineage.reorg_invalidated must be true when finality_state is reorg_invalidated"
        )
    if finality_state == "finalized" and reorg_invalidated is True:
        violations.append(
            f"row {row_index}: finalized onchain_block source_lineage must not be reorg_invalidated"
        )
    evidence_usage = source_lineage.get("evidence_usage")
    if evidence_usage not in ALLOWED_ONCHAIN_BLOCK_EVIDENCE_USAGES:
        violations.append(
            f"row {row_index}: source_lineage.evidence_usage must be one of: "
            f"{', '.join(sorted(ALLOWED_ONCHAIN_BLOCK_EVIDENCE_USAGES))}"
        )
    if finality_state == "reorg_invalidated" and evidence_usage != "invalidation_record":
        violations.append(
            f"row {row_index}: reorg_invalidated onchain_block source_lineage must use evidence_usage invalidation_record"
        )
    if finality_state == "finalized" and evidence_usage != "stable_evidence":
        violations.append(
            f"row {row_index}: finalized onchain_block source_lineage must use evidence_usage stable_evidence"
        )
    if evidence_usage == "invalidation_record":
        superseded_by = source_lineage.get("superseded_by_block_hash")
        if not isinstance(superseded_by, str) or not superseded_by:
            violations.append(
                f"row {row_index}: invalidation_record onchain_block source_lineage requires superseded_by_block_hash"
            )
    return violations


def validate_onchain_mempool_lineage(source_lineage: dict[str, Any], row_index: int) -> list[str]:
    violations: list[str] = []
    missing = sorted(ONCHAIN_MEMPOOL_LINEAGE_FIELDS - set(source_lineage))
    if missing:
        violations.append(
            f"row {row_index}: onchain_mempool source_lineage missing fields: {', '.join(missing)}"
        )
    forbidden_present = sorted(MEMPOOL_FORBIDDEN_BLOCK_FIELDS & set(source_lineage))
    if forbidden_present:
        violations.append(
            f"row {row_index}: onchain_mempool source_lineage must not include confirmed block fields: "
            f"{', '.join(forbidden_present)}"
        )
    chain_id = source_lineage.get("chain_id")
    if not isinstance(chain_id, str) or not chain_id:
        violations.append(f"row {row_index}: source_lineage.chain_id must be non-empty for onchain_mempool")
    tx_hash = source_lineage.get("tx_hash")
    if not isinstance(tx_hash, str) or not tx_hash:
        violations.append(f"row {row_index}: source_lineage.tx_hash must be non-empty for onchain_mempool")
    mempool_observation_id = source_lineage.get("mempool_observation_id")
    if not isinstance(mempool_observation_id, str) or not mempool_observation_id:
        violations.append(
            f"row {row_index}: source_lineage.mempool_observation_id must be non-empty for onchain_mempool"
        )
    mempool_state = source_lineage.get("mempool_state")
    if mempool_state not in ALLOWED_MEMPOOL_STATES:
        violations.append(
            f"row {row_index}: source_lineage.mempool_state must be one of: "
            f"{', '.join(sorted(ALLOWED_MEMPOOL_STATES))}"
        )
    confirmed_in_block = source_lineage.get("confirmed_in_block")
    if not isinstance(confirmed_in_block, bool):
        violations.append(f"row {row_index}: source_lineage.confirmed_in_block must be boolean for onchain_mempool")
    if mempool_state in {"pending", "dropped"} and confirmed_in_block is not False:
        violations.append(
            f"row {row_index}: source_lineage.confirmed_in_block must be false when mempool_state is {mempool_state}"
        )
    if mempool_state == "included":
        if confirmed_in_block is not True:
            violations.append(
                "row "
                f"{row_index}: source_lineage.confirmed_in_block must be true when mempool_state is included"
            )
        if not isinstance(source_lineage.get("included_block_number"), int):
            violations.append(
                f"row {row_index}: source_lineage.included_block_number must be an integer when mempool_state is included"
            )
        if not isinstance(source_lineage.get("included_block_hash"), str) or not source_lineage.get("included_block_hash"):
            violations.append(
                f"row {row_index}: source_lineage.included_block_hash must be non-empty when mempool_state is included"
            )
    return violations


def validate_joined_source_refs(
    source_lineage: dict[str, Any],
    row_index: int,
) -> tuple[list[str], list[datetime]]:
    joined_sources = source_lineage.get("joined_source_refs")
    if joined_sources is None:
        return [], []
    violations: list[str] = []
    known_ats: list[datetime] = []
    if not isinstance(joined_sources, list):
        return [f"row {row_index}: source_lineage.joined_source_refs must be a list"], []
    if len(joined_sources) < 2:
        violations.append(f"row {row_index}: source_lineage.joined_source_refs must contain at least two sources")
    required_fields = {"source_ref", "evidence_domain", "venue", "source_known_at"}
    for source_index, source in enumerate(joined_sources, start=1):
        if not isinstance(source, dict):
            violations.append(f"row {row_index}: joined_source_refs[{source_index}] must be an object")
            continue
        missing = sorted(required_fields - set(source))
        if missing:
            violations.append(
                f"row {row_index}: joined_source_refs[{source_index}] missing fields: {', '.join(missing)}"
            )
        if source.get("evidence_domain") not in ALLOWED_EVIDENCE_DOMAINS:
            violations.append(
                f"row {row_index}: joined_source_refs[{source_index}].evidence_domain must be one of: "
                f"{', '.join(sorted(ALLOWED_EVIDENCE_DOMAINS))}"
            )
        if source.get("evidence_domain") == "onchain_block":
            joined_finality = source.get("finality_state")
            joined_reorg_invalidated = source.get("reorg_invalidated")
            if joined_finality == "reorg_invalidated" or joined_reorg_invalidated is True:
                violations.append(
                    f"row {row_index}: joined_source_refs[{source_index}] must not use reorg-invalidated onchain_block evidence"
                )
        if not isinstance(source.get("source_ref"), str) or not source.get("source_ref"):
            violations.append(f"row {row_index}: joined_source_refs[{source_index}].source_ref must be non-empty")
        if not isinstance(source.get("venue"), str) or not source.get("venue"):
            violations.append(f"row {row_index}: joined_source_refs[{source_index}].venue must be non-empty")
        source_known_at = parse_utc_timestamp(source.get("source_known_at"))
        if source_known_at is None:
            violations.append(
                f"row {row_index}: joined_source_refs[{source_index}].source_known_at must be an ISO-8601 UTC timestamp"
            )
        else:
            known_ats.append(source_known_at)
    return violations, known_ats


def validate_offchain_funding_lineage(source_lineage: dict[str, Any], row_index: int) -> list[str]:
    violations: list[str] = []
    missing = sorted(OFFCHAIN_FUNDING_LINEAGE_FIELDS - set(source_lineage))
    if missing:
        violations.append(
            f"row {row_index}: offchain_funding source_lineage missing fields: {', '.join(missing)}"
        )
    period_start = parse_utc_timestamp(source_lineage.get("funding_period_start"))
    period_end = parse_utc_timestamp(source_lineage.get("funding_period_end"))
    if period_start is None:
        violations.append(
            f"row {row_index}: source_lineage.funding_period_start must be an ISO-8601 UTC timestamp"
        )
    if period_end is None:
        violations.append(
            f"row {row_index}: source_lineage.funding_period_end must be an ISO-8601 UTC timestamp"
        )
    if period_start is not None and period_end is not None and period_end <= period_start:
        violations.append(
            f"row {row_index}: source_lineage.funding_period_end must be later than funding_period_start"
        )
    settlement_state = source_lineage.get("settlement_state")
    if settlement_state not in ALLOWED_FUNDING_SETTLEMENT_STATES:
        violations.append(
            f"row {row_index}: source_lineage.settlement_state must be one of: "
            f"{', '.join(sorted(ALLOWED_FUNDING_SETTLEMENT_STATES))}"
        )
    settlement_known_at = parse_utc_timestamp(source_lineage.get("settlement_known_at"))
    source_known_at = parse_utc_timestamp(source_lineage.get("source_known_at"))
    if settlement_state == "estimated" and "settlement_known_at" in source_lineage:
        violations.append(
            f"row {row_index}: estimated offchain_funding source_lineage must not include settlement_known_at"
        )
    if settlement_state == "settled":
        if settlement_known_at is None:
            violations.append(
                f"row {row_index}: settled offchain_funding source_lineage requires settlement_known_at"
            )
        elif source_known_at is not None and source_known_at < settlement_known_at:
            violations.append(
                f"row {row_index}: source_lineage.source_known_at must not be earlier than settlement_known_at for settled offchain_funding"
            )
    return violations


def validate_listing_context(source_lineage: dict[str, Any], row_index: int) -> list[str]:
    listing_context = source_lineage.get("listing_context")
    if listing_context is None:
        return []
    violations: list[str] = []
    if not isinstance(listing_context, dict):
        return [f"row {row_index}: source_lineage.listing_context must be an object"]
    missing = sorted(LISTING_CONTEXT_FIELDS - set(listing_context))
    if missing:
        violations.append(
            f"row {row_index}: source_lineage.listing_context missing fields: {', '.join(missing)}"
        )
    listed_at = parse_utc_timestamp(listing_context.get("listed_at"))
    source_known_at = parse_utc_timestamp(source_lineage.get("source_known_at"))
    if listed_at is None:
        violations.append(
            f"row {row_index}: source_lineage.listing_context.listed_at must be an ISO-8601 UTC timestamp"
        )
    listing_phase = listing_context.get("listing_phase")
    if listing_phase not in ALLOWED_LISTING_PHASES:
        violations.append(
            f"row {row_index}: source_lineage.listing_context.listing_phase must be one of: "
            f"{', '.join(sorted(ALLOWED_LISTING_PHASES))}"
        )
    listing_age_seconds = listing_context.get("listing_age_seconds")
    if (
        isinstance(listing_age_seconds, bool)
        or not isinstance(listing_age_seconds, int)
        or listing_age_seconds < 0
    ):
        violations.append(
            f"row {row_index}: source_lineage.listing_context.listing_age_seconds must be a non-negative integer"
        )
    thin_market_flag = listing_context.get("thin_market_flag")
    if not isinstance(thin_market_flag, bool):
        violations.append(
            f"row {row_index}: source_lineage.listing_context.thin_market_flag must be boolean"
        )
    if listed_at is not None and source_known_at is not None and source_known_at < listed_at:
        violations.append(
            f"row {row_index}: source_lineage.source_known_at must not be earlier than listing_context.listed_at"
        )
    if listing_phase == "initial_listing" and thin_market_flag is not True:
        violations.append(
            f"row {row_index}: initial_listing listing_context requires thin_market_flag true"
        )
    if listing_phase == "seasoned" and isinstance(listing_age_seconds, int) and listing_age_seconds < 86_400:
        violations.append(
            f"row {row_index}: seasoned listing_context requires listing_age_seconds of at least 86400"
        )
    return violations


def validate_fixture(path: Path) -> dict[str, Any]:
    rows = load_jsonl(path)
    violations = validate_rows(rows)
    readiness = build_domain_extension_readiness(rows, violations)
    return {
        "fixture": str(path),
        "row_count": len(rows),
        "status": "PASS" if not violations else "FAIL",
        "domain_extension_readiness": readiness,
        "violations": violations,
    }


def build_domain_extension_readiness(
    rows: list[dict[str, Any]],
    violations: list[str],
) -> dict[str, Any]:
    domains = {
        str(row.get("source_lineage", {}).get("evidence_domain") or "")
        for row in rows
        if isinstance(row.get("source_lineage"), dict)
    }
    required_domains = {"offchain_exchange", "offchain_funding"}
    blockers: list[str] = []
    if violations:
        blockers.append("fixture_contract_violations_present")
    if not required_domains.issubset(domains):
        blockers.append("public_fixture_must_cover_offchain_exchange_and_funding")
    if not all(row.get("session_model") == "continuous_24_7" for row in rows):
        blockers.append("all_rows_must_use_continuous_24_7_session_model")
    if not all(_research_policy_ready(row) for row in rows):
        blockers.append("all_rows_must_have_research_only_policy")
    if not all(_adapter_contract_ready(row) for row in rows):
        blockers.append("all_rows_must_have_safe_adapter_contract")
    if not all(_source_lineage_timing_ready(row) for row in rows):
        blockers.append("all_rows_must_have_source_lineage_timing")
    return {
        "status": "READY" if not blockers else "BLOCKED",
        "covered_evidence_domains": sorted(domain for domain in domains if domain),
        "required_public_fixture_domains": sorted(required_domains),
        "blockers": blockers,
    }


def _adapter_contract_ready(row: dict[str, Any]) -> bool:
    lineage = row.get("source_lineage") if isinstance(row.get("source_lineage"), dict) else {}
    adapter = lineage.get("adapter_contract") if isinstance(lineage.get("adapter_contract"), dict) else {}
    return (
        adapter.get("adapter_type") == "synthetic_fixture_adapter"
        and adapter.get("adapter_schema_version")
        and adapter.get("provider_contract_version")
        and adapter.get("deprecation_policy") == "fail_closed_on_unknown_change"
        and adapter.get("read_only") is True
        and adapter.get("fixture_only") is True
        and adapter.get("network_allowed") is False
        and adapter.get("credential_required") is False
        and adapter.get("private_api_allowed") is False
    )


def _research_policy_ready(row: dict[str, Any]) -> bool:
    policy = row.get("research_policy") if isinstance(row.get("research_policy"), dict) else {}
    return (
        policy.get("policy_id") == "research_only_no_advice_no_execution"
        and policy.get("research_only") is True
        and policy.get("financial_advice_allowed") is False
        and policy.get("execution_guidance_allowed") is False
        and policy.get("jurisdiction_specific_instruction_allowed") is False
    )


def _source_lineage_timing_ready(row: dict[str, Any]) -> bool:
    lineage = row.get("source_lineage") if isinstance(row.get("source_lineage"), dict) else {}
    return (
        parse_utc_timestamp(row.get("observed_at")) is not None
        and parse_utc_timestamp(row.get("known_at")) is not None
        and parse_utc_timestamp(lineage.get("source_observed_at")) is not None
        and parse_utc_timestamp(lineage.get("source_known_at")) is not None
    )
