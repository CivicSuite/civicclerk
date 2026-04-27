# Milestone 11 Browser QA Checklist

Status: complete for the CivicClerk documentation and state-fixture surfaces.

## Rendered States Checked

- Loading: `docs/browser-qa/states.html` includes an aria-live loading state with an action path if loading stalls.
- Success: public meeting record success copy is visible.
- Empty: empty public archive copy explains that no public records are posted yet.
- Error: error copy is actionable and says how to fix the failed connector import.
- Partial: partial import copy explains the missing metadata and how to fix it.

## Accessibility Checks

- Keyboard: the state fixture includes a real keyboard focus target.
- Focus: `:focus-visible` styling is present on links and buttons.
- Contrast: text and accent colors were selected for high contrast against the paper/panel backgrounds.
- Console: desktop and mobile browser QA runs recorded `0` console errors.

## Evidence

- Desktop screenshot: `docs/screenshots/milestone11-browser-qa-desktop.png`
- Mobile screenshot: `docs/screenshots/milestone11-browser-qa-mobile.png`
- Gate script: `scripts/verify-browser-qa.py`
