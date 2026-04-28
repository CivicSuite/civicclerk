# Browser QA: Live Connector Import Staff Screen

Status: passed  
URL: `http://127.0.0.1:8795/staff?screen=imports`  
Date: 2026-04-28

## Evidence

- Desktop screenshot: `docs/browser-qa-production-depth-live-connector-import-screen-desktop.png` (229,156 bytes)
- Mobile screenshot: `docs/browser-qa-production-depth-live-connector-import-screen-mobile.png` (118,354 bytes)
- Browser interaction: selected `Connector Import`, submitted `Import local connector payload`, and received a success state from the live API.

## States Checked

- Loading: submit action changed output to a loading message before the API response.
- Success: output showed imported `granicus` meeting `gr-demo-100` with one agenda item.
- Empty: initial output explained no action had run yet.
- Error: invalid JSON produces actionable retry copy.
- Partial: shared browser QA fixture remains enforced by `scripts/verify-browser-qa.py`.

## Accessibility And Copy

- Keyboard/focus styling remains covered through `:focus-visible`.
- The live output uses `role="status"` and `aria-live="polite"`.
- Empty/error copy tells clerks how to fix missing or malformed local export payloads.
- Console errors: 0.

## Guardrail Verified

The staff action posts pasted local JSON to `/imports/{connector}/meetings`; it does not fetch from vendor networks and keeps source-provenance review as the next step.
