# Changelog

All notable changes to CivicClerk are documented here.

## [Unreleased]

## [0.1.18] - 2026-05-02

### Changed
- CivicClerk now targets the published `civiccore` v0.20.0 release wheel and
  consumes shared CivicCore startup config placeholder detection for OIDC staff
  auth readiness checks, keeping operator-facing misconfiguration guidance
  consistent across CivicSuite modules.

### Added
- Added a staff-auth regression test proving CivicClerk uses the shared
  `civiccore.security.looks_like_placeholder()` helper for OIDC placeholder
  detection instead of carrying a module-local copy.

## [0.1.17] - 2026-05-02

### Changed
- CivicClerk now targets the published `civiccore` v0.19.0 release wheel and consumes shared CivicCore vendor-delta request planning plus reusable mock-city vendor, IdP, and backup-retention contracts instead of carrying local copies.
- `civicclerk.vendor_delta` is now a compatibility export for `civiccore.connectors`, preserving the existing CivicClerk import path while moving the reusable delta contract to CivicCore for the rest of CivicSuite.
- `civicclerk.mock_city_environment` now adapts the shared CivicCore mock-city contracts for CivicClerk-specific OIDC validation, so future modules can reuse the same contracts while each module keeps its own auth audience, client, and redirect proof.

## [0.1.16] - 2026-05-02

### Added
- `scripts/run_mock_city_environment_suite.py` now includes a reusable
  Brookfield Entra ID-style municipal OIDC contract with issuer, audience,
  authorization-code + PKCE URLs, JWKS shape, role claims, and staff-token
  validation so future modules can reuse protected-auth proof without contacting
  an identity provider or reporting mock secrets.
- `scripts/check_pilot_readiness.py` now includes the mock municipal IdP
  contract suite in its developer-owned readiness rollup, so pilot handoff
  reports cannot pass on vendor contracts alone.
- `scripts/run_mock_city_environment_suite.py` now includes a reusable
  Brookfield backup-retention/off-host policy contract with seven-year
  retention, monthly restore-test cadence, encrypted immutable mock off-host
  storage, legal-hold support, and restore-manifest fields so future modules can
  reuse backup-readiness proof without contacting storage providers.
- `scripts/check_pilot_readiness.py` now includes that backup-retention/off-host
  contract suite in developer-owned readiness while keeping real city retention
  approval as an external proof slot.

## [0.1.15] - 2026-05-02

### Added
- `civicclerk.mock_city_environment` and
  `scripts/run_mock_city_environment_suite.py` add a reusable no-network City of
  Brookfield test suite for Legistar, Granicus, PrimeGov, and NovusAGENDA
  contracts so future CivicSuite modules can reuse the same municipal interface
  evidence before adding module-specific assertions.
- `civicclerk.vendor_network_sync` and `scripts/run_vendor_live_sync.py` add the
  first explicitly enabled vendor-network pull runner: approved source lookup,
  circuit-open refusal, URL revalidation, credential loading from deployment
  secret env vars, JSON normalization through the existing connector contract,
  secret-free reporting, and run outcome persistence in the vendor sync ledger.
- `civicclerk.worker.vendor_network_sync` adds the first scheduled
  vendor-network pull task for Celery Beat. It stays disabled by default,
  requires both the schedule gate and live-network gate, runs only configured
  approved source IDs, writes per-source reports, and reuses the same
  circuit-breaker ledger as the one-shot runner.
- `civicclerk.vendor_delta` adds connector-specific delta request planning for
  Legistar, Granicus, PrimeGov, and NovusAGENDA so scheduled pulls have a
  tested "changed since" URL contract before cursor persistence is wired in.
- Vendor-network sync sources now persist `last_success_cursor_at`, plan
  one-shot and scheduled pulls from that cursor, and advance it only after a
  fully successful normalized pull so failed or partial vendor runs do not skip
  records.
