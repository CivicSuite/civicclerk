# React Staff Access Browser QA

AUDITOR-RUN: 2026-05-01

Scope: React dashboard staff access/session status panel for OIDC browser
session polish.

Evidence:
- Desktop success screenshot:
  `docs/screenshots/react-staff-access-oidc-desktop.png`
- Mobile success screenshot:
  `docs/screenshots/react-staff-access-oidc-mobile.png`
- Desktop actionable session-error screenshot:
  `docs/screenshots/react-staff-access-session-error.png`

Checked states:
- Success: OIDC browser session shows municipal SSO heading, provider,
  signed-in subject, auth method, roles, sign-out link, and IT auth-readiness
  link.
- Error: missing/expired browser session shows an alert, direct municipal SSO
  sign-in link, and `/staff/auth-readiness` fix guidance for IT.
- Mobile: the access card stacks actions and session facts without horizontal
  clipping at 390px width.

Accessibility and console:
- Keyboard-visible links remain native anchors for sign-in, sign-out, and IT
  readiness.
- Focusable actions have visible button styling and readable contrast against
  success and error card backgrounds.
- CDP console check found 0 JavaScript console errors and 0 runtime exceptions
  on the success path.
- CDP console check found 0 JavaScript console errors and 0 runtime exceptions
  on the error path; Chrome emitted one expected network log for the mocked
  `/staff/session` 401 used to render the actionable sign-in-needed state.
