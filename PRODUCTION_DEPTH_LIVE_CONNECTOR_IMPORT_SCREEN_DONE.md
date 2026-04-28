# Production Depth: Live Connector Import Screen Done

Status: complete  
Branch: `production-depth/live-connector-import-screen`  
Scope: browser-visible staff workflow action for local connector import normalization

## What Changed

- Added a `Connector Import` staff workflow card to `/staff`.
- Added a live browser form that posts pasted local export JSON through `/imports/{connector}/meetings`.
- Preserved the CivicClerk connector guardrail: imports normalize local payloads only and do not call vendor networks in the default local profile.
- Updated root runtime messaging, README, README.txt, user manual, landing page, changelog, browser-QA gate, tests, screenshots, and completion record.

## UX Evidence

- Desktop browser QA: `docs/browser-qa-production-depth-live-connector-import-screen-desktop.png`
- Mobile browser QA: `docs/browser-qa-production-depth-live-connector-import-screen-mobile.png`
- Summary: `docs/browser-qa-production-depth-live-connector-import-screen-summary.md`

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

Remaining live clerk-console action after this slice:

- packet export creation workflow action
