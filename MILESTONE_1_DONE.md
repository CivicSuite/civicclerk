# Milestone 1 Done

Milestone 1 created the CivicClerk runtime foundation. It does not implement meeting, agenda, packet, notice, vote, minutes, archive, schema, migration, or frontend workflows.

## Criteria Covered

- FastAPI runtime package exists at `civicclerk.main:app`.
- Root endpoint explains that the runtime foundation is online and meeting workflows are not implemented yet.
- `/health` endpoint returns service, status, CivicClerk version, and CivicCore version for IT staff.
- `pyproject.toml` declares `civicclerk` version `0.1.0.dev0`.
- Runtime dependency is exactly `civiccore==0.2.0`.
- CI installs the package, runs `python -m pytest`, runs `scripts/verify-docs.sh`, and runs `scripts/check-civiccore-placeholder-imports.py`.
- Current-facing docs and CHANGELOG describe the runtime foundation without promoting planned meeting workflows as shipped.
- Browser QA evidence exists for the updated landing page at desktop and mobile widths.

## Test Counts

- E2E/browser: 2 headless screenshot checks for `docs/index.html` desktop and mobile.
- Integration/API: 2 FastAPI ASGI endpoint tests.
- Unit/script/docs: 8 package metadata, package layout, CI, docs, and placeholder-gate tests.
- Total automated pytest count: 10 passed, 0 skipped, 0 xfail.

## TDD Iterations

- Iteration 1: `f78217a` - pyproject runtime metadata green.
- Iteration 2: `bbe5648` - FastAPI runtime import path green.
- Iteration 3: `4f471ab` - CI runtime tests green.
- Iteration 4: `33a3c77` - runtime foundation docs green.

## Browser QA Evidence

- `docs/screenshots/desktop-milestone1-qa.png`
- `docs/screenshots/mobile-milestone1-qa.png`
- Chrome headless rendered `docs/index.html` at 1440x1000 and 390x844.
- Static HTML contains no `<script>` tags, so there were no page scripts capable of emitting console errors.

## Deferred Items

None for Milestone 1. Milestone 2 remains the canonical schema and Alembic migration milestone and has not been started.

## Verification

- `python -m pytest -q` passed.
- `bash scripts/verify-docs.sh` passed.
- `python scripts/check-civiccore-placeholder-imports.py` passed.
