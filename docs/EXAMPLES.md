# Examples

This page explains how the public synthetic fixture is interpreted by the
research-only validation checks. The examples are not market recommendations,
execution guidance, or financial advice.

## Synthetic Observation Row

The public JSONL fixture keeps two rows:

- `obs_SYN_001` is an `offchain_exchange` spot-market observation.
- `obs_SYN_002` is an `offchain_funding` funding-period observation.

Spot example row, formatted for readability:

```json
{
  "observation_id": "obs_SYN_001",
  "symbol": "BTCUSDT",
  "venue_symbol": "BTCUSDT",
  "normalized_symbol": "BTC/USDT",
  "base_asset": "BTC",
  "quote_asset": "USDT",
  "venue": "synthetic_exchange",
  "market_type": "synthetic_spot",
  "quote_currency": "USDT",
  "normalization_version": "synthetic_symbol_normalization_v1",
  "session_model": "continuous_24_7",
  "observed_at": "2026-01-01T00:00:00Z",
  "known_at": "2026-01-01T00:01:00Z",
  "source_ref": "src_SYN_001",
  "research_policy": {
    "policy_id": "research_only_no_advice_no_execution",
    "research_only": true,
    "financial_advice_allowed": false,
    "execution_guidance_allowed": false,
    "jurisdiction_specific_instruction_allowed": false
  },
  "source_lineage": {
    "source_ref": "src_SYN_001",
    "source_type": "synthetic_fixture",
    "evidence_domain": "offchain_exchange",
    "adapter_contract": {
      "adapter_type": "synthetic_fixture_adapter",
      "adapter_schema_version": "synthetic_adapter_contract_v1",
      "provider_contract_version": "synthetic_provider_contract_v1",
      "deprecation_policy": "fail_closed_on_unknown_change",
      "read_only": true,
      "fixture_only": true,
      "network_allowed": false,
      "credential_required": false,
      "private_api_allowed": false
    },
    "venue": "synthetic_exchange",
    "market_type": "synthetic_spot",
    "source_identity_key": "synthetic_exchange:synthetic_spot:BTCUSDT:USDT",
    "source_observed_at": "2026-01-01T00:00:00Z",
    "source_known_at": "2026-01-01T00:01:00Z"
  },
  "hypothesis": "synthetic_liquidity_context",
  "confidence_evidence_score": 0.72,
  "direct_trading_allowed": false,
  "order_execution_allowed": false,
  "private_exchange_api_allowed": false
}
```

The validator treats this as an evidence-quality record:

- `observation_id` identifies the synthetic observation.
- `symbol` and `venue_symbol` preserve the fixture's venue-facing symbol.
- `normalized_symbol`, `base_asset`, `quote_asset`, and
  `normalization_version` make exchange-specific raw symbols comparable without
  treating venue formats as canonical.
- `venue`, `market_type`, and `quote_currency` identify which synthetic market
  context the observation belongs to.
- `session_model` must be `continuous_24_7`, matching crypto-style market
  timing rather than regular market hours.
- `observed_at` is when the synthetic observation is said to occur.
- `known_at` is when the observation is allowed to become usable evidence.
- `source_ref` and `source_lineage.source_ref` must match.
- `research_policy` keeps the row research-only and blocks advice, execution
  guidance, and jurisdiction-specific instructions.
- `source_lineage.evidence_domain` distinguishes off-chain exchange evidence
  from on-chain block and mempool evidence.
- `source_lineage.adapter_contract` keeps adapters read-only, fixture-only,
  network-disabled, credential-free, and private-API-disabled.
- `source_lineage.source_identity_key` prevents the row from implying a single
  universal price source across venues or market types.
- `source_lineage.source_observed_at` and `source_lineage.source_known_at`
  preserve the timing of the source itself, before the row is used as evidence.
- `confidence_evidence_score` is bounded from `0` to `1` and describes fixture
  evidence quality only.
- The three permission flags must remain `false`.

## Known-At Ordering Rule

`observed_at` is the timestamp assigned to the synthetic observation.
`known_at` is the timestamp when that observation is allowed to become usable
research evidence. The validator accepts rows where `known_at` is the same as
or later than `observed_at`.

The source lineage carries the same separation for the source itself:

```text
source_lineage.source_observed_at = 2026-01-01T00:00:00Z
source_lineage.source_known_at    = 2026-01-01T00:01:00Z
```

The row-level `known_at` must not be earlier than
`source_lineage.source_known_at`; otherwise the row would claim source evidence
before the source became available.

