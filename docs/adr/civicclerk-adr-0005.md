# CivicClerk ADR-0005: Auth and RBAC Extraction Order

Status: Accepted

## Context

CivicClerk needs staff roles, approval records, closed-session access control,
and permission-aware archive search. CivicCore 0.22.1 does not ship a document
or RBAC table package that CivicClerk can foreign-key into.

## Decision

CivicClerk stores staff-only ACL fields as role-name arrays on sensitive
canonical tables and enforces public archive visibility through the staff
session roles exposed by the current auth layer. This is a compatibility bridge,
not a forked CivicCore RBAC implementation. When CivicCore ships released RBAC
tables, CivicClerk will add a migration/ADR to map these role names to the
shared tables.

## Consequences

- Closed-session material has explicit `sensitivity_label` and
  `staff_acl_roles` fields on relevant tables.
- Public endpoints must continue proving that anonymous and under-privileged
  users cannot infer closed-session material from bodies, counts, suggestions,
  or error messages.
- The extraction plan is a migration from role-name arrays to CivicCore RBAC
  foreign keys once those tables are released.
