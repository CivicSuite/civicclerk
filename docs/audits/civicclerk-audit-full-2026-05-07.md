# CivicClerk Audit Full - 2026-05-07 Recovery Pass

## 1. Executive Audit

- Scope: `C:\Users\scott\OneDrive\Desktop\Claude\civicclerk`
- Audit mode: release-gate recovery audit
- Active cleanup: yes; this audit drove the recovery branch `recovery/civicclerk-release-truth-playwright`
- Local/live parity: checked against `origin/main`; local and remote both started at `ee1b7a07cadcec2ed20bba44f0e9ea0ed8297f71`
- Overall verdict: CivicClerk has substantial runtime and test depth, but the prior public `v1.0.0` presentation was too confident for the evidence then enforced. This branch freezes public product-ready claims and adds hard recovery gates.
- Ship posture: not product-ready for public promotion until this branch is pushed, reviewed, merged, and CI is green. Local release-gate verification now passes.
- Real state: CivicClerk is a working municipal-meeting runtime foundation with meaningful backend coverage and a React staff/public surface, but the UI is still concentrated in a large single-file app and the previous "browser QA" relied too much on generated artifacts. The recovery branch adds tracked Playwright user-flow tests, docs-source parity, a secret/prompt-injection scan, explicit provisional labeling, and isolated wheel runtime install proof.
- Severity summary counts: Blocker 0 open / 1 fixed; Critical 0 open / 3 fixed; Major 3 open; Minor 3 open; Nit 0
- Static audit confidence: High for repo state, docs claims, test/gate presence, version surfaces, CI config, and release scripts.
- Runtime sign-off confidence: Medium-high locally after WSL `scripts/verify-release.sh` passed; live GitHub CI remains pending until push/PR.
- Top findings: `REL-001` fixed public overclaiming; `TEST-001` fixed missing tracked Playwright user-flow specs; `BOOT-001` fixed missing isolated install proof in release gate; `SEC-001` fixed missing local secret/prompt-injection scan; `DOC-001` fixed docs-source parity enforcement; `UX-001` remains large single-file React app; `TEST-002` remains Playwright breadth is initial, not exhaustive; `ENG-001` remains frontend architecture concentration; `QA-001` remains some old screenshot evidence is historical; `PM-001` remains public announcement should wait for merged CI.
- CI/workflow posture: CI now runs recovery gates, secret scan, browser evidence check, Playwright user flows, frontend build/tests, backend tests, docs, and prompt evals.

## 2. Audit Coverage Ledger

