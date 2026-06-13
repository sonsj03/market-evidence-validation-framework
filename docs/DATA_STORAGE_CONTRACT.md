# Sovereign V3.5 Data Storage Contract

Updated: 2026-05-11

Purpose: define ownership and promotion-evidence rules for runtime, journal, research, and operator files before reorganizing storage.

This document is a contract first. It does not require immediate file moves.

Related schema catalog:

```text
docs/EVENT_SCHEMA_CATALOG.md
```

Related readiness contracts:

```text
docs/MICROSTRUCTURE_DATA_CONTRACT.md
docs/BORROW_FINANCING_READINESS_CONTRACT.md
docs/PAIRED_EXECUTION_FAILURE_READINESS_CONTRACT.md
```

## 1. Storage Principles

- Append-only event files are preferred for facts.
- Mutable JSON files are allowed only for current runtime state.
- Research results must include enough metadata to reproduce the command and assumptions.
- Telegram/LLM should read compact packs, not raw unbounded logs.
- Promotion evidence must come from governed validation/evidence outputs, not ad hoc logs.
- File ownership must be clear before new writers are added.

## 2. Current Runtime Files

| Path | Type | Owner | Writer Count Target | Retention | Promotion Evidence | Notes |
|---|---|---|---:|---|---|---|
| `data_logs/shadow_journal.jsonl` | append JSONL | executor/logger | 1 primary | permanent | support only | Trade journal source for dry-run/shadow records |
| `data_logs/live_journal.jsonl` | append JSONL | executor/logger | 1 primary | permanent | support only | Live journal, should remain separate from shadow |
| `data_logs/blocked_signals.jsonl` | append JSONL | brain/executor filters | 1-2 controlled | 30-90d | support only | Used by no-trade explainer and LLM packs |
| `data_logs/replacement_decisions.jsonl` | append JSONL | replacement logic | 1 primary | 30-90d | support only | Portfolio saturation/replacement context |
| `data_logs/governed_shadow_observations.jsonl` | append JSONL | `shadow_observation_logger` | 1 primary | permanent | yes, after aggregation | Registry-eligible candidate observations only |
| `data_logs/runtime_health.json` | mutable JSON | runtime health helpers | many via helper | latest | no | Operational state only |
| `data_logs/shadow_positions.json` | mutable JSON | dry-run wallet/executor | 1 primary | latest + backups | no | Current paper positions and balance |
| `data_logs/shadow_wallet.json` | mutable JSON | dry-run wallet/executor | 1 primary | latest + backups | no | Compatibility/accounting state |
| `data_logs/open_feedback.json` | mutable JSON | executor feedback | 1 primary | latest | no | Cross-process feedback |
| `data_logs/close_feedback.json` | mutable JSON | executor feedback | 1 primary | latest | no | Cross-process feedback |
| `data_logs/operator_control_audit.jsonl` | append JSONL | `operator_control` | 1 primary | permanent | no | Operator command attempt/execution audit, including audit-only fail-closed callback events such as `CALLBACK_FAIL_CLOSED` |
| `data_logs/operator_llm_audit.jsonl` | append JSONL | `operator_llm_runner` | 1 primary | permanent | no | Operator LLM query/result audit; compact metadata only, including `query_accepted` and `pack_reject_reason` for input-level hard stops |
| `data_logs/shadow_admin_audit.jsonl` | append JSONL | `shadow_admin` | 1 primary | permanent | no | Shadow wallet/reset/admin mutation audit |
| `data_logs/screener_admin_audit.jsonl` | append JSONL | `screener_admin` | 1 primary | permanent | no | Symbol universe mutation audit |
| `data_logs/operator_settings_audit.jsonl` | append JSONL | `operator_settings` | 1 primary | permanent | no | Operator-driven guardian/notify/settings mutation audit |
| `data_logs/no_trade_explainer_state.json` | mutable JSON | `operator_status` | 1 primary | latest | no | Same-reason compression state |

## 3. Research Data Files

