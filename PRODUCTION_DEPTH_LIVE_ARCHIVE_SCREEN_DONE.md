# Production Depth: Live Public Archive Screen Done

Status: complete  
Branch: `production-depth/live-archive-screen`  
Scope: browser-visible staff workflow action for public-safe archive publishing

## What Changed

- Added a `Public Archive` staff workflow card to `/staff`.
- Added a live browser form that creates a demo meeting, publishes a public-safe archive record through `/meetings/{id}/public-record`, and verifies visibility through `/public/meetings` plus `/public/archive/search`.
- Preserved the CivicClerk public-record guardrail: clerks publish public-safe agenda, packet, and approved-minutes text; closed-session material remains outside anonymous public views.
- Updated root runtime messaging, README, README.txt, user manual, landing page, changelog, browser-QA gate, tests, screenshots, and completion record.

## UX Evidence

- Desktop browser QA: `docs/browser-qa-production-depth-live-archive-screen-desktop.png`
- Mobile browser QA: `docs/browser-qa-production-depth-live-archive-screen-mobile.png`
- Summary: `docs/browser-qa-production-depth-live-archive-screen-summary.md`

## Verification Snapshot

Run before push:

```bash
python -m pytest
python -m ruff check .
bash scripts/verify-docs.sh
python scripts/check-civiccore-placeholder-imports.py
python scripts/verify-browser-qa.py
CIVICCORE_LLM_PROVIDER=ollama CIVICCLERK_EVAL_OFFLINE=1 NO_NETWORK=1 python scripts/run-prompt-evals.py
bash scripts/verify-release.sh
```

## Next Production-Depth Work

Remaining live clerk-console actions after this slice:

- connector import workflow action
- packet export creation workflow action
