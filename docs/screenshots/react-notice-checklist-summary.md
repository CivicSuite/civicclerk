# React Notice Checklist Browser QA

Captured on 2026-05-01 from `http://127.0.0.1:5174/?source=demo&page=notice`
using the Vite React app.

Evidence files:

- `react-notice-checklist-live-desktop.png` - desktop success state, 1440px wide.
- `react-notice-checklist-live-mobile.png` - mobile success state, 390px wide.
- `react-notice-checklist-blocked.png` - blocked statutory notice record with
  legal-blocker copy and disabled posting-proof action.
- `react-notice-checklist-focus.png` - keyboard tab focus pass.
- `react-notice-checklist-state-loading.png` - loading fixture.
- `react-notice-checklist-state-empty.png` - empty fixture.
- `react-notice-checklist-state-error.png` - error fixture.
- `react-notice-checklist-state-partial.png` - partial fixture.

Checks performed:

- Success state shows the legal gate, computed statutory deadline, basis,
  approver, audit hash, and posting-proof action.
- Blocked state says `notice_deadline_missed`, tells the clerk to reschedule or
  document the lawful emergency basis, and disables posting-proof attachment.
- Desktop and mobile screenshots rendered without layout failure.
- Keyboard tab traversal produced visible focus.
- Console had Vite dev/debug and React DevTools informational messages only; no
  page errors were reported.
