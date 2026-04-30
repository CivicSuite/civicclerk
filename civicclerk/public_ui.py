"""Accessible resident-facing public portal shell for CivicClerk."""

from __future__ import annotations

from civicclerk import __version__


def render_public_portal() -> str:
    """Render the current resident-facing public portal shell."""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CivicClerk Public Portal</title>
  <style>
    :root {{
      --ink: #14231f;
      --muted: #546761;
      --paper: #f5efe2;
      --panel: #fffdf7;
      --line: #d8ccb8;
      --accent: #1f6b5a;
      --accent-dark: #10483d;
      --blue: #244b73;
      --warn: #8a5a16;
      --error: #8b2d24;
      --good: #236b46;
      --wash: rgba(31, 107, 90, .1);
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; overflow-x: hidden; }}
    body {{
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 8% 6%, rgba(31,107,90,.18), transparent 28rem),
        radial-gradient(circle at 88% 16%, rgba(36,75,115,.16), transparent 24rem),
        linear-gradient(180deg, var(--paper), #ebe0cd);
      line-height: 1.55;
    }}
    .skip {{ position: absolute; left: -999px; top: 12px; background: var(--accent-dark); color: white; padding: 10px 14px; border-radius: 10px; }}
    .skip:focus {{ left: 12px; z-index: 5; }}
    a {{ color: var(--accent-dark); }}
    a:focus-visible, button:focus-visible, input:focus-visible {{ outline: 4px solid var(--accent-dark); outline-offset: 4px; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 42px 20px 64px; }}
    .hero {{ background: rgba(255,253,247,.9); border: 1px solid var(--line); border-radius: 30px; padding: 34px; box-shadow: 0 20px 70px rgba(20,35,31,.09); position: relative; overflow: hidden; }}
    .hero::after {{ content: ""; position: absolute; inset: auto -7% -46% 52%; height: 280px; background: repeating-linear-gradient(135deg, var(--wash) 0 12px, transparent 12px 28px); transform: rotate(-10deg); pointer-events: none; }}
    .eyebrow {{ color: var(--accent); font-size: .78rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }}
    h1 {{ font-size: clamp(2.25rem, 7vw, 4.9rem); line-height: .95; margin: 12px 0 18px; }}
    h2 {{ margin: 0 0 10px; }}
    p {{ max-width: 78ch; }}
    .status {{ color: var(--warn); font-weight: 700; }}
    .grid {{ display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(300px, .9fr); gap: 18px; margin-top: 22px; }}
    .panel {{ background: rgba(255,253,247,.95); border: 1px solid var(--line); border-radius: 24px; padding: 22px; box-shadow: 0 16px 46px rgba(20,35,31,.07); }}
    .toolbar {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin: 14px 0; }}
    input {{ min-width: min(100%, 280px); border: 1px solid var(--line); border-radius: 999px; padding: 12px 14px; font: inherit; background: white; color: var(--ink); }}
    button {{ border: 0; border-radius: 999px; background: var(--accent); color: white; padding: 12px 16px; font: inherit; font-weight: 700; cursor: pointer; }}
    button.secondary {{ background: var(--blue); }}
    .state {{ border-radius: 18px; padding: 14px; margin: 12px 0; border: 1px solid var(--line); background: #fffaf0; }}
    .state[data-state="loading"] {{ border-color: rgba(31,107,90,.4); }}
    .state[data-state="success"] {{ border-color: rgba(35,107,70,.45); background: #eef8f1; }}
    .state[data-state="empty"] {{ border-color: rgba(138,90,22,.45); background: #fff7e4; }}
    .state[data-state="error"] {{ border-color: rgba(139,45,36,.45); background: #fff2ef; }}
    .state[data-state="partial"] {{ border-color: rgba(36,75,115,.45); background: #eff5fb; }}
    .records {{ display: grid; gap: 12px; margin-top: 14px; }}
    .record-card {{ border: 1px solid var(--line); border-radius: 20px; padding: 16px; background: var(--panel); }}
    .record-card h3 {{ margin: 0 0 6px; }}
    .record-card dl {{ display: grid; gap: 8px; margin: 12px 0 0; }}
    .record-card dt {{ font-weight: 700; color: var(--muted); }}
    .record-card dd {{ margin: 0; }}
    .pill {{ display: inline-block; border-radius: 999px; padding: 5px 9px; background: #e0eee6; color: var(--accent-dark); font-weight: 700; font-size: .82rem; }}
    .detail {{ min-height: 180px; }}
    .fine-print {{ font-size: .94rem; color: var(--muted); }}
    @media (max-width: 760px) {{
      main {{ padding: 24px 14px 44px; }}
      .hero, .panel {{ border-radius: 22px; padding: 22px; }}
      .grid {{ grid-template-columns: 1fr; }}
      button, input {{ width: 100%; }}
    }}
  </style>
</head>
<body>
  <a class="skip" href="#portal">Skip to public meeting records</a>
  <main id="portal" aria-label="CivicClerk public portal shell">
    <section class="hero">
      <div class="eyebrow">Resident public portal shell</div>
      <h1>CivicClerk Public Portal</h1>
      <p class="status">Status: v{__version__} first public portal shell. This is a browser-visible resident view over the existing public calendar and archive APIs, not the finished full public portal.</p>
      <p>Residents can review public meeting records that clerks have published, open a public-safe detail view, and search approved agenda, packet, and minutes text. Anonymous views intentionally exclude closed-session notes and restricted records.</p>
    </section>

    <section class="grid" aria-label="Public meeting portal">
      <article class="panel">
        <h2>Published meetings</h2>
        <p class="fine-print">Loaded from <code>/public/meetings</code>. If this list is empty, staff must publish a public record from the staff Public Archive workflow first.</p>
        <div id="calendar-state" class="state" data-state="loading" role="status">Loading public meetings. If this does not update, refresh the page and confirm the API is running at <code>/public/meetings</code>.</div>
        <div id="meeting-records" class="records" aria-live="polite"></div>
      </article>

      <article class="panel detail">
        <h2>Record detail</h2>
        <p class="fine-print">Details are loaded from <code>/public/meetings/{{id}}</code> after selecting a meeting.</p>
        <div id="detail-state" class="state" data-state="empty" role="status">Choose a published meeting to view agenda, packet, and approved minutes. Closed-session content is not displayed here.</div>
        <div id="record-detail"></div>
      </article>

      <article class="panel">
        <h2>Archive search</h2>
        <p class="fine-print">Search uses <code>/public/archive/search</code> and only returns public-safe results for anonymous residents.</p>
        <form id="search-form" class="toolbar">
          <label for="archive-query">Search public archive</label>
          <input id="archive-query" name="q" value="agenda" autocomplete="off">
          <button type="submit">Search</button>
        </form>
        <div id="search-state" class="state" data-state="empty" role="status">Enter a word from the public agenda, packet, or approved minutes. If no results appear, try a broader term or ask the clerk whether the record has been published.</div>
        <div id="search-results" class="records" aria-live="polite"></div>
      </article>

      <article class="panel">
        <h2>What is not here yet</h2>
        <p>This shell is intentionally small. The full public portal, subscription preferences, polished public posting workflow, and integrated React experience remain future work.</p>
        <p class="fine-print">For staff publishing, use <a href="/staff">/staff</a>. For raw public API checks, use <a href="/public/meetings">/public/meetings</a>.</p>
      </article>
    </section>
  </main>

  <script>
    const calendarState = document.querySelector("#calendar-state");
    const detailState = document.querySelector("#detail-state");
    const searchState = document.querySelector("#search-state");
    const meetingRecords = document.querySelector("#meeting-records");
    const recordDetail = document.querySelector("#record-detail");
    const searchResults = document.querySelector("#search-results");

    function setState(node, state, message) {{
      node.dataset.state = state;
      node.textContent = message;
    }}

    function text(value) {{
      return value || "Not posted yet.";
    }}

    function renderRecordCard(record) {{
      const article = document.createElement("article");
      article.className = "record-card";
      const title = document.createElement("h3");
      title.textContent = record.title;
      const meta = document.createElement("p");
      meta.className = "pill";
      meta.textContent = `Meeting record ${{record.id}}`;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary";
      button.textContent = "View public detail";
      button.addEventListener("click", () => loadDetail(record.id));
      article.append(title, meta, button);
      return article;
    }}

    function renderDetail(record) {{
      const wrapper = document.createElement("article");
      wrapper.className = "record-card";
      const heading = document.createElement("h3");
      heading.textContent = record.title;
      const list = document.createElement("dl");
      for (const [label, value] of [
        ["Posted agenda", record.posted_agenda],
        ["Posted packet", record.posted_packet],
        ["Approved minutes", record.approved_minutes],
      ]) {{
        const term = document.createElement("dt");
        term.textContent = label;
        const detail = document.createElement("dd");
        detail.textContent = text(value);
        list.append(term, detail);
      }}
      wrapper.append(heading, list);
      return wrapper;
    }}

    async function loadCalendar() {{
      setState(calendarState, "loading", "Loading public meetings from /public/meetings.");
      try {{
        const response = await fetch("/public/meetings");
        if (!response.ok) {{
          throw new Error(`HTTP ${{response.status}}`);
        }}
        const payload = await response.json();
        meetingRecords.replaceChildren();
        if (!payload.meetings || payload.meetings.length === 0) {{
          setState(calendarState, "empty", "No public meetings are published yet. Staff should publish a public record from /staff before residents can see it here.");
          return;
        }}
        for (const record of payload.meetings) {{
          meetingRecords.append(renderRecordCard(record));
        }}
        setState(calendarState, "success", `${{payload.meetings.length}} public meeting record(s) loaded. Choose a meeting to review public-safe details.`);
      }} catch (error) {{
        setState(calendarState, "error", `Public meetings could not load. Confirm the app is running, then retry /public/meetings. Details: ${{error.message}}`);
      }}
    }}

    async function loadDetail(recordId) {{
      setState(detailState, "loading", `Loading public detail for ${{recordId}}.`);
      recordDetail.replaceChildren();
      try {{
        const response = await fetch(`/public/meetings/${{encodeURIComponent(recordId)}}`);
        if (!response.ok) {{
          throw new Error(`HTTP ${{response.status}}`);
        }}
        const record = await response.json();
        recordDetail.append(renderDetail(record));
        setState(detailState, "success", "Public-safe agenda, packet, and approved minutes loaded. Closed-session notes remain excluded.");
      }} catch (error) {{
        setState(detailState, "error", `This public record could not be opened. It may not be published publicly yet. Retry from /public/meetings. Details: ${{error.message}}`);
      }}
    }}

    async function searchArchive(query) {{
      const trimmed = query.trim();
      searchResults.replaceChildren();
      if (!trimmed) {{
        setState(searchState, "empty", "Enter a search term before searching the public archive.");
        return;
      }}
      setState(searchState, "loading", `Searching public archive for "${{trimmed}}".`);
      try {{
        const response = await fetch(`/public/archive/search?q=${{encodeURIComponent(trimmed)}}`);
        if (!response.ok) {{
          throw new Error(`HTTP ${{response.status}}`);
        }}
        const payload = await response.json();
        if (!payload.results || payload.results.length === 0) {{
          setState(searchState, "empty", "No public archive results matched. Try a broader term or ask the clerk whether the record has been published.");
          return;
        }}
        for (const record of payload.results) {{
          searchResults.append(renderDetail(record));
        }}
        setState(searchState, "success", `${{payload.results.length}} public archive result(s) loaded. Results exclude restricted records for anonymous visitors.`);
      }} catch (error) {{
        setState(searchState, "error", `Archive search failed. Confirm the API is running at /public/archive/search and retry. Details: ${{error.message}}`);
      }}
    }}

    document.querySelector("#search-form").addEventListener("submit", (event) => {{
      event.preventDefault();
      searchArchive(document.querySelector("#archive-query").value);
    }});

    loadCalendar().then(() => searchArchive(document.querySelector("#archive-query").value));
  </script>
</body>
</html>
"""
