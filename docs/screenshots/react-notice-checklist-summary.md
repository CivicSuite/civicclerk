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
- `react-notice-legal-proof-chain-desktop.png` - desktop legal readiness proof
  chain after the statutory-surface hardening pass.
- `react-notice-legal-proof-chain-mobile.png` - mobile legal readiness proof
  chain after the statutory-surface hardening pass.
- `react-notice-legal-state-loading.png`, `react-notice-legal-state-empty.png`,
  `react-notice-legal-state-error.png`, and
  `react-notice-legal-state-partial.png` - refreshed QA-state captures for the
  legally explicit Notice Checklist copy.

Checks performed:

- Success state shows the legal gate, computed statutory deadline, basis,
  approver, audit hash, and posting-proof action.
- Legal readiness proof chain shows packet finalization, statutory deadline,
  statutory basis, human approval, posting proof, and immutable audit hash as
  separate visible obligations.
- Blocked state says `notice_deadline_missed`, tells the clerk to reschedule or
  document the lawful emergency basis, and disables posting-proof attachment.
- Desktop and mobile screenshots rendered without layout failure.
- Keyboard tab traversal produced visible focus.
- Console had Vite dev/debug and React DevTools informational messages only; no
  page errors were reported.
