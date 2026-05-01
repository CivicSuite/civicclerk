import { useMemo, useState } from "react";

type ViewState = "success" | "loading" | "empty" | "error" | "partial";
type Page = "dashboard" | "meetings" | "meeting-detail";
type LifecycleStage =
  | "Scheduled"
  | "Notice posted"
  | "Agenda published"
  | "In session"
  | "Adjourned"
  | "Minutes drafted"
  | "Minutes approved"
  | "Closed and archived";

type Meeting = {
  id: string;
  body: string;
  title: string;
  date: string;
  time: string;
  location: string;
  stage: LifecycleStage;
  agendaItems: number;
  packetPages: number;
  noticeStatus: "Ready" | "Warning" | "Blocked";
};

const lifecycle: LifecycleStage[] = [
  "Scheduled",
  "Notice posted",
  "Agenda published",
  "In session",
  "Adjourned",
  "Minutes drafted",
  "Minutes approved",
  "Closed and archived",
];

const meetings: Meeting[] = [
  {
    id: "M-2026-053",
    body: "City Council",
    title: "Regular Meeting",
    date: "May 5, 2026",
    time: "6:00 PM",
    location: "Council Chambers",
    stage: "Agenda published",
    agendaItems: 18,
    packetPages: 142,
    noticeStatus: "Ready",
  },
  {
    id: "M-2026-049",
    body: "Planning Commission",
    title: "Special Session",
    date: "May 7, 2026",
    time: "4:30 PM",
    location: "Room 204",
    stage: "Notice posted",
    agendaItems: 7,
    packetPages: 38,
    noticeStatus: "Warning",
  },
  {
    id: "M-2026-041",
    body: "Parks Advisory Board",
    title: "Monthly Meeting",
    date: "May 13, 2026",
    time: "5:15 PM",
    location: "Civic Center Annex",
    stage: "Scheduled",
    agendaItems: 4,
    packetPages: 0,
    noticeStatus: "Blocked",
  },
];

const tasks = [
  "Review 3 department agenda submissions",
  "Finalize packet for City Council",
  "Resolve notice warning for Planning Commission",
];

function Icon({ label }: { label: string }) {
  return <span className="icon" aria-hidden="true">{label.slice(0, 1)}</span>;
}

export function App() {
  const initial = getInitialView();
  const [page, setPage] = useState<Page>(initial.page);
  const [viewState, setViewState] = useState<ViewState>(initial.state);
  const [activeMeetingId, setActiveMeetingId] = useState(meetings[0].id);
  const [auditOpen, setAuditOpen] = useState(initial.audit);
  const activeMeeting = meetings.find((meeting) => meeting.id === activeMeetingId) ?? meetings[0];

  return (
    <div className="app-shell">
      <aside className="rail" aria-label="CivicClerk navigation">
        <div className="brand">
          <div className="seal">B</div>
          <div>
            <strong>CivicSuite</strong>
            <span>City of Brookfield</span>
          </div>
        </div>
        <nav>
          <button className={page === "dashboard" ? "active" : ""} onClick={() => setPage("dashboard")}>
            <Icon label="Dashboard" /> Dashboard
          </button>
          <button className={page !== "dashboard" ? "active" : ""} onClick={() => setPage("meetings")}>
            <Icon label="Meetings" /> Meetings
          </button>
          <button className="muted" aria-disabled="true">
            <Icon label="Agenda" /> Agenda intake
          </button>
          <button className="muted" aria-disabled="true">
            <Icon label="Packet" /> Packet builder
          </button>
          <button className="muted" aria-disabled="true">
            <Icon label="Minutes" /> Minutes
          </button>
        </nav>
        <div className="install-card">
          <span>Partial install</span>
          <strong>Clerk + Records + Code + Admin</strong>
        </div>
      </aside>

      <header className="topbar">
        <button className="search" type="button">Search city work... <kbd>Ctrl K</kbd></button>
        <div className="surface-switch" aria-label="Surface switcher">
          <button className="on">Staff</button>
          <button>Resident</button>
          <button>IT/Admin</button>
        </div>
        <button className="audit-toggle" onClick={() => setAuditOpen((open) => !open)}>
          {auditOpen ? "Hide audit" : "Show audit"}
        </button>
      </header>

      <main className={auditOpen ? "workspace with-audit" : "workspace"}>
        <section>
          <StateToolbar viewState={viewState} setViewState={setViewState} />
          {page === "dashboard" && (
            <Dashboard
              viewState={viewState}
              setPage={setPage}
              setActiveMeetingId={setActiveMeetingId}
            />
          )}
          {page === "meetings" && (
            <MeetingCalendar
              viewState={viewState}
              setPage={setPage}
              setActiveMeetingId={setActiveMeetingId}
            />
          )}
          {page === "meeting-detail" && (
            <MeetingDetail meeting={activeMeeting} viewState={viewState} />
          )}
        </section>
        {auditOpen && <AuditDrawer meeting={activeMeeting} />}
      </main>
    </div>
  );
}

