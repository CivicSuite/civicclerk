# Production Depth Live Agenda Intake Screen Slice

Status: ready for audit
Branch: `production-depth/live-agenda-intake-screen`

## Shipped

- `/staff` agenda intake screen now submits department intake items through the live `/agenda-intake` API.
- `/staff` agenda intake screen now records clerk readiness review through the live `/agenda-intake/{id}/review` API.
- Browser-visible success, loading, empty, and error states now reflect live API results with actionable fix copy.
- Root endpoint, README, text README, user manual, text manual, changelog, and landing page distinguish the shipped live agenda intake form actions from still-planned packet and notice form actions.
- Browser QA evidence proves desktop and mobile live form submission, readiness review, tab interaction, focus state, console output, and overflow checks.

## Not Shipped

- Live packet assembly form submission from `/staff`.
- Live notice checklist/posting-proof form submission from `/staff`.
- Database-backed meeting lifecycle persistence.
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
- Desktop live-action screenshot: `docs/browser-qa-production-depth-live-agenda-intake-screen-desktop.png`
- Mobile live-action screenshot: `docs/browser-qa-production-depth-live-agenda-intake-screen-mobile.png`
- Summary: `docs/browser-qa-production-depth-live-agenda-intake-screen-summary.md`
- Expected checks: live agenda intake form submission, live readiness review, visible success output, actionable fix copy, desktop and mobile viewports, no console messages, no horizontal document overflow, visible focus outline.
