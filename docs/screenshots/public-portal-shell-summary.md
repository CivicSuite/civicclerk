# Public Portal Shell Browser QA

Captured on 2026-04-30 from branch `feat/public-portal-shell` against a local
FastAPI instance at `http://127.0.0.1:8794/public`.

Evidence:

- `public-portal-shell-empty-desktop.png` captures the empty public-record state
  before staff publish a public record.
- `public-portal-shell-desktop.png` captures the seeded success state after a
  public meeting record was created through `/meetings` and
  `/meetings/{id}/public-record`.
- `public-portal-shell-mobile.png` captures the same seeded state at mobile
  width.

QA checks:

- Loading state: visible before `/public/meetings` resolves.
- Empty state: tells staff to publish a public record from `/staff`.
- Success state: shows a public meeting record and a public-detail action.
- Error state: page copy tells residents to retry the specific public API path.
- Partial state: styled and covered as a browser QA state for future degraded
  public API results.
- Keyboard/focus: skip link, search input, record-detail button, and links use
  visible `:focus-visible` outlines.
- Contrast: text, buttons, and state cards use high-contrast ink/accent colors
  on light panels.
- Console: Chrome headless screenshots completed without browser crash output;
  API responses were served by the branch-local app.
