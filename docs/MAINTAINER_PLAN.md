# Maintainer Plan

This repository is maintained as a research-only market evidence validation
framework. It is not a trading bot, does not execute orders, and does not use
private exchange APIs.

## 1-2 Week Maintenance Plan

Routine maintenance status is recorded in `docs/MAINTENANCE_LOG.md` using a
planned / completed / next format.

### Week 1

- Issue triage: label new issues as `bug`, `docs`, `fixture`, `validator`,
  `ci`, or `safety`.
- Fixture expansion: add one small synthetic observation fixture that exercises
  missing source lineage and known-at timestamp checks.
- Guard and security tests: keep the execution guard covered by dependency-free
  tests and add one scan-oriented test for forbidden runtime surfaces.
- Source-lineage validator improvements: document required fields and add a
  minimal example for source reference validation.
- Documentation polish: tighten README, SAFETY, and ARCHITECTURE wording so the
  project remains clearly research-only.

### Week 2

- Known-at validation examples: add examples for valid and invalid known-at
  ordering using synthetic rows.
- Confidence rollup examples: add a small fixture that demonstrates confidence
  as evidence-quality metadata, not a performance claim.
- CI hardening: keep CI dependency-free and add a safety scan command once it is
  available as a small script.
- Contributor workflow: add issue labels and close stale drafts that request
  out-of-scope runtime behavior.
- v0.1.0 release checklist: confirm docs, fixtures, guard tests, CI, and safety
  scans are green before tagging.

## v0.1.0 Release Checklist

- [ ] README describes purpose, fixture-only quickstart, and safety boundaries.
- [ ] SAFETY states no order execution, no private exchange API, and no
      financial advice.
- [ ] ARCHITECTURE shows fixture -> observation -> source lineage ->
      outcome/postmortem -> confidence rollup.
- [ ] Synthetic fixture validation passes.
- [ ] Guard tests pass.
- [ ] Syntax check passes.
- [ ] Safety scan reports zero secret, execution, and data artifact hits.
- [ ] Issue drafts are converted into GitHub issues or intentionally deferred.
- [ ] `docs/MAINTENANCE_LOG.md` records the latest planned/completed/next
      maintenance cycle.

## Issue Drafts

### 1. Add Known-At Validation Examples

- Type: documentation
- Priority: high
- Scope: Add synthetic valid/invalid known-at examples and explain why ordering
  matters for research evidence.
- Acceptance criteria:
  - Includes at least two small fixture rows.
  - Documents expected pass/fail behavior.
  - Does not add runtime execution paths.

### 2. Expand Source-Lineage Fixture Coverage

- Type: fixture
- Priority: high
- Scope: Add synthetic source-lineage examples for present, missing, and
  mismatched source references.
- Acceptance criteria:
  - Fixture rows are synthetic and small.
  - Validator output identifies each lineage case.
  - Safety scan still reports zero forbidden artifacts.

### 3. Add Dependency-Free Safety Scan Script

- Type: safety
- Priority: high
- Scope: Convert the local secret/execution/data artifact scan into a reusable
  standard-library script.
- Acceptance criteria:
  - Script exits non-zero on forbidden paths.
  - Allows only `fixtures/synthetic_market_observations.jsonl` as JSONL.
  - CI runs the script without third-party dependencies.

### 4. Document Confidence Rollup Semantics

- Type: documentation
- Priority: medium
- Scope: Explain confidence as evidence-quality metadata based on source
  coverage, known-at integrity, outcome linkage, and blocker reduction.
- Acceptance criteria:
  - Avoids performance or outcome-maximizing language.
  - Includes one synthetic example.
  - Links to SAFETY and ARCHITECTURE.

### 5. Add Outcome/Postmortem Fixture Pair

- Type: fixture
- Priority: medium
- Scope: Add a synthetic observation with a matching outcome and postmortem row.
- Acceptance criteria:
  - Original observation remains immutable.
  - Outcome and postmortem rows reference the observation id.
  - Validator reports a complete evidence chain.

### 6. Harden Guard Tests For Additional Surfaces

- Type: safety
- Priority: high
- Scope: Extend guard tests to cover private API, wallet, account, balance, and
  position surfaces.
- Acceptance criteria:
  - Tests use only `unittest`.
  - Each forbidden surface raises `ExecutionDisabledError`.
  - README safety wording remains aligned.

### 7. Add Labeling Guide For Maintainers

- Type: maintenance
- Priority: medium
- Scope: Document issue labels and triage rules for fixture, validator, docs,
  CI, and safety work.
- Acceptance criteria:
  - Includes out-of-scope close reasons.
  - References CONTRIBUTING and SAFETY.
  - Keeps research-only language consistent.

### 8. Add Architecture Diagram Text Snapshot

- Type: documentation
- Priority: low
- Scope: Add a concise text diagram for fixture -> observation -> lineage ->
  outcome/postmortem -> confidence flow.
- Acceptance criteria:
  - Diagram is text-only and easy to maintain.
  - No runtime execution components are introduced.
  - README links to the architecture section.

### 9. CI Hardening With Safety Scan

- Type: ci
- Priority: medium
- Scope: Add the dependency-free safety scan script to CI after it lands.
- Acceptance criteria:
  - CI runs syntax, fixture validation, guard tests, and safety scan.
  - CI remains dependency-free.
  - CI fails on forbidden artifact paths.

### 10. Prepare v0.1.0 Release Notes

- Type: release
- Priority: medium
- Scope: Draft release notes for the initial research-only validation framework.
- Acceptance criteria:
  - Includes safety boundary summary.
  - Lists fixtures and validation commands.
  - States that the release is not for automated market execution.
