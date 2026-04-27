# Milestone 3 Done

Milestone 3 adds agenda item lifecycle enforcement. It does not implement
meeting lifecycle enforcement, packet assembly, public portal behavior, minutes
drafting, or database-backed agenda item persistence.

## Criteria Covered

- Agenda item lifecycle follows:
  `DRAFTED -> SUBMITTED -> DEPT_APPROVED -> LEGAL_REVIEWED -> CLERK_ACCEPTED -> ON_AGENDA -> IN_PACKET -> POSTED -> HEARD -> DISPOSED -> ARCHIVED`.
- Parametrized matrix covers every `(from, to)` lifecycle pair.
- Only direct forward transitions return 2xx.
- Invalid transitions return 4xx and write rejected audit entries.
- Unknown requested statuses return an actionable 422 response and do not
  change the agenda item state.
- Runtime endpoints exist for creating draft agenda items, transitioning
  status, reading current state, and reading lifecycle audit entries.
- Current-facing README, user manual, landing page, and changelog describe
  agenda item lifecycle enforcement without claiming full meeting workflows.
- Landing page browser QA evidence exists for desktop and mobile screenshots.

## Test Counts

- Total automated pytest count: 146 passed, 0 skipped, 0 xfail.
- Milestone 3 agenda lifecycle tests: 125 passed.
- Existing Milestone 1 and 2 tests: 21 passed.

## TDD Iterations

- Iteration 1: `5cbfc36` - failing agenda item lifecycle contract.
- Iteration 2: `acc4cee` - agenda item lifecycle implementation.
- Iteration 3: `b487a79` and `de2e695` - agenda item lifecycle documentation,
  browser QA screenshots, and completion evidence.

## Deferred Items

None for Milestone 3. Milestone 4 remains meeting lifecycle enforcement and
has not been started.

## Verification

- `python -m pytest -q` passed.
- `bash scripts/verify-docs.sh` passed.
- `python scripts/check-civiccore-placeholder-imports.py` passed.
- `python -m ruff check .` passed.
- Chrome headless screenshots captured:
  `docs/screenshots/milestone3-desktop.png` and
  `docs/screenshots/milestone3-mobile.png`.
