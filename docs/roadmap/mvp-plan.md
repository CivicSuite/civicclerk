# CivicClerk MVP Plan

The first CivicClerk MVP is a vertical slice, not a full Granicus-style
replacement.

Current status after CivicClerk v0.1.17: all four MVP sprint goals below are
API-complete, tested, and represented by live-backed `/staff` cockpit panels.
The runtime foundation, staff workflow HTML reference shell, prompt gates,
release gates, connector import normalization, public archive filtering, the
React public portal, packet export bundles, backup/restore rehearsal,
OIDC staff-token validation, protected staff-auth rehearsal, deployment
preflight, and fresh-install rehearsal helpers are present. The OIDC
browser-session foundation is now shipped: `/staff/login` starts
authorization-code + PKCE sign-in, `/staff/oidc/callback` accepts the provider
callback, CivicClerk issues a signed HttpOnly staff session cookie for
protected staff APIs, `/staff/session` reports the active identity and roles,
and the React dashboard staff-access panel makes the current auth mode,
provider, subject, roles, and sign-in/readiness actions visible to clerks and
IT staff. The remaining production auth work is municipal IdP configuration,
operational hardening, and protected-deployment proof; it is not an unbuilt
OIDC browser-session feature. The first React app slice now exists under
`frontend/`: it translates the CivicSuite mockup into a typed staff shell,
meeting calendar, meeting detail lifecycle ribbon, audit/evidence drawer, and
explicit loading/success/empty/error/partial QA states, and the staff dashboard,
calendar, and detail flow now load live meeting records through `/api/meetings`.
Meeting body CRUD now has a backend API and first React staff dashboard
management surface. Sprint 1 meeting setup now includes live React scheduling
and pre-lock schedule editing backed by `POST /meetings` and
`PATCH /meetings/{id}`. Sprint 2 is now present in React through agenda intake
submit/review, ready-item promotion into canonical agenda lifecycle records
through `POST /agenda-intake/{id}/promote`, and the first Packet Builder
workspace for creating and finalizing packet assembly records from promoted
agenda items. Sprint 3 is now present with a legally explicit Notice Checklist
workspace for statutory deadline review, basis/approval capture, an Official
Notice Record proof summary, posting-proof attachment, legal-blocker copy, and
immutable audit-hash visibility, plus a resident-oriented Public Posting portal for public meeting list/detail/search
over posted agenda, packet, and approved minutes records with restricted-record
non-disclosure guidance. Sprint 4 is now
present with a React Meeting Outcomes workspace for immutable motion capture,
roll-call vote capture, source-linked action items, and append-only correction
guidance plus a React Minutes Draft workspace for citation-gated draft creation,
prompt provenance, human approver capture, and blocked auto-posting visibility.
The first Docker Compose deployment stack is now present with PostgreSQL 17 +
pgvector, Redis 7.2, Ollama, FastAPI, Celery worker/beat, and nginx-served
React. Compose now seeds a Brookfield demo dataset by default so staff can open
the React app against live API-backed data immediately. Unsigned Windows
installer source packaging is now present for the same Docker stack, including
install/repair and daily-start launchers, and the enterprise signing-readiness
contract now verifies SignTool, certificate identity, timestamp URL, and setup
artifact inputs without printing secrets. Remaining MVP work now centers on
municipal IdP deployment proof, real vendor API deployment proof,
city-approved retention/off-host backup proof, and deployment hardening. Signed
installer publication is certificate-gated and not expected during the
developer process. The Docker/PostgreSQL backup and restore
rehearsal for the Compose product path is now present; real deployments still
need an approved retention schedule and off-host storage target. The connector
path now has a local import-sync runner that produces normalized ledgers from
exported agenda-system JSON, plus an optional Docker/Celery Beat schedule for
approved local export-drop ingestion. The first vendor live-sync operational
foundation is also present: proposed source URLs are validated through
CivicCore guards, credentials in URLs are rejected, source/run/failure state
persists in the vendor sync ledger, source health is computed as `healthy`,
`degraded`, or `circuit_open`, and the circuit opens after five consecutive
full-run failures or two post-unpause grace-period failures. The React staff
workspace now surfaces this ledger through a Vendor Sync screen with source
registration, health/circuit status, run-outcome logging, no-network safety
copy, persisted cursor visibility, full-reconciliation cursor reset, and
actionable IT fix guidance. The first guarded vendor-network pull
runner is present for one explicitly enabled source at a time: it refuses
circuit-open sources, revalidates the source URL, reads credentials from a
deployment secret env var, normalizes returned JSON through the existing
connector contract, and records the run outcome in the same circuit-breaker
ledger. The first scheduled vendor-network pull task is also present in Celery
Beat, disabled by default, guarded by both a schedule gate and live-network
gate, and limited to configured approved source IDs with per-source reports.
Remaining live-sync work is deployment proof against real municipal vendor APIs
and operational runbook hardening. The delta-planning, cursor persistence, and
operator reset contract is now present: each
supported connector gets an explicit "changed since" query parameter, sources
persist `last_success_cursor_at`, one-time and scheduled pulls plan from that
cursor, the cursor advances only after a fully successful normalized run, and
IT can clear or move the cursor without a vendor call when a full reconciliation
or replay from an earlier point is required, and each reset reason is preserved
as a `cursor_reset` run-log event.
The reusable City of Brookfield mock-city environment suite is now being added
as shared product infrastructure for the remaining CivicSuite modules:
`scripts/run_mock_city_environment_suite.py` verifies Legistar, Granicus,
PrimeGov, and NovusAGENDA connector contracts without vendor network calls,
labels public-reference versus vendor-gated interfaces honestly, and gives
future modules a repeatable baseline before module-specific assertions are
added. The same suite now validates a Brookfield Entra ID-style municipal OIDC
contract with issuer, audience, authorization-code + PKCE URLs, JWKS shape,
role claims, and staff-token validation without contacting an identity provider
or printing mock secrets, and it now validates a Brookfield
backup-retention/off-host policy contract with seven-year retention, monthly
restore-test cadence, encrypted immutable mock off-host storage, legal-hold
support, and restore-manifest fields without contacting storage providers or
printing secrets. Unsigned Windows install remains expected until an enterprise
code-signing certificate is issued and the secured signing workstation is ready;
installer and docs warnings now name the "Unknown Publisher" / "Windows
protected your PC" first-install experience directly. The pilot-readiness
rollup now separates developer-owned readiness from external proofs for code
signing, municipal IdP deployment, real vendor API access, and city
backup-retention/off-host storage approval.

