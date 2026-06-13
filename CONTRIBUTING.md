# Contributing

Thanks for considering a contribution.

This project is a research-only market evidence validation pipeline. It is not
a trading bot. Contributions must preserve the safety boundary: no order
execution, no private exchange API, no wallet/account/balance access, no
scanner-to-executor routing, no live/shadow runtime, and no promotion gate.

## Accepted Contributions

- Fixture-only validation improvements.
- Source lineage and known-at timestamp checks.
- Outcome and postmortem validation.
- Confidence rollup quality checks.
- Documentation that makes the research-only boundary clearer.
- Tests for `research_safety.guard`.
- Maintenance tasks listed in `docs/MAINTAINER_PLAN.md`.

## Not Accepted

- Exchange order placement or cancellation code.
- Private or signed exchange API clients.
- Wallet, account, balance, or position access.
- Live, shadow, scanner, executor, or promotion enablement.
- Trade alerts or financial advice.

## Issue Triage

Maintainers prioritize safety, fixture validation, source-lineage examples,
known-at validation, CI hardening, and documentation polish. Requests that add
runtime execution behavior are closed as out of scope.
Maintenance pass status is recorded in `docs/MAINTENANCE_LOG.md`.

## Local Checks

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m compileall -q .
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_synthetic_fixture.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_synthetic_fixture_validation
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
from research_safety.guard import ExecutionDisabledError, assert_research_only, require_execution_disabled

assert assert_research_only() is True
for surface in ["executor", "live", "order", "scanner", "promotion"]:
    try:
        require_execution_disabled(surface)
    except ExecutionDisabledError:
        pass
    else:
        raise AssertionError(f"{surface} did not fail closed")
print("research safety guard: PASS")
PY
```
