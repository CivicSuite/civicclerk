# React Staff Route Browser QA

Captured on 2026-05-01 from
`http://127.0.0.1:4176/staff?source=demo` using the Vite React app.

Evidence files:

- `react-staff-route-dashboard.png` - desktop success state for the product
  `/staff` route.
- `../browser-qa/react-staff-route-qa-2026-05-01.json` - DOM, route,
  copy, accessibility, and console evidence.

Checks performed:

- `/staff` opens the React staff dashboard directly.
- The dashboard greeting and Meeting Runbook are visible.
- The resident Public Posting heading is absent, confirming the route did not
  land in the public portal.
- Console errors: 0.