The passing example above has:

```text
observed_at = 2026-01-01T00:00:00Z
known_at    = 2026-01-01T00:01:00Z
```

The failing example below reverses that relationship. Its `known_at` value is
earlier than `observed_at`, so the validator reports exactly:

```text
row 1: known_at must not be earlier than observed_at
```

If the source timing itself is reversed, the validator reports:

```text
row 1: source_lineage.source_known_at must not be earlier than source_observed_at
```

If the row claims evidence before the source is known, the validator reports:

```text
row 1: known_at must not be earlier than source_lineage.source_known_at
```

## Confidence Evidence Score Boundaries

`confidence_evidence_score` is evidence-quality metadata for the synthetic
fixture. It is not a forecast, recommendation, or permission field. The
validator accepts numeric values from `0` through `1`, including the boundary
values:

```text
confidence_evidence_score = 0
confidence_evidence_score = 1
```

Values below `0`, above `1`, booleans, or non-numeric values fail validation.
For example, this field value is invalid:

```json
{
  "confidence_evidence_score": 1.2
}
```

Expected validator finding:

```text
row 1: confidence_evidence_score must be a number from 0 to 1
```

## Source Lineage Matching Rule

`source_ref` names the synthetic source reference for the observation.
`source_lineage.source_ref` must repeat the same value so a reviewer can follow
the evidence record back to the source it claims to use. The passing example at
the top of this page uses `src_SYN_001` in both places.

For example, this mismatch is invalid:

```json
{
  "source_ref": "src_SYN_001",
  "source_lineage": {
    "source_ref": "src_OTHER",
    "source_type": "synthetic_fixture",
    "evidence_domain": "offchain_exchange",
    "venue": "synthetic_exchange",
    "market_type": "synthetic_spot",
    "source_identity_key": "synthetic_exchange:synthetic_spot:BTCUSDT:USDT",
    "source_observed_at": "2026-01-01T00:00:00Z",
    "source_known_at": "2026-01-01T00:01:00Z"
  }
}
```

Expected validator finding:

```text
row 1: source_lineage.source_ref must match source_ref
```

## Evidence Domain Rule

`source_lineage.evidence_domain` must identify the evidence family before any
validator can compare or roll up rows. The accepted public domains are:

```text
offchain_exchange
offchain_funding
onchain_block
onchain_mempool
```

The synthetic fixture currently uses `offchain_exchange` because it represents
a local, fixture-only exchange-market observation. A row must not silently mix
that with block-confirmed or mempool-only evidence.

For example, this value is invalid:

```json
{
  "source_lineage": {
    "evidence_domain": "mixed_unknown"
  }
}
```

Expected validator finding:

```text
row 1: source_lineage.evidence_domain must be one of: offchain_exchange, offchain_funding, onchain_block, onchain_mempool
```

## Adapter Contract Rule

`source_lineage.adapter_contract` must describe the adapter boundary without
creating a live adapter. The public fixture accepts only:

```json
{
  "adapter_type": "synthetic_fixture_adapter",
  "adapter_schema_version": "synthetic_adapter_contract_v1",
  "provider_contract_version": "synthetic_provider_contract_v1",
  "deprecation_policy": "fail_closed_on_unknown_change",
  "read_only": true,
  "fixture_only": true,
  "network_allowed": false,
  "credential_required": false,
  "private_api_allowed": false
}
```

Any adapter contract that allows network access, requires credentials, opens a
private API, stops being fixture-only, lacks version metadata, or does not fail
closed on unknown provider-contract changes is rejected.

## Research Policy Rule

Every public fixture row must include:

```json
{
  "policy_id": "research_only_no_advice_no_execution",
  "research_only": true,
  "financial_advice_allowed": false,
  "execution_guidance_allowed": false,
  "jurisdiction_specific_instruction_allowed": false
}
```

This policy marker does not encode legal advice. It keeps the fixture scoped to
research evidence validation and rejects rows that try to become financial
advice, execution guidance, or jurisdiction-specific operating instructions.

## Symbol Normalization Rule

The validator requires both the venue-facing symbol and normalized asset
identity:

```text
symbol
venue_symbol
normalized_symbol
base_asset
quote_asset
quote_currency
normalization_version
```

For the public synthetic fixture, `symbol` must match `venue_symbol`,
`quote_asset` must match `quote_currency`, and `normalized_symbol` must equal
`base_asset/quote_asset`. This keeps exchange-specific raw symbols separate
from normalized comparison keys.

