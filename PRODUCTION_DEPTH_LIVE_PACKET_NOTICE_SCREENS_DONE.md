# Production Depth Live Packet And Notice Screens Slice

Status: ready for audit
Branch: `production-depth/live-packet-notice-screens`

## Shipped

- `/staff` packet assembly screen now creates a demo meeting, creates a packet assembly record, and finalizes it through the live API.
- `/staff` notice checklist screen now creates a demo meeting, persists a notice checklist record, and attaches posting proof through the live API.
- `/staff` agenda intake, packet assembly, and notice checklist screens all have browser-verified live API actions.
- Root endpoint, README, text README, user manual, text manual, changelog, and landing page now point the next slice toward meeting persistence and remaining live clerk-console actions.
- Browser QA evidence proves desktop and mobile live intake, packet, and notice workflows, console output, overflow, and focus state.

## Not Shipped

- Database-backed meeting lifecycle persistence.
- Live browser form submission for motions, votes, actions, minutes, public archive, and connector import workflows.
- React/nginx production shell.
- Release version bump or package release.

## Verification Snapshot

- `python -m pytest --collect-only -q` -> 379 tests collected
- `python -m pytest -q` -> 379 passed
- `bash scripts/verify-docs.sh` -> `VERIFY-DOCS: PASSED`
- `python scripts/check-civiccore-placeholder-imports.py` -> `PLACEHOLDER-IMPORT-CHECK: PASSED (24 source files scanned)`
- `python -m ruff check .` -> `All checks passed!`
- `bash scripts/verify-release.sh` -> `VERIFY-RELEASE: PASSED` (374 release-gate tests passed; milestone 12 release tests excluded by script)

## Browser QA Evidence

- Desktop screenshot: `docs/screenshots/milestone13-staff-ui-desktop.png`
- Mobile screenshot: `docs/screenshots/milestone13-staff-ui-mobile.png`
- Desktop live-action screenshot: `docs/browser-qa-production-depth-live-packet-notice-screens-desktop.png`
- Mobile live-action screenshot: `docs/browser-qa-production-depth-live-packet-notice-screens-mobile.png`
- Summary: `docs/browser-qa-production-depth-live-packet-notice-screens-summary.md`
- Expected checks: live agenda intake submit/review, live packet create/finalize, live notice checklist/posting proof, visible success output, actionable fix copy, desktop and mobile viewports, no console messages, no horizontal document overflow, visible focus outline.