| Lane | Status | Evidence summary | Blocker |
|---|---|---|---|
| remote parity | Checked | `HEAD == origin/main` at audit start | none |
| local-vs-live commit truth | Checked | `ee1b7a07cadcec2ed20bba44f0e9ea0ed8297f71` | none |
| CI/workflow presence | Checked | `.github/workflows/ci.yml` reviewed and updated | none |
| Windows install path | Partially checked | scripts and docs inspected; no Windows runtime execution in this pass | Windows host proof pending |
| Linux or Unix install path | Checked | WSL release gate and isolated venv install proof passed | none |
| platform parity verdict | Partially checked | WSL strong, Windows docs/scripts static only | Windows execution pending |
| first boot | Checked | isolated wheel install hit `/health` and `/staff` | none |
| required post-install steps | Checked | README/manual/docs index reviewed | none |
| migrations | Checked | migration tests passed in full suite | none |
| seed/bootstrap requirements | Checked | demo seed tests passed | none |
| runtime dependency and model requirements | Checked | CivicCore wheel install and offline prompt eval passed | none |
| first-boot dependency truth | Checked | runtime install proof now enforced | none |
| secrets and credential handling | Checked | `scripts/verify-secret-scan.py` passed | none |
| auth and session handling | Checked | staff auth tests passed | none |
| authorization and role boundaries | Checked | protected staff and archive tests passed | none |
| response-schema sensitive-data exposure | Checked | public archive leakage tests passed | none |
| audit and compliance logging | Checked | lifecycle/audit hash tests passed | none |
| external and admin surfaces | Checked | integration readiness and admin routes tested | none |
| connector implementation completeness | Checked | local/mock connector tests passed | none |
| connector docs truth | Checked | recovery docs distinguish mock from production | none |
| background jobs and schedulers | Checked | scheduled connector/vendor tests passed | none |
| frontend critical journeys | Checked | Vitest 33 + Playwright 4 user-flow runs passed | none |
| loading states | Checked | browser evidence gate passed | none |
| empty states | Checked | browser evidence gate passed | none |
| error states | Checked | browser evidence gate passed | none |
| partial states | Checked | browser evidence gate passed | none |
| accessibility cues | Checked | keyboard/focus/contrast/console evidence gate passed | none |
| docs truthfulness | Checked | provisional language added | none |
| version consistency | Checked | release contract passed | none |
| release artifact consistency | Checked | wheel/sdist/SHA256SUMS built | none |
| test realism | Partially checked | Playwright added; breadth still initial | expand flows |
| runtime, build, and test verification | Checked | `VERIFY-RELEASE: PASSED` in WSL | none |
| browser verification | Checked | Playwright desktop/mobile plus evidence gate | none |
| prior audit or verification challenge | Checked | external audit criticisms addressed for this repo | none |

## 3. Claim Verification Matrix

| Claim | Source | Verdict | Evidence |
|---|---|---|---|
| CivicClerk is product-ready/public-announcement-ready | prior public framing | False before recovery; now explicitly frozen | README/manual/docs index say not product-ready during recovery |
| `v1.0.0` is current package version | `pyproject.toml`, `frontend/package.json` | True | release contract passed |
| `v1.0.0` release status is fully earned | public release label | Partially true locally after recovery; not live until merge/CI | local `verify-release.sh` passed; PR/CI pending |
| Browser QA covers user flows | prior docs | Partially true before; stronger now | tracked Playwright desktop/mobile flows added |
| Browser QA only checks docs artifact strings | external audit | True before; no longer sufficient | CI now runs Playwright user flows |
| WSL runtime install proof exists | recovery requirement | True now | isolated wheel install proof passed |
| Mock validation is not production deployment | docs | True now | required language in README/manual/docs index |
| Secret/prompt-injection scan exists | recovery requirement | True now | `SECRET-SCAN: PASSED` |
| README and text mirror are in sync | docs-source | True now | recovery gate checks exact parity |
| React app is modular production architecture | external audit concern | False | `frontend/src/App.tsx` remains large single-file app |

## 4. What The Dev Team Needs To Do Now

### Must fix before ship

- `PM-001`: Push branch, open PR, wait for CI green. Why now: local proof is not live proof. Owner: release. Verification: GitHub CI pass.

### Should fix this sprint

- `UX-001`: Split the monolithic React app into route/workflow components. Why now: maintainability and review quality. Owner: frontend. Verification: existing Vitest and Playwright remain green after extraction.
- `TEST-002`: Expand Playwright from two critical flows to a broader clerk-day suite: agenda intake, packet, notice, minutes, public posting, and vendor sync. Owner: QA/frontend. Verification: `npm run test:e2e`.
- `QA-001`: Replace remaining historical browser artifacts with current-session captures where docs changed. Owner: QA/docs. Verification: browser evidence manifest and screenshots refreshed.

### Can defer if consciously accepted

- `ENG-001`: Preserve current backend module shape until after recovery. The backend suite is strong enough to avoid blocking this branch.
- `DOC-002`: Shorten the very long docs index status paragraph after recovery. It is truthful now but not humane reading.

## 5. Next-Sprint Watchlist

