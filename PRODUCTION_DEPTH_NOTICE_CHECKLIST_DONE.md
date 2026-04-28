# Production Depth Notice Checklist Records Slice

Status: ready for audit
Branch: `production-depth/notice-posting-proof`

## Shipped

- Database-backed notice checklist records with compliance outcomes, warnings, and posting-proof metadata.
- Alembic migration `civicclerk_0004_notice_ck` creates the persistent notice checklist table in the `civicclerk` schema.
- `CIVICCLERK_NOTICE_CHECKLIST_DB_URL` configuration for persistent SQLAlchemy storage; local smoke checks can use the in-memory default.
- `/meetings/{meeting_id}/notice-checklists` create and list endpoints.
- `/notice-checklists/{record_id}/posting-proof` endpoint for posting proof metadata.
- Durable `last_audit_hash` evidence on each notice checklist record, generated from CivicCore hash-chained audit events for check and posting-proof actions.
- Staff dashboard and product docs now describe notice checklist service depth without claiming full notice workflow screens.

## Not Shipped

- Full notice checklist UI screens.
- Automatic legal sufficiency decisions.
- Automatic public posting.
- Release version bump or package release.

## Verification Snapshot

- `python -m pytest --collect-only -q` -> 379 tests collected
- `python -m pytest -q` -> 379 passed
- `bash scripts/verify-docs.sh` -> `VERIFY-DOCS: PASSED`
- `python scripts/check-civiccore-placeholder-imports.py` -> `PLACEHOLDER-IMPORT-CHECK: PASSED (24 source files scanned)`
- `python -m ruff check .` -> `All checks passed!`
- `bash scripts/verify-release.sh` -> `VERIFY-RELEASE: PASSED` (374 release-gate tests passed; milestone 12 release tests excluded by script)

## Browser QA Evidence

- Landing desktop screenshot: `docs/browser-qa-production-depth-notice-checklist-landing-desktop.png`
- Landing mobile screenshot: `docs/browser-qa-production-depth-notice-checklist-landing-mobile.png`
- Staff desktop screenshot: `docs/browser-qa-production-depth-notice-checklist-staff-desktop.png`
- Staff mobile screenshot: `docs/browser-qa-production-depth-notice-checklist-staff-mobile.png`
- Summary: `docs/browser-qa-production-depth-notice-checklist-summary.md`
- Expected checks: notice checklist copy, posting-proof copy, `/meetings/{id}/notice-checklists`, `CIVICCLERK_NOTICE_CHECKLIST_DB_URL`, no stale notice-checklist deferral, no horizontal overflow, visible focus outline, and no console messages.