| Path | Type | Owner | Promotion Evidence | Notes |
|---|---|---|---|---|
| `backtest/data/cache/ohlcv/.../*.parquet` | Parquet | `backtest.data.ohlcv` | input only | Must include exchange and market_type when relevant |
| `backtest/data/cache/funding/...` | cache | funding provider | input only | Funding data must be timestamp-safe |
| `backtest/data/cache/basis/...` | cache | basis builder | input only | Exact spot/perp alignment, no interpolation |
| `backtest/results/*.json` | JSON result | experiment scripts | maybe | Only if metadata envelope is sufficient |
| `backtest/results/*.jsonl` | JSONL result | experiment scripts | maybe | Must not be promotion evidence without manifest status |
| `backtest/results/paper_trades/low_confidence_virtual_trades.jsonl` | append JSONL | low-confidence paper trade writer | no direct | Dedicated append-only ledger for schema-validated virtual paper trade rows. Rows must keep row-level no-execution flags false, must not contain real order ids or outcomes, and cannot authorize outcome join, shadow, limited-live, live, scanner, executor, promotion, or cost-adjusted replay. |
| `backtest/results/paper_ledger_audit_latest.json` | JSON report | paper ledger audit | no direct | Read-only audit of the low-confidence paper ledger. Empty ledger is a normal wait state. Detects schema violations, duplicate `paper_trade_id`, no-execution flag leaks, real-order field leaks, and outcome contamination without mutating ledger rows. |
| `backtest/results/outcome_join_delayed_contract_latest.json` | JSON contract | delayed paper outcome join contract | no direct | Contract-only definition for future delayed outcome/correction append rows. It keeps `outcome_join_allowed_now=false`, requires minimum delay and replay-decision timestamp ordering, preserves known-at boundaries, forbids original row mutation, and cannot fetch outcomes or calculate returns. |
| `backtest/results/paper_outcome_join_readiness_audit_latest.json` | JSON report | paper outcome join readiness audit | no direct | Composes paper ledger audit and delayed outcome contract. It reports wait/blocker state only, keeps paper-to-shadow review disabled, and cannot execute outcome joins or grant shadow/live permissions. |
| `backtest/results/llm_research/*.json` | JSON | LLM research pipeline | no direct | Journal review packs, event/regime packs, LLM reports, validation plans, and event replay evidence artifacts are compact research artifacts only. LLM reports include non-mutating `followup_route`; validation plans preserve it as `source_followup_route`; event replay evidence must keep `direct_trading_allowed=false`, `strategy_execution_allowed=false`, and `auto_execute=false`; never direct trading |
| `backtest/results/llm_research/event_replay_coverage_requirements_*.json` | JSON report | event replay coverage requirements | no direct | Local-only summary of missing OHLCV windows blocking event replay evidence. It is a planning artifact for bounded cache work, not replay evidence or execution permission. |
| `backtest/results/llm_research/event_replay_ohlcv_collection_plan_*.json` | JSON report | event replay OHLCV collection plan | no direct | Dry-run-only, bounded planning artifact for event replay OHLCV gap fill. `network_required=false` means it does not fetch; `hard_max_requests` caps any future reviewed batch size. |
| `backtest/results/historical_market_context_*.json` | JSON dataset | historical market context store | no direct | Reusable, research-only context/evidence dataset for historical windows. Stores event-vs-organic-vs-market-beta/mixed classification, evidence sources, source hashes, known-at timestamps, analyzer model/prompt metadata, confidence, source reliability score/tier, record-level evidence reliability, and strategy usability flags so replay engines can reuse one analysis instead of re-running LLM/news interpretation. Event-regime, market-beta, and reviewed manual/local-LLM tagging workflows may upsert records, but the dataset remains support-only and cannot authorize strategy execution. |
| `backtest/results/historical_context_tagging_ingest_*.json` | JSON report | historical context tagging ingest | no direct | Review report for manual/local-LLM context-tag proposals. Rejects direct trade tokens, `auto_execute=true`, and execution permission flags; accepted proposals only update the research-only historical context dataset. |
| `backtest/results/shadow_observation_evidence_latest.json` | JSON evidence | shadow outcome aggregator | yes, if gate passes | Still requires manual approval after gate |
| `backtest/results/operator_status_report_latest.json` | JSON report | research operator report | no direct | Read-only next-action view |
| `backtest/results/data_quality_alert_summary_latest.json` | JSON report | data quality alert composer | no direct | Basis/funding/microstructure coverage alerts for research/operator visibility only; operator status derives `validation_data_ready` / `validation_blocked` from this summary |
| `backtest/results/delta_neutral_validation_readiness_latest.json` | JSON report | validation infra readiness checker | no direct | Optional operator-status input; research-only blocker summary for data quality, 90d basis coverage, orderbook depth/impact, borrow/financing, and paired execution failure model readiness. Includes `model_foundations` to show helper availability separately from readiness booleans, `model_validation_violations` for failed model-artifact validation, `next_required_evidence` to map blockers to required data/model-validation work with `contract_ref`, and grouped `next_action_plan` for operator triage. Must include `artifact_contract_violations`; normal value is `[]`, non-empty values are operator-visible safety warnings. |
| `backtest/results/orderbook_depth_impact_validation_*.json` | JSON report | orderbook impact validation | no direct | Future research-only artifact validated by `backtest.research.orderbook_impact_readiness.validate_orderbook_depth_impact_validation_artifact`; may only support `orderbook_depth_model_ready=true`, never strategy execution. |
| `backtest/results/borrow_financing_validation_*.json` | JSON report | borrow/financing validation | no direct | Research-only artifact validated by `backtest.research.borrow_financing_readiness.validate_borrow_financing_validation_artifact`; may support `borrow_financing_model_ready=true`, never strategy execution. Current latest artifact is source-quality blocked: conservative fallback benchmark inputs cannot make the model ready without measured or explicitly approved exchange/source-specific borrow inputs. |
| `backtest/results/borrow_financing_source_plan_*.json` | JSON report | borrow/financing source plan | no direct | Research-only source-plan artifact for separating fully funded spot/perp hedge lanes from margin-short or financed-spot lanes. It records official/public reference locations and signed/user-specific source requirements, but must keep `network_collection_allowed=false`, `execute_allowed=false`, and `cost_adjusted_replay_allowed=false`; it is not a borrow-rate value source by itself. |
| `backtest/results/paired_execution_failure_validation_*.json` | JSON report | paired execution validation | no direct | Research-only artifact validated by `backtest.research.paired_execution_readiness.validate_paired_execution_failure_validation_artifact`; may support `paired_execution_failure_model_ready=true`, never strategy execution. Current latest artifact is model-ready from deterministic stress scenarios, not production paired execution or recovery logic. |
| `backtest/results/execution_model_input_requirements_*.json` | JSON report | execution model input requirements | no direct | Research-only summary of missing local orderbook/rate/scenario inputs derived from the three execution-model validation artifacts. Orderbook groups may include `collection_schedule` and fail-closed `collection_schedule_violations`; non-empty violations must be operator-visible and prevent `input_ready=true`. |
| `backtest/results/orderbook_collection_policy_*.json` | JSON report | orderbook collection policy | no direct | Research-only policy check for whether the next bounded L2 collection batch is allowed under hard snapshot caps. Generation is local-only with `network_required=false`; the artifact must keep `direct_trading_allowed=false` and `strategy_execution_allowed=false` even when `network_collection_allowed=true` for a reviewed public-data batch. |
| `backtest/results/research_data_soak_scheduler_latest.json` | JSON report | research data-soak scheduler | no direct | Research-only scheduler artifact. It refreshes Orderbook/OI guards, executes bounded public-data collection only when guard artifacts explicitly allow it, regenerates dependent artifacts/operator report/full validation, and records next eligible times. It must keep scanner/executor/live/shadow/promotion/cost-adjusted replay flags false. |
| `backtest/results/research_data_soak_scheduler_runs.jsonl` | JSONL log | research data-soak scheduler run log | no direct | Append-only run history for scheduler cycles, including actions, skipped blockers, validation results, and next exact command. This is not a service state file and does not authorize collection without current guard approval. |
| `backtest/results/exchange_adapter_contract_latest.json` | JSON report | research exchange adapter contract | no direct | Defines the exchange-neutral research adapter contract. Current implementation is `binance_usdm`; Bybit/OKX are documented as interface-compatible future adapters only. Artifacts that consume exchange data should preserve `exchange`, `market_type`, `adapter_id`, canonical/exchange symbol mapping where row-level, `orderbook_schema_version` for L2 books, and funding-rate internal units as bps. |
| `backtest/results/exchange_adapter_registry_latest.json` | JSON report | research exchange adapter registry | no direct | Source-backed exchange-neutral adapter registry for Binance USD-M, Bybit linear, and OKX swap metadata. It records official public endpoint docs, required public query params, symbol normalization, funding-rate unit conversion, OI unit notes, cache namespaces, and no-execution boundaries. Bybit/OKX rows are interface-compatibility code only; no collector, scanner, executor, signed endpoint, shadow, promotion, or live wiring is authorized by this artifact. |
| `backtest/results/oi_coverage_*.json` | JSON report | open-interest coverage | no direct | Research-only OI cache coverage report used before OI/liquidation forced-flow replay. |
| `backtest/results/liquidation_coverage_*.json` | JSON report | liquidation coverage | no direct | Research-only liquidation cache coverage report used before forced-flow replay. |
| `backtest/results/forced_flow_readiness_*.json` | JSON report | forced-flow readiness | no direct | Research-only readiness composition for OI/liquidation/orderbook forced-flow replay. |
| `backtest/results/forced_flow_collection_plan_*.json` | JSON report | forced-flow collection plan | no direct | Dry-run/local-only plan for OI, liquidation, and orderbook forced-flow coverage gaps. `network_required=false` means it does not fetch; current `BLOCKED` status reflects missing coverage units, not strategy permission. |
| `backtest/results/forced_flow_replay_labels_*.json` | JSON artifact | forced-flow replay labels | no direct | Future research-only FF-1~FF-4 replay-label artifact validated by `backtest.research.forced_flow_replay_contract.validate_forced_flow_replay_labels_artifact`. Must keep no-execution flags false, separate context/reliability buckets, reject v0 promotion, and block v1/v2 rows without required liquidation/execution evidence. |
| `backtest/results/forced_flow_validation_report_*.json` | JSON report | forced-flow validation report | no direct | Research-only summary of forced-flow replay-label artifacts. Aggregates strategy/context/reliability/status/failure counts and preserves no-execution flags; it cannot authorize shadow/live behavior. |
| `backtest/results/volatility_regime_report_*.json` | JSON report | volatility regime report | no direct | Descriptive regime-label report with `result_envelope`; must keep `direct_trading_allowed=false` and `strategy_execution_allowed=false`. Operator status fail-closes malformed promotion/execution flags and surfaces coverage/label-dominance blockers. |
| `backtest/results/volatility_regime_coverage_plan_*.json` | JSON report | volatility regime coverage plan | no direct | Dry-run/local-only coverage and label-balance plan derived from the latest volatility regime report. It does not fetch data and cannot grant live gating permission. |
| `backtest/results/pre_strategy_foundation_status_*.json` | JSON report | pre-strategy foundation status | no direct | Research-only blocker digest from delta-neutral readiness, execution-model input requirements, forced-flow readiness/collection plan, volatility-regime report/coverage plan, LLM event replay evidence, replay coverage requirements, and replay OHLCV collection plan. It never grants strategy execution; unsafe execution flags in any source group keep the digest blocked. |
| `backtest/results/pre_strategy_blocker_triage_*.json` | JSON report | pre-strategy blocker triage | no direct | Research-only classifier that separates pre-strategy blockers into local implementation gaps versus long-horizon data-soak gaps. It is a work-control artifact only and cannot authorize strategy execution. |
| `backtest/results/result_envelope_no_execution_audit_*.json` | JSON report | result envelope no-execution audit | no direct | Research-only audit for result artifacts with `result_envelope`; flags unsafe `direct_trading_allowed=true` or `strategy_execution_allowed=true`, and tracks legacy envelopes missing explicit no-execution fields. |
| `backtest/results/stale_promotion_artifact_audit_*.json` | JSON report | stale promotion artifact audit | no direct | Research-only inventory of old result files containing legacy promotion-like labels; not promotion evidence. Current schema separates real stale result artifacts from context/report artifacts and keeps all execution/promotion flags false. |
| `backtest/results/stale_promotion_doc_audit_*.json` | JSON report | stale promotion doc audit | no direct | Research-only inventory of active docs mentioning legacy promotion-like labels and whether the context is safe. |
| `backtest/results/stale_readiness_doc_audit_*.json` | JSON report | stale readiness doc audit | no direct | Research-only inventory of active docs with stale current-readiness wording such as old 7d basis or orderbook `0d/90d` statements; operator status surfaces high-risk counts but it is not promotion evidence. |
| `backtest/results/stage4_artifact_freshness_audit_*.json` | JSON report | Stage 4 artifact freshness audit | no direct | Research-only freshness guard that compares Stage 4/operator latest artifact mtimes against key input artifacts. `FRESHNESS_AUDIT_BLOCKED_STALE_ARTIFACTS` means regenerate the stale output before trusting operator visibility; it cannot authorize replay, shadow, promotion, or live behavior. |
| `backtest/results/stage4_replay_review_closeout_decision_*.json` | JSON report | Stage 4 closeout decision | no direct | Research-only closeout artifact that records the approved definition of Phase 4 completion: descriptive/review-only closeout plus explicit blocker classification. It moves cost-adjusted replay to Phase 4B and keeps shadow observe, promotion, scanner/executor/live wiring, and live/limited-live disabled. |
| `backtest/results/codebase_foundation_audit_*.json` | JSON report | post-Stage-4 codebase foundation audit | no direct | Read-only whole-codebase audit artifact for unsafe permission literals, silent placeholders, legacy gates, and direct runtime test coverage gaps. It never authorizes replay, shadow, promotion, scanner/executor/live wiring, or live/limited-live operation. |
| `backtest/results/codebase_foundation_audit_triage_*.json` | JSON report | codebase audit triage | no direct | Read-only triage of codebase audit rows into runtime-action, runtime-review, legacy-review, fixture/comment, and test-gap buckets. It is a work-control artifact only and cannot authorize execution or strategy promotion. |
| `backtest/results/runtime_silent_pass_review_*.json` | JSON report | runtime silent-pass review | no direct | Read-only classifier for runtime silent pass rows. It separates fail-silent review candidates from abstract/no-op and intentional best-effort paths; it does not mutate runtime behavior or grant execution permission. |
| `backtest/results/experiment_manifest_legacy_review_*.json` | JSON report | experiment manifest legacy review | no direct | Read-only closeout for legacy/diagnostic/archive experiment runners. It proves non-active runners remain gated by `enforce_runner_gate`, `allow_legacy` is reproduction/diagnostic-only, and `promotion_allowed=false` for all reviewed paths. |
| `backtest/results/codebase_nonruntime_review_closeout_*.json` | JSON report | nonruntime codebase audit closeout | no direct | Read-only closeout for non-runtime audit inventory after runtime/action rows are closed. It requires legacy review pass, fixture rows to stay in tests/audit fixtures, comment rows to be comment-only, and all execution/promotion flags false. |
| `backtest/results/secret_boundary_audit_*.json` | JSON report | secret boundary audit | no direct | Read-only source-text audit that never reads private secret configuration. It reports unauthorized direct secret read paths as contract violations. |
| `backtest/results/local_llm_routing_status_*.json` | JSON report | local LLM routing status | no direct | Read-only artifact generated from public settings only. It records the installed-role mapping (`llama3.1:8b` fast fallback, `gemma3:27b` operator/review JSON default, `qwen3:30b` manual deep analysis only), rejects removed `gemma2:27b` active references, and keeps all execution/promotion flags false. |
| `backtest/results/limited_live_approval.json` | JSON result | limited live approval gate | no direct | Manual approval validation result with provenance and `artifact_contract_violations`; still not normal-live permission. Startup guard rejects non-empty contract violations if this artifact is used as `mode.live_approval_result_path`. |

