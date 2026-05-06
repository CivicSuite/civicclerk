# CivicClerk ADR-0002: Public Comments in v0.1.0

Status: Accepted

## Context

The unified spec includes `civicclerk.public_comments` and CC-4 added public
comment intake where a posted public record explicitly enables it. The schema
must support resident submissions without weakening closed-session or
staff-only leakage protections.

## Decision

Public comments are part of the canonical CivicClerk data model. The table keeps
meeting and agenda-item linkage for records governance, public-record linkage
for the live resident intake path, submission status, submitted timestamp, and
moderation notes for future clerk review.

## Consequences

- Comment intake remains opt-in per public record.
- Disabled or closed records return actionable refusals rather than accepting
  comments.
- Closed-session and staff-only content stays out of anonymous public responses,
  search counts, suggestions, and not-found responses.
