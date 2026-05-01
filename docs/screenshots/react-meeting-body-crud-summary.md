# React Meeting Body CRUD Browser QA

Reviewed: 2026-04-30

Frontend target: `http://127.0.0.1:5180`
Backend target: `http://127.0.0.1:8782`

## Rendered States

- Live dashboard with meeting body management: `docs/screenshots/react-meeting-body-crud-dashboard-desktop.png`
- Live mobile dashboard with meeting body management: `docs/screenshots/react-meeting-body-crud-dashboard-mobile.png`

## QA Notes

- Live API path checked through Vite proxy: `GET /api/meeting-bodies` returned seeded City Council and Planning Commission rows.
- Browser interaction evidence through Edge CDP confirmed the Meeting Bodies panel rendered, create succeeded, deactivate succeeded, and console issues were `0`.
- Unit-level browser tests cover create, rename, and deactivate flows with actionable success/failure copy.
- Desktop viewport checked at 1440x1300.
- Mobile viewport checked at 390x1400.