## 4. Research Artifact Contracts

### 4.1 LLM Research Artifact Contract

LLM research artifacts under `backtest/results/llm_research/` must keep the
review path non-mutating and auditable.

Required fields by artifact:

| Artifact | Required Safety Fields |
|---|---|
| `journal_review_pack_*.json` | `research_only=true`, `direct_trading_allowed=false`, compact summaries, `llm_task_contract` |
| `journal_review_pack_*.json` | `research_only=true`, `direct_trading_allowed=false`, compact journal/blocked/replacement/runtime-health summaries, `runtime_llm_gate_snapshot`, `llm_task_contract` |
| `event_regime_pack_*.json` | `research_only=true`, `direct_trading_allowed=false`, `published_ts`, `known_at_ts`, event/source/symbol metadata, `llm_task_contract` |
| `llm_research_report_*.json` | `research_only=true`, `direct_trading_allowed=false`, `status`, `direct_trade_actions`, `hypothesis` when accepted, `followup_route` when accepted; accepted reports must keep `direct_trade_actions=[]`, while rejected reports may preserve rejected direct-action tokens as audit evidence |
| `validation_plan_*.json` | `research_only=true`, `direct_trading_allowed=false`, `auto_execute=false`, optional `source_followup_route`, manifest-backed script plans |

