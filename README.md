# CivicClerk

**CivicClerk is the CivicSuite module for municipal meetings, agendas, packets, minutes, votes, notices, and public meeting archives.**

Status: CivicClerk v0.1.0 runtime foundation release  
Current version: `0.1.0`  
Repository: <https://github.com/CivicSuite/civicclerk>  
Depends on: `civiccore==0.3.0`

## What CivicClerk will do

CivicClerk is designed for the legal record of public meetings:

- agenda item intake from departments
- packet assembly
- statutory notice deadline tracking
- meeting motions, votes, and action logging
- minute drafting with source citations
- ordinance and resolution adoption-event export
- public meeting pages for posted agendas, packets, and approved minutes
- searchable meeting archives

AI may draft or extract. Humans approve every consequential action.

## What exists today

CivicClerk v0.1.0 ships the runtime and schema foundation plus agenda item lifecycle, meeting lifecycle, packet snapshot, notice compliance, immutable motion capture, immutable vote capture, action-item capture, citation-gated minutes draft capture, permission-aware public calendar/detail/archive endpoints, a prompt YAML library with an offline evaluation harness, local-first connector imports for Granicus, Legistar, PrimeGov, and NovusAGENDA, accessibility/browser QA gates, CivicCore v0.3.0-backed records export bundles, database-backed agenda intake readiness, database-backed packet assembly records, database-backed notice checklist/posting-proof records, database-backed meeting records, and first staff workflow screens for intake, packet assembly, notice checklist, meeting outcome, minutes draft, public archive, and connector import work. The staff screens now submit agenda intake, record readiness review, create/finalize packet assembly records, persist notice checklist records, attach posting proof, capture motions/votes/action items, create citation-gated minutes drafts, publish public-safe archive records, and normalize local connector exports through the live API; live clerk-console form submission for the remaining workflows is not implemented yet.

Shipped in this foundation:

- project README
- user manual with non-technical, IT/technical, and architecture sections
- GitHub Pages landing page at `docs/index.html`
- contributing, support, security, code of conduct, issue templates, and PR template
- discussion seed posts
- docs verification script and CI workflow
- Python package metadata with `civiccore==0.3.0`
- FastAPI application import path at `civicclerk.main:app`
- root endpoint that explains the current product state
- `/health` endpoint for IT staff
- `/staff` staff workflow screens for agenda intake, packet assembly, notice checklist/posting-proof, meeting outcome, minutes draft, public archive, and connector import work
- live `/staff` agenda intake submission and clerk readiness-review form actions backed by `/agenda-intake`
- live `/staff` packet assembly create/finalize form actions backed by `/meetings/{id}/packet-assemblies`
- live `/staff` notice checklist and posting-proof form actions backed by `/meetings/{id}/notice-checklists`
- database-backed agenda intake queue with clerk readiness review state and
  Alembic migration `civicclerk_0002_intake_queue`
- `/agenda-intake` submit/list/review endpoints with audit events for consequential review actions
- canonical SQLAlchemy metadata for the fourteen CivicClerk tables
- Alembic scaffold and first idempotent migration for the `civicclerk` schema
- agenda item lifecycle enforcement from `DRAFTED` through `ARCHIVED`
- audit entries for allowed and rejected agenda item transitions
- meeting lifecycle enforcement from `SCHEDULED` through `ARCHIVED`
- database-backed meeting records with lifecycle audit entries, scheduled
  starts, normalized meeting type, and Alembic migration
  `civicclerk_0005_meetings`
- emergency/special meeting notice preconditions requiring a statutory basis
- closed/executive session in-progress preconditions requiring a statutory basis
- cancellation support from scheduled or noticed meetings, with terminal-state audit entries
- packet snapshot versioning for meetings
- database-backed packet assembly records with source references, citations,
  packet snapshot linkage, and Alembic migration `civicclerk_0003_packet_asm`
