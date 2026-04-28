# Production Depth Notice Checklist Browser QA

Generated: 2026-04-28T08:12:19.788Z

## Checks

- Surfaces: landing page (`docs/index.html`) and staff dashboard (`/staff`).
- Viewports: desktop 1440x1100 and mobile 390x1200.
- Required copy: notice checklist, posting-proof, `/meetings/{id}/notice-checklists`, and `CIVICCLERK_NOTICE_CHECKLIST_DB_URL` where applicable.
- Stale copy rejected: `database-backed notice checklist/posting-proof persistence beyond the current runtime slice`.
- Console errors: none.
- Horizontal overflow: none.
- Keyboard focus: visible focus indication checked.

## Evidence

| Surface | Viewport | Screenshot | Console | Overflow | Focus |
|---|---|---|---|---|---|
| landing | desktop | docs/browser-qa-production-depth-notice-checklist-landing-desktop.png | 0 messages | no | solid 4px none |
| landing | mobile | docs/browser-qa-production-depth-notice-checklist-landing-mobile.png | 0 messages | no | solid 4px none |
| staff | desktop | docs/browser-qa-production-depth-notice-checklist-staff-desktop.png | 0 messages | no | solid 4px none |
| staff | mobile | docs/browser-qa-production-depth-notice-checklist-staff-mobile.png | 0 messages | no | solid 4px none |

## Result

PASS: desktop and mobile browser QA found no console messages, no horizontal overflow, no stale notice-checklist deferral, required notice checklist copy present, and focus evidence captured.