Reports and validation plans should also include `artifact_contract_violations`.
For normal accepted/rejected artifacts this list should be empty. A non-empty
list is an audit warning and must not be converted into execution.

Allowed `followup_route.route` values:

```text
VALIDATION_TASK_TICKET
DATA_GAP_TICKET
REJECTION_NOTE
OPERATOR_OBSERVATION
REJECT_SOURCE
```

No LLM research artifact may be treated as a wallet/config/process/order
mutation request.

## 5. File Movement Policy

Do not move existing files immediately.

Safe migration order:

1. add compatibility readers
2. write new files to the new location
3. read both old and new locations
4. verify equality for a full observation window
5. update docs and Telegram paths
6. archive old files

## 5. Target Layout

Future target:

```text
data_logs/
  events/
    blocked_signals.jsonl
    replacement_decisions.jsonl
    governed_shadow_observations.jsonl
  journals/
    shadow_journal.jsonl
    live_journal.jsonl
  runtime_state/
    runtime_health.json
    shadow_positions.json
    shadow_wallet.json
    open_feedback.json
    close_feedback.json
    no_trade_explainer_state.json
  operator/
    operator_control_audit.jsonl
    operator_query_audit.jsonl
    operator_llm_audit.jsonl
    shadow_admin_audit.jsonl
    screener_admin_audit.jsonl
  reports/
    shadow_report.md
    auto_tuning_report.md

backtest/results/
  experiments/
  evidence/
  llm_research/
```

