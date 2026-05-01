# React Meeting API Wiring Browser QA

Reviewed: 2026-04-30

Frontend target: `http://127.0.0.1:5178`
Backend target: `http://127.0.0.1:8781`

## Rendered States

- Live dashboard: `docs/screenshots/react-meeting-api-wiring-dashboard-live-desktop.png`
- Live meeting calendar: `docs/screenshots/react-meeting-api-wiring-calendar-live-desktop.png`
- Live meeting detail with audit drawer: `docs/screenshots/react-meeting-api-wiring-detail-live-audit-desktop.png`
- Live mobile meeting detail with audit drawer: `docs/screenshots/react-meeting-api-wiring-detail-live-audit-mobile.png`
- Loading state: `docs/screenshots/react-meeting-api-wiring-loading-desktop.png`
- Empty state: `docs/screenshots/react-meeting-api-wiring-empty-desktop.png`
- Error state: `docs/screenshots/react-meeting-api-wiring-error-desktop.png`
- Partial install state: `docs/screenshots/react-meeting-api-wiring-partial-desktop.png`

## QA Notes

- Live API path checked through Vite proxy: `GET /api/meetings` returned two
  seeded meetings from the FastAPI process.
- Desktop viewport checked at 1440x1100.
- Mobile viewport checked at 390x1200.
- Loading, success, empty, error, and partial states were opened through direct
  QA URLs.
- Error copy tells IT to confirm the backend is running, verify staff auth mode,
  and retry.
- Keyboard/focus evidence: after tabbing through the dashboard, focus landed on
  the native search button with visible browser outline.
- Console evidence through Edge CDP: dashboard, meeting calendar, meeting
  detail with audit drawer, and forced error state all reported `console: clean`.
- Copy evidence through Edge CDP confirmed live API wording, meeting count,
  seeded meeting titles, and actionable error recovery text.
