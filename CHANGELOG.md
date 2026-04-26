# Changelog

All notable changes to CivicClerk are documented here.

## [Unreleased]

### Added
- Milestone 2 canonical schema and Alembic migration scaffold for the
  fourteen CivicClerk tables. This is schema foundation only; agenda and
  meeting lifecycle enforcement has not shipped.
- Executable Alembic env smoke coverage proving CivicClerk and CivicCore
  migrations receive the same configured database URL.

### Changed
- README and root endpoint now describe the shipped schema foundation and
  point reviewers to Milestone 3 as the next implementation step.

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
