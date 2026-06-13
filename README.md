# Market Evidence Validation Framework

CI: configured in `.github/workflows/ci.yml`; enable the hosted badge after the
public GitHub repository path is finalized.

Market Evidence Validation Framework is a research-only market evidence
validation pipeline for checking whether market observations are traceable,
timestamped, and reviewable before anyone treats them as evidence.

This is not a trading bot. It has no order execution, no private exchange API,
no wallet/account/balance access, and no financial advice. The public repo is
designed around synthetic fixtures and validation contracts, not live markets.

## Why not another backtester?

This project is not about producing market actions. It is about making
market-data claims auditable before anyone trusts them.

Instead of searching for market calls, it checks whether evidence has source
lineage, known-at timing, append-only records, outcome/postmortem links, and
execution-disabled safety boundaries.

## What this catches

- Missing source lineage.
- Known-at or time-travel contamination.
- Outcome rows without source references.
- Postmortems without complete evidence chains.
- Accidental execution path reintroduction.
- Unsafe use of raw market data as confidence evidence.

## Codex angle

This started as an exploratory AI-assisted coding project and was refined into
a small, tested, research-only OSS framework. It demonstrates how Codex can help
turn loosely scoped ideas into maintainable software with explicit safety
boundaries.

## Purpose

The project helps review market-research evidence without creating a path to
trade. It focuses on questions like:

- Did an observation have a source reference?
- Was the source known at the time claimed?
- Can an outcome or postmortem be connected without mutating the original row?
- Does a confidence rollup reflect evidence quality rather than outcome claims?

The intended use is educational and research-oriented: inspect the validation
shape, run fixture-only checks, and adapt the contracts for non-private data.

## Architecture

```text
synthetic fixture
  -> observation validation
  -> source lineage validation
  -> outcome and postmortem validation
  -> historical-forward comparison design
  -> confidence evidence rollup
```

Runtime trading surfaces are intentionally outside this architecture. There is
no exchange order API, no signed request handling, no scanner-to-executor
route, no live/shadow enablement, and no promotion gate.

## Safety Boundaries

- Not a trading bot.
- Research-only market evidence validation pipeline.
- No order execution.
- No private exchange API.
- No signed exchange API.
- No wallet, account, balance, or position access.
- No financial advice.
- No live, shadow, scanner, executor, or promotion runtime connection.

`research_safety.guard` hard-codes `EXECUTION_DISABLED = True`. Environment
variables cannot enable execution. Calls to forbidden runtime surfaces such as
`executor`, `live`, `order`, `scanner`, or `promotion` raise
`ExecutionDisabledError`.

## Fixture-Only Quickstart

Inspect the synthetic fixture:

```bash
sed -n '1,20p' fixtures/synthetic_market_observations.jsonl
```

Validate the synthetic fixture:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_synthetic_fixture.py
```

Run the guard check without writing bytecode:

```bash
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

## Validation Command

If `pytest` is available:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_research_safety_guard.py
```

Without third-party test dependencies:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_synthetic_fixture_validation
```

If `pytest` is not installed, use the fixture validation and guard checks
above. The public repo does not require exchange credentials, services, raw
data, or deployment setup.

## Codex-Built And Maintained

This public copy was prepared with Codex as a research-safe OSS artifact:
allowlist export, safety documentation, execution-disabled guard design,
synthetic fixtures, and validation checks were all shaped to keep the project
positioned as a non-trading evidence validation framework.

## Maintainer Workflow With Codex

Maintenance is tracked as small, reviewable tasks: fixture expansion, source
lineage validation, known-at examples, guard/security checks, CI hardening, and
documentation polish. Codex is used to draft changes, run local validation, and
check that the research-only safety boundary remains intact before human
review.

See `docs/MAINTAINER_PLAN.md` for the current 1-2 week maintainer plan and
issue drafts. See `docs/MAINTENANCE_LOG.md` for the planned / completed / next
maintenance log.

For a line-by-line explanation of the public synthetic fixture, see
`docs/EXAMPLES.md`.
