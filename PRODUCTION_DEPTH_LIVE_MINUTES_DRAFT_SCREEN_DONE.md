# Production Depth: Live Minutes Draft Screen Done

Status: complete  
Branch: `production-depth/live-minutes-draft-screen`  
Scope: browser-visible staff workflow action for citation-gated minutes draft creation

## What Changed

- Added a `Minutes Draft` staff workflow card to `/staff`.
- Added a live browser form that creates a demo meeting and submits a cited draft through `/meetings/{id}/minutes/drafts`.
- Preserved the CivicClerk minutes guardrail: drafts are created as unadopted and unposted records that require human review before any public posting workflow.
- Updated root runtime messaging, README, README.txt, user manual, landing page, changelog, browser-QA gate, and staff UI tests to reflect the shipped screen.

## UX Evidence

- Desktop browser QA: `docs/browser-qa-production-depth-live-minutes-draft-screen-desktop.png`
- Mobile browser QA: `docs/browser-qa-production-depth-live-minutes-draft-screen-mobile.png`
- Summary: `docs/browser-qa-production-depth-live-minutes-draft-screen-summary.md`

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

- archive workflow action
- connector import workflow action
- packet export creation workflow action
