# Browser QA: Live Minutes Draft Staff Screen

Status: passed  
URL: `http://127.0.0.1:8795/staff?screen=minutes`  
Date: 2026-04-28

## Evidence

- Desktop screenshot: `docs/browser-qa-production-depth-live-minutes-draft-screen-desktop.png` (224,629 bytes)
- Mobile screenshot: `docs/browser-qa-production-depth-live-minutes-draft-screen-mobile.png` (117,958 bytes)
- Browser interaction: selected `Minutes Draft`, submitted `Create cited minutes draft`, and received a success state from the live API.

## States Checked

- Loading: submit action changed output to a loading message before the API response.
- Success: output showed a created draft id with status `DRAFT`.
- Empty: initial output explained no action had run yet.
- Error: form has actionable error copy for missing citations/source material.
- Partial: shared browser QA fixture remains enforced by `scripts/verify-browser-qa.py`.

## Accessibility And Copy

- Keyboard/focus styling remains covered through `:focus-visible`.
- The live output uses `role="status"` and `aria-live="polite"`.
- Empty/error copy tells clerks how to fix citation/source issues.
- Console errors: 0.

## Guardrail Verified

The staff action creates a minutes draft but does not adopt or post it. The success message tells clerks that human review is required before public posting.
