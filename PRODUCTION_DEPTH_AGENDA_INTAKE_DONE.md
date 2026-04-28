# Production Depth Agenda Intake Readiness Slice

Status: ready for audit
Branch: `production-depth/agenda-intake-readiness`

## Shipped

- Database-backed agenda intake queue for department-submitted agenda items.
- Alembic migration `civicclerk_0002_intake_queue` creates the persistent queue table in the `civicclerk` schema.
- `CIVICCLERK_AGENDA_INTAKE_DB_URL` configuration for persistent SQLAlchemy storage; local smoke checks can use the in-memory default.
- `/agenda-intake` submit and list endpoints.
- `/agenda-intake/{item_id}/review` endpoint for clerk readiness review.
- Readiness states: `PENDING`, `READY`, and `NEEDS_REVISION`.
- Durable `last_audit_hash` evidence on each queue row, generated from CivicCore hash-chained audit events for submit and review actions.
- Staff dashboard and product docs now describe the first database-backed workflow queue without claiming full workflow UI screens.

## Not Shipped

- Full staff agenda intake screens.
- Database-backed packet assembly and notice checklist workflow queues.
- Cross-module source adapters beyond the source-reference metadata accepted by this queue.
- Release version bump or package release.

## Verification Snapshot

- `python -m pytest --collect-only -q` -> 368 tests collected
- `python -m pytest -q` -> 368 passed
- `bash scripts/verify-docs.sh` -> `VERIFY-DOCS: PASSED`
- `python scripts/check-civiccore-placeholder-imports.py` -> `PLACEHOLDER-IMPORT-CHECK: PASSED (20 source files scanned)`
- `python -m ruff check .` -> all checks passed
- `bash scripts/verify-release.sh` -> `VERIFY-RELEASE: PASSED`

## Browser QA Evidence

- Landing desktop screenshot: `docs/browser-qa-production-depth-agenda-intake-landing-desktop.png`
- Landing mobile screenshot: `docs/browser-qa-production-depth-agenda-intake-landing-mobile.png`
- Staff desktop screenshot: `docs/browser-qa-production-depth-agenda-intake-staff-desktop.png`
- Staff mobile screenshot: `docs/browser-qa-production-depth-agenda-intake-staff-mobile.png`
- Summary: `docs/browser-qa-production-depth-agenda-intake-summary.md`
- Desktop and mobile checks found agenda intake copy, database-backed queue copy, `CIVICCLERK_AGENDA_INTAKE_DB_URL`, no stale "No live database-backed queue is connected yet" copy, no horizontal overflow, visible focus outline, and no console messages.
