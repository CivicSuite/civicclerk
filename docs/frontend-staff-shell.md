# CivicClerk React Staff Shell

Status: Sprint 3 implementation slice with live agenda intake promotion,
packet builder draft/finalize workflow, legally explicit notice checklist work,
and first public posted-meeting workspace.

The `frontend/` package is the start of the production React app that will
replace the HTML reference shell at `/staff`. It is adapted from the CivicSuite
mockup direction, but implemented as typed React/Vite code rather than as the
mockup's browser-global JSX bundle.

## What This Slice Includes

- CivicSuite staff shell with Brookfield branding, left navigation, surface
  switcher, search affordance, and partial-install disclosure.
- CivicClerk dashboard with priority work, meeting metrics, and clear clerk
  next actions.
- Meeting calendar for Sprint 1 navigation.
- Meeting detail workspace with the eight-stage lifecycle ribbon.
- Right-side audit/evidence drawer per meeting object.
- Live `/api/meetings` list loading for dashboard metrics, calendar cards, and
  detail selection, with a `?source=demo` fallback for deterministic QA states.
- Live `/api/meeting-bodies` management on the dashboard so clerks can create,
  rename, and deactivate boards or commissions before scheduling meetings.
- Live meeting scheduling on the dashboard, backed by `POST /api/meetings`.
- Live pre-lock meeting schedule editing on detail screens, backed by
  `PATCH /api/meetings/{id}` for title, body, type, start time, and location.
- Meeting body integrity checks so raw API callers receive actionable errors
  when schedule create/update references a nonexistent or inactive body.
- Schedule-edit audit behavior: backend edits are blocked once a meeting reaches
  the in-session lock point, with an actionable replacement-meeting fix path.
- First Sprint 2 Agenda Intake workflow: department submission, live queue,
  clerk ready/revision review actions, readiness metrics, and audit-hash cues
  backed by `/api/agenda-intake`.
- Ready agenda intake handoff into canonical agenda lifecycle work, backed by
  `POST /api/agenda-intake/{id}/promote`, with the generated agenda item id,
  `CLERK_ACCEPTED` status, promotion audit hash, and next packet-assembly step
  visible to staff.
- First Packet Builder workflow: staff can choose a meeting, select promoted
  agenda items, create a packet assembly draft through
  `POST /api/meetings/{id}/packet-assemblies`, review packet queue status, and
  finalize a draft through `POST /api/packet-assemblies/{id}/finalize`.
- Packet queues are loaded per selected meeting so staff do not accidentally
  finalize a packet from the wrong meeting context.
- First Notice Checklist workflow: staff can choose a meeting, see the computed
  statutory notice deadline, record notice type/minimum hours/posting time,
  enter the statutory basis and human approver, run the live
  `POST /api/meetings/{id}/notice-checklists` compliance check, and attach
  posting proof through `POST /api/notice-checklists/{id}/posting-proof` only
  after the checklist passes.
- Notice Checklist legal-blocker states plainly explain when the statutory
  deadline has passed, why posting proof is disabled, and that the clerk must
  reschedule or document a lawful emergency/special basis before proceeding.
- First Public Posting workflow: staff can open a resident-safe public record
  view that reads `/api/public/meetings`, `/api/public/meetings/{id}`, and
  `/api/public/archive/search`, shows posted agenda, packet, and approved
  minutes text, and avoids implying closed-session existence when records are
  missing.
- Explicit QA state controls for success, loading, empty, error, and partial
  states.
- Actionable state copy that tells staff or IT what to do next.

## What This Slice Does Not Yet Include

- Replacement of the shipped `/staff` HTML reference shell.
- Motion/vote capture and minutes draft React workspaces.
- Docker/nginx packaging.
- Installer integration.

## Local Frontend Commands

Run these from `frontend/`:

```bash
npm ci
npm audit --audit-level=moderate
npm run dev
npm run test
npm run build
```

The Vite dev proxy sends `/api/*` to `http://127.0.0.1:8776` by default so it
matches the documented Windows-first CivicClerk app command. Set
`CIVICCLERK_API_PROXY_TARGET=http://host:port` before `npm run dev` when the
FastAPI app is listening somewhere else.

Before any commit that touches this frontend, capture browser evidence for:

- success, loading, empty, error, and partial states
- desktop and mobile viewports
- keyboard navigation and visible focus
- browser console
- copy review for every user-visible warning, error, and empty state

For direct QA capture, the app accepts these query parameters:

- `?page=dashboard|meetings|meeting-detail|agenda|packet|notice|public`
- `?state=success|loading|empty|error|partial`
- `?audit=1`
- `?source=demo` to bypass the live API and render fixed demo data
