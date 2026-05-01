## Milestone 13 Staff UI Protected-Mode QA

- URL checked: `http://127.0.0.1:8891/staff` returned the current staff dashboard with `Product cockpit` and `Today's clerk desk`
- Screenshot render source: the same `civicclerk.staff_ui.render_staff_dashboard()` HTML saved as a local browser fixture for deterministic desktop/mobile capture
- Auth mode checked: `open` readiness shell with trusted-header deployment guidance rendered
- Product cockpit checked: `Product cockpit`, `Today's clerk desk`, `Items ready for clerk review`, `Live workflow actions`, `Silent dead ends`, `Go-live checks`, and the `1. Intake` / `2. Build` / `3. Publish` lane render before the workflow forms
- Live cockpit count checked: `/staff` reads the agenda intake queue and renders `Live agenda intake queue is empty; submit a department item to start the clerk desk.` when no intake records exist
- Live Agenda Intake panel checked: the panel renders `No intake items yet` with a creation fix path when the queue is empty, live reviewed queue rows when records exist, escaped submitted titles, and an actionable unavailable-store row when the database cannot be reached
- Live Packet Assembly panel checked: the panel renders `No packet assemblies yet` with a creation fix path when no packet work exists, recent live packet assembly rows when records exist, escaped packet titles, and an actionable unavailable-store row when the database cannot be reached
- Desktop evidence: `docs/screenshots/milestone13-staff-ui-desktop.png`
- Mobile evidence: `docs/screenshots/milestone13-staff-ui-mobile.png`
- Console: 0 messages expected from the shipped auth panel flow and no browser gate failures in `python scripts/verify-browser-qa.py`
- Required state verified: the auth panel renders `Trusted proxy reference`, `docs/examples/trusted-header-nginx.conf`, `Local proxy rehearsal`, `scripts/local_trusted_header_proxy.py`, `Session probe`, and `Write probe`
- Accessibility spot check: keyboard focus ring remains visible on the skip link, cockpit/auth-panel copy stays readable at desktop and mobile widths, and the deployment guidance gives both real-proxy and localhost rehearsal next steps instead of a dead-end warning