function getInitialView(): { page: Page; state: ViewState; audit: boolean } {
  if (typeof window === "undefined") {
    return { page: "dashboard", state: "success", audit: false };
  }
  const params = new URLSearchParams(window.location.search);
  const requestedPage = params.get("page");
  const requestedState = params.get("state");
  const pages: Page[] = ["dashboard", "meetings", "meeting-detail"];
  const states: ViewState[] = ["success", "loading", "empty", "error", "partial"];
  return {
    page: pages.includes(requestedPage as Page) ? (requestedPage as Page) : "dashboard",
    state: states.includes(requestedState as ViewState) ? (requestedState as ViewState) : "success",
    audit: params.get("audit") === "1",
  };
}

function StateToolbar({
  viewState,
  setViewState,
}: {
  viewState: ViewState;
  setViewState: (state: ViewState) => void;
}) {
  const states: ViewState[] = ["success", "loading", "empty", "error", "partial"];
  return (
    <div className="state-toolbar" aria-label="QA state controls">
      <span>QA states</span>
      {states.map((state) => (
        <button
          key={state}
          className={viewState === state ? "selected" : ""}
          onClick={() => setViewState(state)}
        >
          {state}
        </button>
      ))}
    </div>
  );
}

function Dashboard({
  viewState,
  setPage,
  setActiveMeetingId,
}: {
  viewState: ViewState;
  setPage: (page: Page) => void;
  setActiveMeetingId: (id: string) => void;
}) {
  if (viewState !== "success") {
    return <StateMessage state={viewState} context="dashboard" />;
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="CivicClerk staff workspace"
        title="Good morning, City Clerk."
        description="Today's meeting work is grouped by urgency, public posting risk, and packet readiness."
      />
      <div className="metric-grid">
        <MetricCard label="Meetings this week" value="3" note="2 ready for public posting" />
        <MetricCard label="Agenda items pending" value="14" note="3 need clerk review" />
        <MetricCard label="Notice warnings" value="1" note="Fix before 4:00 PM today" tone="warn" />
      </div>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Priority queue</h2>
            <p>Actionable work for the current staff role.</p>
          </div>
          <button className="secondary" onClick={() => setPage("meetings")}>Open calendar</button>
        </div>
        <div className="task-list">
          {tasks.map((task, index) => (
            <button
              key={task}
              onClick={() => {
                setActiveMeetingId(meetings[Math.min(index, meetings.length - 1)].id);
                setPage("meeting-detail");
              }}
            >
              <span>{task}</span>
              <strong>{index === 0 ? "Review" : index === 1 ? "Finalize" : "Fix warning"}</strong>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

function MeetingCalendar({
  viewState,
  setPage,
  setActiveMeetingId,
}: {
  viewState: ViewState;
  setPage: (page: Page) => void;
  setActiveMeetingId: (id: string) => void;
}) {
  if (viewState !== "success") {
    return <StateMessage state={viewState} context="meeting calendar" />;
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Meeting calendar"
        title="May 2026 clerk calendar"
        description="Track meeting lifecycle, packet readiness, and notice risk from one staff view."
      />
      <div className="calendar-layout">
        <section className="calendar-board" aria-label="May 2026 calendar">
          {Array.from({ length: 35 }, (_, index) => {
            const day = index - 4;
            const dayMeetings = meetings.filter((meeting) => meeting.date.includes(String(day)));
            return (
              <div key={index} className={day > 0 && day <= 31 ? "day" : "day outside"}>
                <span>{day > 0 && day <= 31 ? day : ""}</span>
                {dayMeetings.map((meeting) => (
                  <button
                    key={meeting.id}
                    className="meeting-chip"
                    onClick={() => {
                      setActiveMeetingId(meeting.id);
                      setPage("meeting-detail");
                    }}
                  >
                    {meeting.body}
                  </button>
                ))}
              </div>
            );
          })}
        </section>
        <aside className="panel">
          <h2>Upcoming meetings</h2>
          <div className="meeting-list">
            {meetings.map((meeting) => (
              <button
                key={meeting.id}
                onClick={() => {
                  setActiveMeetingId(meeting.id);
                  setPage("meeting-detail");
                }}
              >
                <span>
                  <strong>{meeting.body}</strong>
                  {meeting.title} - {meeting.date}
                </span>
                <StatusBadge tone={meeting.noticeStatus} label={meeting.stage} />
              </button>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}

function MeetingDetail({ meeting, viewState }: { meeting: Meeting; viewState: ViewState }) {
  const activeIndex = lifecycle.indexOf(meeting.stage);
  const tabs = useMemo(
    () => [
      ["Agenda", `${meeting.agendaItems} items`],
      ["Packet", meeting.packetPages ? `${meeting.packetPages} pages` : "Not assembled"],
      ["Notice", meeting.noticeStatus],
      ["Minutes", activeIndex >= 5 ? "Draft ready" : "Waiting for outcomes"],
    ],
    [activeIndex, meeting],
  );

  if (viewState !== "success") {
    return <StateMessage state={viewState} context="meeting detail" />;
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow={`${meeting.body} - ${meeting.id}`}
        title={meeting.title}
        description={`${meeting.date} at ${meeting.time} - ${meeting.location}`}
      />
      <section className="panel lifecycle-panel">
        <h2>Meeting lifecycle</h2>
        <ol className="lifecycle-ribbon" aria-label="Meeting lifecycle stages">
          {lifecycle.map((stage, index) => (
            <li key={stage} className={index <= activeIndex ? "complete" : ""}>
              <span>{index + 1}</span>
              {stage}
            </li>
          ))}
        </ol>
      </section>
      <section className="detail-grid">
        {tabs.map(([title, detail]) => (
          <article className="panel" key={title}>
            <h2>{title}</h2>
            <p>{detail}</p>
            <div className="evidence-card">
              <strong>Evidence trail</strong>
              <span>Source, user, timestamp, and export provenance will remain attached.</span>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}

function AuditDrawer({ meeting }: { meeting: Meeting }) {
  return (
    <aside className="audit-drawer" aria-label="Audit and evidence drawer">
      <div>
        <span className="eyebrow">Audit and evidence</span>
        <h2>{meeting.id}</h2>
        <p>{meeting.body} - {meeting.title}</p>
      </div>
      <div className="audit-event">
        <strong>Agenda published</strong>
        <span>Brookfield Clerk - 2026-04-30 3:42 PM</span>
        <p>Packet manifest, posting checklist, and agenda checksum recorded.</p>
      </div>
      <div className="audit-event">
        <strong>Notice compliance checked</strong>
        <span>System - 2026-04-30 3:39 PM</span>
        <p>No open blockers. One public-posting reminder remains before finalization.</p>
      </div>
      <button className="secondary full">Export audit package</button>
    </aside>
  );
}

function StateMessage({ state, context }: { state: ViewState; context: string }) {
  const copy = {
    loading: {
      title: `Loading ${context}`,
      body: "CivicClerk is contacting the API. If this takes more than a few seconds, check the API service and reload the page.",
      action: "Retry loading",
    },
    empty: {
      title: `No ${context} data yet`,
      body: "Create a meeting body and schedule the first meeting to populate this workspace.",
      action: "Create first meeting",
    },
    error: {
      title: `Could not load ${context}`,
      body: "The staff API did not respond. Confirm the backend is running, verify staff auth mode, then retry.",
      action: "Retry after checking API",
    },
    partial: {
      title: `${context} is partially available`,
      body: "Some Clerk services are not installed in this environment. Install packet and minutes services or continue with calendar-only work.",
      action: "View installed services",
    },
    success: {
      title: "",
      body: "",
      action: "",
    },
  }[state];

  return (
    <section className={`state-card ${state}`} role={state === "error" ? "alert" : "status"}>
      <div className="state-mark">{state.slice(0, 1).toUpperCase()}</div>
      <h1>{copy.title}</h1>
      <p>{copy.body}</p>
      <button>{copy.action}</button>
    </section>
  );
}

function PageHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <header className="page-header">
      <span className="eyebrow">{eyebrow}</span>
      <h1>{title}</h1>
      <p>{description}</p>
    </header>
  );
}

function MetricCard({
  label,
  value,
  note,
  tone,
}: {
  label: string;
  value: string;
  note: string;
  tone?: "warn";
}) {
  return (
    <article className={tone === "warn" ? "metric warn" : "metric"}>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{note}</p>
    </article>
  );
}

function StatusBadge({ tone, label }: { tone: Meeting["noticeStatus"]; label: string }) {
  return <span className={`status ${tone.toLowerCase()}`}>{label}</span>;
}
