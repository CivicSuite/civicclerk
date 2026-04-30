## Milestone 13 Staff UI Protected-Mode QA

- URL checked: `http://127.0.0.1:8790/staff`
- Auth mode checked: `open` readiness shell with trusted-header deployment guidance rendered
- Desktop evidence: `docs/screenshots/milestone13-staff-ui-desktop.png`
- Mobile evidence: `docs/screenshots/milestone13-staff-ui-mobile.png`
- Console: 0 messages expected from the shipped auth panel flow and no browser gate failures in `python scripts/verify-browser-qa.py`
- Required state verified: the auth panel renders `Trusted proxy reference`, `docs/examples/trusted-header-nginx.conf`, `Local proxy rehearsal`, `scripts/local_trusted_header_proxy.py`, `Session probe`, and `Write probe`
- Accessibility spot check: keyboard focus ring remains visible on the skip link, auth-panel copy stays readable at desktop and mobile widths, and the deployment guidance gives both real-proxy and localhost rehearsal next steps instead of a dead-end warning