- Vendor Sync now exposes that cursor in the React staff workspace and adds a
  no-network cursor reset endpoint/workflow so IT can force a full source
  reconciliation with an operator reason before the next controlled pull; each
  reset is persisted as a `cursor_reset` run-log event and returned as
  `reset_event` by the API.
- `scripts/check_pilot_readiness.py` adds a no-network pilot handoff rollup
  that proves developer-owned readiness while listing code-signing certificate,
  municipal IdP, real vendor API, and city backup-retention proof as explicit
  external dependencies.

### Changed
- CivicClerk now targets the published `civiccore` v0.18.1 release wheel and
  consumes the shared `civiccore.connectors` live-sync circuit primitives for
  vendor source health, run-result transitions, and operator-facing
  healthy/degraded/circuit-open copy.
- The vendor sync ledger, source validation, delta cursor handling,
  no-network cursor reset, and module-specific persistence stay in
  CivicClerk; the reusable circuit-breaker contract now lives in CivicCore so
  the next CivicSuite modules can adopt the same behavior instead of cloning
  it.
- Release docs, install rehearsal paths, health-check examples, and build
  artifact checks now identify CivicClerk v0.1.15 paired with CivicCore
  v0.18.1.
- Windows installer packaging and docs now explicitly warn that unsigned setup
  packages can trigger "Unknown Publisher" or "Windows protected your PC" until
  CivicSuite has an issued code-signing certificate and secured signing
  workstation; operators are told to continue only from a trusted release
  source or verified IT-built handoff.

## [0.1.14] - 2026-05-02

### Added
- React staff workspace now includes a Vendor Sync screen that reads
  `/api/vendor-live-sync/sources`, shows healthy/degraded/circuit-open source
  state, registers approved no-network sources, records run outcomes, and gives
  IT actionable fix copy before scheduled vendor pulls are enabled.
- Vendor live-sync operator state now persists: `civicclerk.vendor_sync_persistence`
  adds durable source, run-log, and failure records plus
  `/vendor-live-sync/sources` and `/vendor-live-sync/sources/{id}/run-log`
  endpoints that validate proposed sources and record run outcomes without
  contacting vendor networks. `CIVICCLERK_VENDOR_SYNC_DB_URL` controls the
  ledger store.
- Vendor live-sync readiness now has a bounded operational foundation:
  `civicclerk.vendor_live_sync` validates proposed source URLs through
  CivicCore guards, rejects credentials in URLs, computes
  `healthy`/`degraded`/`circuit_open`, opens the circuit after five consecutive
  full-run failures or two grace-period failures, and exposes actionable
  operator fix text. `scripts/check_vendor_live_sync_readiness.py` previews that
  contract without contacting vendor networks.

### Fixed
- The MVP plan now clearly states that OIDC browser-session support is shipped
  and that the remaining production auth work is municipal IdP configuration,
  operational hardening, and protected-deployment proof.
- Frontend staff workspace tests now wait for async rendered headings in the
  notice checklist and meeting-detail flows, removing React `act(...)` warning
  noise from the test lane without changing product behavior.

## [0.1.13] - 2026-05-01

### Changed
- CivicClerk now targets the published `civiccore` v0.17.0 release wheel so the
  Clerk product stays aligned with the shared persisted audit primitives already
  released from CivicCore and adopted by CivicRecords AI.
- Release, install, handoff, readiness, and browser-QA version surfaces now
  identify CivicClerk v0.1.13 and expect CivicCore v0.17.0 in `/health`.
- The root product status copy now states that the integrated React clerk
  console and public portal are present for Docker product rehearsal instead of
  describing them as future work.

## [0.1.12] - 2026-05-01

### Added
- Enterprise installer signing readiness is now explicit: the Windows installer
  build helper can optionally invoke SignTool when `CIVICCLERK_SIGN_INSTALLER`
  is enabled, and `scripts/check_enterprise_installer_signing.py` verifies the
  artifact, SignTool path, certificate identity, and timestamp URL without
  printing secrets.
