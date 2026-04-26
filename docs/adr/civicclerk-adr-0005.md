# CivicClerk ADR-0005: Auth and RBAC Extraction Order

Status: Proposed

## Context

AGENTS.md §3.1 marks CivicCore auth and RBAC packages as importable placeholders in v0.2.0. CivicClerk requires staff roles, approval records, closed-session access control, and permission-aware archive search.

## Decision

Status: Open Question - pending human decision.

## Consequences

- CivicClerk cannot import from `civiccore.auth` or `civiccore.rbac` in v0.1.0 unless CivicCore ships real implementations first.
- If CivicClerk implements local auth/RBAC, that choice must be reversible when CivicCore extracts shared functionality later.
- Tests must prove closed-session and staff-only content never leaks through public endpoints or search.
