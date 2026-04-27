# Changelog

All notable changes to CivicClerk are documented here.

## [Unreleased]

### Added
- Milestone 4 meeting lifecycle enforcement for the canonical state chain
  from `SCHEDULED` through `ARCHIVED`.
- API endpoints to create meetings, transition meeting status, inspect
  current meeting state, and read meeting lifecycle audit entries.
- Transition tests for emergency/special statutory-basis requirements,
  closed/executive session statutory-basis requirements, cancellation, and
  rejected non-canonical meeting transitions.
- Milestone 3 agenda item lifecycle enforcement for the canonical state
  chain from `DRAFTED` through `ARCHIVED`.
- API endpoints to create draft agenda items, transition agenda item
  status, inspect current agenda item state, and read lifecycle audit
  entries.
- Parametrized transition matrix tests covering every `(from, to)` agenda
  item status pair. Invalid transitions return 4xx responses and write
  audit entries.
- Milestone 2 canonical schema and Alembic migration scaffold for the
  fourteen CivicClerk tables.
- pgvector-backed Alembic integration coverage proving CivicClerk and
  CivicCore migrations run against the same configured database URL.

### Changed
- README and root endpoint now describe the shipped schema foundation and
  point reviewers to Milestone 3 as the next implementation step.
- README, user manual, landing page, and root endpoint now describe the
  shipped meeting lifecycle foundation and point reviewers to Milestone 5
  as the next implementation step.

## [0.1.0.dev0] - 2026-04-26

### Added

#### Milestone 1 (runtime foundation)
- Milestone 1 runtime foundation with Python package metadata, exact
  `civiccore==0.2.0` dependency pin, FastAPI import path, root and health
  endpoints, pytest CI, and placeholder-import CI gate.

#### Milestone 0 (scaffold reconciliation)
- Initial professional repository scaffold for CivicClerk.
- README, user manual, landing page, discussion seeds,
  community files, issue templates, PR template, docs verification script,
  and CI workflow.
