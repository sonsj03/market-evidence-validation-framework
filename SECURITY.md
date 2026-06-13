# Security Policy

This repository should not contain secrets, exchange credentials, account
files, private market data, raw logs, or deployment state.

## Reporting

Please open a security advisory or contact the maintainer privately if you
find:

- A secret, credential, session, or account artifact.
- Any path that could enable order execution.
- Any private or signed exchange API integration.
- Any wallet, account, balance, or position access.
- Any live/shadow/scanner/executor/promotion route.

## Safety Boundary

This project is not a trading bot. It is a research-only market evidence
validation pipeline. `research_safety.guard` keeps execution disabled with a
hard-coded guard.