- Architecture: React component extraction and route ownership.
- Security and compliance debt: extend secret scan with entropy checks after false-positive tuning.
- UX debt: make public/staff split more obvious at URL and layout level.
- Docs debt: replace historical "ships" language throughout older milestone docs with dated historical framing.
- Install and bootstrap debt: add a Windows runtime-install proof run on a Windows runner.
- Test debt: broaden Playwright and add browser console artifacts to CI uploads.
- Operational and release debt: require recovery gates across every CivicSuite repo, not just CivicClerk.

## 6. Engineering Deep Dive

Checked architecture, runtime entry points, scripts, CI, dependencies, release gate, and generated artifacts. The backend has broad coverage and clear contracts around agenda lifecycle, meetings, packet assembly, notice, minutes, public archive, auth, vendor sync, and mocks. The largest engineering risk is frontend concentration: one large `App.tsx` holds domain types, fetchers, routing, forms, and rendering. That is not a release blocker after current tests, but it is not professional long-term structure.

## 7. Security And Authorization Deep Dive

Checked staff auth tests, OIDC/bearer/trusted-header paths, public archive restrictions, credential docs, vendor URL guards, and release scripts. Added `scripts/verify-secret-scan.py`, including a check for prompt-injection sentinels such as `stop claude`, while allowing mock values explicitly labeled as mock/not-reported and env-var pass-throughs.

## 8. UI/UX Deep Dive

Checked the React app through Vitest and Playwright. The added Playwright tests exercise a clerk notice proof flow and a resident public-posting flow at desktop and mobile widths. Existing UI copy has actionable error paths, but information density is high. The public docs index now opens with recovery truth instead of burying status in a massive paragraph.

## 9. Product/PM Deep Dive

The product has real CivicClerk-shaped substance, but the old release label overstated confidence. The correct public position is "provisional v1 runtime foundation under recovery validation" until live CI and PR review pass. Do not announce as a finished public product from the old tag alone.

## 10. Documentation Deep Dive

Checked README, manual, text mirrors, docs index, changelog, release evidence, and docs gate. Added provisional status language and mock-vs-production labeling. Added exact README/manual parity checks so `.txt` mirrors cannot drift silently.

## 11. Install / Bootstrap / Seeding Deep Dive

Checked WSL dependency setup, backend tests, build, wheel artifact creation, and isolated runtime install. `scripts/verify-release.sh` now creates a temporary venv, installs the built wheel, imports the app, and checks `/health` plus `/staff`.

## 12. Version And Release Consistency Deep Dive

Version remains `1.0.0` in Python and frontend manifests. The audit does not treat that label as earned until recovery gates and live CI pass. Release evidence hash was refreshed using CivicCore's normalized text hashing.

## 13. Test Engineering Deep Dive

Observed full WSL release gate: 583 backend tests passed with 2 skipped in the main gate; frontend build passed; Vitest passed 33 tests; Playwright passed 4 browser user-flow tests across desktop and mobile; release-contract tests passed 8 with 3 skipped. This is much stronger than the prior artifact-only browser QA, but Playwright breadth remains initial.

## 14. Runtime QA Deep Dive

Runtime QA now includes browser evidence, Playwright, npm audit, package build, wheel install, `/health`, `/staff`, and release artifact checksum generation. No console errors were reported by the new Playwright clerk notice flow or browser evidence gate.

## 15. Cross-Cutting Synthesis

The external audit was directionally right: CivicClerk contained substantial work, but its release storytelling exceeded the enforced proof. The recovery branch changes that posture from self-certification to gates. The remaining work is to merge this branch cleanly, then repeat the same pattern repo-by-repo.

## 16. Verification Gaps And Sign-Off Limits

- Live GitHub CI is not yet observed for this branch.
- Windows runtime proof was not executed locally in this pass.
- Playwright coverage is real but not exhaustive.
- React architecture remains too concentrated for long-term professional maintenance.
- This audit covers CivicClerk only; it does not re-earn release status for other CivicSuite repos.
