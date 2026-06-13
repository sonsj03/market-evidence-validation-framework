# Event Schema Catalog
> 기준: 2026-05-12

## Purpose

This catalog defines common event shapes before any storage migration. Existing
files stay in place. New writers should choose one of these schemas and document
the owner before writing.

## Principles

- Facts are append-only JSONL when possible.
- Mutable JSON is only for latest runtime state.
- Every event has a timestamp that was knowable at the time.
- Research and LLM packs may summarize events, but raw LLM answers are not
  promotion evidence.
- Event/regime replay must use `known_at_ts` as the event time and must carry a
  deterministic replay contract before it can feed validation planning.
- Existing file paths remain compatible until a full migration window is
  planned.

## Common Header

Every append-only event row should include:

| Field | Type | Meaning |
|---|---|---|
| `type` | string | Event family |
| `schema_version` | int | Schema version |
| `event_id` | string | Stable id if available |
| `ts` | float | Event timestamp, seconds |
| `known_at_ts` | float | First timestamp bot/research could know this fact |
| `source` | string | Writer/module/source |
| `symbol` | string | Optional symbol |
| `research_only` | bool | True if not executable |
| `direct_trading_allowed` | bool | Must be false for research/operator/LLM events |

Replay must never consume an event before `known_at_ts`.

## Runtime Event Families

| Family | Current File | Owner | Promotion Evidence |
|---|---|---|---|
| `trade_journal_event` | `shadow_journal.jsonl`, `live_journal.jsonl` | executor/logger | support only |
| `blocked_signal_event` | `blocked_signals.jsonl` | brain/filter path | support only |
| `replacement_decision_event` | `replacement_decisions.jsonl` | replacement logic | support only |
| `governed_shadow_observation_event` | `governed_shadow_observations.jsonl` | `shadow_observation_logger` | yes after aggregation |
| `operator_control_audit_event` | `operator_control_audit.jsonl` | `operator_control` | no |
| `operator_llm_audit_event` | `operator_llm_audit.jsonl` | `operator_llm_runner` | no |
| `shadow_admin_audit_event` | `shadow_admin_audit.jsonl` | `shadow_admin` | no |
| `screener_admin_audit_event` | `screener_admin_audit.jsonl` | `screener_admin` | no |

## Research Event Families

| Family | Current/Planned File | Owner | Notes |
|---|---|---|---|
| `llm_journal_review_pack` | `backtest/results/llm_research/*.json` | `journal_review_pack` | compact post-trade evidence |
| `llm_event_regime_pack` | `backtest/results/llm_research/*.json` | `event_regime_pack` | event/regime interpretation input |
| `llm_validation_bridge_plan` | `backtest/results/llm_research/*.json` | `validation_bridge` | tickets only, `auto_execute=false` |
| `llm_event_replay_evidence` | `backtest/results/llm_research/*.json` | `event_replay_evidence_adapter` | research-only evidence, no execution |
| `shadow_observation_evidence` | `backtest/results/*.json` | `shadow_outcome_aggregator` | promotion evidence only after gate |
| `limited_live_approval_result` | `backtest/results/*.json` | `limited_live_approval` | limited-live gate only |

`llm_event_regime_pack` minimum replay contract:

```text
deterministic_replay_contract.event_time_field = known_at_ts
deterministic_replay_contract.label_windows_min = positive minute windows
deterministic_replay_contract.required_outcome_fields includes outcome_completeness
```

`llm_event_replay_evidence` minimum contract:

```text
type = llm_event_replay_evidence
research_only = true
direct_trading_allowed = false
strategy_execution_allowed = false
auto_execute = false
allowed_mutations = []
source_pack_type = llm_event_regime_pack
deterministic_replay_contract.event_time_field = known_at_ts
pre_event_ohlcv_window = object
post_event_ohlcv_windows = object
outcome_summary.outcome_completeness present
evidence_rows = list
```

Validator:

```text
backtest.research.event_replay_evidence_contract.validate_llm_event_replay_evidence_artifact
```

## Migration Rule

Do not move current files until all of the following exist:

1. compatibility readers for old and target paths;
2. schema-versioned writer tests;
3. one observation window of equality checks;
4. updated Telegram/operator paths;
5. rollback note in `docs/NEXT_TASK.md`.

## Immediate Code Target

Add a tiny schema helper only when a new writer is introduced. Do not retrofit
all existing JSONL writers in one patch.
