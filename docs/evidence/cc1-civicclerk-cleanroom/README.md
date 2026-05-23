# CC-1 CivicClerk Cleanroom Evidence

This directory is the repo-controlled anchor for CC-1 cleanroom evidence.

The full evidence bundle is produced by:

```bash
CLEANROOM_RUN_COUNT=2 bash scripts/run-civicclerk-cleanroom.sh
```

The online phase requires access to the host Docker socket so the full
`scripts/verify-release.sh` gate can launch its disposable pgvector migration
container. Set `CLEANROOM_DOCKER_SOCKET` if the socket is not available at
`/var/run/docker.sock`.

The online phase also accepts `GITHUB_TOKEN` or `GH_TOKEN` for the live
CivicCore provenance API check. CI supplies the token automatically; evidence
records only that authenticated API access is supported, never the token value.

Generated run directories are intentionally not pre-populated here because they
contain large logs, downloaded upstream assets, and compressed bundles. The
pull-request cleanroom workflow uploads those generated directories as GitHub
Actions artifacts. Sprint-boundary reports link the workflow artifact and record
the stable `cleanroom-manifest.json` hashes.

Required stable comparison surface:

- `comparison.json` at the generated evidence root,
- each run's `cleanroom-manifest.json`,
- matching stable manifest hashes across both runs,
- each run's `timestamp-manifest.json` documenting run-specific fields.

Upstream trust anchor:

- CivicCore release tag: `v1.2.0`,
- CivicCore package asset: `civiccore-1.0.0-py3-none-any.whl`,
- expected Sigstore identity:
  `https://github.com/CivicSuite/civiccore/.github/workflows/release.yml@refs/tags/v1.2.0`,
- expected issuer: `https://token.actions.githubusercontent.com`.
