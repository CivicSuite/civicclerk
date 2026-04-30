## Milestone 13 Staff UI Protected-Mode QA

- URL checked: `http://127.0.0.1:8877/staff`
- Auth mode checked: `trusted-header`
- Desktop evidence: `docs/screenshots/milestone13-staff-ui-desktop.png`
- Mobile evidence: `docs/screenshots/milestone13-staff-ui-mobile.png`
- Console: 0 messages on desktop and mobile captures
- Required state verified: the auth panel renders both `Session probe` and `Write probe`
- Accessibility spot check: keyboard focus ring present, copy remains readable at desktop and mobile widths, and the auth panel exposes actionable next-step guidance instead of a dead-end warning
