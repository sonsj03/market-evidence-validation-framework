# Coin Domain Extension Risks

This project must not expand from synthetic market evidence validation into
coin-domain validation until the risks below are handled as explicit contracts.
The goal is evidence hygiene, not trading execution, exchange integration, or
market advice.

## Data Quality Risks

- No single source of truth: prices can differ across exchanges, venues,
  market types, and quote currencies.
- `observed_at` and `known_at` must remain separate. A row may describe when a
  market event happened, but it must also prove when that information became
  available to the validator.
- On-chain and off-chain data need separate lineage. A block event, mempool
  observation, exchange candle, funding record, and listing notice are not the
  same evidence type.
- Chain reorganizations can invalidate previously observed on-chain facts.
  Rows need finality or reorg status before they can be treated as stable
  evidence.
- Mempool state and confirmed block state must be modeled separately.

## Look-Ahead Bias Risks

- Cross-exchange arbitrage context can leak future or unavailable information
  when venues are joined without per-source `known_at` boundaries.
- Funding data must distinguish pre-settlement expectations from post-
  settlement finalized funding records.
- Newly listed assets need explicit listing-phase metadata. Early data can be
  thin, unstable, manually adjusted, or unavailable on comparable venues.
- Reorg-aware rows must prevent retroactive contamination after chain state is
  rewritten.

## Architecture Risks

- A raw-data normalization layer is required before exchange-specific data can
  be compared.
- Timestamp handling must assume 24/7 markets and avoid equity-market session
  assumptions.
- Current synthetic fixtures are intentionally small and do not yet represent
  realistic coin-domain data shapes.
- Adapter abstractions are needed before adding exchange, chain, or data-
  provider examples. Adapters must remain read-only and credential-free in the
  public repository.

## Scope And Maintenance Risks

- Exchange API schemas and availability change frequently.
- Expanding domain scope before the core evidence contracts are deeper risks
  making both the original framework and the coin-specific layer shallow.
- Regulatory expectations can change, so documentation must avoid financial
  advice, execution guidance, and exchange-specific operational instructions.

## Required Preconditions

Before any coin-domain fixture or validator is added:

- Define per-source identity, source type, and trust metadata.
- Require both `observed_at` and `known_at` on every event-like row.
- Represent exchange, market type, symbol normalization, quote currency, and
  venue timestamp explicitly.
- Require venue raw symbols and normalized symbols to remain separate, with
  explicit base asset, quote asset, quote currency, and normalization version.
- Require a continuous 24/7 session model and reject regular-session
  open/close assumptions in coin-domain rows.
- Add finality fields for chain-derived evidence.
- Require reorg-invalidated on-chain block rows to be explicitly marked and
  blocked from being treated as finalized evidence.
- Reorg-invalidated block rows must only be used as invalidation records, never
  as stable joined evidence for later cross-source rows.
- Distinguish mempool observations from confirmed block observations.
- Keep mempool status separate from block finality; pending or dropped mempool
  rows must not be interpreted as confirmed block evidence.
- Keep all adapters fixture-only, local-file-only, and read-only.
- Adapter contracts must explicitly disable network access, credentials, and
  private APIs.
- Adapter contracts must carry schema/provider contract versions and fail
  closed on unknown provider changes.
- Add tests that reject cross-source joins without source-specific `known_at`
  boundaries.
- Cross-venue or arbitrage-style rows must not be accepted unless every joined
  source carries its own `source_known_at`, and the row-level `known_at` is not
  earlier than the latest joined source.
- Funding rows must distinguish estimated pre-settlement values from settled
  post-settlement values, and settled rows must prove when settlement became
  known.
- Newly listed assets require listing-phase metadata so initial thin-market
  data is not treated as seasoned market evidence.
- Domain expansion should remain blocked until the public fixture covers the
  minimum required evidence domains and passes the readiness gate.
- Every row must carry a research-only policy marker that rejects financial
  advice, execution guidance, and jurisdiction-specific operating instructions.
- Preserve the existing no-execution boundary: no order execution, private API,
  signed request, wallet, account, balance, position, live, shadow, scanner,
  executor, or promotion surface.
