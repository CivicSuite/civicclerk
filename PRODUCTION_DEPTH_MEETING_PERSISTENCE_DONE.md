# Production-Depth Meeting Persistence Done

## Scope

This slice adds database-backed meeting records while keeping CivicClerk at
version `0.1.0`.

## What shipped

- `CIVICCLERK_MEETING_DB_URL` selects the persistent meeting store.
- `/meetings`, `/meetings/{id}`, `/meetings/{id}/transitions`, and
  `/meetings/{id}/audit` use the configured store when the environment
  variable is set.
- Meeting records persist title, normalized meeting type, scheduled start,
  lifecycle status, and lifecycle audit entries.
- `civicclerk_0005_meetings` adds the `civicclerk.meeting_records` migration
  after `civicclerk_0004_notice_ck`.
- SQLite smoke checks normalize persisted datetimes back to UTC so local tests
  and operator checks behave consistently.

## Verification snapshot

- `python -m pytest --collect-only -q`: 382 tests collected
- Targeted runtime and migration suite: 184 passed
- Real pgvector Alembic operator path: passed through
  `tests/test_milestone_2_schema_and_migrations.py::test_alembic_command_upgrades_real_pgvector_database`
- Browser QA:
  - `docs/browser-qa-production-depth-meeting-persistence-desktop.png`
  - `docs/browser-qa-production-depth-meeting-persistence-mobile.png`
  - `docs/browser-qa-production-depth-meeting-persistence-summary.md`

## Not shipped

- Full end-to-end meeting workflow UI.
- Browser form actions for motions, votes, action items, minutes, archive, and
  connector imports.
- Installer or public portal.

