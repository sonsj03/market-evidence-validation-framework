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

## Later

- Add more validator examples for non-private historical datasets supplied by
  users.
- Add schema diagrams for the fixture -> observation -> lineage -> outcome ->
  postmortem -> confidence flow.
- Add contributor guidance for writing new validators without adding runtime
  execution surfaces.

## Out Of Scope

- Order execution.
- Private or signed exchange APIs.
- Wallet, account, balance, or position access.
- Live/shadow runtime.
- Scanner/executor routing.
- Promotion gates.
- Financial advice.

