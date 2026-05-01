# React Public Posting Browser QA

Captured on 2026-05-01 from `http://127.0.0.1:5175/?source=demo&page=public`
using the Vite React app.

Evidence files:

- `react-public-posting-live-desktop.png` - desktop success state, 1440px wide.
- `react-public-posting-live-mobile.png` - mobile success state, 390px wide.
- `react-public-posting-search.png` - archive search result state.
- `react-public-posting-focus.png` - keyboard tab focus pass.
- `react-public-posting-state-loading.png` - loading fixture.
- `react-public-posting-state-empty.png` - empty fixture.
- `react-public-posting-state-error.png` - error fixture.
- `react-public-posting-state-partial.png` - partial fixture.

Checks performed:

- Success state shows public records, selected resident-safe detail, posted
  agenda, posted packet, and approved minutes.
- Missing-record and partial-state copy tells residents to ask the clerk for the
  official posted record link instead of implying a restricted meeting exists.
- Search state confirms public archive results and says restricted or
  closed-session records are not shown to anonymous visitors.
- Desktop and mobile screenshots rendered without layout failure.
- Keyboard tab traversal produced visible focus.
- Console had Vite dev/debug and React DevTools informational messages only; no
  page errors were reported.
