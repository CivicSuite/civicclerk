# CivicClerk Milestones

This plan restates AGENTS.md §4 for CivicClerk v0.1.0. Each milestone is a complete TDD loop: failing tests first, implementation second, documentation update, CI green, and a milestone done file. Test counts are planning ballparks, not completion claims.

| # | Milestone | Acceptance Criteria | Expected Test Ballpark |
|---|---|---|---|
| 0 | Reconcile CivicClerk docs and ADRs to the unified spec | `docs/RECONCILIATION.md` exists with verbatim disagreements; v0.1.0-scope ADR queue exists; `docs/MILESTONES.md` exists; `scripts/verify-docs.sh` is wired into CI; placeholder-import gate is wired into CI; no runtime code is introduced. | E2E: 0; integration: 0; unit/script: 2 local checks |
| 1 | CivicClerk runtime foundation | FastAPI package layout exists; runtime pins `civiccore==0.2.0`; CI runs tests, docs verification, and placeholder-import gate; no imports from CivicCore placeholders; docs describe shipped foundation only. | E2E: 0-1; integration: 2-4; unit: 6-10 |
| 2 | Canonical schema and Alembic migrations | CivicClerk schema follows the accepted table ADR; migrations run after CivicCore baseline `civiccore_0001_baseline_v1.py`; foreign keys into CivicCore shared tables only where those tables exist in v0.2.0; idempotency and fresh-install migration tests pass. | E2E: 0; integration: 6-10; unit: 4-8 |
| 3 | Agenda item lifecycle enforcement | Agenda item lifecycle follows `DRAFTED -> SUBMITTED -> DEPT_APPROVED -> LEGAL_REVIEWED -> CLERK_ACCEPTED -> ON_AGENDA -> IN_PACKET -> POSTED -> HEARD -> DISPOSED -> ARCHIVED`; parametrized matrix proves only valid transitions return 2xx; invalid transitions return 4xx and write audit entries. | E2E: 1-2; integration: 8-14; unit: 8-12 |
| 4 | Meeting lifecycle enforcement | Meeting lifecycle follows `SCHEDULED -> NOTICED -> PACKET_POSTED -> IN_PROGRESS -> RECESSED -> ADJOURNED -> TRANSCRIPT_READY -> MINUTES_DRAFTED -> MINUTES_POSTED -> MINUTES_ADOPTED -> MINUTES_SIGNED -> ARCHIVED`; cancelled, emergency/special, statutory-basis, and closed/executive paths are covered by transition tests. | E2E: 1-2; integration: 10-16; unit: 8-12 |
| 5 | Packet assembly and notice compliance | Packet snapshots are versioned; notice deadlines and postings are testable; warning/error states are actionable; statutory-basis handling follows accepted ADRs; no public posting occurs without human approval. | E2E: 2-3; integration: 8-14; unit: 10-16 |
| 6 | Motion / vote / action-item capture | Captured motions and votes are immutable; `PUT`/`PATCH` against captured records returns `409 Conflict`; correction endpoints create rows referencing originals; action items are linked to meeting outcomes. | E2E: 1-2; integration: 8-12; unit: 8-12 |
| 7 | Minutes drafting with sentence citations | AI drafts never auto-adopt or auto-post minutes; every material AI output has sentence-level citations; output without citations is rejected; provenance records model, prompt version, data sources, and human approver. | E2E: 2-3; integration: 8-14; unit: 12-18 |
| 8 | Public meeting calendar / detail / archive | Public pages expose only permitted posted agendas, packets, approved minutes, and archives; anonymous endpoints never leak closed-session content in body, counts, suggestions, or errors; permission-aware archive search is tested for anonymous, under-privileged staff, and permitted staff users. | E2E: 3-5; integration: 10-16; unit: 8-12 |
| 9 | Prompt YAML library and evaluation harness | Prompts live under `prompts/`; policy-bearing prompt strings are not hardcoded in `app/`; prompt versioning and provenance are enforced; eval harness runs before prompt changes; local Ollama happy path passes with outbound network blocked. | E2E: 1-2; integration: 6-10; unit: 10-16 |
| 10 | Connectors / imports for Granicus, Legistar, PrimeGov, NovusAGENDA | Connector/import behavior is local-first; source provenance is recorded; failures show actionable errors; no outbound runtime calls are required in default local profile. | E2E: 2-4; integration: 8-14; unit: 10-16 |
| 11 | Accessibility and browser QA gates | Browser QA evidence exists for desktop and mobile; loading, success, empty, error, and partial states are checked; keyboard navigation, focus states, contrast, and console output are verified. | E2E/browser: 6-10; integration: 2-4; unit: 4-8 |
| 12 | v0.1.0 release | Version surfaces synchronize across package metadata, README files, user manuals, CHANGELOG, landing page, installer metadata if any, generated docs/binaries, GitHub release notes, and tests asserting displayed version; `scripts/verify-docs.sh` passes; release assets and checksums exist where applicable; CivicSuite compatibility matrix PR is opened for `civicclerk v0.1.0` paired with `civiccore==0.2.0`. | E2E: full suite; integration: full suite; unit: full suite |

## Cross-Cutting Definition of Done

Every milestone must satisfy:

- Tests are written before implementation for the milestone's behavior.
- CI is green on the feature branch, including `scripts/verify-docs.sh` and the placeholder-import gate.
- No skipped or `xfail` tests are added.
- Documentation for the milestone is committed.
- CHANGELOG has an `[Unreleased]` entry in Keep a Changelog format matching the suite convention.
- Version surfaces are synchronized explicitly across `pyproject.toml`, `package.json`, `README.md`, `README.txt`, `USER-MANUAL.md`, `CHANGELOG.md`, landing page, and version-asserting tests when those files exist.
- UI work includes desktop and mobile browser QA, accessibility checks, console checks, copy review, and screenshots in `docs/screenshots/`.
- AI work records provenance, validates citations, keeps prompts in YAML, and runs the evaluation harness.
