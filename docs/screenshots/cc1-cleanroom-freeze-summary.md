# CC-1 Cleanroom Freeze Docs Browser QA

Page: `docs/index.html`
Reviewed at: `2026-05-06T00:20:15.661656Z`
Page SHA256: `b4a6f16e84f228cc590378fb01c8890cac57054e2fc0f79556e9bb9b39abe36b`

## Evidence

- desktop viewport: `1366x900`
- desktop screenshot: `docs/screenshots/cc1-cleanroom-freeze-desktop.png` (1562165 bytes)
- desktop console_events=0
- desktop exceptions=0
- desktop horizontal_overflow=False
- desktop focused_element=`A:Read the README`
- desktop freeze_copy_visible=True

- mobile viewport: `390x844`
- mobile screenshot: `docs/screenshots/cc1-cleanroom-freeze-mobile.png` (1359549 bytes)
- mobile console_events=0
- mobile exceptions=0
- mobile horizontal_overflow=False
- mobile focused_element=`A:Read the README`
- mobile freeze_copy_visible=True

## Accessibility And Copy Checks

- keyboard: first documentation link accepts focus and keeps a focus-visible rule in CSS.
- focus: `a:focus-visible` outline is present in `docs/index.html`.
- contrast: body text contrast is 15.19:1 against the page background approximation.
- contrast: link text contrast is 5.91:1 against card white.
- console: no browser console events or page exceptions were recorded in either viewport.
- copy: the docs page now states that CivicClerk uses the published `civiccore` 0.22.1 wheel from the `civiccore-m1-freeze` release asset.
