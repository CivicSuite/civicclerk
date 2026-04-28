# Production Depth Packet Assembly Browser QA

Generated: 2026-04-28T07:59:36.384Z

## Checks

- Surfaces: landing page (`docs/index.html`) and staff dashboard (`/staff`).
- Viewports: desktop 1440x1100 and mobile 390x1200.
- Required copy: packet assembly, database-backed packet assembly records, `/meetings/{id}/packet-assemblies`, and `CIVICCLERK_PACKET_ASSEMBLY_DB_URL` where applicable.
- Stale copy rejected: `database-backed packet and notice persistence beyond the current runtime slice`.
- Console errors: none.
- Horizontal overflow: none.
- Keyboard focus: visible focus indication checked on first focusable element where present.

## Evidence

| Surface | Viewport | Screenshot | Console | Overflow | Focus |
|---|---|---|---|---|---|
| landing | desktop | docs/browser-qa-production-depth-packet-assembly-landing-desktop.png | 0 messages | no | solid 4px none |
| landing | mobile | docs/browser-qa-production-depth-packet-assembly-landing-mobile.png | 0 messages | no | solid 4px none |
| staff | desktop | docs/browser-qa-production-depth-packet-assembly-staff-desktop.png | 0 messages | no | solid 4px none |
| staff | mobile | docs/browser-qa-production-depth-packet-assembly-staff-mobile.png | 0 messages | no | solid 4px none |

## Result

PASS: desktop and mobile browser QA found no console messages, no horizontal overflow, no stale packet-persistence copy, required packet-assembly copy present, and focus evidence captured.
