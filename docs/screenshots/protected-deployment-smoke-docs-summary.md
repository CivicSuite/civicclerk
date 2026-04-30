# Protected Deployment Smoke Docs Browser QA

Date: 2026-05-01

Page checked: `docs/index.html`

Evidence:

- Desktop screenshot: `docs/screenshots/protected-deployment-smoke-docs-desktop.png`
- Mobile-width screenshot: `docs/screenshots/protected-deployment-smoke-docs-mobile.png`
- Browser QA gate: `python scripts/verify-browser-qa.py`

Checks:

- Desktop viewport: 1440x1000.
- Mobile-width viewport: 500x844.
- User-visible copy mentions `scripts/check_protected_deployment_smoke.py` and the protected session/write probe path after strict readiness.
- Console/runtime risk: no page JavaScript was introduced in this docs-only change; the browser QA gate reports `console errors: 0`.
