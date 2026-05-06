# CivicClerk ADR-0001: Canonical v0.1.0 Table List

Status: Accepted

## Context

AGENTS.md and CivicSuite Unified Spec section 9.10 list fourteen canonical
CivicClerk tables. The early scaffold documentation described an MVP-sized
subset and left several tables as open questions, including `staff_reports`,
`public_comments`, `notices`, `minutes`, `transcripts`, `action_items`,
`ordinances_adopted`, and `closed_sessions`.

## Decision

CivicClerk keeps all fourteen canonical tables in the `civicclerk` schema. The
SQLAlchemy metadata and Alembic chain treat this list as the downstream data
contract. Future reductions are not allowed without a new ADR and migration
plan.

## Consequences

- Schema tests fail if a canonical table is removed or renamed.
- Downstream modules can depend on the table names existing, but not on planned
  columns until those columns are present in the released Alembic chain.
- Any deviation from the fourteen-table list requires a new accepted ADR before
  implementation.
