# Milestone 7 Done: Minutes Drafting With Sentence Citations

Status: complete on branch `milestone-7-minutes-drafting-citations`

## Scope Completed

- Minutes drafts require sentence-level citations for every material sentence.
- Minutes drafts reject uncited AI output with an actionable `422` response.
- Minutes drafts reject citations that do not point to a declared source material id.
- Minutes draft provenance records model, prompt version, data source ids, and human approver.
- AI-drafted minutes are created as `DRAFT`, never adopted automatically, and never posted automatically.
- Automatic public posting attempts return `409 Conflict` with a human-approval fix path.
- The root endpoint, README, user manual, landing page, and changelog now describe the shipped minutes citation foundation and point to Milestone 8.

## TDD Evidence

- Red contract commit: `6515a6f test(milestone-7): define minutes citation contract`
- Initial red run: `python -m pytest tests/test_milestone_7_minutes_citations.py -q`
- Initial result: `6 failed`
- Green implementation commit: `1c9074a feat(milestone-7): add citation-gated minutes drafts`
- Targeted green run: `python -m pytest tests/test_milestone_7_minutes_citations.py tests/test_milestone_1_runtime_foundation.py -q`
- Targeted result: `16 passed in 0.44s`

## Verification Snapshot

- `python -m pytest --collect-only -q`: `325 tests collected in 0.76s`
- `python -m pytest -q`: `325 passed in 5.87s`
- `bash scripts/verify-docs.sh`: `VERIFY-DOCS: PASSED`
- `python scripts/check-civiccore-placeholder-imports.py`: `PLACEHOLDER-IMPORT-CHECK: PASSED (13 source files scanned)`
- `python -m ruff check .`: `All checks passed!`

## Audit Fix

- Added `tests/conftest.py` to use the Windows selector event-loop policy during tests.
- Reason: the audit full-suite run hit Windows Proactor self-pipe socket exhaustion while creating an async test loop.
- Result: full suite rerun completed cleanly with `325 passed`.

## Browser QA Evidence

- Desktop landing page QA: `docs/screenshots/milestone7-desktop.png`
- Mobile landing page QA: `docs/screenshots/milestone7-mobile.png`
- Desktop result: Milestone 7 citation/provenance copy visible, stale Milestone 6 minutes-planned copy absent, console errors `0`.
- Mobile result: Milestone 7 citation/provenance copy visible, stale Milestone 6 minutes-planned copy absent, console errors `0`.

## Runtime Contract

`GET /` now returns:

```json
{
  "name": "CivicClerk",
  "status": "minutes citation foundation",
  "message": "CivicClerk agenda item, meeting lifecycle, packet snapshot, and notice compliance enforcement are online with immutable motion, vote, action-item, and citation-gated minutes draft capture; archive and UI workflows are not implemented yet.",
  "next_step": "Milestone 8: public meeting calendar, detail, and archive"
}
```

## Out of Scope

- Public meeting archive workflow.
- Anonymous public pages.
- Permission-aware public search.
- Full frontend workflow screens.
- Database-backed persistence beyond the current runtime slice.
- CivicCore, CivicSuite umbrella, or CivicRecords AI changes.
