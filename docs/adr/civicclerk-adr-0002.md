# CivicClerk ADR-0002: Public Comments in v0.1.0

Status: Proposed

## Context

The unified spec and AGENTS.md canonical table list include `civicclerk.public_comments`, but the current scaffold roadmap does not explicitly place public-comment intake, moderation, display, or archival behavior into a milestone.

## Decision

Status: Open Question - pending human decision.

## Consequences

- Including public comments in v0.1.0 expands schema, public portal UX, permission checks, and archive search tests.
- Deferring public comments requires documentation updates so the landing page and manuals do not imply shipped support.
- Either path must preserve closed-session and staff-only leakage protections.
