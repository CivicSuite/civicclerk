# Release Signing and Provenance

CivicClerk consumes the canonical CivicSuite release-provenance gate from
`civiccore.release_provenance`. The local `scripts/verify-release-provenance.py`
wrapper exists only so repo workflows have a stable command.

GitHub release pages can show a "Verified" badge for the target commit even
when the release tag itself is lightweight or unsigned. Treat that badge as a
commit signal only. Under the strengthened model, the Git tag is a release
pointer and the trust artifact is the Sigstore-signed `release-attestation.json`
plus `release-attestation.json.bundle`.

The active release workflow now runs CivicCore's adversarial provenance fixtures
before any build, verifies the full CivicClerk release gate against the
published CivicCore wheel, generates a schema-version-1 release attestation for
the built wheel, sdist, and checksum manifest, signs it with GitHub Actions OIDC
via cosign, and verifies the attestation before the GitHub Release is
published. Existing releases are not modified by this wiring.

## Verification Shape

For a post-baseline release, auditors verify the release with the exact repo and
tag identity:

```bash
cosign verify-blob release-attestation.json \
  --bundle release-attestation.json.bundle \
  --certificate-identity "https://github.com/CivicSuite/civicclerk/.github/workflows/release.yml@refs/tags/<tag>" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com

sha256sum -c SHA256SUMS.txt
python scripts/verify-release-provenance.py <tag> \
  --repo CivicSuite/civicclerk \
  --attestation release-attestation.json \
  --bundle release-attestation.json.bundle \
  --artifacts-dir .
```

## v0.1.20 Defect Statement

Current public artifact: `v0.1.20`

Defect an outside auditor can verify:

- GitHub tag ref `refs/tags/v0.1.20` points directly at commit
  `4a100f10694cfb167c815b98f2f2abc62d5ca2ca`.
- The target commit is GitHub-verified and uses the GitHub web-flow identity.
- The release tag is lightweight, so there is no verified annotated tag object.
- Therefore v0.1.20 fails the strengthened release provenance bar.

Reproducer:

```bash
python scripts/verify-release-provenance.py v0.1.20 --repo CivicSuite/civicclerk
```

Expected output:

```text
FAIL: Live release verification requires --attestation and --bundle under the Sigstore attestation provenance model.
```

This release is part of the Tier 1 live-surface correction window. Do not delete
or recreate it, edit its release notes, or attach retrofit attestation assets
without explicit chat authorization for that specific release.