## Continuous Session Rule

The public fixture uses:

```text
session_model = continuous_24_7
```

Rows must not use equity-style regular-session assumptions. Fields such as
`market_open`, `market_close`, `regular_session_open`,
`regular_session_close`, and `trading_session` are forbidden.

## Funding Settlement Rule

Rows with `source_lineage.evidence_domain = "offchain_funding"` must identify
the funding period and whether the value is estimated or settled:

```text
funding_period_start
funding_period_end
settlement_state
```

`settlement_state` must be either `estimated` or `settled`.

Estimated funding rows must not include `settlement_known_at`, because that
would mix pre-settlement and post-settlement evidence. Settled funding rows
must include `settlement_known_at`, and `source_lineage.source_known_at` must
not be earlier than `settlement_known_at`.

The second public fixture row uses this funding shape with
`settlement_state = estimated`, which keeps pre-settlement funding evidence
separate from finalized settlement evidence.

## Domain Extension Readiness

`scripts/validate_synthetic_fixture.py` also reports
`domain_extension_readiness`. This is separate from row-level validation and
checks whether the public fixture is deep enough to support further
coin-domain examples.

The readiness gate currently requires:

```text
offchain_exchange coverage
offchain_funding coverage
continuous_24_7 session model on every row
safe fixture-only adapter contract on every row
research-only policy on every row
source observed/known timing on every row
no fixture contract violations
```

If those conditions are not met, `domain_extension_readiness.status` is
`BLOCKED` even when individual helper functions can still validate isolated
test rows. This prevents broadening the domain before the core evidence
contracts are represented in the public fixture.

## Listing Phase Rule

Rows may include `source_lineage.listing_context` when an asset is newly listed
or listing age affects evidence quality. When present, it must include:

```text
listed_at
listing_phase
listing_age_seconds
thin_market_flag
```

`listing_phase` must be one of:

```text
pre_listing
initial_listing
seasoned
```

`source_lineage.source_known_at` must not be earlier than `listed_at`.
`initial_listing` rows must set `thin_market_flag = true`, and `seasoned` rows
must have at least 86400 seconds of listing age. This prevents fresh listing
data from being treated as normal seasoned-market evidence.

## On-Chain Block Finality Rule

Rows with `source_lineage.evidence_domain = "onchain_block"` must carry chain
and finality metadata:

```text
chain_id
block_number
block_hash
finality_state
reorg_invalidated
evidence_usage
```

`finality_state` must be one of:

```text
finalized
pending
reorg_invalidated
```

If `finality_state` is `reorg_invalidated`, then `reorg_invalidated` must be
`true`. If `finality_state` is `finalized`, then `reorg_invalidated` must be
`false`. This keeps reorg-invalidated block evidence from being treated as
stable historical evidence.

`evidence_usage` must be `stable_evidence` for finalized block evidence and
`invalidation_record` for a reorg-invalidated block record. An
`invalidation_record` must include `superseded_by_block_hash`. Reorg-invalidated
block evidence is also rejected inside `joined_source_refs`; joined sources
must not silently include retroactively invalidated block state.

## On-Chain Mempool State Rule

Rows with `source_lineage.evidence_domain = "onchain_mempool"` must carry
mempool-specific metadata:

```text
chain_id
tx_hash
mempool_observation_id
mempool_state
confirmed_in_block
```

`mempool_state` must be one of:

```text
pending
dropped
included
```

Pending and dropped mempool observations must have `confirmed_in_block =
false`. Included mempool observations must have `confirmed_in_block = true`
and must point to `included_block_number` and `included_block_hash`.

Mempool lineage must not include confirmed block finality fields such as
`block_number`, `block_hash`, `finality_state`, or `reorg_invalidated`.
Confirmed block evidence belongs in an `onchain_block` row.

## Cross-Source Known-At Rule

Rows that join multiple sources, such as cross-venue comparison or arbitrage
context, may include `source_lineage.joined_source_refs`. Each joined source
must identify:

```text
source_ref
evidence_domain
venue
source_known_at
```

The row-level `known_at` must not be earlier than any joined source's
`source_known_at`. This prevents a row from using the later exchange, chain, or
provider observation before it was actually available.

For example, if a row joins two exchange observations and the second source is
known at `2026-01-01T00:02:00Z`, the row itself cannot have `known_at =
2026-01-01T00:01:30Z`.

Source identity is also required. This prevents a coin-domain row from treating
all exchange prices as one universal truth source. For example, this lineage is
invalid because it omits `source_identity_key`:

