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
  "observed_at": "2026-01-01T00:00:00Z",
  "known_at": "2026-01-01T00:01:00Z",
  "source_ref": "src_SYN_001",
  "source_lineage": {
    "source_ref": "src_SYN_001",
    "source_type": "synthetic_fixture"
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
- `observed_at` is when the synthetic observation is said to occur.
- `known_at` is when the observation is allowed to become usable evidence.
- `source_ref` and `source_lineage.source_ref` must match.
- `confidence_evidence_score` is bounded from `0` to `1` and describes fixture
  evidence quality only.
- The three permission flags must remain `false`.

## Failure Examples

The fixture validator rejects rows that would make research evidence hard to
audit:

- Missing `source_lineage`.
- `known_at` earlier than `observed_at`.
- `confidence_evidence_score` outside the `0` to `1` range.
- Extra schema fields such as runtime hints.
- Any fixture field that tries to enable execution or private exchange access.

Run the examples through the dependency-free checks:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_synthetic_fixture.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_synthetic_fixture_validation
```
