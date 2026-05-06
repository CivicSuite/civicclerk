# CC-7 API and Frontend Completeness

Status: implemented in the current development branch.

## API Contract

The published OpenAPI artifact is `docs/api/openapi.json`, generated from the
live FastAPI app by:

```bash
python scripts/generate-openapi-spec.py
```

`tests/test_cc7_api_frontend_completeness.py` verifies the artifact matches
`civicclerk.main.app.openapi()` exactly and that every CC-7 API category in
`civicclerk/cc7_completeness.py` appears in the published schema.

New CC-7 coverage includes staff report normalization,
meeting transcript capture, ordinance/resolution handoff, public comment review
queue, admin config, and prompt-library admin endpoints. Protected non-public
routes remain behind the staff auth middleware. Bearer, trusted-header, trusted
proxy-source, and optional archive bearer checks use CivicCore auth helpers.
`/admin/config` reports category-level auth scope, including mixed public intake
and protected staff-review queues.

## Frontend Contract

The React staff workspace now accepts direct QA routes for all 20 spec pages:
staff dashboard, meeting calendar/detail, agenda builder/intake, staff report
editor, packet builder, notice checklist, live meeting capture, minutes review,
motions/votes/action items, transcript management, public comment review,
closed-session workspace, archive search, public calendar/detail, admin
settings, prompt-library admin, and connector/import admin.

Every page supports `loading`, `success`, `empty`, `error`, and `partial` QA
states through `?page=<id>&state=<state>&source=demo`.

## Browser QA Evidence

Current evidence:

- `docs/browser-qa/cc7-api-frontend-completeness-qa-2026-05-06.json`
- `docs/screenshots/cc7-api-frontend-completeness-summary.md`
- `docs/screenshots/cc7-<page>-desktop.png`
- `docs/screenshots/cc7-<page>-mobile.png`

The evidence runner is:

```bash
node scripts/capture-cc7-browser-qa.mjs
```

It checks 20 pages x 5 states x desktop/mobile for semantic main landmarks,
visible state copy, keyboard focus, visible focus styling, horizontal overflow,
console errors, runtime exceptions, and sampled contrast. Success states also
write desktop and mobile screenshots for every page.
