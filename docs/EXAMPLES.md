# Examples

This page explains how the public synthetic fixture is interpreted by the
research-only validation checks. The examples are not market recommendations,
execution guidance, or financial advice.

## Synthetic Observation Row

Example row, formatted for readability:

```json
{
  "observation_id": "obs_SYN_001",
  "symbol": "BTCUSDT",
  "venue": "synthetic_exchange",
  "market_type": "synthetic_spot",
  "quote_currency": "USDT",
  "observed_at": "2026-01-01T00:00:00Z",
  "known_at": "2026-01-01T00:01:00Z",
  "source_ref": "src_SYN_001",
  "source_lineage": {
    "source_ref": "src_SYN_001",
    "source_type": "synthetic_fixture",
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
- `venue`, `market_type`, and `quote_currency` identify which synthetic market
  context the observation belongs to.
- `observed_at` is when the synthetic observation is said to occur.
- `known_at` is when the observation is allowed to become usable evidence.
- `source_ref` and `source_lineage.source_ref` must match.
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

Source identity is also required. This prevents a coin-domain row from treating
all exchange prices as one universal truth source. For example, this lineage is
invalid because it omits `source_identity_key`:

```json
{
  "source_lineage": {
    "source_ref": "src_SYN_001",
    "source_type": "synthetic_fixture",
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
row 1: missing fields: confidence_evidence_score, direct_trading_allowed, hypothesis, known_at, market_type, observed_at, order_execution_allowed, private_exchange_api_allowed, quote_currency, source_lineage, source_ref, venue
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
  "venue": "synthetic_exchange",
  "market_type": "synthetic_spot",
  "quote_currency": "USDT",
  "observed_at": "2026-01-01T00:10:00Z",
  "known_at": "2026-01-01T00:09:00Z",
  "source_ref": "src_SYN_FAIL_001",
  "source_lineage": {
    "source_ref": "src_SYN_FAIL_001",
    "source_type": "synthetic_fixture",
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
