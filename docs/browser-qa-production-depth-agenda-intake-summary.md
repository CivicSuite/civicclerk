# Production Depth Agenda Intake Browser QA

Generated: 2026-04-28T07:35:09.272Z

## Checks

- Surfaces: landing page (`docs/index.html`) and staff dashboard (`/staff`).
- Viewports: desktop 1440x1100 and mobile 390x1200.
- Required copy: agenda intake, database-backed queue, `/agenda-intake`, and `CIVICCLERK_AGENDA_INTAKE_DB_URL` where applicable.
- Stale copy rejected: `No live database-backed queue is connected yet`.
- Console errors: none.
- Horizontal overflow: none.
- Keyboard focus: visible focus indication checked on first focusable element where present.

## Evidence

| Surface | Viewport | Screenshot | Console | Overflow | Focus |
|---|---|---|---|---|---|
| landing | desktop | docs/browser-qa-production-depth-agenda-intake-landing-desktop.png | 0 messages | no | solid 4px none |
| landing | mobile | docs/browser-qa-production-depth-agenda-intake-landing-mobile.png | 0 messages | no | solid 4px none |
| staff | desktop | docs/browser-qa-production-depth-agenda-intake-staff-desktop.png | 0 messages | no | solid 4px none |
| staff | mobile | docs/browser-qa-production-depth-agenda-intake-staff-mobile.png | 0 messages | no | solid 4px none |

## Result

PASS: desktop and mobile browser QA found no console messages, no horizontal overflow, no stale queue copy, required agenda-intake copy present, and focus evidence captured.