```json
{
  "source_lineage": {
    "source_ref": "src_SYN_001",
    "source_type": "synthetic_fixture",
    "evidence_domain": "offchain_exchange",
    "adapter_contract": {
      "adapter_type": "synthetic_fixture_adapter",
      "adapter_schema_version": "synthetic_adapter_contract_v1",
      "provider_contract_version": "synthetic_provider_contract_v1",
      "deprecation_policy": "fail_closed_on_unknown_change",
      "read_only": true,
      "fixture_only": true,
      "network_allowed": false,
      "credential_required": false,
      "private_api_allowed": false
    },
    "venue": "synthetic_exchange",
    "market_type": "synthetic_spot",
    "source_observed_at": "2026-01-01T00:00:00Z",
    "source_known_at": "2026-01-01T00:01:00Z"
  }
}
```

Expected validator finding:

```text
row 1: source_lineage missing fields: source_identity_key
```

## Schema Field Validation

The validator keeps the public fixture schema narrow. Required fields must be
present, and fields outside the public schema are rejected so schema drift is
caught before a row is used as research evidence.

Missing required field example:

```json
{
  "observation_id": "obs_SYN_FAIL_SCHEMA",
  "symbol": "BTCUSDT"
}
```

Expected validator finding:

```text
row 1: missing fields: base_asset, confidence_evidence_score, direct_trading_allowed, hypothesis, known_at, market_type, normalization_version, normalized_symbol, observed_at, order_execution_allowed, private_exchange_api_allowed, quote_asset, quote_currency, research_policy, session_model, source_lineage, source_ref, venue, venue_symbol
```

Unexpected field example:

```json
{
  "runtime_hint": "not allowed"
}
```

Expected validator finding:

```text
row 1: unexpected fields: runtime_hint
```

## Failure Examples

The fixture validator rejects rows that would make research evidence hard to
audit:

- Missing `source_lineage`.
- `known_at` earlier than `observed_at`.
- `confidence_evidence_score` outside the `0` to `1` range.
- Extra schema fields such as runtime hints.
- Any fixture field that tries to enable execution or private exchange access.

Example failing row:

```json
{
  "observation_id": "obs_SYN_FAIL_KNOWN_AT",
  "symbol": "BTCUSDT",
  "venue_symbol": "BTCUSDT",
  "normalized_symbol": "BTC/USDT",
  "base_asset": "BTC",
  "quote_asset": "USDT",
  "venue": "synthetic_exchange",
  "market_type": "synthetic_spot",
  "quote_currency": "USDT",
  "normalization_version": "synthetic_symbol_normalization_v1",
  "session_model": "continuous_24_7",
  "observed_at": "2026-01-01T00:10:00Z",
  "known_at": "2026-01-01T00:09:00Z",
  "source_ref": "src_SYN_FAIL_001",
  "research_policy": {
    "policy_id": "research_only_no_advice_no_execution",
    "research_only": true,
    "financial_advice_allowed": false,
    "execution_guidance_allowed": false,
    "jurisdiction_specific_instruction_allowed": false
  },
  "source_lineage": {
    "source_ref": "src_SYN_FAIL_001",
    "source_type": "synthetic_fixture",
    "evidence_domain": "offchain_exchange",
    "adapter_contract": {
      "adapter_type": "synthetic_fixture_adapter",
      "adapter_schema_version": "synthetic_adapter_contract_v1",
      "provider_contract_version": "synthetic_provider_contract_v1",
      "deprecation_policy": "fail_closed_on_unknown_change",
      "read_only": true,
      "fixture_only": true,
      "network_allowed": false,
      "credential_required": false,
      "private_api_allowed": false
    },
    "venue": "synthetic_exchange",
    "market_type": "synthetic_spot",
    "source_identity_key": "synthetic_exchange:synthetic_spot:BTCUSDT:USDT",
    "source_observed_at": "2026-01-01T00:10:00Z",
    "source_known_at": "2026-01-01T00:10:30Z"
  },
  "hypothesis": "synthetic_timing_context",
  "confidence_evidence_score": 0.4,
  "direct_trading_allowed": false,
  "order_execution_allowed": false,
  "private_exchange_api_allowed": false
}
```

Expected validator finding:

```text
row 1: known_at must not be earlier than observed_at
```

This row is useful for documentation because it shows a timing violation
without adding private data, live data access, or any execution path.

Run the examples through the dependency-free checks:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_synthetic_fixture.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_synthetic_fixture_validation
```