## 6. Promotion Evidence Rules

Allowed evidence sources:

- active validation scripts marked as promotion evidence in `experiment_manifest.py`
- shadow observation evidence generated from governed observations
- limited-live approval results after manual approval checks

Not allowed as direct promotion evidence:

- Telegram reports
- raw shadow journal
- raw blocked signals
- LLM answers
- old experiment outputs from rejected/archive scripts
- operator status reports
- single-window backtest output without metadata envelope

## 7. Required Experiment Result Envelope

Every new research output should include:

```text
type:
created_at:
script:
script_status:
promotion_allowed:
alpha_family:
strategy_id:
data_contract_version:
feature_version:
exchange:
market_type:
symbols:
start_ts:
end_ts:
cost_model:
fill_model:
latency_assumption:
sample_count:
effective_sample_count:
cluster_count:
recent_gate:
blocking_reasons:
command:
config:
```

Status:

```text
implemented foundation: backtest/experiments/result_envelope.py
applied first: run_delta_neutral_basis_scan.py, run_delta_neutral_basis_rolling_scan.py
```

The field is additive and should appear as:

```text
result_envelope: {...}
```

Existing report fields remain for compatibility.

## 8. Immediate Engineering Rule

Before adding another strategy scanner, first decide:

```text
Where does the input data live?
Who owns the writer?
Can the replay know the timestamp without lookahead?
Where does the result envelope get written?
Can the result become promotion evidence, or is it support-only?
```