- Scheduled local connector import sync is now available through Celery Beat:
  `CIVICCLERK_CONNECTOR_SYNC_ENABLED=true` makes the worker periodically
  normalize approved local Granicus, Legistar, PrimeGov, or NovusAGENDA JSON
  export drops from `/data/connector-imports`, write a provenance ledger under
  `/data/exports`, and keep vendor network calls disabled.
- `scripts/check_docker_backup_restore_rehearsal.py` plus PowerShell and Bash
  wrappers now rehearse the Docker Compose PostgreSQL backup path with
  `pg_dump`, restore into a temporary database with `pg_restore`, verify
  restored application tables, write `civicclerk-docker-backup-manifest.json`, and
  avoid overwriting the source database.
- Frontend tests now add focused coverage for the legally sensitive Notice
  Checklist proof obligations, append-only/source-linked Meeting Outcomes
  evidence, and citation-blocked Minutes Draft creation path.
- Staff auth now supports `CIVICCLERK_STAFF_AUTH_MODE=oidc` for municipal
  identity-provider access tokens, including issuer/audience/JWKS validation,
  role-claim enforcement, `/staff/session` identity reporting, and
  `/staff/auth-readiness` session/write probes.
- OIDC staff auth now includes the first browser sign-in/session foundation:
  `/staff/login` starts authorization-code + PKCE sign-in,
  `/staff/oidc/callback` validates the returned token and issues a signed
  HttpOnly CivicClerk session cookie, `/staff/logout` clears it, and protected
  staff APIs accept that browser session without storing raw OIDC tokens in the
  browser.
- The React dashboard now includes a staff access panel that reads
  `/staff/session`, shows the current auth mode, signed-in subject, provider,
  roles, and OIDC browser-session method, and gives clerks/IT direct
  `/staff/login`, `/staff/logout`, and `/staff/auth-readiness` paths with
  actionable sign-in failure copy.
- Docker Compose now forwards the OIDC browser-login, bearer-token, and
  trusted-header staff auth environment variables from `.env` into the API,
  worker, and beat services so protected pilot profiles behave like the
  documented `/staff/auth-readiness` contract.
- `frontend/` now contains the first CivicClerk React/Vite staff workspace
  slice, adapted from the CivicSuite mockup into production TypeScript rather
  than copied as a browser-global prototype.
- The React staff workspace includes a CivicSuite shell, Clerk meeting calendar,
  meeting detail lifecycle ribbon, audit/evidence drawer, and explicit
  loading, success, empty, error, and partial QA states with actionable copy.
- The React staff workspace now reads the live `/api/meetings` list for
  dashboard metrics, calendar cards, and meeting detail selection, while
  retaining `?source=demo` for deterministic browser QA captures.
- The FastAPI app now exposes `GET /meetings` so the React staff calendar can
  load scheduled meetings in calendar order without depending on fixture data.
- The FastAPI app now exposes meeting body CRUD at `/meeting-bodies`, backed by
  the canonical `meeting_bodies` table; deletes are implemented as
  deactivation so meeting history is not destroyed.
- The React staff dashboard now includes a live Meeting Bodies panel for
  creating, renaming, and deactivating boards and commissions.
- The FastAPI app now accepts `meeting_body_id` and `location` on meeting
  records, exposes `PATCH /meetings/{id}` for pre-lock schedule edits, and
  writes an audit entry for changed scheduling fields.
- The React staff dashboard now includes a live Schedule Meeting panel, and
  meeting detail now includes an Edit Schedule panel for changing title, body,
  type, time, and location before the meeting reaches an in-session lock point.
- Meeting scheduling APIs now reject nonexistent or inactive meeting body ids
  with actionable 422/409 responses so raw API callers cannot bypass the React
  body picker and attach a legal meeting record to invalid ownership metadata.
