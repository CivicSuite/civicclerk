# Production Depth Packet Export Slice

Status: ready for audit
Branch: `production-depth/packet-notice-services`

## Shipped

- CivicClerk now pins `civiccore==0.3.0`.
- Packet snapshots can be exported as records-ready bundles using CivicCore v0.3.0 primitives.
- Export bundles include `packet.json`, `provenance.json`, `notices.json`, `manifest.json`, and `SHA256SUMS.txt`.
- Public packet exports reject closed-session, staff-only, and restricted source files with an actionable fix path.
- Packet snapshot and packet export creation record hash-chained audit events.
- `/meetings/{meeting_id}/export-bundle` accepts a relative `bundle_name` under `CIVICCLERK_EXPORT_ROOT` after a packet snapshot exists.

## Not Shipped

- Full packet builder UI screens.
- Database-backed packet export queues.
- Legal sufficiency decisions or automatic public posting.
- Cloud export destinations.

## Verification Snapshot

- `python -m pytest --collect-only -q` -> 362 tests collected
- `python -m pytest -q` -> 362 passed
- `bash scripts/verify-docs.sh` -> `VERIFY-DOCS: PASSED`
- `python scripts/check-civiccore-placeholder-imports.py` -> `PLACEHOLDER-IMPORT-CHECK: PASSED (18 source files scanned)`
- `python -m ruff check .` -> all checks passed
- `bash scripts/verify-release.sh` -> `VERIFY-RELEASE: PASSED`

## Browser QA Evidence

- Desktop screenshot: `docs/browser-qa-production-depth-packet-export-desktop.png`
- Mobile screenshot: `docs/browser-qa-production-depth-packet-export-mobile.png`
- Summary: `docs/browser-qa-production-depth-packet-export-summary.md`
- Desktop and mobile checks found CivicCore v0.3.0 copy, packet export copy, checksum/provenance copy, no stale `civiccore==0.2.0`, no horizontal overflow, visible focus outline, and no console messages.
