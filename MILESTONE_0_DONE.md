# Milestone 0 Done

Milestone 0 reconciled the CivicClerk scaffold against the upstream CivicSuite unified spec, suite ADRs, and the attached AGENTS.md operating contract. No runtime application code was introduced.

## Criteria Covered

- Read upstream unified spec sections 4, 5, 9, 15, 16, 17, and 21.
- Read suite ADR-0001, ADR-0002, and ADR-0003 from `CivicSuite/civicsuite`.
- Recorded scaffold-vs-spec disagreements with verbatim current text in `docs/RECONCILIATION.md`.
- Queued v0.1.0-scope open questions as proposed CivicClerk ADRs.
- Added `docs/MILESTONES.md` with milestones 0 through 12, acceptance criteria, and test-count ballparks.
- Replaced the docs verifier with a required-artifact and stale-string gate.
- Added a placeholder-import CI gate for CivicCore v0.2.0 placeholder packages.
- Confirmed no FastAPI route, SQLAlchemy model, React component, Celery task, or prompt template was introduced.

## Artifacts Produced

| Artifact | Commit |
|---|---|
| `docs/RECONCILIATION.md` | `ccfd319` |
| `docs/adr/civicclerk-adr-0001.md` | `f71294f` |
| `docs/adr/civicclerk-adr-0002.md` | `f71294f` |
| `docs/adr/civicclerk-adr-0003.md` | `f71294f` |
| `docs/adr/civicclerk-adr-0004.md` | `f71294f` |
| `docs/adr/civicclerk-adr-0005.md` | `f71294f` |
| `docs/adr/civicclerk-adr-0006.md` | `f71294f` |
| `docs/adr/civicclerk-adr-0007.md` | `f71294f` |
| `docs/adr/civicclerk-adr-0008.md` | `f71294f` |
| `docs/MILESTONES.md` | `0a00fc6` |
| `LICENSE-CODE` | `33b2036` |
| `scripts/verify-docs.sh` | `33b2036` |
| `.github/workflows/ci.yml` docs-verifier wiring | `33b2036` |
| `scripts/check-civiccore-placeholder-imports.py` | `3e4c03a` |
| `.github/workflows/ci.yml` placeholder-gate wiring | `3e4c03a` |
| `MILESTONE_0_DONE.md` | this commit |

## ADRs Queued

- `civicclerk-adr-0001.md` - Canonical v0.1.0 Table List
- `civicclerk-adr-0002.md` - Public Comments in v0.1.0
- `civicclerk-adr-0003.md` - Transcription Packaging Scope
- `civicclerk-adr-0004.md` - Resident Portal Shell Boundary
- `civicclerk-adr-0005.md` - Auth and RBAC Extraction Order
- `civicclerk-adr-0006.md` - Document and Search Extraction Order
- `civicclerk-adr-0007.md` - Prompt Library Repository Strategy
- `civicclerk-adr-0008.md` - State Statutory Rule Data Strategy

## Deferred Items

None for Milestone 0. The ADR files intentionally mark open questions as pending human decisions; that is the deliverable for unresolved scope decisions, not a deferral of Milestone 0 work.

## Verification

- `bash scripts/verify-docs.sh` passed with exit code 0.
- `python scripts/check-civiccore-placeholder-imports.py` passed with exit code 0.
- `git log --oneline main..HEAD` showed one commit for each artifact-producing deliverable before this done-file commit.

## Anomalies

- The required drift-marker grep pattern includes unbounded `MIT`, so it matches unrelated substrings such as `SUBMITTED` in the required agenda lifecycle and `COMMIT` inside `.git/hooks/prepare-commit-msg.sample`. The real current-facing stale-string gate in `scripts/verify-docs.sh` scopes checks to current-facing docs and still includes the required drift markers.
