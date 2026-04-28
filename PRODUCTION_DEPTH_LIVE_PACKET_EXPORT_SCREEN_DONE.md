# Production Depth: Live Packet Export Screen

## Scope

Added the final live clerk-console action for the released API foundation: the `/staff?screen=packet` page can now create a records-ready packet export bundle through the live API.

## What Changed

- Added a packet export form to the Packet Assembly staff screen.
- The browser flow creates a demo meeting, creates the required packet snapshot through `/meetings/{id}/packet-snapshots`, then creates the export bundle through `/meetings/{id}/export-bundle`.
- The success state shows the bundle path, manifest path, checksum path, and next records step.
- Updated root runtime messaging, README, README.txt, user manual, landing page, changelog, browser-QA gate, tests, screenshots, and completion record.
- Added `exports/` to `.gitignore` because the local export workflow intentionally writes records bundles to disk.

## UX Evidence

- `docs/browser-qa-production-depth-live-packet-export-screen-desktop.png`
- `docs/browser-qa-production-depth-live-packet-export-screen-mobile.png`
- `docs/browser-qa-production-depth-live-packet-export-screen-summary.md`

## Verification Snapshot

Run before push:

- `python -m pytest -q`
- `bash scripts/verify-docs.sh`
- `python scripts/check-civiccore-placeholder-imports.py`
- `python -m ruff check .`
- `python scripts/verify-browser-qa.py`
- `CIVICCORE_LLM_PROVIDER=ollama CIVICCLERK_EVAL_OFFLINE=1 NO_NETWORK=1 python scripts/run-prompt-evals.py`
- `bash scripts/verify-release.sh`

## Next

All production-depth live clerk-console actions for the released API foundation now have browser form paths. The next work is consolidation: audit the whole staff workflow surface, remove any remaining stale "planned" copy, and then move on to the next CivicSuite module sprint.
