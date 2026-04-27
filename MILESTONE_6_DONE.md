# Milestone 6 Done: Motion / Vote / Action-Item Capture

Status: complete on branch `milestone-6-motion-vote-action-capture`

## Scope Completed

- Captured motions are immutable once recorded.
- Direct `PUT` and `PATCH` attempts against captured motions return `409 Conflict` with an actionable correction path.
- Motion corrections are append-only records that reference the original motion through `correction_of_id`.
- Captured votes are immutable once recorded.
- Direct `PUT` and `PATCH` attempts against captured votes return `409 Conflict` with an actionable correction path.
- Vote corrections are append-only records that reference the original vote through `correction_of_id`.
- Action items can be created for meetings and linked to source motions as meeting outcomes.
- Action items reject source motions from other meetings with an actionable `422` response.
- The root endpoint, README, user manual, landing page, and changelog now describe the shipped motion/vote/action foundation and point to Milestone 7.

## TDD Evidence

- Red contract commit: `131ae4a test(milestone-6): define motion vote action capture contract`
- Initial red run: `python -m pytest tests/test_milestone_6_motion_vote_action_capture.py -q`
- Initial result: `5 failed`
- Green implementation commit: `7b4d813 feat(milestone-6): add motion vote action capture`
- Targeted green run: `python -m pytest tests/test_milestone_6_motion_vote_action_capture.py tests/test_milestone_1_runtime_foundation.py -q`
- Targeted result: `15 passed in 0.36s`

## Verification Snapshot

- `python -m pytest --collect-only -q`: `318 tests collected in 0.71s`
- `python -m pytest -q`: `318 passed in 6.14s`
- `bash scripts/verify-docs.sh`: `VERIFY-DOCS: PASSED`
- `python scripts/check-civiccore-placeholder-imports.py`: `PLACEHOLDER-IMPORT-CHECK: PASSED (12 source files scanned)`
- `python -m ruff check .`: `All checks passed!`

## Browser QA Evidence

- Desktop landing page QA: `docs/screenshots/milestone6-desktop.png`
- Mobile landing page QA: `docs/screenshots/milestone6-mobile.png`
- Desktop result: Milestone 6 copy visible, stale Milestone 5 vote-copy absent, console errors `0`.
- Mobile result: Milestone 6 copy visible, stale Milestone 5 vote-copy absent, console errors `0`.

## Runtime Contract

`GET /` now returns:

```json
{
  "name": "CivicClerk",
  "status": "motion vote action foundation",
  "message": "CivicClerk agenda item, meeting lifecycle, packet snapshot, and notice compliance enforcement are online with immutable motion, vote, and action-item capture; minutes, archive, and UI workflows are not implemented yet.",
  "next_step": "Milestone 7: minutes drafting with sentence citations"
}
```

## Out of Scope

- Minutes drafting.
- Sentence-level citations.
- Public archive workflows.
- Full frontend workflow screens.
- Database-backed persistence beyond the current runtime slice.
- CivicCore, CivicSuite umbrella, or CivicRecords AI changes.
