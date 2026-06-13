# Experiment Manifest

Updated: 2026-05-12

## Purpose

The repository contains active validation tools, data-foundation tools, diagnostics, and rejected legacy experiments in the same `backtest/experiments/` directory. That is useful for reproducibility but dangerous for promotion decisions.

`backtest/experiments/experiment_manifest.py` is now the source of truth for script-level governance.

Scope boundary:

- The manifest classifies executable experiment scripts under `backtest/experiments/`.
- Research artifact composers under `backtest/research/` are governed by artifact
  contracts, explicit no-execution flags, storage contracts, and operator status
  visibility rather than this script manifest.
- A `backtest/research/` module only needs manifest classification if it is moved
  into `backtest/experiments/` or becomes an experiment runner entry point.

## Status Classes

- `ACTIVE_FOUNDATION`: data, coverage, registry, or verdict infrastructure. These scripts support research but do not promote strategies by themselves.
- `ACTIVE_VALIDATION`: current validation paths that may contribute to promotion or rejection decisions.
- `DIAGNOSTIC_ONLY`: useful for inspection, but not valid as a final promotion path.
- `REJECTED_LEGACY`: old strategy research paths rejected by the current roadmap.
- `ARCHIVE_CANDIDATE`: older parameter-grid or tuning tools retained for reproducibility, not current research direction.

## Current Rule

Only `promotion_allowed=True` scripts may be used as direct strategy-promotion evidence. Everything else can be run for debugging, supporting analysis, risk review, or historical reproduction only.

`ACTIVE_VALIDATION` does not automatically mean `promotion_allowed=True`. A report, ledger replay, fill analysis, or cap simulation can support a decision, but it must not become standalone proof of edge.

Experiment result envelopes are evidence artifacts, not execution approval
artifacts. They must keep `direct_trading_allowed=false` and
`strategy_execution_allowed=false` even when `promotion_allowed=true`; live or
limited-live permission still requires registry/shadow/manual approval gates.

The most important current split:

- Use `run_delta_neutral_basis_scan.py` and `run_delta_neutral_basis_rolling_scan.py` for direct delta-neutral carry validation.
- Treat `run_delta_neutral_ledger_replay.py` as supporting accounting evidence, not standalone promotion evidence.
- Do not use `run_delta_neutral_carry_scan.py` as promotion evidence. It is funding-only and optimistic.
- Do not use legacy directional, cross-asset mean-reversion, stop-sweep, listing-dump, or old grid scripts as promotion evidence without a new economic rationale and a fresh data contract.

## Result Artifact Quarantine

Script governance is not enough by itself because old JSON result files can
still contain legacy labels such as `PROMOTE_REPLAY_CANDIDATE`. Those labels
are historical output vocabulary, not current promotion authority.

Current audit artifact:

```text
backtest/results/stale_promotion_artifact_audit_latest.json
```

Current rule:

- any result file listed in the stale promotion audit is `promotion_allowed=false`;
- required handling is `do_not_use_as_promotion_evidence`;
- old result files may remain for reproducibility, but promotion decisions must
  start from current manifest-governed scripts, current readiness artifacts, and
  registry-backed validation/shadow lineage;
- operator status reports render the stale audit so these files are visible
  before strategy discussion.

## Commands

```bash
python3 -m backtest.experiments.show_experiment_manifest
python3 -m backtest.experiments.show_experiment_manifest --status REJECTED_LEGACY
python3 -m backtest.experiments.show_experiment_manifest --unclassified
python3 -m backtest.experiments.run_validation_engine_v2_report --section H
python3 -m backtest.research.stale_promotion_artifact_audit \
  --out-json backtest/results/stale_promotion_artifact_audit_latest.json
```

## Remaining Cleanup

This manifest blocks accidental promotion, but it does not delete old files. The next cleanup step is to decide whether archive-candidate scripts and old result JSONs should be moved under an explicit archive namespace or left in place with stronger runtime warnings.
