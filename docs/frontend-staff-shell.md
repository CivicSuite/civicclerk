# CivicClerk React Staff Shell

Status: first implementation slice on `feat/react-staff-shell-sprint1`.

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
- Explicit QA state controls for success, loading, empty, error, and partial
  states.
- Actionable state copy that tells staff or IT what to do next.

## What This Slice Does Not Yet Include

- Live API wiring.
- Meeting body CRUD.
- Replacement of the shipped `/staff` HTML reference shell.
- Docker/nginx packaging.
- Installer integration.

## Local Frontend Commands

Run these from `frontend/` after dependencies are installed:

```bash
npm run dev
npm run test
npm run build
```

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
