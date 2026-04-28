"""Accessible staff workflow screens for CivicClerk staff."""

from __future__ import annotations


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
        "secondary_api": "/packet-assemblies/{id}/finalize",
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
    .screen-nav {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin: 28px 0 18px; }}
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
      .screen-nav, .api-strip, .form-grid {{ grid-template-columns: 1fr; }}
      .work-table {{ display: block; overflow-x: auto; }}
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <a class="skip" href="#workflow-screens">Skip to workflow screens</a>
  <main aria-label="CivicClerk staff workflow screens">
    <section class="hero">
      <div class="eyebrow">CivicClerk v0.1.0</div>
      <h1>CivicClerk Staff Workflow Screens</h1>
      <p class="status">These are the first browser-visible staff workflow screens for the released API foundation. They guide agenda intake review, packet assembly, and notice checklist/posting proof work without claiming the full end-to-end clerk console is finished.</p>
      <p>The screens show the live API paths, safe next actions, required staff states, and actionable fix copy for the three database-backed service slices available today: agenda intake, packet assembly records, and notice checklist records.</p>
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
    function activate(target) {{
      tabs.forEach((tab) => tab.setAttribute("aria-selected", String(tab.dataset.target === target)));
      panels.forEach((panel) => panel.classList.toggle("is-active", panel.id === `screen-${{target}}`));
    }}
    tabs.forEach((tab) => tab.addEventListener("click", () => activate(tab.dataset.target)));
    activate("intake");

    const intakeForm = document.querySelector("#agenda-intake-form");
    const reviewForm = document.querySelector("#agenda-review-form");
    const output = document.querySelector("#agenda-intake-output");
    const itemIdInput = document.querySelector("#review-item-id");

    function setOutput(state, html) {{
      output.dataset.state = state;
      output.innerHTML = html;
    }}

    async function postJson(path, payload) {{
      const response = await fetch(path, {{
        method: "POST",
        headers: {{ "content-type": "application/json" }},
        body: JSON.stringify(payload),
      }});
      const data = await response.json();
      if (!response.ok) {{
        const detail = data.detail || {{}};
        throw new Error(`${{detail.message || "Request failed."}} How to fix: ${{detail.fix || "Check the required fields and retry."}}`);
      }}
      return data;
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
        {_render_live_intake_region() if card["id"] == "intake" else ""}
      </article>
    """


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
