# Safety

This repository is not a trading bot. It is a research-only market evidence
validation pipeline.

It does not provide financial advice, investment advice, market-action
instructions, market calls, or execution guidance.

## Hard Boundaries

- No order execution.
- No private exchange API.
- No signed exchange API.
- No exchange credential handling.
- No wallet, account, balance, or position access.
- No scanner-to-executor connection.
- No live or shadow trading runtime.
- No promotion gate that can authorize trading.
- No trade-alert delivery path.

## Hard-Coded Execution Guard

`research_safety.guard` defines:

```python
EXECUTION_DISABLED = True
```

That value is hard-coded. The public repo does not expose an environment
variable, settings file, CLI flag, or fixture field that can turn execution on.

Forbidden runtime surfaces fail closed:

- `executor`
- `live`
- `order`
- `scanner`
- `promotion`
- private or signed exchange API access
- wallet/account/balance/position access

The expected failure is `ExecutionDisabledError`.

## Data Boundary

Fixtures are synthetic and small. They are included only to exercise evidence
validation contracts. They are not raw market data, personal logs, account
records, exchange exports, or trading ledgers.

## Public-Use Boundary

Use this repository to study validation structure, source lineage, known-at
timestamps, outcome/postmortem linkage, and confidence rollup design. Do not
use it to build or operate an automated trading system.
