"""Accessible staff workflow screens for CivicClerk staff."""

from __future__ import annotations

from civicclerk import __version__

SCREEN_CARDS = [
    {
        "id": "intake",
        "title": "Agenda Intake",
        "eyebrow": "Department submission queue",
        "summary": "Review submitted items, decide readiness, and preserve clerk review evidence.",
        "primary_api": "/agenda-intake",
        "secondary_api": "/agenda-intake/{id}/review",
        "status": "Live API + screen pattern",
        "cta": "Review readiness",
        "rows": [
            ("Public Works", "Crosswalk safety update", "READY", "Move toward packet assembly."),
            ("Finance", "Quarterly appropriation amendment", "NEEDS INFO", "Request fiscal attachment."),
            ("Parks", "Trail maintenance award", "PARTIAL", "One source reference missing."),
        ],
        "fix": "If the queue is empty, submit a department item with title, department, summary, and source references.",
    },
    {
        "id": "packet",
        "title": "Packet Assembly",
        "eyebrow": "Source + citation binder",
        "summary": "Tie agenda item ids to packet versions, source files, citations, and audit evidence.",
        "primary_api": "/meetings/{id}/packet-assemblies",
        "secondary_api": "/packet-assemblies/{id}/finalize + /meetings/{id}/export-bundle",
        "status": "Live API + screen pattern",
        "cta": "Finalize packet",
        "rows": [
            ("Packet v3", "4 sources", "DRAFT", "Citation review still open."),
            ("Packet v2", "4 sources", "FINALIZED", "Ready for export bundle."),
            ("Packet v1", "3 sources", "SUPERSEDED", "Kept for audit trail."),
        ],
        "fix": "If finalization fails, create the packet assembly record first and include at least one source reference and citation.",
    },
    {
        "id": "notice",
        "title": "Notice Checklist",
        "eyebrow": "Deadline + posting proof",
        "summary": "Persist notice compliance outcomes, warning details, and posting-proof metadata.",
        "primary_api": "/meetings/{id}/notice-checklists",
        "secondary_api": "/notice-checklists/{id}/posting-proof",
        "status": "Live API + screen pattern",
        "cta": "Attach posting proof",
        "rows": [
            ("Regular notice", "72 hours", "CHECKED", "Compliant, awaiting posting proof."),
            ("Special notice", "24 hours", "WARNING", "Statutory basis required."),
            ("Emergency notice", "Immediate", "POSTED", "Proof metadata attached."),
        ],
        "fix": "If posting proof cannot attach, create the notice checklist record before posting proof metadata.",
    },
    {
        "id": "outcomes",
        "title": "Meeting Outcomes",
        "eyebrow": "Motions, votes, and actions",
        "summary": "Capture immutable motions and votes, then create action items tied to the meeting outcome.",
        "primary_api": "/meetings/{id}/motions",
        "secondary_api": "/meetings/{id}/action-items",
        "status": "Live API + screen pattern",
        "cta": "Capture outcome",
        "rows": [
            ("Council", "Approve packet as amended", "CAPTURED", "Vote recorded; action item open."),
            ("Finance", "Return with fee study", "ACTION OPEN", "Assigned to Finance."),
            ("Clerk", "Vote correction", "APPENDED", "Original vote preserved."),
        ],
        "fix": "If action creation fails, capture the source motion for this meeting first and use that motion id.",
    },
    {
        "id": "minutes",
        "title": "Minutes Draft",
        "eyebrow": "Citations + provenance",
        "summary": "Create AI-assisted minutes drafts only when every material sentence cites source material.",
        "primary_api": "/meetings/{id}/minutes/drafts",
        "secondary_api": "/minutes/{id}/post",
        "status": "Live API + screen pattern",
        "cta": "Create draft",
        "rows": [
            ("Clerk", "Motion sentence", "CITED", "Source material attached."),
            ("Clerk", "Vote sentence", "CITED", "Vote record attached."),
            ("System", "Auto-post attempt", "BLOCKED", "Human approval required."),
        ],
        "fix": "If draft creation fails, add citations to every sentence and use source ids from the source material list.",
    },
    {
        "id": "archive",
        "title": "Public Archive",
        "eyebrow": "Public-safe records",
        "summary": "Publish a public meeting record and verify anonymous archive views exclude closed-session material.",
        "primary_api": "/meetings/{id}/public-record",
        "secondary_api": "/public/archive/search",
        "status": "Live API + screen pattern",
        "cta": "Publish archive record",
        "rows": [
            ("Clerk", "Public agenda", "POSTED", "Visible in public calendar."),
            ("Clerk", "Approved minutes", "APPROVED", "Visible in archive search."),
            ("System", "Closed notes", "FILTERED", "Anonymous users cannot see restricted material."),
        ],
        "fix": "If publishing fails, create the meeting first and provide public-safe agenda, packet, and approved-minutes text.",
    },
    {
        "id": "imports",
        "title": "Connector Import",
        "eyebrow": "Local export payloads",
        "summary": "Normalize local agenda-platform exports with source provenance and no outbound network calls.",
        "primary_api": "/imports/{connector}/meetings",
        "secondary_api": "Granicus, Legistar, PrimeGov, NovusAGENDA",
        "status": "Live API + screen pattern",
        "cta": "Import payload",
        "rows": [
            ("Clerk", "Granicus export", "NORMALIZED", "Source provenance attached."),
            ("IT", "Legistar export", "VALIDATED", "Required fields checked."),
            ("System", "Outbound network", "BLOCKED", "Local payload only."),
        ],
        "fix": "If import fails, choose a supported connector and paste a local export payload with its required meeting id, title, and start fields.",
    },
]

STATE_CARDS = [
    ("loading", "Loading", "The staff screen should tell clerks which workflow is loading and what to try if it stalls."),
    ("success", "Success", "Completed actions should name the affected record and the next safe step."),
    ("empty", "Empty", "Empty queues should say what to create first and link to the matching API path."),
    ("error", "Error", "Errors must explain what failed and how staff can fix the input."),
    ("partial", "Partial", "Partial imports or checks should identify what succeeded, what did not, and what to retry."),
]