- `/meetings/{id}/packet-assemblies` create/list endpoint and
  `/packet-assemblies/{id}/finalize` endpoint with durable audit hashes
- notice compliance checks for deadlines, statutory basis, and human approval
- database-backed notice checklist and posting-proof records with Alembic
  migration `civicclerk_0004_notice_ck`
- `/meetings/{id}/notice-checklists` create/list endpoint and
  `/notice-checklists/{id}/posting-proof` endpoint with durable audit hashes
- approved public notice posting records with actionable warning/error responses
- immutable captured motions with append-only correction records
- immutable captured votes with append-only correction records
- action items linked to meeting outcomes and source motions
- live `/staff` meeting outcome form actions backed by `/meetings/{id}/motions`,
  `/motions/{id}/votes`, and `/meetings/{id}/action-items`
- live `/staff` minutes draft form actions backed by
  `/meetings/{id}/minutes/drafts`
- live `/staff` public archive form actions backed by
  `/meetings/{id}/public-record`, `/public/meetings`, and
  `/public/archive/search`
- live `/staff` connector import form actions backed by
  `/imports/{connector}/meetings`
- citation-gated minutes draft records
- provenance for minutes drafts: model, prompt version, data sources, and human approver
- rejection of uncited AI-drafted minutes output before it can be accepted
- permission-aware public meeting calendar, detail, and archive search endpoints
- closed-session leak prevention for anonymous public archive bodies, counts, suggestions, and not-found responses
- YAML prompt library under `prompts/`
- offline prompt evaluation harness that runs with `CIVICCORE_LLM_PROVIDER=ollama` and outbound network blocked
- prompt-version provenance enforcement for minutes drafts
- local-first Granicus, Legistar, PrimeGov, and NovusAGENDA meeting imports
- source provenance on imported meetings and agenda items
- records-ready packet export bundles with CivicCore v0.3.0 manifests, SHA256 checksums, provenance, and hash-chained audit events
- closed-session/restricted source guardrails for public packet export bundles
- safe API export-path handling through `bundle_name` under `CIVICCLERK_EXPORT_ROOT`
- browser QA gate covering loading, success, empty, error, and partial states
- accessibility checks for keyboard navigation, focus states, contrast, and console errors
- CivicClerk v0.1.0 release gate and build artifacts

Not shipped yet:

- full frontend app
- installer
- public portal
- database-backed agenda item persistence beyond the current runtime slice
- live browser form submission from `/staff` into the remaining backing service API for packet export creation
- browser workflow screens for packet export creation and review

## New user experience today

A new user can inspect and run the foundation, open first staff workflow screens at `/staff`, submit agenda intake items into a database-backed queue from the browser, record clerk readiness review from the browser, create/finalize packet assembly records from the browser, persist notice checklist/posting-proof records from the browser, capture motions/votes/action items from the browser, create citation-gated minutes drafts from the browser, publish public-safe archive records from the browser, normalize local connector exports from the browser, persist meeting records and lifecycle audit entries through `CIVICCLERK_MEETING_DB_URL`, create draft agenda items and meetings through the API, and generate a records-ready packet export bundle with manifest, checksums, provenance, and audit evidence. They cannot use CivicClerk for end-to-end meeting work yet. The correct next experience is:

