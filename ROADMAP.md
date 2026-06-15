# Roadmap

This roadmap keeps the project positioned as a research-only market evidence
validation pipeline, not a trading bot.

## Near Term

- Keep synthetic fixtures small and inspectable.
- Add fixture-only examples for observation, source lineage, outcome,
  postmortem, and confidence rollup validation.
- Improve documentation around known-at timestamps and immutable evidence
  rows.
- Keep CI focused on syntax checks and safety guard checks.
- Follow the 1-2 week maintainer plan in `docs/MAINTAINER_PLAN.md`.
- Record each maintenance cycle in `docs/MAINTENANCE_LOG.md`.
- Convert maintainer-plan drafts into GitHub issues after repository creation.

## Later

- Add more validator examples for non-private historical datasets supplied by
  users.
- Define coin-domain extension contracts before adding exchange, on-chain,
  mempool, funding, listing, or cross-venue fixtures. See
  `docs/COIN_DOMAIN_EXTENSION_RISKS.md`.
- Add schema diagrams for the fixture -> observation -> lineage -> outcome ->
  postmortem -> confidence flow.
- Add contributor guidance for writing new validators without adding runtime
  execution surfaces.
- Prepare a v0.1.0 release once fixture validation, guard tests, syntax checks,
  and safety scans are consistently green.

## Out Of Scope

- Order execution.
- Private or signed exchange APIs.
- Wallet, account, balance, or position access.
- Live/shadow runtime.
- Scanner/executor routing.
- Promotion gates.
- Financial advice.
