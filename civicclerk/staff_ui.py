"""Accessible staff workflow UI foundation."""

from __future__ import annotations


WORKFLOWS = [
    (
        "Agenda intake",
        "Submit department items into the database-backed staff queue and record clerk readiness review.",
        "/agenda-intake",
        "Use /agenda-intake/{id}/review before moving a ready item toward packet assembly.",
    ),
    (
        "Meeting lifecycle",
        "Create meetings, apply canonical meeting transitions, and enforce statutory-basis preconditions.",
        "/meetings",
        "Emergency, special, closed-session, and executive-session guardrails remain enforced by the API.",
    ),
    (
        "Packet and notice",
        "Version packet snapshots, persist packet assembly records, and check notice deadlines before posting public notices.",
        "/meetings/{id}/packet-snapshots · /meetings/{id}/packet-assemblies",
        "Use /packet-assemblies/{id}/finalize before export; use /meetings/{id}/notices/check before posting.",
    ),
    (
        "Motions, votes, actions",
        "Capture immutable motions and votes, then add action items linked to source motions.",
        "/meetings/{id}/motions",
        "Corrections are append-only; direct mutation returns 409 Conflict.",
    ),
    (
        "Minutes drafts",
        "Create citation-gated minutes drafts with source provenance, model, prompt version, and human approver.",
        "/meetings/{id}/minutes/drafts",
        "Every material sentence needs citations before the draft can be accepted.",
    ),
    (
        "Public archive",
        "Expose public meeting records while preventing closed-session leakage to anonymous users.",
        "/public/archive/search",
        "Anonymous counts, suggestions, bodies, and not-found responses never reveal restricted content.",
    ),
    (
        "Connector imports",
        "Normalize local Granicus, Legistar, PrimeGov, and NovusAGENDA export payloads with source provenance.",
        "/imports/{connector}/meetings",
        "No outbound network call is required in the default local-first profile.",
    ),
]

STATE_CARDS = [
    ("loading", "Loading", "The staff screen should tell clerks which workflow is loading and what to try if it stalls."),
    ("success", "Success", "Completed actions should name the affected record and the next safe step."),
    ("empty", "Empty", "Empty queues should say what to create first and link to the matching API path."),
    ("error", "Error", "Errors must explain what failed and how staff can fix the input."),
    ("partial", "Partial", "Partial imports or checks should identify what succeeded, what did not, and what to retry."),
]


def render_staff_dashboard() -> str:
    """Render the current staff workflow foundation as dependency-free HTML."""
    workflow_cards = "\n".join(
        f"""
        <article class="workflow-card">
          <h3>{title}</h3>
          <p>{description}</p>
          <p><strong>Primary API:</strong> <code>{api_path}</code></p>
          <p class="fix-path">{fix_path}</p>
        </article>
        """
        for title, description, api_path, fix_path in WORKFLOWS
    )
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
  <title>CivicClerk Staff Workflow Foundation</title>
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
    a:focus-visible, button:focus-visible {{ outline: 4px solid var(--accent-dark); outline-offset: 4px; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 48px 20px; }}
    .hero {{ background: rgba(255,255,255,.82); border: 1px solid var(--line); border-radius: 28px; padding: 34px; box-shadow: 0 18px 60px rgba(23,32,27,.08); }}
    .eyebrow {{ color: var(--accent); font-weight: 700; letter-spacing: .08em; text-transform: uppercase; font-size: .78rem; }}
    h1 {{ font-size: clamp(2.2rem, 7vw, 5rem); line-height: .95; margin: 14px 0 18px; }}
    h2 {{ margin-top: 34px; }}
    p {{ max-width: 78ch; }}
    .status {{ color: var(--warn); font-weight: 700; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin-top: 22px; }}
    .workflow-card, .state-card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 20px; padding: 20px; }}
    .workflow-card h3, .state-card h3 {{ margin-top: 0; }}
    code {{ background: #eadfca; padding: 2px 5px; border-radius: 5px; overflow-wrap: anywhere; }}
    .fix-path {{ color: var(--muted); }}
    [data-state="error"] {{ border-color: rgba(140,47,36,.45); }}
    [data-state="partial"] {{ border-color: rgba(138,90,22,.5); }}
    @media (max-width: 640px) {{
      main {{ padding: 30px 14px; }}
      .hero, .workflow-card, .state-card {{ border-radius: 20px; padding: 18px; }}
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <a class="skip" href="#workflow-board">Skip to workflow board</a>
  <main aria-label="CivicClerk staff workflow foundation">
    <section class="hero">
      <div class="eyebrow">CivicClerk v0.1.0</div>
      <h1>CivicClerk Staff Workflow Foundation</h1>
      <p class="status">Full workflow UI screens are still planned; this page is the first staff-facing workflow map for the released API foundation, the database-backed agenda intake queue, and database-backed packet assembly records.</p>
      <p>The agenda intake queue is available through the API at <code>/agenda-intake</code>, and packet assembly records are available at <code>/meetings/{{id}}/packet-assemblies</code>. Use this screen to orient clerks and IT staff to the workflows that are already enforced by the API, the user-visible states every future screen must handle, and the API paths to smoke-check today.</p>
    </section>

    <section id="workflow-board" aria-labelledby="workflow-heading">
      <h2 id="workflow-heading">Workflow board</h2>
      <div class="grid">
        {workflow_cards}
      </div>
    </section>

    <section aria-labelledby="states-heading">
      <h2 id="states-heading">Required rendered states</h2>
      <p>Every future staff workflow screen must render these states with actionable copy, keyboard focus, contrast, and zero browser console errors.</p>
      <div class="grid">
        {state_cards}
      </div>
    </section>
  </main>
</body>
</html>"""
