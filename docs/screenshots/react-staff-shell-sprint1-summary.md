# React Staff Shell Sprint 1 Browser QA

Reviewed: 2026-04-30

Target: `http://127.0.0.1:5177`

## Rendered States

- Success dashboard: `docs/screenshots/react-staff-shell-sprint1-dashboard-desktop.png`
- Success meeting calendar: `docs/screenshots/react-staff-shell-sprint1-calendar-desktop.png`
- Success meeting detail with audit drawer: `docs/screenshots/react-staff-shell-sprint1-detail-audit-desktop.png`
- Loading state: `docs/screenshots/react-staff-shell-sprint1-loading-desktop.png`
- Empty state: `docs/screenshots/react-staff-shell-sprint1-empty-desktop.png`
- Error state: `docs/screenshots/react-staff-shell-sprint1-error-desktop.png`
- Partial install state: `docs/screenshots/react-staff-shell-sprint1-partial-desktop.png`
- Mobile meeting detail with audit drawer: `docs/screenshots/react-staff-shell-sprint1-detail-audit-mobile.png`

## QA Notes

- Desktop viewport checked at 1440x1000.
- Mobile viewport checked at 390x900.
- Loading, success, empty, error, and partial states were opened through direct
  QA URLs.
- Error, empty, and partial copy gives the user a next step rather than a dead
  end.
- Keyboard/focus pass: controls are native buttons, links are not used for
  actions, and focus-visible inherits browser focus rings where custom focus is
  not required.
- Contrast pass: navy/gold/cream palette keeps primary text on light surfaces
  and white text on navy surfaces.
- Console check via Edge CDP on
  `/?page=meeting-detail&state=error&audit=1`: `console_events=3`,
  `errors_or_exceptions=0`.
