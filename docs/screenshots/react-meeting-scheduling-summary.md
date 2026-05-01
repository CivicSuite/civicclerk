# React Meeting Scheduling Browser QA

Slice: `feat/react-meeting-scheduling-flow`

Runtime used:

- FastAPI: `http://127.0.0.1:8784`
- Vite: `http://127.0.0.1:5181`
- Temporary stores: `.tmp-browser-qa-scheduling/meetings.db` and `.tmp-browser-qa-scheduling/bodies.db`

Evidence captured:

- `react-meeting-scheduling-dashboard-desktop.png`
- `react-meeting-scheduling-dashboard-mobile.png`
- `react-meeting-scheduling-calendar-desktop.png`
- `react-meeting-scheduling-create-desktop.png`
- `react-meeting-scheduling-detail-edit-desktop.png`
- `react-meeting-scheduling-edit-saved-desktop.png`
- `react-meeting-scheduling-keyboard-focus.png`
- `react-meeting-scheduling-state-success.png`
- `react-meeting-scheduling-state-loading.png`
- `react-meeting-scheduling-state-empty.png`
- `react-meeting-scheduling-state-error.png`
- `react-meeting-scheduling-state-partial.png`

Checks performed:

- Live dashboard loaded from `/api/meetings` and `/api/meeting-bodies`.
- Schedule Meeting form created a live Planning Commission meeting through `POST /api/meetings`.
- Meeting detail Edit Schedule form updated a live meeting through `PATCH /api/meetings/{id}`.
- The edit confirmation remains visible after the parent meeting record refreshes.
- QA state routes rendered success, loading, empty, error, and partial states.
- Mobile-width screenshot was captured with Edge headless at `390x900`; desktop evidence was captured through the in-app browser plus Edge headless for the calendar.
- Browser console checks reported `0` warning/error entries during dashboard load, create, edit, focus, and QA-state captures.
- Copy review: empty/error/partial states include explicit fix paths; schedule create/edit errors tell staff to check API/auth or use a replacement meeting after lock.