1. Read this README.
2. Read `USER-MANUAL.md`.
3. Read `docs/roadmap/mvp-plan.md`.
4. For an IT smoke check, run the FastAPI app at `civicclerk.main:app`, call `/health`, and open `/staff`.
5. Exercise `/agenda-intake`, `/agenda-intake/{id}/review`, `/agenda-items`, `/agenda-items/{id}/transitions`, `/meetings`, `/meetings/{id}/transitions`, `/meetings/{id}/packet-snapshots`, `/meetings/{id}/packet-assemblies`, `/packet-assemblies/{id}/finalize`, `/meetings/{id}/notice-checklists`, `/notice-checklists/{id}/posting-proof`, `/meetings/{id}/export-bundle`, `/meetings/{id}/notices/post`, `/meetings/{id}/motions`, `/motions/{id}/votes`, `/meetings/{id}/action-items`, `/meetings/{id}/minutes/drafts`, `/meetings/{id}/public-record`, `/public/meetings`, `/public/archive/search`, and `/imports/{connector}/meetings` to smoke-check Milestone 10 plus the production-depth live staff action slices.
6. Run `CIVICCORE_LLM_PROVIDER=ollama CIVICCLERK_EVAL_OFFLINE=1 NO_NETWORK=1 python scripts/run-prompt-evals.py` before changing prompt YAML.
7. Set `CIVICCLERK_MEETING_DB_URL` before meeting persistence smoke checks, and set `CIVICCLERK_EXPORT_ROOT` before API packet export smoke checks; API callers provide a relative `bundle_name`, not an arbitrary filesystem path.
8. Run `python scripts/verify-browser-qa.py` before landing frontend or browser-visible documentation changes.
9. Follow GitHub issues and discussions as live sync, full UI, and database-backed workflows land.

## Architecture direction

CivicClerk follows the CivicSuite pattern:

- FastAPI backend
- React frontend
- PostgreSQL 17 + pgvector
- Redis 7.2 + Celery + Celery Beat
- Ollama / Gemma 4 through `civiccore.llm`, selected by `CIVICCORE_LLM_PROVIDER=ollama`
- local data ownership, no runtime telemetry, no cloud inference

The foundation is intentionally thin. Canonical schema, Alembic scaffolding, agenda item lifecycle enforcement, meeting lifecycle enforcement, meeting records, packet snapshot versioning, packet assembly records, notice checklist records, notice compliance enforcement, immutable motion capture, immutable vote capture, action-item capture, citation-gated minutes draft capture, permission-aware public archive endpoints, prompt YAML/evaluation gates, local-first connector import normalization, browser QA gates, CivicClerk v0.1.0 release artifacts, and CivicCore v0.3.0 packet export primitives are present. Minutes drafts require sentence-level citations, YAML prompt-version provenance, and human approval before acceptance, and they are never auto-adopted or auto-posted. Anonymous public archive endpoints do not reveal closed-session content in response bodies, counts, suggestions, or error messages. Connector imports record source provenance and do not require outbound network calls in the default local profile. Public packet exports block closed-session/restricted sources and include manifest, checksum, provenance, and audit evidence. Meeting records now persist scheduled starts, normalized meeting type, lifecycle status, and audit entries when `CIVICCLERK_MEETING_DB_URL` is configured. Packet assembly records now persist source references, citations, linked packet snapshot ids, and durable audit hashes. Notice checklist records persist compliance outcomes, warnings, posting proof, and durable audit hashes. Browser QA now checks loading, success, empty, error, and partial states plus keyboard, focus, contrast, and console evidence. CivicClerk v0.1.0 now pairs with `civiccore==0.3.0`.

The staff experience at `/staff` now includes first workflow screens for agenda intake, packet assembly, notice checklist/posting-proof, meeting outcome, minutes draft, public archive, and connector import work. It is intentionally honest: these seven screens can submit their corresponding live API actions, while the remaining workflow areas are still API/service foundations until their browser form actions land.

## Verification

Before every push:

```bash
python -m pytest
bash scripts/verify-docs.sh
python scripts/check-civiccore-placeholder-imports.py
python scripts/verify-browser-qa.py
CIVICCORE_LLM_PROVIDER=ollama CIVICCLERK_EVAL_OFFLINE=1 NO_NETWORK=1 python scripts/run-prompt-evals.py
bash scripts/verify-release.sh
```

## License

Code: Apache License 2.0; see `LICENSE-CODE`.  
Documentation: CC BY 4.0 unless otherwise stated; see `LICENSE-DOCS`.
