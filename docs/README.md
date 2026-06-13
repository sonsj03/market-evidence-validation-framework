# Sovereign Docs Index

This directory keeps only current operating documents at the top level.
Archived notes, old prompts, retired roadmaps, and legacy idea documents live
under `docs/archive/`.

## Read First

- `GOAL_CONTROL.md` - current work-control rules.
- `ROADMAP.md` - current research-only roadmap.
- `NEXT_TASK.md` - current task log and next work queue.
- `CURRENT_PROBLEM_STATUS.md` - current blockers and status history.
- `AUTO_GOAL_LOOP.md` - automation-loop history.
- `DOCUMENT_INVENTORY.md` - active/archive classification and cleanup policy.
- `LONG_TERM_RESEARCH_ARCHITECTURE.md` - evidence-first long-term research
  architecture, historical/forward reliability boundaries, and no-execution
  constraints.

## Active Contracts

- `DATA_STORAGE_CONTRACT.md`
- `MICROSTRUCTURE_DATA_CONTRACT.md`
- `SIGNAL_PROVENANCE_CONTRACT.md`
- `BORROW_FINANCING_READINESS_CONTRACT.md`
- `PAIRED_EXECUTION_FAILURE_READINESS_CONTRACT.md`
- `EVENT_SCHEMA_CATALOG.md`
- `EXPERIMENT_MANIFEST.md`

## Active Architecture And Strategy

- `EXCHANGE_ADAPTER_ARCHITECTURE.md`
- `PROJECT_VISION_AND_PURPOSE.md`
- `STRATEGY_DESIGN_MATRIX.md`
- `STRATEGY_FAMILY_MASTER_DESIGN.md`
- `LEGACY_GATED_PATHS.md`

## Retired Top-Level Stubs

- `ARCHITECTURE_GUIDE.md` - compatibility stub; full document archived under
  `docs/archive/plans_legacy/`.
- `VALIDATION_ENGINE_DEVELOPMENT.md` - compatibility stub; full document
  archived under `docs/archive/strategy_docs_20260507/`.

## Archive Policy

Do not delete old documents by default. Move them to `docs/archive/` with a
clear category. Archived files are historical references and should not be used
as current instructions unless a current top-level document points to them.

Run `python3 tools/docs_inventory_audit.py` after major documentation cleanup.
The audit writes `backtest/results/docs_inventory_audit_latest.json` and does
not move files automatically.
