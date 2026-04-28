# Browser QA: Live Public Archive Staff Screen

Status: passed  
URL: `http://127.0.0.1:8795/staff?screen=archive`  
Date: 2026-04-28

## Evidence

- Desktop screenshot: `docs/browser-qa-production-depth-live-archive-screen-desktop.png` (219,502 bytes)
- Mobile screenshot: `docs/browser-qa-production-depth-live-archive-screen-mobile.png` (118,314 bytes)
- Browser interaction: selected `Public Archive`, submitted `Publish public archive record`, and received a success state from the live API.

## States Checked

- Loading: submit action changed output to a loading message before the API response.
- Success: output showed a created public archive record id with public calendar and archive search counts.
- Empty: initial output explained no action had run yet.
- Error: form has actionable error copy for missing public-safe agenda, packet, or approved-minutes text.
- Partial: shared browser QA fixture remains enforced by `scripts/verify-browser-qa.py`.

## Accessibility And Copy

- Keyboard/focus styling remains covered through `:focus-visible`.
- The live output uses `role="status"` and `aria-live="polite"`.
- Empty/error copy tells clerks how to fix missing public-safe archive material.
- Console errors: 0.

## Guardrail Verified

The staff action publishes only public-safe agenda, packet, and approved-minutes text, then verifies anonymous public visibility through `/public/meetings` and `/public/archive/search`.
