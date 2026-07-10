# CivicClerk Tier 1 Retrofit Ledger

Status: CO-4 ledger, live-release scan current as of 2026-05-05.

This ledger records the CO-4 decision for the CivicClerk release named in the
CivicSuite finish directive. It does not rewrite history and does not alter
public release notes, tags, or assets. The correction action taken here is a
repo-controlled ledger plus documentation truth update.

Structured source of truth:
[`docs/ops/tier1-retrofit-ledger.json`](tier1-retrofit-ledger.json).

## Rules

- `v0.1.20` is a historical pre-gate release.
- `v0.1.20` has no Sigstore `release-attestation.json` or
  `release-attestation.json.bundle` public release assets.
- `v0.1.20` must not be promoted as an attested provenance baseline.
- The active CivicCore platform dependency now points to the first attested
  CivicCore baseline, `v0.22.1`.

## Entry

| Tag | Published | Git ref type | Target commit | Ledger status | Attestation | Rule |
| --- | --- | --- | --- | --- | --- | --- |
| `v0.1.20` | 2026-05-03T08:59:13Z | commit | `4a100f10694cfb167c815b98f2f2abc62d5ca2ca` | Pre-gate, no attestation | None | Do not promote as baseline. |

## Verification

```bash
python scripts/check-tier1-ledger.py
python scripts/check-tier1-ledger.py --live
```

The live check confirms the public release page exposes exactly the release
assets named by the ledger and no attestation assets.