- The React staff workspace now includes the first Agenda Intake workflow:
  department submission, live clerk review queue, readiness metrics, ready/revision
  review actions, audit-hash visibility, and no-dead-end state copy backed by
  `/api/agenda-intake`.
- Ready agenda intake records can now be promoted into canonical agenda item
  lifecycle work through `POST /agenda-intake/{id}/promote`; the promotion
  stores the generated agenda item id, promotion timestamp, and audit hash on
  the intake record, advances the agenda item to `CLERK_ACCEPTED`, and returns
  the next packet-assembly step for staff.
- The React Agenda Intake workspace now includes a "Promote to agenda" action
  for ready records, blocks premature promotion with an actionable fix path, and
  shows the resulting agenda lifecycle id/status after promotion.
- The React staff workspace now includes the first Packet Builder workflow:
  meeting selection, promoted agenda item checkboxes, packet draft creation,
  packet queue review, per-meeting queue loading, and packet finalization backed
  by the live packet assembly APIs.
- The React staff workspace now includes the first Notice Checklist workflow:
  meeting selection, statutory deadline preview, notice-type/minimum-hours
  capture, statutory basis and human approval fields, posting-proof attachment,
  immutable audit-hash visibility, and explicit legal-blocker copy backed by
  the live notice checklist APIs.
- Notice Checklist error and blocked states now explain when the statutory
  deadline has passed, why posting proof cannot be attached, and what the clerk
  must do next before treating a meeting as lawfully noticed.
- Notice Checklist now shows a legal readiness proof chain for packet
  finalization, statutory deadline, statutory basis, human approval, posting
  proof, and immutable audit hash so clerks can see exactly which obligation is
  still missing.
- The React dashboard now includes a Clerk Meeting Runbook that reads the
  meeting, agenda, packet, notice, outcomes, minutes, and public posting data
  already loaded by the staff app, shows ready/warning/blocked lifecycle gates,
  highlights legal notice blockers, and opens the next safe workspace for the
  selected meeting.
- The nginx-served product path now explicitly routes `/staff` and `/staff/...`
  to the React staff dashboard, matching the documented installer shortcut
  instead of relying on the generic SPA fallback, while preserving backend
  proxy access to `/staff/auth-readiness` and `/staff/session`.
- The React Notice Checklist now includes an Official Notice Record summary
  that tells clerks whether a meeting may proceed, is blocked, or is still
  missing proof, with deadline, statutory basis, human approval, posting proof,
  and immutable audit-hash fields visible in one place.

### Changed
- The README and user manual now describe CivicClerk as an end-to-end
  React/Docker local product rehearsal with all four MVP workflow surfaces
  present, OIDC staff-token validation and browser-session foundation
  available, React staff access/session status visible on the dashboard, and
  the remaining deployment gaps narrowed to a signed installer, live sync,
  city-approved backup retention/off-host storage, and deployment hardening.
- The React staff workspace now includes a resident-oriented Public Posting
  portal: public meeting list/detail/search over the public archive APIs,
  separate official agenda/packet/approved-minutes sections, missing-record
  guidance, and copy that avoids implying restricted-session existence when
  records are absent.
- The nginx-served product path now opens that React Public Posting portal
  directly from `/public`, while public API calls stay behind `/api/public/...`.
- `scripts/run_connector_import_sync.py` now turns local Granicus, Legistar,
  PrimeGov, and NovusAGENDA export JSON into a repeatable normalized import
  ledger without contacting vendor systems.
- The React staff workspace now includes the first Meeting Outcomes workflow:
  meeting selection, motion capture, roll-call vote capture, action-item
  creation tied to source motions, outcome ledger review, and append-only
  correction guidance backed by the live motion/vote/action-item APIs.
- The React staff workspace now includes the first Minutes Draft workflow:
  meeting selection, existing draft review, explicit source material entry,
  sentence-level citation capture, model/prompt provenance, human approver
  capture, and a visible blocked public-posting gate backed by the live
  minutes draft APIs.
