# CivicClerk B1 Protected Default Browser QA

Date: 2026-05-10

Scope: verify the CivicClerk staff app and protected-default API behavior after changing the default staff auth mode from `open` to `protected`.

## Evidence Files

- Desktop: `docs/browser-qa-b1-default-protected-desktop.png`
- Mobile: `docs/browser-qa-b1-default-protected-mobile.png`

## Expected Behavior

- Fresh default `/staff/auth-readiness` reports `mode == "protected"`.
- Anonymous writes to `/meeting-bodies`, `/meetings`, `/meetings/{id}/motions`, and `/motions/{id}/votes` return `401`.
- The React staff app shows a user-facing sign-in/auth-readiness path instead of a stack trace or dead-end error.
- `open` mode remains available only by explicit opt-in.

## Observed Behavior

- `GET /staff/auth-readiness` returned `200` with `mode=protected` and message `Protected staff mode is active by default; anonymous staff writes are denied.`
- Anonymous `POST /meeting-bodies`, `POST /meetings`, `POST /meetings/not-a-meeting/motions`, and `POST /motions/not-a-motion/votes` each returned `401` with the actionable `Staff authentication is required.` detail.
- The React staff app rendered `Staff sign-in needed`, displayed the protected-default fix copy including `CIVICCLERK_STAFF_AUTH_MODE=protected`, and linked operators to `/staff/auth-readiness`.
- Desktop and mobile screenshots were captured from the React app with mocked API data and the protected-default `/staff/session` response.

## Console

- Page exceptions: `0`.
- Console output contained only the expected browser resource errors for protected-default `401 Unauthorized` responses from `/staff/session`; no proxy failures, stack traces, or runtime exceptions were observed after the mock surface was completed.

## Delta From Prior Open-Mode Evidence

Prior open-mode evidence showed local rehearsal access as the default posture. This B1 evidence shows the default is now protected: anonymous staff writes are denied and the UI points operators to sign in, configure staff auth, or inspect `/staff/auth-readiness`.
