# Milestone 10 Done: Connectors And Imports

Status: complete on branch `milestone-10-connectors-imports`

## Scope Completed

- Local export payload imports are supported for Granicus, Legistar, PrimeGov, and NovusAGENDA.
- Import normalization records source provenance for meetings and agenda items.
- Connector imports are local-first and do not require outbound network calls in the default profile.
- Unsupported connectors return actionable `404` responses.
- Malformed local payloads return actionable `422` responses.
- The root endpoint, README, user manual, landing page, and changelog now describe the shipped connector import foundation and point to Milestone 11.

## TDD Evidence

- Red contract commit: `6356a28 test(milestone-10): define connector import contract`
- Initial red run: `python -m pytest tests/test_milestone_10_connectors_imports.py -q`
- Initial result: `9 failed`
- Green implementation commit: `a9450bd feat(milestone-10): add local connector imports`
- Targeted green run: `python -m pytest tests/test_milestone_10_connectors_imports.py tests/test_milestone_1_runtime_foundation.py -q`
- Targeted result: `19 passed in 0.43s`

## Verification Snapshot

- `python -m pytest --collect-only -q`: `345 tests collected in 0.80s`
- `python -m pytest -q`: `345 passed in 7.53s`
- `bash scripts/verify-docs.sh`: `VERIFY-DOCS: PASSED`
- `python scripts/check-civiccore-placeholder-imports.py`: `PLACEHOLDER-IMPORT-CHECK: PASSED (17 source files scanned)`
- `python -m ruff check .`: `All checks passed!`
- `CIVICCORE_LLM_PROVIDER=ollama CIVICCLERK_EVAL_OFFLINE=1 NO_NETWORK=1 python scripts/run-prompt-evals.py`: `PROMPT-EVALS: PASSED`

## Browser QA Evidence

- Desktop landing page QA: `docs/screenshots/milestone10-desktop.png`
- Mobile landing page QA: `docs/screenshots/milestone10-mobile.png`
- Desktop result: Milestone 10 connector/source-provenance copy visible, stale live-sync-shipped copy absent, console errors `0`.
- Mobile result: Milestone 10 connector/source-provenance copy visible, stale live-sync-shipped copy absent, console errors `0`.

## Runtime Contract

`GET /` now returns:

```json
{
  "name": "CivicClerk",
  "status": "connector import foundation",
  "message": "CivicClerk agenda item, meeting lifecycle, packet snapshot, and notice compliance enforcement are online with immutable motion, vote, action-item, and citation-gated minutes draft capture plus permission-aware public calendar and archive endpoints; prompt YAML and offline evaluation gates protect policy-bearing prompt changes; local-first Granicus, Legistar, PrimeGov, and NovusAGENDA imports now normalize source provenance; full UI workflows are not implemented yet.",
  "next_step": "Milestone 11: accessibility and browser QA gates"
}
```

## Out of Scope

- Live connector sync.
- Full frontend workflow screens.
- Database-backed connector persistence beyond the current runtime slice.
- CivicCore, CivicSuite umbrella, or CivicRecords AI changes.
