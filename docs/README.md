# Documentation Index

This directory contains the current public documentation for the research-only
Market Evidence Validation Framework.

## Start Here

- `../README.md` - project purpose, fixture-only quickstart, and safety
  boundaries.
- `../ARCHITECTURE.md` - public architecture and explicit non-architecture.
- `../SAFETY.md` - hard research-only boundaries.
- `../CONTRIBUTING.md` - accepted contributions and local checks.

## Public Contracts

- `DATA_STORAGE_CONTRACT.md` - data storage and artifact boundary.
- `SIGNAL_PROVENANCE_CONTRACT.md` - evidence provenance expectations.
- `EVENT_SCHEMA_CATALOG.md` - event schema catalog.
- `EXPERIMENT_MANIFEST.md` - fixture-only experiment manifest.

## Examples And Maintenance

- `EXAMPLES.md` - synthetic fixture examples and expected validation behavior.
- `MAINTAINER_PLAN.md` - current maintenance checklist and issue drafts.
- `MAINTENANCE_LOG.md` - planned, completed, and next maintenance entries.
- `GOAL_CONTROL.md` - maintainer work-control rules.

## Public Repo Scope

The public repository intentionally excludes private market archives,
credentials, deployment state, and live/shadow/execution runtime components.
Docs in this directory should describe only fixture validation, source
lineage, known-at timing, append-only outcome/postmortem contracts, confidence
evidence metadata, and safety checks.
