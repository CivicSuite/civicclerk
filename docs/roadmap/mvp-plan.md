# CivicClerk MVP Plan

The first CivicClerk MVP is a vertical slice, not a full Granicus-style
replacement.

Current status after CivicClerk v0.1.11: all four MVP sprint goals below are
API-complete, tested, and represented by live-backed `/staff` cockpit panels.
The runtime foundation, staff workflow HTML reference shell, prompt gates,
release gates, connector import normalization, public archive filtering, the
first public portal shell, packet export bundles, backup/restore rehearsal,
protected staff-auth rehearsal, deployment preflight, and fresh-install
rehearsal helpers are present. The first React app slice now exists under
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
workspace for statutory deadline review, basis/approval capture, posting-proof
attachment, legal-blocker copy, and immutable audit-hash visibility, plus a
resident-oriented Public Posting portal for public meeting list/detail/search
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
install/repair and daily-start launchers. Remaining MVP work now centers on a
signed/enterprise installer release artifact, live sync/deployment hardening,
and routing the legacy HTML `/public` shell to the React portal.

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

- Notice checklist: first React statutory deadline, basis, approval, posting
  proof, legal-blocker, and audit-hash workflow present
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
