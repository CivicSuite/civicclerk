# Production Depth Staff Workflow Screens Slice

Status: ready for audit
Branch: `production-depth/staff-workflow-screens`

## Shipped

- `/staff` upgraded from a static workflow map into first staff workflow screens for agenda intake, packet assembly, and notice checklist/posting-proof work.
- Screen tabs for Agenda Intake, Packet Assembly, and Notice Checklist with visible sample work queues, live API paths, safe next actions, and actionable fix copy.
- Root endpoint now reports that staff workflow screens are online and points the next slice toward live clerk-console form actions and meeting persistence.
- README, text README, user manual, text manual, changelog, and landing page now distinguish shipped staff workflow screens from still-planned live browser form submission.
- Browser QA evidence for desktop and mobile tab interactions, console output, overflow, and focus state.

## Not Shipped

- Live browser form submission from `/staff` into backing service APIs.
- End-to-end meeting workflow completion.
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
- Desktop slice screenshot: `docs/browser-qa-production-depth-staff-workflow-screens-desktop.png`
- Mobile slice screenshot: `docs/browser-qa-production-depth-staff-workflow-screens-mobile.png`
- Summary: `docs/browser-qa-production-depth-staff-workflow-screens-summary.md`
- Expected checks: screen tabs for intake, packet assembly, and notice checklist; visible API paths; actionable fix copy; desktop and mobile viewports; no console messages; no horizontal document overflow; visible focus outline.
