# Browser QA - Live CivicCode Handoff Emitter

Generated: 2026-05-23

Surface checked:

- React admin settings page in demo QA mode:
  `/ ?source=demo&page=admin-settings&state=success`

Evidence:

- Desktop screenshot: `docs/browser-qa/live-handoff-emitter-2026-05-23/desktop.png`
- Mobile screenshot: `docs/browser-qa/live-handoff-emitter-2026-05-23/mobile.png`
- Machine-readable capture: `docs/browser-qa/live-handoff-emitter-2026-05-23/summary.json`

Checks:

- Desktop and mobile rendered the CivicCode handoff contract as `live-when-configured`.
- Copy surfaced `CIVICCODE_INTAKE_URL`.
- Copy surfaced `EMIT_SKIPPED_UNCONFIGURED` so operators can see the unconfigured state.
- Browser console events: none.
