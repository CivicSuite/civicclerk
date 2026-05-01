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
agenda items. Remaining MVP work now centers on Sprint 3 notice/public posting
surfaces, Sprint 4 outcome/minutes surfaces, standing up the Docker Compose
deployment stack, actual installer packaging beyond the non-installer release
handoff bundle, the finished public portal, and live sync/deployment hardening.

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

- Notice checklist
- Public posted-meeting page

## Sprint 4

- Motion and vote capture
- Minutes draft workspace
- Citation model

## Current release bar

- Full docs baseline updated
- CI green
- frontend browser QA evidence
- no skipped tests
- no cloud/runtime telemetry
- no stale version references
