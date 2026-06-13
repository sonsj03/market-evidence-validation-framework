# Signal Provenance Contract
> 기준: 2026-05-11

This contract defines when an OPEN signal may carry validation provenance fields
such as `candidate_id`, `source_plan`, and `source_evidence`.

It prevents a live-safety bypass where a runtime directional signal is falsely
tagged as an approved validation candidate.

## Current Finding

Current `core.brain` OPEN signals are produced from runtime market logic,
filters, recovery paths, and pyramiding branches. They do not originate from a
validated shadow candidate registry record.

Therefore, current directional/TA signals must not receive synthetic
`candidate_id` fields just to satisfy limited-live order checks.

## Allowed Provenance

An OPEN signal may carry `candidate_id` only when all of these are true:

- the signal source is a validation/shadow candidate, not a generic runtime
  strategy branch;
- the candidate exists in the shadow candidate registry;
- the candidate has governed shadow evidence;
- the operator status report shows the shadow observation gate passed;
- the limited-live approval result references the same candidate id;
- `source_plan` and `source_evidence` point to the artifacts used for the
  approval decision.

## Required Fields

Limited-live eligible OPEN signals must carry:

```json
{
  "candidate_id": "registry candidate id",
  "source_plan": "validation plan artifact path or stable id",
  "source_evidence": "shadow evidence artifact path or stable id",
  "provenance_source": "shadow_candidate_registry"
}
```

These fields are safety/provenance metadata only. They must not change scoring,
entry timing, position sizing, or strategy decisions.

## Explicitly Forbidden

- Do not tag legacy directional/TA signals with the latest approved candidate id.
- Do not infer candidate id from symbol, timeframe, side, or strategy name.
- Do not let LLM output create a live-eligible candidate id directly.
- Do not treat blocked-signal logs as approval provenance.
- Do not use current `target_bucket_shadow` observation ids for live OPEN
  routing unless that exact candidate has completed the full validation bridge,
  registry, shadow evidence, operator report, and manual approval path.

## Implementation Implication

`core.live_safety.build_live_order_approval_intent` should continue to
fail-close missing `signal.candidate_id`.

`core.live_safety.validate_live_signal_provenance` now validates already-tagged
OPEN signals and rejects missing candidate id, source plan/evidence, invalid
provenance source, and approval candidate mismatch before the intent builder can
return a ready live order intent.
