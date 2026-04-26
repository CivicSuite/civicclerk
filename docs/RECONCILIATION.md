# CivicClerk Milestone 0 Reconciliation

This report records disagreements between the current CivicClerk scaffold and the upstream CivicSuite unified spec / suite ADRs. "Current text" is quoted verbatim from the scaffold so each row can be grepped by a reviewer.

| File path | Current text (verbatim) | Required correction (verbatim) | Driver (spec § or ADR #) |
|---|---|---|---|
| `README.md` | `Depends on: `civiccore >=0.2.0, <0.3.0` once runtime work begins` | `Depends on: `civiccore==0.2.0` once runtime work begins` | AGENTS.md §6; AGENTS.md §8; unified spec §16 |
| `USER-MANUAL.md` | `The first runtime version should pin to civiccore `>=0.2.0,<0.3.0`.` | `The first runtime version should pin to civiccore `==0.2.0`.` | AGENTS.md §6; AGENTS.md §8; suite ADR-0001 |
| `README.md` | `- agenda item intake from departments` | `- agenda item intake from departments, including staff report intake and normalization` | AGENTS.md §6 canonical tables; unified spec §9 |
| `README.md` | `- statutory notice deadline tracking` | `- statutory notice deadline tracking, notice postings, and statutory-basis capture` | AGENTS.md §5; AGENTS.md §6 canonical tables; unified spec §9 |
| `README.md` | `- meeting motions, votes, and action logging` | `- immutable meeting motions, votes, and action logging with corrections referencing originals` | AGENTS.md §5; AGENTS.md §6; unified spec §9 |
| `README.md` | `- public meeting pages for posted agendas, packets, and approved minutes` | `- public meeting pages for posted agendas, packets, approved minutes, public comments, and permission-aware archives` | AGENTS.md §5; AGENTS.md §6 canonical tables; unified spec §9 |
| `README.md` | `- searchable meeting archives` | `- searchable meeting archives that never leak closed-session content in body, counts, suggestions, or errors` | AGENTS.md §5; AGENTS.md §6; unified spec §9 |
| `README.md` | `- Redis + Celery` | `- Redis 7.2 pinned `<8.0`, Celery, and Celery Beat` | AGENTS.md §6 backend; unified spec §5 |
| `README.md` | `- Ollama / Gemma 4 through `civiccore.llm`` | `- Ollama / Gemma 4 through `civiccore.llm`, selected by `CIVICCORE_LLM_PROVIDER=ollama`` | AGENTS.md §5; AGENTS.md §6 default LLM stack |
| `docs/index.html` | `<p>Planned local-first stack: FastAPI, React, PostgreSQL, Redis, Celery, Ollama, and <code>civiccore</code>.</p>` | `<p>Planned local-first stack: FastAPI, React served behind nginx, PostgreSQL 17 + pgvector, Redis 7.2 pinned below 8.0, Celery, Celery Beat, Ollama selected by <code>CIVICCORE_LLM_PROVIDER=ollama</code>, and <code>civiccore==0.2.0</code>.</p>` | AGENTS.md §6; AGENTS.md §8 |
| `USER-MANUAL.md` | `- local Docker-based deployment` | `- local Docker-based deployment behind nginx` | AGENTS.md §6 frontend; unified spec §5 |
| `USER-MANUAL.md` | `- Redis + Celery` | `- Redis 7.2 pinned `<8.0`, Celery, and Celery Beat` | AGENTS.md §6 backend; unified spec §5 |
| `USER-MANUAL.md` | `- Ollama/Gemma 4 for local LLM inference through `civiccore.llm`` | `- Ollama/Gemma 4 for local LLM inference through `civiccore.llm`, selected by `CIVICCORE_LLM_PROVIDER=ollama`` | AGENTS.md §5; AGENTS.md §6 |
| `docs/architecture/ADR-0001-mvp-boundary.md` | `Status: Accepted` | `Status: Superseded by Milestone 0 reconciliation; unresolved scope questions are queued under docs/adr/civicclerk-adr-0001.md and following.` | AGENTS.md §12 deliverable 4; unified spec §20 |
| `docs/architecture/ADR-0001-mvp-boundary.md` | `It does not start with livestream hosting, electronic voting, full`<br>`transcription packaging, CivicCode integration, or broad boards and`<br>`commissions management.` | `Livestream hosting, electronic voting, and broad boards and commissions management are excluded from v0.1.0. Transcription packaging, CivicCode ordering, and other v0.1.0-impacting questions are not decided here; they are queued as proposed ADRs.` | AGENTS.md §12 deliverable 4; unified spec §20 |
| `docs/roadmap/mvp-plan.md` | `## Sprint 1` | `## Milestone 1 — CivicClerk runtime foundation (FastAPI app, package layout, CivicCore pin, CI)` | AGENTS.md §4; AGENTS.md §12 deliverable 5 |
| `docs/roadmap/mvp-plan.md` | `## Sprint 4` | `## Milestone 12 — v0.1.0 release with docs, tests, browser evidence, generated artifacts` | AGENTS.md §4; AGENTS.md §12 deliverable 5 |
| `docs/roadmap/mvp-plan.md` | `- no stale version references` | `- scripts/verify-docs.sh passes; placeholder-import CI gate passes; no skipped or xfail'd tests; version surfaces are synchronized across pyproject.toml, package.json, README.md, README.txt, USER-MANUAL.md, CHANGELOG.md, landing page, and version-asserting tests` | AGENTS.md §8 definition of done |
| `scripts/verify-docs.sh` | `if grep -RInE 'scottconverse/civicrecords-ai\|v1\.3\.0\|civiccore 0\.1\.0\|Phase 0 scaffold' \` | `if grep -RInE 'MIT\|26 modules across 6 tiers\|~=0\.2\|civicclerk shipping\|scottconverse/civicrecords-ai\|v1\.3\.0\|civiccore 0\.1\.0\|Phase 0 scaffold' \` | AGENTS.md §8; AGENTS.md §12 deliverable 6 |
| `.github/workflows/ci.yml` | `- name: Verify docs baseline`<br>`  run: bash scripts/verify-docs.sh` | `- name: Verify docs baseline`<br>`  run: bash scripts/verify-docs.sh`<br><br>`- name: Check CivicCore placeholder imports`<br>`  run: python scripts/check-civiccore-placeholder-imports.py` | AGENTS.md §3.1; AGENTS.md §12 deliverable 7 |
| `scripts/verify-docs.sh` | `required=(` | `required=(` plus every required artifact in AGENTS.md §9, including `docs/MILESTONES.md`, `docs/RECONCILIATION.md`, and `MILESTONE_0_DONE.md` once Milestone 0 is complete. | AGENTS.md §9; AGENTS.md §12 deliverable 6 |

## Section 20 ADR Triage

Queued for v0.1.0 scope because each question affects schema, user-facing behavior, source control layout, runtime dependency ordering, or release gates before CivicClerk v0.1.0:

- CivicClerk v0.1.0 canonical table list / any reduction from the 14-table canonical set.
- Public comments in v0.1.0.
- Transcription packaging in v0.1.0 vs v0.2.0.
- Shared resident portal shell boundary.
- CivicCore auth/RBAC extraction order.
- CivicCore document/search extraction order.
- Prompt-library repository strategy.
- State statutory-rule data-release strategy.

Excluded from v0.1.0 ADR queue:

- CivicCode-before-CivicZone ordering. This affects later module sequencing, not CivicClerk v0.1.0 implementation.
