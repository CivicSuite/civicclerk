# Production Depth Packet Assembly Records Slice

Status: ready for audit
Branch: `production-depth/packet-assembly-records`

## Shipped

- Database-backed packet assembly records with source references and citations.
- Alembic migration `civicclerk_0003_packet_asm` creates the persistent packet assembly table in the `civicclerk` schema.
- `CIVICCLERK_PACKET_ASSEMBLY_DB_URL` configuration for persistent SQLAlchemy storage; local smoke checks can use the in-memory default.
- `/meetings/{meeting_id}/packet-assemblies` create and list endpoints.
- `/packet-assemblies/{record_id}/finalize` endpoint for staff finalization.
- Packet assembly creation also creates a packet snapshot, so existing packet export bundle workflows can export the current packet version.
- Durable `last_audit_hash` evidence on each assembly record, generated from CivicCore hash-chained audit events for create and finalize actions.
- Staff dashboard and product docs now describe packet assembly service depth without claiming full packet builder screens.

## Not Shipped

- Full packet builder UI screens.
- Database-backed notice checklist and posting-proof workflow queues.
- Legal sufficiency decisions or automatic public posting.
- Release version bump or package release.

## Verification Snapshot

- `python -m pytest --collect-only -q` -> 374 tests collected
- `python -m pytest -q` -> 374 passed
- `bash scripts/verify-docs.sh` -> `VERIFY-DOCS: PASSED`
- `python scripts/check-civiccore-placeholder-imports.py` -> `PLACEHOLDER-IMPORT-CHECK: PASSED (22 source files scanned)`
- `python -m ruff check .` -> all checks passed
- `bash scripts/verify-release.sh` -> `VERIFY-RELEASE: PASSED`

## Browser QA Evidence

- Landing desktop screenshot: `docs/browser-qa-production-depth-packet-assembly-landing-desktop.png`
- Landing mobile screenshot: `docs/browser-qa-production-depth-packet-assembly-landing-mobile.png`
- Staff desktop screenshot: `docs/browser-qa-production-depth-packet-assembly-staff-desktop.png`
- Staff mobile screenshot: `docs/browser-qa-production-depth-packet-assembly-staff-mobile.png`
- Summary: `docs/browser-qa-production-depth-packet-assembly-summary.md`
- Expected checks: packet assembly copy, database-backed packet assembly copy, `/meetings/{id}/packet-assemblies`, `CIVICCLERK_PACKET_ASSEMBLY_DB_URL`, no stale "database-backed packet and notice persistence" claim, no horizontal overflow, visible focus outline, and no console messages.
