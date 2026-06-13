# Architecture

The public architecture is intentionally small and research-only.

```text
fixture
  -> observation
  -> source lineage
  -> outcome / postmortem
  -> historical-forward comparison
  -> confidence rollup
```

## 1. Fixture

Synthetic fixtures provide tiny, inspectable input rows. They exist so the
validators can be run without private data, raw market archives, exchange
accounts, background services, or network collectors.

## 2. Observation

Observation validators check that a row has the minimum fields needed for
research review. The row is not an order, trigger, or market-action
instruction.

## 3. Source Lineage

Source-lineage checks connect observations to source references and known-at
timestamps. The goal is replay-safe evidence hygiene: a row should not claim
information that was unavailable at the time.

## 4. Outcome And Postmortem

Outcome and postmortem validators attach later review context without mutating
the original observation. This keeps the evidence chain auditable and avoids
rewriting history after an outcome is known.

## 5. Historical-Forward Comparison

Historical-forward comparison is treated as research context. It is not a
promotion gate and cannot authorize trading. Its role is to compare whether
evidence quality, source coverage, and context remain consistent across time.

## 6. Confidence Rollup

Confidence rollup is evidence-quality metadata. It should reflect source
coverage, outcome linkage, postmortem completeness, known-at integrity, and
blocker reduction. It is not a performance claim.

## Explicit Non-Architecture

These surfaces are intentionally absent:

- Exchange order APIs.
- Private or signed exchange requests.
- Wallet, account, balance, or position access.
- Scanner-to-executor routing.
- Live or shadow runtime enablement.
- Promotion gates.
- Deployment services.
- Trade-alert delivery.

The hard-coded safety guard in `research_safety.guard` keeps execution disabled
even if a downstream user tries to touch a forbidden runtime surface.