- The first Docker Compose stack now provides PostgreSQL 17 + pgvector, Redis
  7.2, Ollama, FastAPI, Celery worker, Celery Beat, and nginx-served React
  services for local product rehearsal without claiming installer completion.
- Docker Compose now enables `CIVICCLERK_DEMO_SEED=1` by default, seeding a
  Brookfield rehearsal dataset with meeting bodies, lifecycle-diverse meetings,
  promoted agenda intake, finalized packet assembly, posted notice proof,
  captured outcomes, citation-gated minutes, and a public archive record.
- CivicClerk now includes unsigned Windows installer source packaging under
  `installer/windows/`, with Inno Setup build wiring, Docker Desktop
  prerequisite checks, Install or Repair and Start launchers, and SmartScreen
  guidance.
- `install.ps1` now prepares `.env` from `docs/examples/docker.env.example`,
  generates a local PostgreSQL password, starts the Docker Compose stack,
  waits for API/frontend health, and opens the seeded React staff app for
  single-workstation rehearsal.
- Already-promoted agenda intake rows now lock review actions and point staff
  forward to Packet Builder instead of allowing duplicate readiness work.
- Frontend unit tests now cover shell rendering, meeting calendar navigation,
  meeting scheduling, meeting schedule editing, agenda intake submit/review/promote,
  packet draft creation/finalization, notice compliance/proof attachment,
  statutory-deadline blocking, public posted-meeting list/detail/search,
  meeting outcome motion/vote/action-item capture,
  citation-gated minutes draft creation and blocked auto-posting,
  required error/empty state copy, and audit drawer toggling.
- CI and `scripts/verify-release.sh` now install, audit, build, and test the
  `frontend/` package so the React app cannot drift outside the release gate.
- The frontend dev proxy now defaults to the documented CivicClerk FastAPI
  port `8776` and can be redirected with `CIVICCLERK_API_PROXY_TARGET`.
- `/staff` now opens with a product cockpit that summarizes the clerk desk,
  visible workflow actions, no-dead-end state promise, and go-live checks before
  staff drill into the live API workflow forms.
- The `/staff` product cockpit now reads the live agenda intake queue and
  reports ready, pending, and needs-revision counts when intake records exist.
- The `/staff` Agenda Intake panel now renders live intake queue rows instead
  of sample data, including escaped user-submitted titles and actionable empty
  or unavailable-store rows.
- The `/staff` Packet Assembly panel now renders recent live packet assembly
  records instead of sample data, including escaped packet titles and actionable
  empty or unavailable-store rows.
- The `/staff` Notice Checklist panel now renders recent live notice checklist
  records instead of sample data, including posting-proof status plus actionable
  empty or unavailable-store rows.
- The `/staff` Meeting Outcomes panel now renders recent live motion-centered
  outcome rows instead of sample data, including vote/action status and
  actionable empty rows.
- The `/staff` Minutes Draft panel now renders recent live citation-gated draft
  rows instead of sample data, including human-review next steps and actionable
  empty rows.
- `scripts/check_connector_sync_readiness.py` now verifies the supported
  Granicus, Legistar, PrimeGov, and NovusAGENDA local payload contracts without
  outbound network calls before future scheduled live-sync work.
- `scripts/check_installer_readiness.py` now verifies release artifacts,
  checksums, and release handoff bundle contents as the first installer input
  contract without claiming CivicClerk ships an installer yet.
- `scripts/check_protected_deployment_smoke.py` now consumes a completed
  deployment env profile, runs strict readiness, executes the readiness-provided
  protected session/write probes, and redacts bearer tokens in output.
- `docs/examples/deployment.env.example` now gives operators a copy-editable
  deployment profile for protected auth, persistent stores, packet export root,
  and release artifact preflight paths.
- `scripts/check_deployment_readiness.py` now supports `--env-file` so CI or IT
  can validate a deployment profile without hand-exporting each environment
  variable first.