## 9. Dedicated Collector Cache Import

Dedicated data-soak collection may run on a separate collector node, while the
main workstation stays validation/import-only.

Collector role:

```bash
python3 -m backtest.research.research_data_soak_scheduler --collector-role --execute-batches --run-validation
```

Mini-PC scheduled collector:

```bash
17 * * * * /usr/bin/flock -n /tmp/research-data-collector.lock /path/to/research/ops/run_data_soak_collector_cycle.sh >> /path/to/research/results/collector_cron.log 2>&1
```

The wrapper `ops/run_data_soak_collector_cycle.sh` blocks if
`timedatectl show -p NTPSynchronized --value` is not `yes`, activates the local
venv, then runs the collector-role scheduler. `flock` prevents overlapping
cycles if a previous validation run is still active.

Collector heartbeat:

- `tools/collector_heartbeat.py` writes
  `backtest/results/collector_heartbeat_latest.json` on the mini PC after each
  collector cycle.
- The heartbeat records scheduler status, NTP state, disk usage, exit code,
  log tail, and no-execution flags.

Main watchdog/import loop:

```bash
25 * * * * /usr/bin/flock -n /tmp/research-collector-import-watchdog.lock /path/to/research/ops/run_collector_import_watchdog.sh >> /path/to/research/results/collector_watchdog_cron.log 2>&1
```

