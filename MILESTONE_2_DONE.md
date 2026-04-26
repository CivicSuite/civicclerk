# Milestone 2 Done

Milestone 2 added the CivicClerk canonical schema and Alembic migration scaffold. It does not implement agenda lifecycle enforcement, meeting lifecycle enforcement, public pages, search, permissions, or workflow behavior.

## Criteria Covered

- `civicclerk.models` defines metadata for all fourteen canonical CivicClerk tables.
- All module tables use the `civicclerk` schema.
- Models import and use CivicCore's shared `Base` from `civiccore.db`.
- No competing SQLAlchemy `DeclarativeBase` or `declarative_base()` is declared.
- No foreign keys target CivicCore placeholder packages or unreleased CivicCore shared tables.
- CivicClerk Alembic scaffold exists under `civicclerk/migrations`.
- Alembic env runs the CivicCore migration baseline before CivicClerk migrations.
- CivicClerk uses a separate `alembic_version_civicclerk` version table.
- First migration creates the `civicclerk` schema and the fourteen canonical tables with idempotent create-table guards.
- Current-facing docs and CHANGELOG describe the canonical schema and Alembic scaffold without claiming lifecycle/workflow behavior.

## Test Counts

- Total automated pytest count: 20 passed, 0 skipped, 0 xfail.
- Milestone 2 schema/migration tests: 10 passed.
- Existing Milestone 1 runtime-foundation tests: 10 passed.

## TDD Iterations

- Iteration 1: `c1eb0a3` - canonical table metadata green.
- Iteration 2: `3386c2d` - Alembic schema scaffold green.
- Iteration 3: `7ea3afa` - schema milestone docs green.

## Deferred Items

None for Milestone 2. Milestone 3 remains agenda item lifecycle enforcement and has not been started.

## Verification

- `python -m pytest -q` passed.
- `bash scripts/verify-docs.sh` passed.
- `python scripts/check-civiccore-placeholder-imports.py` passed.