## Sprint 1

- Meeting body CRUD: backend API plus first React dashboard management surface
  present
- Meeting scheduling/editing: React dashboard scheduling plus detail-screen
  pre-lock schedule edits present
- Meeting calendar: first React implementation present in `frontend/` and wired
  to the live `/api/meetings` list endpoint
- Empty/loading/error/success/partial frontend states: first React reference
  implementation present in `frontend/`
- Browser QA evidence: required before this branch can be committed or pushed

## Sprint 2

- Agenda item intake: first React submit/review workflow present
- Department submitter workflow: first React form present
- Clerk review queue: first React ready/revision queue present
- Packet handoff after ready review: promotion into agenda lifecycle present
- Packet builder: first React meeting assignment, promoted-item selection,
  draft creation, queue review, and finalization workflow present
- Browser QA evidence
- Docs updated

## Sprint 3

- Notice checklist: first React statutory deadline, Official Notice Record,
  basis, approval, posting proof, legal-blocker, and audit-hash workflow present
- Public posted-meeting page: resident-oriented React list, detail, archive
  search, official-record sections, and restricted-record non-disclosure
  guidance present

## Sprint 4

- Motion and vote capture: first React motion/vote/action-item workspace present
- Minutes draft workspace: first React source/citation/provenance workflow present
- Citation model: backend enforcement plus first React visibility present

## Current release bar

- Full docs baseline updated
- CI green
- frontend browser QA evidence
- no skipped tests
- no cloud/runtime telemetry
- no stale version references