- `ops/run_collector_import_watchdog.sh` imports collector cache and then runs
  `tools/collector_watchdog.py`.
- The same wrapper refreshes the read-only operator dashboard through
  `ops/refresh_operator_dashboard.sh` after the import/watchdog step.
- `collector_watchdog_latest.json` checks SSH reachability, clock skew,
  heartbeat freshness, remote cron registration, and latest import status.
- Telegram alerting is optional and only uses
  notification credentials from private runtime configuration. It does not
  read private secret configuration in the public research copy.
- Browser auto-refresh is disabled by default. If a local viewer needs periodic
  browser reloads, regenerate the static HTML with
  `ops/refresh_operator_dashboard.sh --auto-refresh-seconds 60`.

Main-PC long-run coordinator:

```bash
ops/run_collector_data_soak_long_run.sh
```

Active user timer:

```bash
systemctl --user status sovereign-collector-long-run.timer
systemctl --user list-timers --all sovereign-collector-long-run.timer
tail -80 backtest/results/collector_long_run_timer.log
```

- `sovereign-collector-long-run.timer` runs every 15 minutes.
- The service executes `ops/run_collector_data_soak_long_run.sh` under
  `/usr/bin/flock -n /tmp/sovereign-collector-long-run.lock`.
- Before remote eligible time, the coordinator writes
  `COLLECTOR_LONG_RUN_WAITING` and does not collect.
- After remote eligible time, the coordinator executes the mini-PC collector
  cycle over SSH, then runs local import/watchdog, artifact rebuild, operator
  dashboard refresh, direct tests, and full validation.
- If `rows_added=0`, sample maturity and Stage 4 confidence must remain flat.
- The main PC remains import/watchdog/rebuild/validation-only; direct network
  collection on the main PC is not allowed.

Main workstation import role:

```bash
python3 tools/import_collector_cache.py \
  --collector-host jin@172.30.1.85 \
  --collector-root /path/to/research-collector \
  --pull \
  --execute
```

Import contract:

- remote cache is first staged under
  `backtest/data/collector_import/jin_172_30_1_85/cache`
- OI parquet files are merged into `backtest/data/cache/oi/...` by `ts`
- Orderbook parquet files are merged into
  `backtest/data/cache/microstructure/.../orderbook/...` by `ts_local`
- API telemetry jsonl files are merged by exact line hash
- import status is written to
  `backtest/results/collector_cache_import_latest.json`
- import run history is appended to
  `backtest/results/collector_cache_import_runs.jsonl`
- before pull/merge, the main workstation checks collector wall-clock skew via
  SSH `date -u` and blocks import if absolute skew exceeds 5 seconds by
  default

Safety boundary:

- the importer does not call exchange APIs
- the importer does not read private secret configuration
- the importer does not connect scanner, executor, shadow, live, or promotion
  paths
- `research_data_soak_scheduler --execute-batches` does not collect unless
  `--collector-role` or `SOVEREIGN_COLLECTOR_ROLE=1` is set

VM collector concerns tracked by the import artifact:

- collector clock skew after VM pause/resume
- different local timezone labels between main and collector
- duplicate collection if both machines execute collector role
- stale artifact ordering after importing raw cache
- partial rsync/import failure before merge