def render_staff_dashboard() -> str:
    """Render the current staff workflow screens as dependency-free HTML."""
    nav_buttons = "\n".join(
        f"""
        <button class="screen-tab" data-target="{card["id"]}" aria-controls="screen-{card["id"]}">
          <span>{card["eyebrow"]}</span>
          {card["title"]}
        </button>
        """
        for card in SCREEN_CARDS
    )
    screen_cards = "\n".join(_render_screen_card(card, index == 0) for index, card in enumerate(SCREEN_CARDS))
    state_cards = "\n".join(
        f"""
        <article class="state-card" data-state="{state}">
          <h3>{label}</h3>
          <p>{copy}</p>
          <p><strong>How to fix:</strong> follow the visible next step before retrying.</p>
        </article>
        """
        for state, label, copy in STATE_CARDS
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CivicClerk Staff Workflow Screens</title>
  <style>
    :root {{
      --ink: #17201b;
      --muted: #53635b;
      --paper: #f8f4ea;
      --panel: #fffdf8;
      --line: #d8d0c1;
      --accent: #2f6f5e;
      --accent-dark: #174739;
      --warn: #8a5a16;
      --error: #8c2f24;
      --good: #26714d;
      --blueprint: rgba(47, 111, 94, .11);
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; overflow-x: hidden; }}
    body {{
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(47,111,94,.2), transparent 32rem),
        linear-gradient(180deg, var(--paper), #efe7d8);
      line-height: 1.55;
    }}
    .skip {{ position: absolute; left: -999px; top: 12px; background: var(--accent-dark); color: white; padding: 10px 14px; border-radius: 10px; }}
    .skip:focus {{ left: 12px; z-index: 5; }}
    a {{ color: var(--accent-dark); }}
    a:focus-visible, button:focus-visible, input:focus-visible, textarea:focus-visible, select:focus-visible {{ outline: 4px solid var(--accent-dark); outline-offset: 4px; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 48px 20px; }}
    .hero {{ background: rgba(255,255,255,.82); border: 1px solid var(--line); border-radius: 28px; padding: 34px; box-shadow: 0 18px 60px rgba(23,32,27,.08); position: relative; overflow: hidden; }}
    .hero::after {{ content: ""; position: absolute; inset: auto -8% -40% 44%; height: 280px; background: repeating-linear-gradient(135deg, var(--blueprint) 0 10px, transparent 10px 24px); transform: rotate(-8deg); pointer-events: none; }}
    .eyebrow {{ color: var(--accent); font-weight: 700; letter-spacing: .08em; text-transform: uppercase; font-size: .78rem; }}
    h1 {{ font-size: clamp(2.2rem, 7vw, 5rem); line-height: .95; margin: 14px 0 18px; }}
    h2 {{ margin-top: 34px; }}
    p {{ max-width: 78ch; }}
    .status {{ color: var(--warn); font-weight: 700; }}
    .auth-panel {{ margin-top: 22px; background: rgba(255,253,248,.94); border: 1px solid var(--line); border-radius: 24px; padding: 22px; box-shadow: 0 18px 60px rgba(23,32,27,.06); }}
    .auth-panel p {{ margin-top: 0; }}
    .auth-grid {{ display: grid; grid-template-columns: 1.3fr .9fr; gap: 16px; align-items: start; }}
    .auth-status {{ border-radius: 18px; padding: 14px; background: var(--panel); border: 1px solid var(--line); }}
    .auth-status[data-state="success"] {{ border-color: rgba(38,113,77,.45); background: #f0faf4; }}
    .auth-status[data-state="error"] {{ border-color: rgba(140,47,36,.45); background: #fff3f0; }}
    .auth-status[data-state="loading"] {{ border-color: rgba(47,111,94,.45); }}
    .screen-nav {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin: 28px 0 18px; }}
    .screen-tab {{ appearance: none; border: 1px solid var(--line); border-radius: 18px; background: var(--panel); color: var(--ink); padding: 16px; text-align: left; font: inherit; cursor: pointer; box-shadow: 0 8px 24px rgba(23,32,27,.06); }}
    .screen-tab span {{ display: block; color: var(--accent); font-size: .72rem; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; }}
    .screen-tab[aria-selected="true"] {{ background: var(--accent-dark); color: white; border-color: var(--accent-dark); transform: translateY(-2px); }}
    .screen-tab[aria-selected="true"] span {{ color: #d8efe2; }}
    .screen-panel {{ display: none; background: rgba(255,253,248,.94); border: 1px solid var(--line); border-radius: 28px; padding: 24px; box-shadow: 0 18px 60px rgba(23,32,27,.08); }}
    .screen-panel.is-active {{ display: block; }}
    .screen-top {{ display: flex; gap: 18px; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; }}
    .pill {{ display: inline-block; border-radius: 999px; padding: 6px 10px; background: #e3efe8; color: var(--accent-dark); font-weight: 700; font-size: .82rem; }}
    .cta {{ border: 0; border-radius: 999px; background: var(--accent); color: white; padding: 12px 16px; font: inherit; font-weight: 700; }}
    .work-table {{ width: 100%; border-collapse: collapse; margin-top: 18px; overflow: hidden; border-radius: 18px; }}
    .work-table th, .work-table td {{ border-bottom: 1px solid var(--line); padding: 12px; text-align: left; vertical-align: top; }}
    .work-table th {{ color: var(--muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 4px 8px; background: #efe7d8; font-weight: 700; }}
    .badge[data-tone="ready"], .badge[data-tone="finalized"], .badge[data-tone="posted"] {{ background: #dbeee3; color: var(--good); }}
    .badge[data-tone="warning"], .badge[data-tone="needs-info"], .badge[data-tone="partial"] {{ background: #f4e1bd; color: var(--warn); }}
    .api-strip {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-top: 16px; }}
    .api-strip p {{ margin: 0; background: #eadfca; padding: 12px; border-radius: 14px; }}
    .fix-path {{ background: #fff7e4; border-left: 5px solid var(--warn); padding: 12px 14px; border-radius: 12px; margin-top: 16px; }}
    .live-action {{ margin-top: 18px; border: 1px solid rgba(47,111,94,.28); border-radius: 22px; padding: 18px; background: linear-gradient(135deg, rgba(47,111,94,.08), rgba(255,253,248,.95)); }}
    .live-action h4 {{ margin: 0 0 8px; font-size: 1.15rem; }}
    .form-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    label {{ display: grid; gap: 5px; font-weight: 700; }}
    input, textarea, select {{ width: 100%; border: 1px solid var(--line); border-radius: 12px; padding: 10px; font: inherit; background: white; color: var(--ink); }}
    textarea {{ min-height: 84px; resize: vertical; }}
    .span-2 {{ grid-column: 1 / -1; }}
    .live-actions {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }}
    .secondary {{ border: 1px solid var(--accent); border-radius: 999px; background: transparent; color: var(--accent-dark); padding: 10px 14px; font: inherit; font-weight: 700; }}
    .live-output {{ margin-top: 14px; border-radius: 16px; padding: 14px; background: var(--panel); border: 1px solid var(--line); }}
    .live-output[data-state="success"] {{ border-color: rgba(38,113,77,.45); background: #f0faf4; }}
    .live-output[data-state="error"] {{ border-color: rgba(140,47,36,.45); background: #fff3f0; }}
    .live-output[data-state="loading"] {{ border-color: rgba(47,111,94,.45); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin-top: 22px; }}
    .state-card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 20px; padding: 20px; }}
    .state-card h3 {{ margin-top: 0; }}
    code {{ background: #eadfca; padding: 2px 5px; border-radius: 5px; overflow-wrap: anywhere; }}
    [data-state="error"] {{ border-color: rgba(140,47,36,.45); }}
    [data-state="partial"] {{ border-color: rgba(138,90,22,.5); }}
    @media (max-width: 640px) {{
      main {{ padding: 30px 14px; }}
      .hero, .screen-panel, .state-card {{ border-radius: 20px; padding: 18px; }}
      .auth-grid, .screen-nav, .api-strip, .form-grid {{ grid-template-columns: 1fr; }}
      .work-table {{ display: block; overflow-x: auto; }}
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <a class="skip" href="#workflow-screens">Skip to workflow screens</a>
  <main aria-label="CivicClerk staff workflow screens">
    <section class="hero">
      <div class="eyebrow">CivicClerk v{__version__}</div>
      <h1>CivicClerk Staff Workflow Screens</h1>
      <p class="status">These are browser-visible staff workflow screens for the released API foundation. They guide agenda intake review, packet assembly and export, notice checklist/posting proof, outcome capture, cited minutes drafting, public archive publishing, and connector import work, and they now disclose whether the service is running in local open mode, bearer-protected staff mode, or trusted-header staff mode.</p>
      <p>The screens show the live API paths, safe next actions, required staff states, actionable fix copy, and the first deployment-ready staff auth contract for the service slices available today. Full OIDC login is not shipped yet; this screen is the bridge contract until that lands.</p>
    </section>

    <section class="auth-panel" aria-labelledby="staff-auth-heading">
      <div class="auth-grid">
        <div>
          <h2 id="staff-auth-heading">Staff access and readiness check</h2>
          <p>Use this panel before live staff actions. In local rehearsals, CivicClerk can run in open mode. For real staff access, either switch the service to bearer mode and enter a token mapped through <code>CIVICCLERK_STAFF_AUTH_TOKEN_ROLES</code>, or front the service with a trusted reverse proxy that injects <code>CIVICCLERK_STAFF_SSO_PRINCIPAL_HEADER</code> and <code>CIVICCLERK_STAFF_SSO_ROLES_HEADER</code> from a source inside <code>CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES</code>. If you need a one-workstation trusted-header rehearsal first, use <code>scripts/local_trusted_header_proxy.py</code> with the loopback starter allowlist <code>127.0.0.1/32</code> instead of sending identity headers straight to the app.</p>
          <p>The readiness check uses <code>/staff/auth-readiness</code> to tell IT staff whether the current auth mode is deployment-ready before a live authenticated session is tested, and it now returns a concrete session probe plus a protected write probe when bearer or trusted-header mode is ready.</p>
          <label>Bearer token for staff actions
            <input id="staff-auth-token" name="staff_auth_token" placeholder="Paste bearer token when bearer mode is enabled" autocomplete="off">
          </label>
          <div class="live-actions">
            <button class="cta" id="staff-auth-refresh" type="button">Check staff access</button>
          </div>
        </div>
        <div id="staff-auth-status" class="auth-status" data-state="loading" role="status" aria-live="polite">
          <strong>Loading:</strong> checking staff auth readiness...
        </div>
      </div>
    </section>

    <section id="workflow-screens" aria-labelledby="workflow-heading">
      <h2 id="workflow-heading">Workflow screens</h2>
      <div class="screen-nav" role="tablist" aria-label="Staff workflow screen selector">
        {nav_buttons}
      </div>
      {screen_cards}
    </section>

    <section aria-labelledby="states-heading">
      <h2 id="states-heading">Required rendered states</h2>
      <p>Every future staff workflow screen must render these states with actionable copy, keyboard focus, contrast, and zero browser console errors.</p>
      <div class="grid">
        {state_cards}
      </div>
    </section>
  </main>
  <script>
    const tabs = [...document.querySelectorAll(".screen-tab")];
    const panels = [...document.querySelectorAll(".screen-panel")];
    const authTokenInput = document.querySelector("#staff-auth-token");
    const authRefreshButton = document.querySelector("#staff-auth-refresh");
    const authStatus = document.querySelector("#staff-auth-status");
    function activate(target) {{
      tabs.forEach((tab) => tab.setAttribute("aria-selected", String(tab.dataset.target === target)));
      panels.forEach((panel) => panel.classList.toggle("is-active", panel.id === `screen-${{target}}`));
    }}
    tabs.forEach((tab) => tab.addEventListener("click", () => activate(tab.dataset.target)));
    const requestedScreen = new URLSearchParams(window.location.search).get("screen");
    const initialScreen = tabs.some((tab) => tab.dataset.target === requestedScreen) ? requestedScreen : "intake";
    activate(initialScreen);

    const intakeForm = document.querySelector("#agenda-intake-form");
    const reviewForm = document.querySelector("#agenda-review-form");
    const output = document.querySelector("#agenda-intake-output");
    const itemIdInput = document.querySelector("#review-item-id");
    const packetForm = document.querySelector("#packet-assembly-form");
    const packetOutput = document.querySelector("#packet-assembly-output");
    const packetExportForm = document.querySelector("#packet-export-form");
    const packetExportOutput = document.querySelector("#packet-export-output");
    const noticeForm = document.querySelector("#notice-checklist-form");
    const noticeOutput = document.querySelector("#notice-checklist-output");
    const outcomeForm = document.querySelector("#meeting-outcomes-form");
    const outcomeOutput = document.querySelector("#meeting-outcomes-output");
    const minutesForm = document.querySelector("#minutes-draft-form");
    const minutesOutput = document.querySelector("#minutes-draft-output");
    const archiveForm = document.querySelector("#public-archive-form");
    const archiveOutput = document.querySelector("#public-archive-output");
    const importForm = document.querySelector("#connector-import-form");
    const importOutput = document.querySelector("#connector-import-output");

    function authHeaders(includeJson = false) {{
      const headers = {{}};
      const token = authTokenInput?.value?.trim();
      if (includeJson) {{
        headers["content-type"] = "application/json";
      }}
      if (token) {{
        headers.Authorization = `Bearer ${{token}}`;
      }}
      return headers;
    }}

    function setAuthStatus(state, html) {{
      authStatus.dataset.state = state;
      authStatus.innerHTML = html;
    }}

    function setOutput(state, html) {{
      output.dataset.state = state;
      output.innerHTML = html;
    }}

    async function postJson(path, payload) {{
      const response = await fetch(path, {{
        method: "POST",
        headers: authHeaders(true),
        body: JSON.stringify(payload),
      }});
      const data = await response.json();
      if (!response.ok) {{
        const detail = data.detail || {{}};
        throw new Error(`${{detail.message || "Request failed."}} How to fix: ${{detail.fix || "Check the required fields and retry."}}`);
      }}
      return data;
    }}

    function formatReadinessChecks(checks) {{
      if (!Array.isArray(checks) || checks.length === 0) {{
        return "";
      }}
      const items = checks.map((check) => `<li><strong>${{check.name}}:</strong> ${{check.status}}${{check.value ? ` (${{
        check.value
      }})` : ""}}</li>`);
      return `<ul>${{items.join("")}}</ul>`;
    }}

    function formatKeyValueTable(data) {{
      if (!data || typeof data !== "object" || Array.isArray(data) || Object.keys(data).length === 0) {{
        return "";
      }}
      const rows = Object.entries(data).map(([key, value]) => `<li><strong>${{key}}:</strong> <code>${{value}}</code></li>`);
      return `<ul>${{rows.join("")}}</ul>`;
    }}

    function formatOrderedList(items) {{
      if (!Array.isArray(items) || items.length === 0) {{
        return "";
      }}
      return `<ol>${{items.map((item) => `<li>${{item}}</li>`).join("")}}</ol>`;
    }}

    function formatWarningList(items) {{
      if (!Array.isArray(items) || items.length === 0) {{
        return "";
      }}
      return `<ul>${{items.map((item) => `<li>${{item}}</li>`).join("")}}</ul>`;
    }}

    function formatProbe(label, probe) {{
      if (!probe || typeof probe !== "object") {{
        return "";
      }}
      const headers = probe.headers && typeof probe.headers === "object"
        ? `<li><strong>Headers:</strong> <code>${{Object.entries(probe.headers).map(([key, value]) => `${{key}}: ${{value}}`).join("; ")}}</code></li>`
        : "";
      const body = probe.body
        ? `<li><strong>Body:</strong><pre>${{JSON.stringify(probe.body, null, 2)}}</pre></li>`
        : "";
      const note = probe.note ? `<li><strong>Why this matters:</strong> ${{probe.note}}</li>` : "";
        return `
          <div class="probe-card">
            <strong>${{label}}</strong>
            <ul>
            <li><strong>Method:</strong> <code>${{probe.method || "GET"}}</code></li>
            <li><strong>Path:</strong> <code>${{probe.path || "/"}}</code></li>
            ${{headers}}
            ${{body}}
            ${{note}}
          </ul>
          </div>
        `;
      }}

    function formatLocalProxyRehearsal(rehearsal) {{
      if (!rehearsal || typeof rehearsal !== "object") {{
        return "";
      }}
      const command = Array.isArray(rehearsal.command)
        ? rehearsal.command.map((part) => `${{part}}`).join(" ")
        : "";
      const trustedProxyCidrs = Array.isArray(rehearsal.trusted_proxy_cidrs)
        ? rehearsal.trusted_proxy_cidrs.map((cidr) => `<code>${{cidr}}</code>`).join(", ")
        : "<code>not set</code>";
      return `
        <div class="probe-card">
          <strong>Local proxy rehearsal</strong>
          <ul>
            <li><strong>Scope:</strong> <code>${{rehearsal.scope || "not set"}}</code></li>
            <li><strong>Helper script:</strong> <code>${{rehearsal.script_path || "not set"}}</code></li>
            <li><strong>Listen URL:</strong> <code>${{rehearsal.listen_url || "not set"}}</code></li>
            <li><strong>Upstream URL:</strong> <code>${{rehearsal.upstream_url || "not set"}}</code></li>
            <li><strong>Trusted proxy CIDRs:</strong> ${{trustedProxyCidrs}}</li>
            <li><strong>Command:</strong> <code>${{command || "not set"}}</code></li>
          </ul>
          <strong>App env</strong>
          ${{formatKeyValueTable(rehearsal.app_env)}}
          <strong>Proxy env</strong>
          ${{formatKeyValueTable(rehearsal.proxy_env)}}
          <strong>Injected headers</strong>
          ${{formatKeyValueTable(rehearsal.headers)}}
          <strong>Steps</strong>
          ${{formatOrderedList(rehearsal.steps)}}
          <strong>Warnings</strong>
          ${{formatWarningList(rehearsal.warnings)}}
        </div>
      `;
    }}

    async function refreshStaffSession() {{
      setAuthStatus("loading", "<strong>Loading:</strong> checking staff auth readiness...");
      try {{
        const readinessResponse = await fetch("/staff/auth-readiness");
        const readiness = await readinessResponse.json();
        if (!readinessResponse.ok) {{
          const detail = readiness.detail || {{}};
          throw new Error(`${{detail.message || "Staff auth readiness check failed."}} How to fix: ${{detail.fix || "Check the configured auth mode and retry."}}`);
        }}
        const readinessChecks = formatReadinessChecks(readiness.checks);
        const localProxy = formatLocalProxyRehearsal(readiness.local_proxy_rehearsal);
        if (readiness.mode === "trusted_header") {{
          const readinessState = readiness.ready ? "success" : "error";
          const probes = `${{formatProbe("Session probe", readiness.session_probe)}}${{formatProbe("Write probe", readiness.write_probe)}}`;
          setAuthStatus(
            readinessState,
            `<strong>${{readiness.ready ? "Ready" : "Not ready"}}:</strong> ${{readiness.message}}<br><strong>Provider:</strong> ${{readiness.provider || "not set"}}<br><strong>Principal header:</strong> <code>${{readiness.principal_header || "not set"}}</code><br><strong>Roles header:</strong> <code>${{readiness.roles_header || "not set"}}</code>${{readinessChecks}}${{localProxy}}${{probes}}<strong>Next step:</strong> ${{readiness.fix}}`,
            );
            return;
          }}
        if (readiness.mode === "open") {{
          setAuthStatus(
            "success",
            `<strong>Rehearsal mode:</strong> ${{readiness.message}}${{readinessChecks}}<strong>Next step:</strong> ${{readiness.fix}}`,
          );
          return;
        }}
        if (!readiness.ready) {{
          setAuthStatus(
            "error",
            `<strong>Not ready:</strong> ${{readiness.message}}${{readinessChecks}}<strong>Next step:</strong> ${{readiness.fix}}`,
          );
          return;
        }}
        const probes = `${{formatProbe("Session probe", readiness.session_probe)}}${{formatProbe("Write probe", readiness.write_probe)}}`;
        const response = await fetch("/staff/session", {{ headers: authHeaders(false) }});
        const data = await response.json();
        if (!response.ok) {{
          const detail = data.detail || {{}};
          setAuthStatus(
            "error",
            `<strong>Ready, but session check failed:</strong> ${{detail.message || "Staff access check failed."}}${{readinessChecks}}${{probes}}<strong>Next step:</strong> ${{detail.fix || readiness.fix || "Check the configured auth mode and retry."}}`,
          );
          return;
        }}
        const roles = (data.roles || []).join(", ");
        setAuthStatus(
          "success",
          `<strong>Success:</strong> mode is <code>${{data.mode}}</code>.<br><strong>Roles:</strong> ${{roles || "none"}}${{readinessChecks}}${{probes}}<strong>Next step:</strong> ${{data.fix || readiness.fix || "Proceed with staff workflow actions."}}`,
        );
      }} catch (error) {{
        setAuthStatus("error", `<strong>Error:</strong> ${{error.message}}`);
      }}
    }}

    authRefreshButton?.addEventListener("click", () => {{
      refreshStaffSession();
    }});
    authTokenInput?.addEventListener("change", () => {{
      refreshStaffSession();
    }});
    refreshStaffSession();

    async function createDemoMeeting(title) {{
      return postJson("/meetings", {{
        title,
        meeting_type: "regular",
        scheduled_start: "2026-05-05T19:00:00Z",
      }});
    }}

    intakeForm?.addEventListener("submit", async (event) => {{
      event.preventDefault();
      setOutput("loading", "<strong>Loading:</strong> submitting agenda intake item...");
      const form = new FormData(intakeForm);
      const payload = {{
        title: form.get("title"),
        department_name: form.get("department_name"),
        submitted_by: form.get("submitted_by"),
        summary: form.get("summary"),
        source_references: [{{ label: form.get("source_label"), url: form.get("source_url") }}],
      }};
      try {{
        const item = await postJson("/agenda-intake", payload);
        itemIdInput.value = item.id;
        setOutput("success", `<strong>Success:</strong> ${{item.title}} is now ${{item.readiness_status}}. <br><strong>Record id:</strong> <code>${{item.id}}</code><br><strong>Next step:</strong> review readiness below.`);
      }} catch (error) {{
        setOutput("error", `<strong>Error:</strong> ${{error.message}}`);
      }}
    }});

    reviewForm?.addEventListener("submit", async (event) => {{
      event.preventDefault();
      setOutput("loading", "<strong>Loading:</strong> recording clerk readiness review...");
      const form = new FormData(reviewForm);
      const itemId = form.get("item_id");
      const payload = {{
        reviewer: form.get("reviewer"),
        ready: form.get("ready") === "true",
        notes: form.get("notes"),
      }};
      try {{
        const item = await postJson(`/agenda-intake/${{itemId}}/review`, payload);
        const nextStep = item.readiness_status === "READY" ? "move toward packet assembly." : "request the missing information before packet assembly.";
        setOutput("success", `<strong>Success:</strong> readiness is ${{item.readiness_status}} for <code>${{item.id}}</code>.<br><strong>Next step:</strong> ${{nextStep}}`);
      }} catch (error) {{
        setOutput("error", `<strong>Error:</strong> ${{error.message}}`);
      }}
    }});

    packetForm?.addEventListener("submit", async (event) => {{
      event.preventDefault();
      packetOutput.dataset.state = "loading";
      packetOutput.innerHTML = "<strong>Loading:</strong> creating packet assembly record...";
      const form = new FormData(packetForm);
      try {{
        const meeting = await createDemoMeeting(form.get("meeting_title"));
        const draft = await postJson(`/meetings/${{meeting.id}}/packet-assemblies`, {{
          title: form.get("title"),
          agenda_item_ids: [form.get("agenda_item_id")],
          actor: form.get("actor"),
          source_references: [{{ source_id: "source-1", label: form.get("source_label") }}],
          citations: [{{ source_id: "source-1", quote: form.get("citation") }}],
        }});
        const finalized = await postJson(`/packet-assemblies/${{draft.id}}/finalize`, {{ actor: form.get("actor") }});
        packetOutput.dataset.state = "success";
        packetOutput.innerHTML = `<strong>Success:</strong> packet assembly <code>${{finalized.id}}</code> is ${{finalized.status}} for meeting <code>${{meeting.id}}</code>.<br><strong>Next step:</strong> export the finalized packet bundle when sources are public-safe.`;
      }} catch (error) {{
        packetOutput.dataset.state = "error";
        packetOutput.innerHTML = `<strong>Error:</strong> ${{error.message}}`;
      }}
    }});

    packetExportForm?.addEventListener("submit", async (event) => {{
      event.preventDefault();
      packetExportOutput.dataset.state = "loading";
      packetExportOutput.innerHTML = "<strong>Loading:</strong> creating records-ready packet export bundle...";
      const form = new FormData(packetExportForm);
      try {{
        const meeting = await createDemoMeeting(form.get("meeting_title"));
        await postJson(`/meetings/${{meeting.id}}/packet-snapshots`, {{
          agenda_item_ids: [form.get("agenda_item_id")],
          actor: form.get("actor"),
        }});
        const exported = await postJson(`/meetings/${{meeting.id}}/export-bundle`, {{
          bundle_name: form.get("bundle_name"),
          actor: form.get("actor"),
          public_bundle: true,
          sources: [{{
            source_id: form.get("source_id"),
            title: form.get("source_title"),
            kind: "document",
            source_system: "local_file",
            source_path: form.get("source_path"),
            citation_label: form.get("citation_label"),
          }}],
        }});
        packetExportOutput.dataset.state = "success";
        packetExportOutput.innerHTML = `<strong>Success:</strong> exported packet bundle for meeting <code>${{meeting.id}}</code> at <code>${{exported.bundle_path}}</code>.<br><strong>Manifest:</strong> <code>${{exported.manifest_path}}</code>. <strong>Checksums:</strong> <code>${{exported.checksums_path}}</code>.<br><strong>Next step:</strong> validate the manifest and attach the checksum file to the records package.`;
      }} catch (error) {{
        packetExportOutput.dataset.state = "error";
        packetExportOutput.innerHTML = `<strong>Error:</strong> ${{error.message}}`;
      }}
    }});

    noticeForm?.addEventListener("submit", async (event) => {{
      event.preventDefault();
      noticeOutput.dataset.state = "loading";
      noticeOutput.innerHTML = "<strong>Loading:</strong> checking notice compliance and attaching proof...";
      const form = new FormData(noticeForm);
      try {{
        const meeting = await createDemoMeeting(form.get("meeting_title"));
        const checklist = await postJson(`/meetings/${{meeting.id}}/notice-checklists`, {{
          notice_type: "regular",
          posted_at: form.get("posted_at"),
          minimum_notice_hours: Number(form.get("minimum_notice_hours")),
          statutory_basis: form.get("statutory_basis"),
          approved_by: form.get("approved_by"),
          actor: form.get("actor"),
        }});
        const posted = await postJson(`/notice-checklists/${{checklist.id}}/posting-proof`, {{
          actor: form.get("actor"),
          posting_proof: {{ location: form.get("location"), posted_url: form.get("posted_url") }},
        }});
        noticeOutput.dataset.state = "success";
        noticeOutput.innerHTML = `<strong>Success:</strong> notice checklist <code>${{posted.id}}</code> is ${{posted.status}} with posting proof saved.<br><strong>Next step:</strong> keep the proof metadata with the public meeting record.`;
      }} catch (error) {{
        noticeOutput.dataset.state = "error";
        noticeOutput.innerHTML = `<strong>Error:</strong> ${{error.message}}`;
      }}
    }});

    outcomeForm?.addEventListener("submit", async (event) => {{
      event.preventDefault();
      outcomeOutput.dataset.state = "loading";
      outcomeOutput.innerHTML = "<strong>Loading:</strong> creating meeting outcome records...";
      const form = new FormData(outcomeForm);
      try {{
        const meeting = await createDemoMeeting(form.get("meeting_title"));
        const motion = await postJson(`/meetings/${{meeting.id}}/motions`, {{
          text: form.get("motion_text"),
          actor: form.get("actor"),
        }});
        const vote = await postJson(`/motions/${{motion.id}}/votes`, {{
          voter_name: form.get("voter_name"),
          vote: form.get("vote"),
          actor: form.get("actor"),
        }});
        const action = await postJson(`/meetings/${{meeting.id}}/action-items`, {{
          description: form.get("action_description"),
          assigned_to: form.get("assigned_to"),
          source_motion_id: motion.id,
          actor: form.get("actor"),
        }});
        outcomeOutput.dataset.state = "success";
        outcomeOutput.innerHTML = `<strong>Success:</strong> captured motion <code>${{motion.id}}</code>, vote <code>${{vote.id}}</code>, and action item <code>${{action.id}}</code> for meeting <code>${{meeting.id}}</code>.<br><strong>Next step:</strong> review the action assignment before minutes drafting.`;
      }} catch (error) {{
        outcomeOutput.dataset.state = "error";
        outcomeOutput.innerHTML = `<strong>Error:</strong> ${{error.message}}`;
      }}
    }});

    minutesForm?.addEventListener("submit", async (event) => {{
      event.preventDefault();
      minutesOutput.dataset.state = "loading";
      minutesOutput.innerHTML = "<strong>Loading:</strong> creating citation-gated minutes draft...";
      const form = new FormData(minutesForm);
      try {{
        const meeting = await createDemoMeeting(form.get("meeting_title"));
        const sourceId = form.get("source_id");
        const draft = await postJson(`/meetings/${{meeting.id}}/minutes/drafts`, {{
          model: form.get("model"),
          prompt_version: form.get("prompt_version"),
          human_approver: form.get("human_approver"),
          source_materials: [{{
            source_id: sourceId,
            label: form.get("source_label"),
            text: form.get("source_text"),
          }}],
          sentences: [{{
            text: form.get("sentence_text"),
            citations: [sourceId],
          }}],
        }});
        minutesOutput.dataset.state = "success";
        minutesOutput.innerHTML = `<strong>Success:</strong> minutes draft <code>${{draft.id}}</code> is ${{draft.status}} and not adopted or posted.<br><strong>Next step:</strong> human review must approve the cited draft before any public posting workflow.`;
      }} catch (error) {{
        minutesOutput.dataset.state = "error";
        minutesOutput.innerHTML = `<strong>Error:</strong> ${{error.message}}`;
      }}
    }});

    archiveForm?.addEventListener("submit", async (event) => {{
      event.preventDefault();
      archiveOutput.dataset.state = "loading";
      archiveOutput.innerHTML = "<strong>Loading:</strong> publishing public archive record...";
      const form = new FormData(archiveForm);
      try {{
        const meeting = await createDemoMeeting(form.get("meeting_title"));
        const record = await postJson(`/meetings/${{meeting.id}}/public-record`, {{
          title: form.get("record_title"),
          visibility: "public",
          posted_agenda: form.get("posted_agenda"),
          posted_packet: form.get("posted_packet"),
          approved_minutes: form.get("approved_minutes"),
        }});
        const calendar = await fetch("/public/meetings").then((response) => response.json());
        const search = await fetch(`/public/archive/search?q=${{encodeURIComponent(form.get("search_query"))}}`).then((response) => response.json());
        archiveOutput.dataset.state = "success";
        archiveOutput.innerHTML = `<strong>Success:</strong> public archive record <code>${{record.id}}</code> is visible to anonymous users.<br><strong>Calendar count:</strong> ${{calendar.total_count}} public record(s). <strong>Search count:</strong> ${{search.total_count}} result(s).<br><strong>Next step:</strong> confirm any closed-session material remains outside the public record before linking it from the portal.`;
      }} catch (error) {{
        archiveOutput.dataset.state = "error";
        archiveOutput.innerHTML = `<strong>Error:</strong> ${{error.message}}`;
      }}
    }});

    importForm?.addEventListener("submit", async (event) => {{
      event.preventDefault();
      importOutput.dataset.state = "loading";
      importOutput.innerHTML = "<strong>Loading:</strong> normalizing local connector payload...";
      const form = new FormData(importForm);
      try {{
        const connector = form.get("connector");
        const payload = JSON.parse(form.get("payload"));
        const imported = await postJson(`/imports/${{connector}}/meetings`, payload);
        importOutput.dataset.state = "success";
        importOutput.innerHTML = `<strong>Success:</strong> imported ${{imported.connector}} meeting <code>${{imported.external_meeting_id}}</code> with ${{imported.agenda_items.length}} agenda item(s).<br><strong>Next step:</strong> review source provenance before moving imported items into the clerk queue.`;
      }} catch (error) {{
        importOutput.dataset.state = "error";
        importOutput.innerHTML = `<strong>Error:</strong> ${{error.message}} <br><strong>How to fix:</strong> paste valid JSON from a supported local export and retry.`;
      }}
    }});
  </script>
</body>
</html>"""


def _render_screen_card(card: dict, active: bool) -> str:
    rows = "\n".join(
        f"""
        <tr>
          <td>{owner}</td>
          <td>{item}</td>
          <td><span class="badge" data-tone="{status.lower().replace(" ", "-")}">{status}</span></td>
          <td>{next_step}</td>
        </tr>
        """
        for owner, item, status, next_step in card["rows"]
    )
    return f"""
      <article id="screen-{card["id"]}" class="screen-panel{' is-active' if active else ''}" role="tabpanel">
        <div class="screen-top">
          <div>
            <div class="eyebrow">{card["eyebrow"]}</div>
            <h3>{card["title"]}</h3>
            <p>{card["summary"]}</p>
            <span class="pill">{card["status"]}</span>
          </div>
          <button class="cta" type="button">{card["cta"]}</button>
        </div>
        <div class="api-strip" aria-label="{card["title"]} API paths">
          <p><strong>Primary API:</strong> <code>{card["primary_api"]}</code></p>
          <p><strong>Next action:</strong> <code>{card["secondary_api"]}</code></p>
        </div>
        <table class="work-table">
          <thead>
            <tr>
              <th>Owner</th>
              <th>Record</th>
              <th>Status</th>
              <th>Safe next step</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
        <p class="fix-path"><strong>How to fix:</strong> {card["fix"]}</p>
        {_render_live_region(card["id"])}
      </article>
    """


def _render_live_region(card_id: str) -> str:
    if card_id == "intake":
        return _render_live_intake_region()
    if card_id == "packet":
        return _render_live_packet_region()
    if card_id == "notice":
        return _render_live_notice_region()
    if card_id == "outcomes":
        return _render_live_outcomes_region()
    if card_id == "minutes":
        return _render_live_minutes_region()
    if card_id == "archive":
        return _render_live_archive_region()
    if card_id == "imports":
        return _render_live_import_region()
    return ""


def _render_live_intake_region() -> str:
    return """
        <section class="live-action" aria-labelledby="live-intake-heading">
          <h4 id="live-intake-heading">Live agenda intake action</h4>
          <p>Submit a real agenda intake item into the configured `CIVICCLERK_AGENDA_INTAKE_DB_URL` store, then record clerk readiness review. In local smoke checks, the in-memory default is used.</p>
          <form id="agenda-intake-form">
            <div class="form-grid">
              <label>Title
                <input name="title" required value="Crosswalk safety update">
              </label>
              <label>Department
                <input name="department_name" required value="Public Works">
              </label>
              <label>Submitted by
                <input name="submitted_by" required value="department@example.gov">
              </label>
              <label>Source label
                <input name="source_label" required value="Staff report">
              </label>
              <label class="span-2">Source URL
                <input name="source_url" required value="https://city.example.gov/staff-reports/crosswalk">
              </label>
              <label class="span-2">Summary
                <textarea name="summary" required>Request council review of crosswalk safety improvements near the library.</textarea>
              </label>
            </div>
            <div class="live-actions">
              <button class="cta" type="submit">Submit intake item</button>
            </div>
          </form>
          <form id="agenda-review-form">
            <div class="form-grid">
              <label>Item id
                <input id="review-item-id" name="item_id" required placeholder="Submit an intake item first">
              </label>
              <label>Reviewer
                <input name="reviewer" required value="clerk@example.gov">
              </label>
              <label>Ready?
                <select name="ready">
                  <option value="true">Ready for packet assembly</option>
                  <option value="false">Needs more information</option>
                </select>
              </label>
              <label class="span-2">Review notes
                <textarea name="notes" required>Sources complete and ready for packet assembly.</textarea>
              </label>
            </div>
            <div class="live-actions">
              <button class="secondary" type="submit">Record readiness review</button>
            </div>
          </form>
          <div id="agenda-intake-output" class="live-output" data-state="empty" role="status" aria-live="polite">
            <strong>Empty:</strong> no live agenda intake action has been submitted in this browser session.
            <br><strong>How to fix:</strong> submit the intake form above, then review the generated item id.
          </div>
        </section>
    """


def _render_live_packet_region() -> str:
    return """
        <section class="live-action" aria-labelledby="live-packet-heading">
          <h4 id="live-packet-heading">Live packet assembly action</h4>
          <p>Create a demo meeting, create a packet assembly record through `/meetings/{id}/packet-assemblies`, and finalize it through `/packet-assemblies/{id}/finalize`.</p>
          <form id="packet-assembly-form">
            <div class="form-grid">
              <label>Meeting title
                <input name="meeting_title" required value="Packet Assembly Demo Meeting">
              </label>
              <label>Packet title
                <input name="title" required value="Council packet v1">
              </label>
              <label>Agenda item id
                <input name="agenda_item_id" required value="agenda-item-demo">
              </label>
              <label>Actor
                <input name="actor" required value="clerk@example.gov">
              </label>
              <label>Source label
                <input name="source_label" required value="Staff report">
              </label>
              <label>Citation
                <input name="citation" required value="Staff report page 2">
              </label>
            </div>
            <div class="live-actions">
              <button class="cta" type="submit">Create and finalize packet</button>
            </div>
          </form>
          <div id="packet-assembly-output" class="live-output" data-state="empty" role="status" aria-live="polite">
            <strong>Empty:</strong> no live packet assembly action has run in this browser session.
            <br><strong>How to fix:</strong> submit the packet form above; the screen will create a demo meeting first.
          </div>
        </section>
        <section class="live-action" aria-labelledby="live-packet-export-heading">
          <h4 id="live-packet-export-heading">Live packet export action</h4>
          <p>Create a demo meeting, create the required packet snapshot through `/meetings/{id}/packet-snapshots`, and export a records-ready bundle through `/meetings/{id}/export-bundle`.</p>
          <form id="packet-export-form">
            <div class="form-grid">
              <label>Meeting title
                <input name="meeting_title" required value="Packet Export Demo Meeting">
              </label>
              <label>Bundle folder name
                <input name="bundle_name" required value="staff-packet-export-demo">
              </label>
              <label>Agenda item id
                <input name="agenda_item_id" required value="agenda-item-export-demo">
              </label>
              <label>Actor
                <input name="actor" required value="clerk@example.gov">
              </label>
              <label>Source id
                <input name="source_id" required value="staff-report-1">
              </label>
              <label>Source title
                <input name="source_title" required value="Staff report">
              </label>
              <label>Source path
                <input name="source_path" required value="staff-report.pdf">
              </label>
              <label>Citation label
                <input name="citation_label" required value="Staff Report p. 1">
              </label>
            </div>
            <div class="live-actions">
              <button class="cta" type="submit">Create packet export bundle</button>
            </div>
          </form>
          <div id="packet-export-output" class="live-output" data-state="empty" role="status" aria-live="polite">
            <strong>Empty:</strong> no live packet export action has run in this browser session.
            <br><strong>How to fix:</strong> submit the export form above; the screen will create the required meeting and packet snapshot before export.
          </div>
        </section>
    """


def _render_live_notice_region() -> str:
    return """
        <section class="live-action" aria-labelledby="live-notice-heading">
          <h4 id="live-notice-heading">Live notice checklist action</h4>
          <p>Create a demo meeting, persist a notice checklist through `/meetings/{id}/notice-checklists`, and attach posting proof through `/notice-checklists/{id}/posting-proof`.</p>
          <form id="notice-checklist-form">
            <div class="form-grid">
              <label>Meeting title
                <input name="meeting_title" required value="Notice Proof Demo Meeting">
              </label>
              <label>Posted at
                <input name="posted_at" required value="2026-05-01T19:00:00Z">
              </label>
              <label>Minimum notice hours
                <input name="minimum_notice_hours" required value="72">
              </label>
              <label>Approved by
                <input name="approved_by" required value="clerk@example.gov">
              </label>
              <label>Actor
                <input name="actor" required value="clerk@example.gov">
              </label>
              <label>Posting location
                <input name="location" required value="City Hall bulletin board">
              </label>
              <label class="span-2">Posted URL
                <input name="posted_url" required value="https://city.example.gov/agendas/demo">
              </label>
              <label class="span-2">Statutory basis
                <textarea name="statutory_basis" required>72-hour regular meeting notice rule.</textarea>
              </label>
            </div>
            <div class="live-actions">
              <button class="cta" type="submit">Check notice and attach proof</button>
            </div>
          </form>
          <div id="notice-checklist-output" class="live-output" data-state="empty" role="status" aria-live="polite">
            <strong>Empty:</strong> no live notice checklist action has run in this browser session.
            <br><strong>How to fix:</strong> submit the notice form above with a timezone-aware posted-at timestamp.
          </div>
        </section>
    """


def _render_live_outcomes_region() -> str:
    return """
        <section class="live-action" aria-labelledby="live-outcomes-heading">
          <h4 id="live-outcomes-heading">Live meeting outcomes action</h4>
          <p>Create a demo meeting, capture an immutable motion, record a vote, and create an action item tied to that motion.</p>
          <form id="meeting-outcomes-form">
            <div class="form-grid">
              <label>Meeting title
                <input name="meeting_title" required value="Meeting Outcomes Demo">
              </label>
              <label>Actor
                <input name="actor" required value="clerk@example.gov">
              </label>
              <label class="span-2">Motion text
                <textarea name="motion_text" required>Move to direct Public Works to inspect sidewalk repairs.</textarea>
              </label>
              <label>Voter name
                <input name="voter_name" required value="Council Member Rivera">
              </label>
              <label>Vote
                <select name="vote">
                  <option value="aye">Aye</option>
                  <option value="nay">Nay</option>
                  <option value="abstain">Abstain</option>
                </select>
              </label>
              <label>Assigned to
                <input name="assigned_to" required value="Public Works">
              </label>
              <label class="span-2">Action description
                <textarea name="action_description" required>Public Works to inspect sidewalk repairs and report back.</textarea>
              </label>
            </div>
            <div class="live-actions">
              <button class="cta" type="submit">Capture motion, vote, and action</button>
            </div>
          </form>
          <div id="meeting-outcomes-output" class="live-output" data-state="empty" role="status" aria-live="polite">
            <strong>Empty:</strong> no live meeting outcome action has run in this browser session.
            <br><strong>How to fix:</strong> submit the outcome form above; the screen will create the meeting and source motion first.
          </div>
        </section>
    """


def _render_live_minutes_region() -> str:
    return """
        <section class="live-action" aria-labelledby="live-minutes-heading">
          <h4 id="live-minutes-heading">Live minutes draft action</h4>
          <p>Create a demo meeting and submit a citation-gated minutes draft through `/meetings/{id}/minutes/drafts`. The draft remains unadopted and unposted until human review.</p>
          <form id="minutes-draft-form">
            <div class="form-grid">
              <label>Meeting title
                <input name="meeting_title" required value="Minutes Draft Demo Meeting">
              </label>
              <label>Human approver
                <input name="human_approver" required value="clerk@example.gov">
              </label>
              <label>Model
                <input name="model" required value="ollama/gemma4">
              </label>
              <label>Prompt version
                <input name="prompt_version" required value="minutes_draft@0.1.0">
              </label>
              <label>Source id
                <input name="source_id" required value="motion-1">
              </label>
              <label>Source label
                <input name="source_label" required value="Motion text">
              </label>
              <label class="span-2">Source text
                <textarea name="source_text" required>Council approved the sidewalk repair packet.</textarea>
              </label>
              <label class="span-2">Minutes sentence
                <textarea name="sentence_text" required>Council approved the sidewalk repair packet.</textarea>
              </label>
            </div>
            <div class="live-actions">
              <button class="cta" type="submit">Create cited minutes draft</button>
            </div>
          </form>
          <div id="minutes-draft-output" class="live-output" data-state="empty" role="status" aria-live="polite">
            <strong>Empty:</strong> no live minutes draft action has run in this browser session.
            <br><strong>How to fix:</strong> provide source material and cite that source id in every sentence before creating the draft.
          </div>
        </section>
    """


def _render_live_archive_region() -> str:
    return """
        <section class="live-action" aria-labelledby="live-archive-heading">
          <h4 id="live-archive-heading">Live public archive action</h4>
          <p>Create a demo meeting, publish a public-safe archive record through `/meetings/{id}/public-record`, then confirm `/public/meetings` and `/public/archive/search` can see it.</p>
          <form id="public-archive-form">
            <div class="form-grid">
              <label>Meeting title
                <input name="meeting_title" required value="Public Archive Demo Meeting">
              </label>
              <label>Record title
                <input name="record_title" required value="Public Archive Demo Meeting">
              </label>
              <label class="span-2">Posted agenda
                <textarea name="posted_agenda" required>Agenda: approve sidewalk repair packet.</textarea>
              </label>
              <label class="span-2">Posted packet
                <textarea name="posted_packet" required>Packet: staff report, fiscal note, and public attachments.</textarea>
              </label>
              <label class="span-2">Approved minutes
                <textarea name="approved_minutes" required>Approved minutes: council approved the sidewalk repair packet 5-0.</textarea>
              </label>
              <label class="span-2">Search query
                <input name="search_query" required value="sidewalk repair">
              </label>
            </div>
            <div class="live-actions">
              <button class="cta" type="submit">Publish public archive record</button>
            </div>
          </form>
          <div id="public-archive-output" class="live-output" data-state="empty" role="status" aria-live="polite">
            <strong>Empty:</strong> no live public archive action has run in this browser session.
            <br><strong>How to fix:</strong> provide public-safe agenda, packet, and approved-minutes text before publishing.
          </div>
        </section>
    """


def _render_live_import_region() -> str:
    return """
        <section class="live-action" aria-labelledby="live-import-heading">
          <h4 id="live-import-heading">Live connector import action</h4>
          <p>Normalize a local agenda-platform export payload through `/imports/{connector}/meetings`. This action does not call the vendor network; it works from pasted local JSON.</p>
          <form id="connector-import-form">
            <div class="form-grid">
              <label>Connector
                <select name="connector">
                  <option value="granicus">Granicus</option>
                  <option value="legistar">Legistar</option>
                  <option value="primegov">PrimeGov</option>
                  <option value="novusagenda">NovusAGENDA</option>
                </select>
              </label>
              <label class="span-2">Local export payload JSON
                <textarea name="payload" required>{
  "id": "gr-demo-100",
  "name": "Budget Hearing",
  "start": "2026-05-05T19:00:00Z",
  "agenda": [
    {
      "id": "gr-item-1",
      "title": "Adopt budget ordinance",
      "department": "Finance"
    }
  ]
}</textarea>
              </label>
            </div>
            <div class="live-actions">
              <button class="cta" type="submit">Import local connector payload</button>
            </div>
          </form>
          <div id="connector-import-output" class="live-output" data-state="empty" role="status" aria-live="polite">
            <strong>Empty:</strong> no live connector import action has run in this browser session.
            <br><strong>How to fix:</strong> choose a supported connector and paste a valid local export payload before importing.
          </div>
        </section>
    """
