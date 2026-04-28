# Browser QA: Live Packet Export Screen

## Target

- URL: `http://127.0.0.1:8796/staff?screen=packet`
- Screen: Packet Assembly
- Action: `Create packet export bundle`

## Evidence

- Desktop screenshot: `docs/browser-qa-production-depth-live-packet-export-screen-desktop.png` (234,659 bytes)
- Mobile screenshot: `docs/browser-qa-production-depth-live-packet-export-screen-mobile.png` (126,050 bytes)
- Runtime interaction: created a demo meeting, created a packet snapshot, then created a records-ready export bundle through `/meetings/{id}/export-bundle`.

## States Checked

- Loading: output copy says the records-ready packet export bundle is being created.
- Success: API smoke returned a bundle path, manifest path, checksum path, and generated files.
- Empty: initial output explains no packet export action has run yet.
- Error: shared API error handling includes the server-provided message and fix path.
- Partial: the page still renders the packet assembly action and packet export action independently on the same screen.

## Accessibility / Console

- Keyboard: form controls and submit button are native focusable elements.
- Focus: existing `:focus-visible` styling remains in the shared staff UI CSS.
- Contrast: screenshots preserve the high-contrast badge and action-panel treatment used by prior staff screens.
- Console errors: 0 observed in the browser QA pass.

## Guardrail Verified

The browser-visible path exercises the same preconditions as the API: it creates the required packet snapshot before export, writes under `CIVICCLERK_EXPORT_ROOT`/`exports`, and shows manifest/checksum next steps instead of hiding the records package path.
