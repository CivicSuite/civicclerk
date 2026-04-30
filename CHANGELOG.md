# Changelog

All notable changes to CivicClerk are documented here.

## [Unreleased]

## [0.1.11] - 2026-04-30

### Added
- `/staff/auth-readiness` now reports whether the current bearer-token or
  trusted-header staff auth mode is deployment-ready, including actionable
  fix paths for missing token mappings and missing or invalid trusted-proxy
  CIDR allowlists.
- README, manual, and landing-page install guidance now document the
  fresh-machine wheel-install rehearsal path, including explicit `uvicorn`
  startup and first-run smoke checks for `/health`, `/staff/auth-readiness`,
  and `/staff`.

### Changed
- The `/staff` workflow shell now checks auth readiness before attempting a
  live session check so operators can distinguish direct-browser access from
  deployable staff-auth configuration.

## [0.1.10] - 2026-04-29

### Changed
- Trusted-header staff auth now consumes the shared `civiccore.auth`
  trusted-header config contract and shared proxy-source enforcement helper
  instead of carrying service-local env parsing and allowlist validation copy.
- CivicClerk now targets the published `civiccore` v0.16.0 release wheel.

## [0.1.9] - 2026-04-29

### Added
- Trusted-header staff mode now enforces a configured trusted-proxy CIDR
  allowlist before CivicClerk accepts asserted principal and roles headers.

### Changed
- The `/staff` workflow shell, current-facing docs, and release gate now
  document `CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES` as part of the trusted
  reverse-proxy contract.

## [0.1.8] - 2026-04-29

### Added
- CivicClerk staff workflow APIs now support a trusted-header reverse-proxy
  bridge for municipal SSO front doors, including configurable principal and
  role header names, provider labeling, and browser-visible `/staff/session`
  status that tells operators exactly which asserted identity contract is in
  effect.

### Changed
- The `/staff` workflow shell now discloses local open, bearer-protected, and
  trusted-header staff modes, and it explains that full OIDC login is still
  future work rather than pretending the proxy bridge is a first-party IdP flow.
- CivicClerk now targets the published `civiccore` v0.14.0 release wheel.

## [0.1.7] - 2026-04-29

### Added
- CivicClerk staff workflow APIs now support a first shared bearer-token
  access contract, including `/staff/session` for browser-visible auth-state
  checks and a local-open rehearsal mode that can be replaced later by SSO.

### Changed
- The `/staff` workflow shell now discloses whether the service is running in
  local open mode or bearer-protected staff mode and sends bearer tokens with
  live staff actions when configured.

## [0.1.6] - 2026-04-29

### Added
- CivicClerk minutes drafting now consumes the shared
  `civiccore.ingest` cited-source contracts and validation helper while
  preserving the module's existing operator-facing minutes error messages.

### Changed
- CivicClerk now targets the published `civiccore` v0.13.0 release wheel.

## [0.1.5] - 2026-04-29

### Added
- `civicclerk.connectors` now re-exports the shared `civiccore.security`
  connector runtime validation helpers so future live-sync work can adopt the
  same blocked-host and ODBC host-validation contract without module-local
  reimplementation.

### Changed
- CivicClerk now targets the published `civiccore` v0.12.0 release wheel.

## [0.1.4] - 2026-04-29

### Added
- Production-depth agenda item lifecycle persistence slice with
  `CIVICCLERK_AGENDA_ITEM_DB_URL`, durable status/audit entries, and Alembic
  migration `civicclerk_0006_agenda_items`.
- Shared browser-QA release evidence validation through
  `civiccore.verification.validate_release_browser_evidence`, so CivicClerk's
  release screenshots and manifest stay bound to the current docs page hash.
- Public archive search now consumes the shared `civiccore.search`
  normalization helper surface, keeping permission-aware archive matching
  whitespace-stable and case-insensitive without a local duplicate helper.
- CivicClerk notice compliance checks now reuse the shared
  `civiccore.notifications.evaluate_notice_compliance` helper while
  preserving the module's existing warning and posting API contract.

### Changed
- CivicClerk now installs the published `civiccore` v0.11.0 release wheel so
  the release gate can consume the shipped shared verification, search, and
  connector import helpers plus the shared notice compliance helper in
  addition to the existing audit, provenance, and export primitives.

## [0.1.2] - 2026-04-29

### Added
- Production-depth agenda intake readiness slice with a database-backed
  department submission queue, clerk review state, and durable CivicCore audit
  hash references.
- `/agenda-intake` submit/list/review endpoints for the first DB-backed staff
  workflow queue, configurable with `CIVICCLERK_AGENDA_INTAKE_DB_URL`.
- Production-depth packet assembly persistence slice with source references,
  citations, packet snapshot linkage, and durable CivicCore audit hash
  references.
- `/meetings/{meeting_id}/packet-assemblies` create/list endpoint and
  `/packet-assemblies/{record_id}/finalize` endpoint, configurable with
  `CIVICCLERK_PACKET_ASSEMBLY_DB_URL`.
- Production-depth notice checklist persistence slice with compliance outcomes,
  warning details, posting proof metadata, and durable CivicCore audit hash
  references.
- `/meetings/{meeting_id}/notice-checklists` create/list endpoint and
  `/notice-checklists/{record_id}/posting-proof` endpoint, configurable with
  `CIVICCLERK_NOTICE_CHECKLIST_DB_URL`.
- Production-depth meeting persistence slice with database-backed meeting
  records, normalized meeting types, scheduled starts, lifecycle status, and
  durable audit entries.
- `CIVICCLERK_MEETING_DB_URL` configuration for `/meetings`,
  `/meetings/{meeting_id}/transitions`, and meeting-dependent service
  endpoints.
- Production-depth staff workflow screens at `/staff` for agenda intake,
  packet assembly, and notice checklist/posting-proof work, with visible
  workflow state examples and actionable fix copy.
- Live `/staff` agenda intake form actions that submit department intake
  items and record clerk readiness review through the existing API.
- Live `/staff` packet assembly and notice checklist form actions that create
  demo meetings, create/finalize packet assembly records, persist notice
  checklist records, and attach posting proof through the existing APIs.
- Live `/staff` meeting outcome form action that creates a demo meeting,
  captures an immutable motion, records a vote, and creates an action item
  tied to the source motion through the existing APIs.
- Live `/staff` minutes draft form action that creates a demo meeting and
  submits a citation-gated minutes draft through `/meetings/{id}/minutes/drafts`
  while preserving the human-review, never-auto-posted guardrail.
- Live `/staff` public archive form action that creates a demo meeting,
  publishes a public-safe record through `/meetings/{id}/public-record`, and
  verifies anonymous visibility through `/public/meetings` plus
  `/public/archive/search`.
- Live `/staff` connector import form action that normalizes pasted local
  Granicus, Legistar, PrimeGov, or NovusAGENDA meeting export JSON through
  `/imports/{connector}/meetings` without vendor-network access.
- Live `/staff` packet export form action that creates the required packet
  snapshot, then writes a records-ready bundle with manifest and checksums
  through `/meetings/{id}/export-bundle`.
- Production-depth packet export bundle slice using CivicCore v0.6.0
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
- Milestone 13 staff workflow UI at `/staff`, upgraded from a workflow map into first workflow screens for the three database-backed service slices with live browser form actions for agenda intake, packet assembly, and notice checklist/posting-proof workflows.

### Changed
- CivicClerk now pins `civiccore==0.6.0` for shared audit, provenance,
  connector manifest, export bundle, and city-profile primitives.
- Version surfaces, release gate artifact checks, and current-facing docs now
  reflect the post-production-depth `v0.1.2` release.

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
