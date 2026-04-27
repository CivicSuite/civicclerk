# Milestone 12 Done - v0.1.0 Release

## Scope

Milestone 12 closes the CivicClerk v0.1.0 runtime-foundation sprint. It synchronizes the release version surfaces, adds the release gate and GitHub release workflow, verifies the package build, and preserves browser QA evidence for the user-facing landing page.

## Commits

- `9b6914e` - `test(milestone-12): define release contract`
- `bd7fbae` - `chore(milestone-12): prepare v0.1.0 release`
- `d798bb0` - `fix(milestone-12): publish GitHub release assets`
- `85eca40` - `docs(milestone-12): record release-publish workflow`

## Version Surfaces

- `pyproject.toml`: `0.1.0`
- `civicclerk/__init__.py`: `__version__ = "0.1.0"`
- `/health`: reports `version = 0.1.0`
- `README.md`, `USER-MANUAL.md`, `docs/index.html`, and `CHANGELOG.md`: current-facing v0.1.0 release language

## Release Gate

`scripts/verify-release.sh` now runs:

- pytest, excluding only the release-script meta-test to avoid recursive self-invocation
- docs verification
- CivicCore placeholder-import gate
- browser QA gate
- offline prompt evals with `CIVICCORE_LLM_PROVIDER=ollama`
- package build
- SHA256 checksum generation

The tag-triggered release workflow runs the release gate, uploads `dist/*` as a workflow artifact, and publishes those same files to the GitHub Release for the pushed tag.

## Release Artifacts

- `dist/civicclerk-0.1.0-py3-none-any.whl` - 29,673 bytes
- `dist/civicclerk-0.1.0.tar.gz` - 43,993 bytes
- `dist/SHA256SUMS.txt` - 192 bytes

Checksums:

```text
b929f7d9cd42c51d7ac813b41dcb3c969190689f99fea87b2acf99d046c86684  civicclerk-0.1.0-py3-none-any.whl
ea1379c0cdccabb92a7a6d0c412ad8a1d977461a783cbbe801a40a44f2e1ca26  civicclerk-0.1.0.tar.gz
```

## Browser QA Evidence

- `docs/screenshots/milestone12-desktop.png` - 239,499 bytes
- `docs/screenshots/milestone12-mobile.png` - 114,942 bytes

Browser QA results:

- Desktop: v0.1.0 visible, release artifacts visible, no `0.1.0.dev0`, zero console errors
- Mobile: v0.1.0 visible, release artifacts visible, no `0.1.0.dev0`, zero console errors

## Verification

```text
python -m pytest --collect-only -q
355 tests collected in 0.85s

python -m pytest -q
355 passed in 27.70s

bash scripts/verify-docs.sh
VERIFY-DOCS: PASSED

python scripts/check-civiccore-placeholder-imports.py
PLACEHOLDER-IMPORT-CHECK: PASSED (17 source files scanned)

python scripts/verify-browser-qa.py
BROWSER-QA: PASSED

CIVICCORE_LLM_PROVIDER=ollama CIVICCLERK_EVAL_OFFLINE=1 NO_NETWORK=1 python scripts/run-prompt-evals.py
PROMPT-EVALS: PASSED

python -m ruff check .
All checks passed!

bash scripts/verify-release.sh
VERIFY-RELEASE: PASSED
```

## Boundaries Honored

- No post-v0.1.0 feature work started.
- No CivicSuite compatibility matrix edit is included in this branch; that is performed after the CivicClerk v0.1.0 release is published.
- No CivicCore changes are included.