- `scripts/check_backup_restore_rehearsal.py` now seeds the SQLite-backed
  agenda intake, agenda item, meeting, packet assembly, and notice checklist
  stores, copies them with packet export evidence into a backup directory,
  restores them to a separate directory, and verifies the restored records can
  be reopened through CivicClerk repositories.
- `scripts/start_backup_restore_rehearsal.ps1` and
  `scripts/start_backup_restore_rehearsal.sh` now provide repeatable
  Windows-first and Bash operator wrappers for the backup/restore rehearsal,
  including print-only plans and actionable failure guidance.
- `scripts/check_deployment_readiness.py` now prints a non-mutating deployment
  preflight for auth posture, persistent-store env vars, packet export root,
  release artifacts, documentation gate files, and trusted-header proxy handoff.
- `scripts/build_release_handoff_bundle.sh` now mirrors the PowerShell release
  handoff bundle helper for Linux, macOS, and Git Bash operators.
- `scripts/build_release_handoff_bundle.ps1` now prints and can create a
  non-installer release handoff zip containing the built artifacts, checksums,
  current docs, proxy reference, and install rehearsal helpers.
- `/public` now renders the first resident-facing public portal shell over the
  existing public calendar, public detail, and anonymous archive search APIs,
  with actionable loading, empty, error, and search states.
- `scripts/start_fresh_install_rehearsal.ps1` now prints and can execute the
  documented Windows-first fresh-machine wheel install plus `/health`,
  `/staff/auth-readiness`, and `/staff` smoke checks from an isolated
  `.fresh-install-rehearsal` virtual environment.
- `scripts/start_fresh_install_rehearsal.sh` now prints and can execute the
  same fresh-machine wheel install and first-run smoke checks from Bash on
  Linux, macOS, or Git Bash.
- `docs/examples/trusted-header-nginx.conf` now ships the first real trusted-header
  reverse-proxy reference bridge for CivicClerk staff auth handoff.
- `scripts/start_protected_demo_rehearsal.ps1` now prints and can launch a
  repeatable Windows PowerShell trusted-header demo profile for CivicClerk plus
  the loopback-only helper proxy.
- `scripts/start_protected_demo_rehearsal.sh` now prints and can launch the
  same trusted-header demo profile for Bash-based rehearsals on Linux, macOS,
  and Git Bash.
- Trusted-header `/staff/auth-readiness` responses now include a structured
  `local_proxy_rehearsal` contract with loopback-only helper command, env vars,
  injected headers, steps, and warnings for `scripts/local_trusted_header_proxy.py`.

### Changed
- Release handoff bundles now include the connector sync readiness helper.
- Release handoff bundles now include the installer-readiness helper.
- Release handoff bundles now include the deployment env profile example and
  protected deployment smoke helper.
- `scripts/start_backup_restore_rehearsal.sh` now supports
  `CIVICCLERK_REHEARSAL_PYTHON` and performs an actionable dependency preflight
  before executing the backup/restore rehearsal from Bash.
- Fresh-install docs now call out the Python `venv` prerequisite for Bash-based
  Linux rehearsals, and the roadmap now labels the release bar as current
  instead of the historical v0.1.0 target.
- The `/staff` auth panel now renders the trusted-header local proxy rehearsal
  guidance directly so operators can follow a safe loopback rehearsal path
  without reading raw JSON output.
- Trusted-header `/staff/auth-readiness` responses now include a structured
  `reverse_proxy_reference` block that points operators to the shipped nginx
  bridge example before they trust live staff traffic.

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
- `/staff/auth-readiness` and the `/staff` auth panel now expose concrete
  protected-session and protected-write probes for bearer and trusted-header
  deployment checks instead of leaving operators with env-var reminders alone.

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
- The `/staff` workflow shell disclosed local open, bearer-protected, and
  trusted-header staff modes, and at that point explained that first-party OIDC
  login was still future work rather than pretending the proxy bridge was an
  IdP flow.
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
