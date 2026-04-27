# Milestone 8 Done: Public Calendar And Archive

Status: complete on branch `milestone-8-public-calendar-archive`

## Scope Completed

- Public meeting records can be published for existing meetings.
- Public calendar listing returns only public records and counts only public records.
- Public meeting detail returns public records and uses a generic `404` for restricted records.
- Anonymous archive search does not leak closed-session content in bodies, counts, suggestions, or not-found responses.
- Staff-role archive search remains restricted from closed-session material.
- Clerk, attorney, and admin archive search can include closed-session records.
- The root endpoint, README, user manual, landing page, and changelog now describe the shipped public archive foundation and point to Milestone 9.

## TDD Evidence

- Red contract commit: `4288fed test(milestone-8): define public archive leak-prevention contract`
- Initial red run: `python -m pytest tests/test_milestone_8_public_archive.py -q`
- Initial result: `5 failed`
- Green implementation commit: `e8aa7ab feat(milestone-8): add permission-aware public archive`
- Targeted green run: `python -m pytest tests/test_milestone_8_public_archive.py tests/test_milestone_1_runtime_foundation.py -q`
- Targeted result: `15 passed in 0.43s`

## Verification Snapshot

- `python -m pytest --collect-only -q`: `330 tests collected in 0.73s`
- `python -m pytest -q`: `330 passed in 6.48s`
- `bash scripts/verify-docs.sh`: `VERIFY-DOCS: PASSED`
- `python scripts/check-civiccore-placeholder-imports.py`: `PLACEHOLDER-IMPORT-CHECK: PASSED (14 source files scanned)`
- `python -m ruff check .`: `All checks passed!`

## Browser QA Evidence

- Desktop landing page QA: `docs/screenshots/milestone8-desktop.png`
- Mobile landing page QA: `docs/screenshots/milestone8-mobile.png`
- Desktop result: Milestone 8 permission-aware public archive copy visible, stale archive-planned copy absent, console errors `0`.
- Mobile result: Milestone 8 permission-aware public archive copy visible, stale archive-planned copy absent, console errors `0`.

## Runtime Contract

`GET /` now returns:

```json
{
  "name": "CivicClerk",
  "status": "public archive foundation",
  "message": "CivicClerk agenda item, meeting lifecycle, packet snapshot, and notice compliance enforcement are online with immutable motion, vote, action-item, and citation-gated minutes draft capture plus permission-aware public calendar and archive endpoints; full UI workflows are not implemented yet.",
  "next_step": "Milestone 9: prompt YAML library and evaluation harness"
}
```

## Out of Scope

- Prompt YAML library and evaluation harness.
- Connectors and imports.
- Full frontend workflow screens.
- Database-backed public archive persistence beyond the current runtime slice.
- CivicCore, CivicSuite umbrella, or CivicRecords AI changes.
