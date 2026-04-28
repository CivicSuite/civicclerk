# Changelog

All notable changes to CivicClerk are documented here.

## [Unreleased]

### Added
- Production-depth packet export bundle slice using CivicCore v0.3.0
  `civiccore.exports`, `civiccore.provenance`, and `civiccore.audit`
  primitives.
- `/meetings/{meeting_id}/export-bundle` endpoint for records-ready packet
  bundles with manifest, SHA256 checksum file, source provenance, and
  hash-chained audit evidence.
- Public packet export guardrail that rejects closed-session, staff-only, and
  restricted source files with an actionable fix path.
- Safe packet export path handling: API callers provide a relative
  `bundle_name` under `CIVICCLERK_EXPORT_ROOT`, not an arbitrary filesystem
  path.
- Milestone 13 staff workflow UI foundation at `/staff`, mapping released API workflows and required rendered states without claiming full workflow screens or live database-backed queues.

### Changed
- CivicClerk now pins `civiccore==0.3.0` for shared audit, provenance,
  connector manifest, export bundle, and city-profile primitives.

## [0.1.0] - 2026-04-26

### Added
- Milestone 11 accessibility and browser QA gates.
- Browser QA state fixture covering loading, success, empty, error, and
  partial states.
- CI browser QA evidence gate for keyboard, focus, contrast, console, and
  screenshot artifacts.
- Milestone 10 local-first connector/import normalization.
- Granicus, Legistar, PrimeGov, and NovusAGENDA meeting import support from
  local export payloads.
- Source provenance on imported meetings and agenda items.
- Actionable connector import errors for unsupported connectors and malformed
  local payloads.
- Milestone 9 prompt YAML library and evaluation harness.
- YAML-backed `minutes_draft@0.1.0` prompt with required variable enforcement.
- Offline prompt evaluation script that runs with `CIVICCORE_LLM_PROVIDER=ollama`
  and outbound network blocked.
- Prompt-version provenance enforcement for minutes drafts.
- Milestone 8 public meeting calendar, detail, and archive search endpoints.
- Permission-aware public archive filtering for anonymous, staff, clerk,
  attorney, and admin roles.
- Closed-session leak prevention across public response bodies, counts,
  suggestions, and not-found responses.
- Milestone 7 minutes drafting with sentence citations.
- Citation-gated minutes draft records that reject uncited material output.
- Minutes draft provenance recording model, prompt version, source ids, and
  human approver.
- Guardrail rejecting automatic public posting of AI-drafted minutes.
- Milestone 6 motion, vote, and action-item capture.
- Immutable captured motion records, append-only motion corrections, and
  `409 Conflict` responses for direct motion mutation attempts.
- Immutable captured vote records, append-only vote corrections, and
  `409 Conflict` responses for direct vote mutation attempts.
- Action items linked to meeting outcomes and source motions.
- Milestone 5 packet snapshot versioning and notice compliance enforcement.
- API endpoints to create/list packet snapshots, check notice compliance,
  and post approved public notices.
- Actionable notice warnings for missed deadlines, missing statutory basis,
  and missing human approval.
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
- README, user manual, landing page, and root endpoint now describe the
  shipped browser QA gate foundation and point reviewers to Milestone 12.
- README, user manual, landing page, and root endpoint now describe the
  shipped connector import foundation and point reviewers to Milestone 11.
- README, user manual, landing page, and root endpoint now describe the
  shipped prompt evaluation foundation and point reviewers to Milestone 10.
- README, user manual, landing page, and root endpoint now describe the
  shipped public archive foundation and point reviewers to Milestone 9.
- README, user manual, landing page, and root endpoint now describe the
  shipped minutes citation foundation and point reviewers to Milestone 8.
- README, user manual, landing page, and root endpoint now describe the
  shipped motion/vote/action foundation and point reviewers to Milestone 7.
- README and root endpoint now describe the shipped schema foundation and
  point reviewers to Milestone 3 as the next implementation step.
- README, user manual, landing page, and root endpoint now describe the
  shipped meeting lifecycle foundation and point reviewers to Milestone 5
  as the next implementation step.
- README, user manual, landing page, and root endpoint now describe the
  shipped packet/notice compliance foundation and point reviewers to
  Milestone 6 as the next implementation step.

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
