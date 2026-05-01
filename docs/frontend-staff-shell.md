# CivicClerk React Staff Shell

Status: Sprint 1 implementation slice with live meeting setup and scheduling.

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
- Schedule-edit audit behavior: backend edits are blocked once a meeting reaches
  the in-session lock point, with an actionable replacement-meeting fix path.
- Explicit QA state controls for success, loading, empty, error, and partial
  states.
- Actionable state copy that tells staff or IT what to do next.

## What This Slice Does Not Yet Include

- Replacement of the shipped `/staff` HTML reference shell.
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

- `?page=dashboard|meetings|meeting-detail`
- `?state=success|loading|empty|error|partial`
- `?audit=1`
- `?source=demo` to bypass the live API and render fixed demo data
