# React Agenda Intake Browser QA

Slice: `feat/react-agenda-intake-workflow`

Runtime used:

- FastAPI: `http://127.0.0.1:8785`
- Vite: `http://127.0.0.1:5182`
- Temporary stores: `.tmp-browser-qa-agenda/agenda-intake.db`, `.tmp-browser-qa-agenda/meetings.db`, and `.tmp-browser-qa-agenda/bodies.db`

Evidence captured:

- `react-agenda-intake-desktop.png`
- `react-agenda-intake-mobile.png`
- `react-agenda-intake-cdp-loaded.png`
- `react-agenda-intake-submit-success.png`
- `react-agenda-intake-review-success.png`
- `react-agenda-intake-state-loading.png`
- `react-agenda-intake-state-empty.png`
- `react-agenda-intake-state-error.png`
- `react-agenda-intake-state-partial.png`

Checks performed:

- Agenda Intake navigation opened the new React workspace.
- Live queue loaded from `/api/agenda-intake` with pending and ready records.
- Department submission created a live intake record through `POST /api/agenda-intake`.
- Clerk review marked an item ready through `POST /api/agenda-intake/{id}/review`.
- QA state routes rendered loading, empty, error, and partial states for the Agenda Intake workspace.
- Desktop and mobile screenshots were captured with Edge headless.
- CDP console capture reported `badEventCount: 0` while loading, submitting, and reviewing.
- Copy review: empty/error/partial and form error messages include specific retry or fix paths.
