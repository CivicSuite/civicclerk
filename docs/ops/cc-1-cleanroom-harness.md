# CC-1 CivicClerk Cleanroom Harness

Status: active CivicClerk productization gate.

Date: 2026-05-05.

Sprint: CC-1.

## Purpose

CC-1 proves CivicClerk can be built and verified from a clean container while
pinning the upstream platform to the CO-7 CivicCore freeze tag,
`civiccore-m1-freeze`, rather than moving CivicCore `main`.

The harness is intentionally stricter than a normal CI run:

- the container base image is digest-pinned,
- Docker builds use `--no-cache --pull`,
- the target CivicClerk commit is fetched by SHA,
- CivicCore is installed from the `civiccore-m1-freeze` release asset,
- CivicCore freeze release assets are downloaded and checked with
  `sha256sum -c SHA256SUMS.txt`,
- `release-attestation.json` is verified with cosign against the exact
  CivicCore release workflow identity,
- `scripts/verify-release-provenance.py civiccore-m1-freeze ...` verifies the
  release provenance contract,
- `scripts/check-civiccore-placeholder-imports.py` rejects imports of
  `civiccore.catalog`, `civiccore.exemptions`, and `civiccore.scaffold`,
- `bash scripts/verify-release.sh` runs the full CivicClerk test apparatus, and
- the offline phase runs under `docker run --network none`.

The online phase mounts the host Docker socket into the cleanroom container so
`scripts/verify-release.sh` can run the disposable pgvector migration test
inside the full release apparatus. The mounted socket is used only during the
online verification phase; offline runtime proof still runs with `--network
none` and without the socket.

## Commands

Run from the CivicClerk repository root:

```bash
CLEANROOM_RUN_COUNT=2 bash scripts/run-civicclerk-cleanroom.sh
```

The host must expose a Docker socket at `/var/run/docker.sock`. If your Docker
socket lives somewhere else, set `CLEANROOM_DOCKER_SOCKET` before running the
harness.

The live CivicCore provenance check uses GitHub's API through `gh api`. CI
passes `GITHUB_TOKEN` into the online cleanroom phase to avoid unauthenticated
rate limits. Local runs can set `GITHUB_TOKEN` or `GH_TOKEN`; token values are
not written to the evidence manifests.

To target a specific commit and output directory:

```bash
CLEANROOM_RUN_COUNT=2 bash scripts/run-civicclerk-cleanroom.sh \
  <commit-sha> \
  docs/evidence/cc1-civicclerk-cleanroom-<short-sha>
```

## Evidence Shape

Each run directory contains:

- `cleanroom-manifest.json` - stable cross-machine comparison surface,
- `cleanroom-manifest.sha256` - checksum for the stable manifest,
- `cleanroom-manifest.json.sig` - local signature over the stable manifest,
- `evidence-signing-public.pem` - public key for the local signature,
- `timestamp-manifest.json` - run-specific timestamp/signature/bundle fields,
- `step-results.tsv` - pass/fail ledger for each command,
- `logs/` - command transcripts,
- `civiccore-freeze-assets/` - downloaded upstream release assets,
- `files.sha256` - checksums for evidence files, and
- `cleanroom-evidence.tar.gz` with its checksum.

The orchestrator writes `comparison.json` and `summary.md` at the evidence
root. `cleanroom-manifest.json` must hash identically across runs. Timestamped
metadata, signatures, and compressed bundles are intentionally run-specific and
are documented by each run's `timestamp-manifest.json`.

## CI

`.github/workflows/cleanroom.yml` runs the same harness on pull requests that
touch the CC-1 harness, the CivicCore pin, or the cleanroom documentation. The
workflow uploads the full evidence directory as a GitHub Actions artifact so an
outside reviewer can inspect the logs and manifests without relying on local
desktop state.

## Upstream Pin

The CivicCore freeze release is:

- tag: `civiccore-m1-freeze`,
- package asset: `civiccore-0.22.1-py3-none-any.whl`,
- Sigstore identity:
  `https://github.com/CivicSuite/civiccore/.github/workflows/release.yml@refs/tags/civiccore-m1-freeze`,
- OIDC issuer: `https://token.actions.githubusercontent.com`.

The package version remains `0.22.1`; the trust anchor is the freeze tag and its
release attestation.
