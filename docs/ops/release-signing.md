# Release Signing and Provenance

CivicClerk consumes the canonical CivicSuite release-provenance gate from
`civiccore.release_provenance`. The local `scripts/verify-release-provenance.py`
wrapper exists only so repo workflows have a stable command.

GitHub release pages can show a "Verified" badge for the target commit even
when the release tag itself is lightweight or unsigned. Treat that badge as a
commit signal only. The strengthened gate verifies the tag ref, tag object,
target commit, committer identity, and release tree before any release assets
are published.

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
FAIL: v0.1.20 is a lightweight tag pointing at commit 4a100f10694cfb167c815b98f2f2abc62d5ca2ca; create a signed annotated release tag instead.
```

This release is part of the Tier 1 live-surface correction window. Do not delete
or recreate it without explicit chat authorization for that specific release.
