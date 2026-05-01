import { useEffect, useMemo, useState, type FormEvent } from "react";

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
  meetingBodyId?: string;
  body: string;
  title: string;
  meetingType: string;
  date: string;
  time: string;
  scheduledStart?: string | null;
  location: string;
  stage: LifecycleStage;
  agendaItems: number;
  packetPages: number;
  noticeStatus: "Ready" | "Warning" | "Blocked";
};

type ApiMeeting = {
  id: string;
  title: string;
  meeting_type: string;
  status: string;
  scheduled_start?: string | null;
  meeting_body_id?: string | null;
  location?: string | null;
};

type MeetingBody = {
  id: string;
  name: string;
  bodyType: string;
  isActive: boolean;
};

type ApiMeetingBody = {
  id: string;
  name: string;
  body_type: string;
  is_active: boolean;
};

type MeetingSchedulePayload = {
  title: string;
  meeting_type: string;
  meeting_body_id?: string;
  scheduled_start: string;
  location: string;
  actor?: string;
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

const demoMeetings: Meeting[] = [
  {
    id: "M-2026-053",
    meetingBodyId: "body-council",
    body: "City Council",
    title: "Regular Meeting",
    meetingType: "regular",
    date: "May 5, 2026",
    time: "6:00 PM",
    scheduledStart: "2026-05-05T18:00:00Z",
    location: "Council Chambers",
    stage: "Agenda published",
    agendaItems: 18,
    packetPages: 142,
    noticeStatus: "Ready",
  },
  {
    id: "M-2026-049",
    meetingBodyId: "body-planning",
    body: "Planning Commission",
    title: "Special Session",
    meetingType: "special",
    date: "May 7, 2026",
    time: "4:30 PM",
    scheduledStart: "2026-05-07T16:30:00Z",
    location: "Room 204",
    stage: "Notice posted",
    agendaItems: 7,
    packetPages: 38,
    noticeStatus: "Warning",
  },
  {
    id: "M-2026-041",
    meetingBodyId: "body-parks",
    body: "Parks Advisory Board",
    title: "Monthly Meeting",
    meetingType: "regular",
    date: "May 13, 2026",
    time: "5:15 PM",
    scheduledStart: "2026-05-13T17:15:00Z",
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

const demoBodies: MeetingBody[] = [
  { id: "body-council", name: "City Council", bodyType: "city_council", isActive: true },
  { id: "body-planning", name: "Planning Commission", bodyType: "commission", isActive: true },
  { id: "body-parks", name: "Parks Advisory Board", bodyType: "advisory_board", isActive: true },
];

function Icon({ label }: { label: string }) {
  return <span className="icon" aria-hidden="true">{label.slice(0, 1)}</span>;
}

export function App() {
  const initial = getInitialView();
  const [page, setPage] = useState<Page>(initial.page);
  const [qaState, setQaState] = useState<ViewState | null>(initial.state);
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [meetingBodies, setMeetingBodies] = useState<MeetingBody[]>([]);
  const [apiState, setApiState] = useState<ViewState>("loading");
  const [apiError, setApiError] = useState<string | null>(null);
  const [bodyState, setBodyState] = useState<ViewState>("loading");
  const [bodyError, setBodyError] = useState<string | null>(null);
  const [activeMeetingId, setActiveMeetingId] = useState(demoMeetings[0].id);
  const [auditOpen, setAuditOpen] = useState(initial.audit);
  const viewState = qaState ?? apiState;
  const visibleMeetings = qaState === null ? meetings : demoMeetings;
  const visibleBodies = qaState === null ? meetingBodies : demoBodies;
  const activeMeeting = visibleMeetings.find((meeting) => meeting.id === activeMeetingId) ?? visibleMeetings[0] ?? demoMeetings[0];

  async function loadWorkspaceData(cancelled: () => boolean) {
    setApiState("loading");
    setBodyState("loading");
    const [apiMeetings, apiBodies] = await Promise.all([fetchMeetings(), fetchMeetingBodies()]);
    if (cancelled()) return;
    const mappedBodies = apiBodies.map(mapApiMeetingBody);
    const mappedMeetings = apiMeetings.map((meeting) => mapApiMeeting(meeting, mappedBodies));
    setMeetingBodies(mappedBodies);
    setMeetings(mappedMeetings);
    setBodyState(mappedBodies.length === 0 ? "empty" : "success");
    setApiState(mappedMeetings.length === 0 ? "empty" : "success");
    if (mappedMeetings[0]) {
      setActiveMeetingId(mappedMeetings[0].id);
    }
  }

  useEffect(() => {
    if (initial.source === "demo") {
      setMeetings(demoMeetings);
      setMeetingBodies(demoBodies);
      setApiState("success");
      setBodyState("success");
      setActiveMeetingId(demoMeetings[0].id);
      return;
    }
    let cancelled = false;
    loadWorkspaceData(() => cancelled)
      .catch((error: Error) => {
        if (cancelled) return;
        setBodyError(error.message);
        setApiError(error.message);
        setApiState("error");
        setBodyState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [initial.source]);

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
          <StateToolbar viewState={viewState} setViewState={setQaState} qaState={qaState} />
          {page === "dashboard" && (
            <Dashboard
              viewState={viewState}
              apiError={apiError}
              meetings={visibleMeetings}
              meetingBodies={visibleBodies}
              bodyState={qaState ?? bodyState}
              bodyError={bodyError}
              onCreateBody={async (name, bodyType) => {
                const body = await createMeetingBody(name, bodyType);
                setMeetingBodies((current) => [...current, mapApiMeetingBody(body)].sort(sortBodies));
                setBodyState("success");
              }}
              onUpdateBody={async (bodyId, name) => {
                const body = await updateMeetingBody(bodyId, { name });
                setMeetingBodies((current) => current.map((item) => item.id === body.id ? mapApiMeetingBody(body) : item).sort(sortBodies));
              }}
              onDeactivateBody={async (bodyId) => {
                const body = await deactivateMeetingBody(bodyId);
                setMeetingBodies((current) => current.map((item) => item.id === body.id ? mapApiMeetingBody(body) : item).sort(sortBodies));
              }}
              onCreateMeeting={async (payload) => {
                const meeting = await createMeeting(payload);
                const mapped = mapApiMeeting(meeting, visibleBodies);
                setMeetings((current) => [...current, mapped].sort(sortMeetings));
                setActiveMeetingId(mapped.id);
              }}
              setPage={setPage}
              setActiveMeetingId={setActiveMeetingId}
            />
          )}
          {page === "meetings" && (
            <MeetingCalendar
              viewState={viewState}
              apiError={apiError}
              meetings={visibleMeetings}
              setPage={setPage}
              setActiveMeetingId={setActiveMeetingId}
            />
          )}
          {page === "meeting-detail" && (
            <MeetingDetail
              meeting={activeMeeting}
              meetingBodies={visibleBodies}
              viewState={viewState}
              apiError={apiError}
              onUpdateMeeting={async (meetingId, payload) => {
                const meeting = await updateMeeting(meetingId, payload);
                const mapped = mapApiMeeting(meeting, visibleBodies);
                setMeetings((current) => current.map((item) => item.id === mapped.id ? mapped : item).sort(sortMeetings));
                setActiveMeetingId(mapped.id);
              }}
            />
          )}
        </section>
        {auditOpen && <AuditDrawer meeting={activeMeeting} />}
      </main>
    </div>
  );
}

async function fetchMeetings(): Promise<ApiMeeting[]> {
  const response = await fetch("/api/meetings", {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Meeting API returned ${response.status}.`);
  }
  const payload = (await response.json()) as { meetings?: ApiMeeting[] };
  return Array.isArray(payload.meetings) ? payload.meetings : [];
}

async function fetchMeetingBodies(): Promise<ApiMeetingBody[]> {
  const response = await fetch("/api/meeting-bodies", {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Meeting body API returned ${response.status}.`);
  }
  const payload = (await response.json()) as { meeting_bodies?: ApiMeetingBody[] };
  return Array.isArray(payload.meeting_bodies) ? payload.meeting_bodies : [];
}

async function createMeetingBody(name: string, bodyType: string): Promise<ApiMeetingBody> {
  const response = await fetch("/api/meeting-bodies", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ name, body_type: bodyType }),
  });
  if (!response.ok) {
    throw new Error(`Meeting body create returned ${response.status}.`);
  }
  return response.json();
}

async function updateMeetingBody(bodyId: string, updates: { name?: string; body_type?: string; is_active?: boolean }): Promise<ApiMeetingBody> {
  const response = await fetch(`/api/meeting-bodies/${bodyId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    throw new Error(`Meeting body update returned ${response.status}.`);
  }
  return response.json();
}

async function deactivateMeetingBody(bodyId: string): Promise<ApiMeetingBody> {
  const response = await fetch(`/api/meeting-bodies/${bodyId}`, {
    method: "DELETE",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Meeting body deactivate returned ${response.status}.`);
  }
  return response.json();
}

async function createMeeting(payload: MeetingSchedulePayload): Promise<ApiMeeting> {
  const response = await fetch("/api/meetings", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Meeting schedule create returned ${response.status}.`);
  }
  return response.json();
}

async function updateMeeting(meetingId: string, payload: MeetingSchedulePayload): Promise<ApiMeeting> {
  const response = await fetch(`/api/meetings/${meetingId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Meeting schedule update returned ${response.status}.`);
  }
  return response.json();
}

function mapApiMeeting(meeting: ApiMeeting, meetingBodies: MeetingBody[] = []): Meeting {
  const scheduled = meeting.scheduled_start ? new Date(meeting.scheduled_start) : null;
  const body = meetingBodies.find((item) => item.id === meeting.meeting_body_id);
  return {
    id: meeting.id,
    meetingBodyId: meeting.meeting_body_id ?? undefined,
    body: body?.name ?? toMeetingBody(meeting.meeting_type),
    title: meeting.title,
    meetingType: meeting.meeting_type,
    date: scheduled ? scheduled.toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" }) : "Not scheduled",
    time: scheduled ? scheduled.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" }) : "Time TBD",
    scheduledStart: meeting.scheduled_start ?? null,
    location: meeting.location ?? "Location TBD",
    stage: toLifecycleStage(meeting.status),
    agendaItems: 0,
    packetPages: 0,
    noticeStatus: meeting.status === "SCHEDULED" ? "Blocked" : "Ready",
  };
}

function mapApiMeetingBody(body: ApiMeetingBody): MeetingBody {
  return {
    id: body.id,
    name: body.name,
    bodyType: body.body_type,
    isActive: body.is_active,
  };
}

function sortBodies(a: MeetingBody, b: MeetingBody) {
  return a.name.localeCompare(b.name);
}

function sortMeetings(a: Meeting, b: Meeting) {
  const left = a.scheduledStart ? new Date(a.scheduledStart).getTime() : Number.MAX_SAFE_INTEGER;
  const right = b.scheduledStart ? new Date(b.scheduledStart).getTime() : Number.MAX_SAFE_INTEGER;
  return left - right || a.title.localeCompare(b.title);
}

function toMeetingBody(meetingType: string): string {
  const normalized = meetingType.replace(/_/g, " ");
  return normalized
    .split(" ")
    .filter(Boolean)
    .map((part) => part.slice(0, 1).toUpperCase() + part.slice(1))
    .join(" ");
}

function toLifecycleStage(status: string): LifecycleStage {
  const map: Record<string, LifecycleStage> = {
    SCHEDULED: "Scheduled",
    NOTICED: "Notice posted",
    PACKET_POSTED: "Agenda published",
    IN_PROGRESS: "In session",
    RECESSED: "In session",
    ADJOURNED: "Adjourned",
    TRANSCRIPT_READY: "Adjourned",
    MINUTES_DRAFTED: "Minutes drafted",
    MINUTES_POSTED: "Minutes drafted",
    MINUTES_ADOPTED: "Minutes approved",
    MINUTES_SIGNED: "Minutes approved",
    ARCHIVED: "Closed and archived",
  };
  return map[status] ?? "Scheduled";
}

function getInitialView(): { page: Page; state: ViewState | null; audit: boolean; source: "api" | "demo" } {
  if (typeof window === "undefined") {
    return { page: "dashboard", state: null, audit: false, source: "api" };
  }
  const params = new URLSearchParams(window.location.search);
  const requestedPage = params.get("page");
  const requestedState = params.get("state");
  const pages: Page[] = ["dashboard", "meetings", "meeting-detail"];
  const states: ViewState[] = ["success", "loading", "empty", "error", "partial"];
  return {
    page: pages.includes(requestedPage as Page) ? (requestedPage as Page) : "dashboard",
    state: states.includes(requestedState as ViewState) ? (requestedState as ViewState) : null,
    audit: params.get("audit") === "1",
    source: params.get("source") === "demo" ? "demo" : "api",
  };
}

function StateToolbar({
  viewState,
  setViewState,
  qaState,
}: {
  viewState: ViewState;
  setViewState: (state: ViewState | null) => void;
  qaState: ViewState | null;
}) {
  const states: ViewState[] = ["success", "loading", "empty", "error", "partial"];
  return (
    <div className="state-toolbar" aria-label="QA state controls">
      <span>QA states</span>
      <button
        className={qaState === null ? "selected" : ""}
        onClick={() => setViewState(null)}
      >
        live
      </button>
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
  apiError,
  meetings,
  meetingBodies,
  bodyState,
  bodyError,
  onCreateBody,
  onUpdateBody,
  onDeactivateBody,
  onCreateMeeting,
  setPage,
  setActiveMeetingId,
}: {
  viewState: ViewState;
  apiError: string | null;
  meetings: Meeting[];
  meetingBodies: MeetingBody[];
  bodyState: ViewState;
  bodyError: string | null;
  onCreateBody: (name: string, bodyType: string) => Promise<void>;
  onUpdateBody: (bodyId: string, name: string) => Promise<void>;
  onDeactivateBody: (bodyId: string) => Promise<void>;
  onCreateMeeting: (payload: MeetingSchedulePayload) => Promise<void>;
  setPage: (page: Page) => void;
  setActiveMeetingId: (id: string) => void;
}) {
  if (viewState !== "success") {
    return <StateMessage state={viewState} context="dashboard" apiError={apiError} />;
  }

  const blockedNotices = meetings.filter((meeting) => meeting.noticeStatus !== "Ready").length;
  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="CivicClerk staff workspace"
        title="Good morning, City Clerk."
        description="Today's meeting work is grouped by urgency, public posting risk, and packet readiness."
      />
      <div className="metric-grid">
        <MetricCard label="Meetings this week" value={String(meetings.length)} note="Live from CivicClerk meeting API" />
        <MetricCard label="Agenda items pending" value="14" note="3 need clerk review" />
        <MetricCard label="Notice warnings" value={String(blockedNotices)} note="Resolve before public posting" tone={blockedNotices ? "warn" : undefined} />
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
                const target = meetings[Math.min(index, meetings.length - 1)];
                if (target) {
                  setActiveMeetingId(target.id);
                }
                setPage("meeting-detail");
              }}
            >
              <span>{task}</span>
              <strong>{index === 0 ? "Review" : index === 1 ? "Finalize" : "Fix warning"}</strong>
            </button>
          ))}
        </div>
      </section>
      <MeetingBodiesPanel
        meetingBodies={meetingBodies}
        bodyState={bodyState}
        bodyError={bodyError}
        onCreateBody={onCreateBody}
        onUpdateBody={onUpdateBody}
        onDeactivateBody={onDeactivateBody}
      />
      <MeetingSchedulingPanel meetingBodies={meetingBodies} onCreateMeeting={onCreateMeeting} />
    </div>
  );
}

function MeetingSchedulingPanel({
  meetingBodies,
  onCreateMeeting,
}: {
  meetingBodies: MeetingBody[];
  onCreateMeeting: (payload: MeetingSchedulePayload) => Promise<void>;
}) {
  const activeBodies = meetingBodies.filter((body) => body.isActive);
  const [title, setTitle] = useState("Regular Meeting");
  const [bodyId, setBodyId] = useState(activeBodies[0]?.id ?? "");
  const [meetingType, setMeetingType] = useState("regular");
  const [scheduledStart, setScheduledStart] = useState("2026-05-05T18:00");
  const [location, setLocation] = useState("Council Chambers");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!bodyId && activeBodies[0]) {
      setBodyId(activeBodies[0].id);
    }
  }, [activeBodies, bodyId]);

  async function submitMeeting(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    const selectedBody = activeBodies.find((body) => body.id === bodyId);
    if (!selectedBody) {
      setMessage("Choose an active meeting body before scheduling. Create or reactivate a body, then retry.");
      return;
    }
    try {
      await onCreateMeeting({
        title: title.trim(),
        meeting_type: meetingType.trim(),
        meeting_body_id: selectedBody.id,
        scheduled_start: new Date(scheduledStart).toISOString(),
        location: location.trim(),
        actor: "clerk@example.gov",
      });
    } catch (error) {
      setMessage(`${error instanceof Error ? error.message : "Meeting schedule create failed."} Confirm the API is running, check staff auth, then retry.`);
      return;
    }
    setMessage("Meeting scheduled. It now appears on the staff calendar and can be opened for detail work.");
  }

  return (
    <section className="panel schedule-admin" aria-label="Meeting scheduling">
      <div className="panel-heading">
        <div>
          <h2>Schedule a meeting</h2>
          <p>Create a real calendar record tied to an active board or commission.</p>
        </div>
        <StatusBadge tone={activeBodies.length ? "Ready" : "Blocked"} label={activeBodies.length ? "Ready" : "Needs body"} />
      </div>
      <form className="schedule-form" onSubmit={submitMeeting}>
        <label>
          Meeting body
          <select value={bodyId} onChange={(event) => setBodyId(event.target.value)} required>
            <option value="" disabled>Choose a body</option>
            {activeBodies.map((body) => (
              <option key={body.id} value={body.id}>{body.name}</option>
            ))}
          </select>
        </label>
        <label>
          Title
          <input value={title} onChange={(event) => setTitle(event.target.value)} required />
        </label>
        <label>
          Type
          <select value={meetingType} onChange={(event) => setMeetingType(event.target.value)} required>
            <option value="regular">Regular</option>
            <option value="special">Special</option>
            <option value="emergency">Emergency</option>
            <option value="closed_session">Closed session</option>
          </select>
        </label>
        <label>
          Starts
          <input type="datetime-local" value={scheduledStart} onChange={(event) => setScheduledStart(event.target.value)} required />
        </label>
        <label>
          Location
          <input value={location} onChange={(event) => setLocation(event.target.value)} required />
        </label>
        <button type="submit">Schedule meeting</button>
      </form>
      {message && <p className="form-message">{message}</p>}
    </section>
  );
}

function MeetingBodiesPanel({
  meetingBodies,
  bodyState,
  bodyError,
  onCreateBody,
  onUpdateBody,
  onDeactivateBody,
}: {
  meetingBodies: MeetingBody[];
  bodyState: ViewState;
  bodyError: string | null;
  onCreateBody: (name: string, bodyType: string) => Promise<void>;
  onUpdateBody: (bodyId: string, name: string) => Promise<void>;
  onDeactivateBody: (bodyId: string) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [bodyType, setBodyType] = useState("board");
  const [draftNames, setDraftNames] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<string | null>(null);

  async function submitBody(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      await onCreateBody(name.trim(), bodyType.trim());
    } catch (error) {
      setMessage(`${error instanceof Error ? error.message : "Meeting body create failed."} Check the API, then retry.`);
      return;
    }
    setName("");
    setBodyType("board");
    setMessage("Meeting body created. It is now available for scheduling.");
  }

  async function saveBody(body: MeetingBody) {
    const nextName = (draftNames[body.id] ?? body.name).trim();
    if (!nextName) {
      setMessage("Name is required before saving a meeting body.");
      return;
    }
    try {
      await onUpdateBody(body.id, nextName);
    } catch (error) {
      setMessage(`${error instanceof Error ? error.message : "Meeting body update failed."} Check the API, then retry.`);
      return;
    }
    setMessage("Meeting body updated without changing its record identity.");
  }

  async function deactivate(body: MeetingBody) {
    try {
      await onDeactivateBody(body.id);
    } catch (error) {
      setMessage(`${error instanceof Error ? error.message : "Meeting body deactivate failed."} Check the API, then retry.`);
      return;
    }
    setMessage(`${body.name} was deactivated. Existing meeting history is preserved.`);
  }

  if (bodyState === "loading" || bodyState === "error" || bodyState === "partial") {
    return <StateMessage state={bodyState} context="meeting bodies" apiError={bodyError} />;
  }

  return (
    <section className="panel body-admin" aria-label="Meeting body management">
      <div className="panel-heading">
        <div>
          <h2>Meeting bodies</h2>
          <p>Create, rename, and deactivate boards without losing meeting history.</p>
        </div>
        <StatusBadge tone="Ready" label={`${meetingBodies.filter((body) => body.isActive).length} active`} />
      </div>
      <form className="body-form" onSubmit={submitBody}>
        <label>
          Body name
          <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Library Board" required />
        </label>
        <label>
          Body type
          <input value={bodyType} onChange={(event) => setBodyType(event.target.value)} placeholder="board" required />
        </label>
        <button type="submit">Create meeting body</button>
      </form>
      {message && <p className="form-message">{message}</p>}
      <div className="body-list">
        {meetingBodies.length === 0 && (
          <p className="empty-inline">No meeting bodies exist yet. Create City Council, Planning Commission, or another board to start scheduling real meetings.</p>
        )}
        {meetingBodies.map((body) => (
          <article key={body.id} className={body.isActive ? "body-row" : "body-row inactive"}>
            <div>
              <strong>{body.name}</strong>
              <span>{body.bodyType.replace(/_/g, " ")} - {body.isActive ? "Active" : "Inactive"}</span>
            </div>
            <input
              aria-label={`Rename ${body.name}`}
              value={draftNames[body.id] ?? body.name}
              onChange={(event) => setDraftNames((current) => ({ ...current, [body.id]: event.target.value }))}
            />
            <button className="secondary" onClick={() => saveBody(body)}>Save name</button>
            <button className="secondary" onClick={() => deactivate(body)} disabled={!body.isActive}>Deactivate</button>
          </article>
        ))}
      </div>
    </section>
  );
}

function MeetingCalendar({
  viewState,
  apiError,
  meetings,
  setPage,
  setActiveMeetingId,
}: {
  viewState: ViewState;
  apiError: string | null;
  meetings: Meeting[];
  setPage: (page: Page) => void;
  setActiveMeetingId: (id: string) => void;
}) {
  if (viewState !== "success") {
    return <StateMessage state={viewState} context="meeting calendar" apiError={apiError} />;
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
            const dayMeetings = meetings.filter((meeting) => dayFromMeeting(meeting) === day);
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

function dayFromMeeting(meeting: Meeting): number | null {
  const match = meeting.date.match(/\b(\d{1,2})\b/);
  return match ? Number(match[1]) : null;
}

function toDateTimeLocalValue(value?: string | null): string {
  if (!value) {
    return "2026-05-05T18:00";
  }
  const date = new Date(value);
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function MeetingDetail({
  meeting,
  meetingBodies,
  viewState,
  apiError,
  onUpdateMeeting,
}: {
  meeting: Meeting;
  meetingBodies: MeetingBody[];
  viewState: ViewState;
  apiError: string | null;
  onUpdateMeeting: (meetingId: string, payload: MeetingSchedulePayload) => Promise<void>;
}) {
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
    return <StateMessage state={viewState} context="meeting detail" apiError={apiError} />;
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
      <MeetingEditPanel meeting={meeting} meetingBodies={meetingBodies} onUpdateMeeting={onUpdateMeeting} />
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

function MeetingEditPanel({
  meeting,
  meetingBodies,
  onUpdateMeeting,
}: {
  meeting: Meeting;
  meetingBodies: MeetingBody[];
  onUpdateMeeting: (meetingId: string, payload: MeetingSchedulePayload) => Promise<void>;
}) {
  const [title, setTitle] = useState(meeting.title);
  const [bodyId, setBodyId] = useState(meeting.meetingBodyId ?? meetingBodies[0]?.id ?? "");
  const [meetingType, setMeetingType] = useState(meeting.meetingType);
  const [scheduledStart, setScheduledStart] = useState(toDateTimeLocalValue(meeting.scheduledStart));
  const [location, setLocation] = useState(meeting.location);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setTitle(meeting.title);
    setBodyId(meeting.meetingBodyId ?? meetingBodies[0]?.id ?? "");
    setMeetingType(meeting.meetingType);
    setScheduledStart(toDateTimeLocalValue(meeting.scheduledStart));
    setLocation(meeting.location);
  }, [meeting, meetingBodies]);

  useEffect(() => {
    setMessage(null);
  }, [meeting.id]);

  async function submitUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      await onUpdateMeeting(meeting.id, {
        title: title.trim(),
        meeting_type: meetingType,
        meeting_body_id: bodyId,
        scheduled_start: new Date(scheduledStart).toISOString(),
        location: location.trim(),
        actor: "clerk@example.gov",
      });
    } catch (error) {
      setMessage(`${error instanceof Error ? error.message : "Meeting schedule update failed."} If the meeting is already in progress, create a replacement meeting or record the change in minutes.`);
      return;
    }
    setMessage("Meeting schedule updated. The audit trail records who changed the scheduling fields.");
  }

  return (
    <section className="panel schedule-admin" aria-label="Edit meeting schedule">
      <div className="panel-heading">
        <div>
          <h2>Edit schedule</h2>
          <p>Adjust clerk-owned scheduling fields before the legal meeting record is locked.</p>
        </div>
        <StatusBadge tone={meeting.stage === "Scheduled" || meeting.stage === "Notice posted" || meeting.stage === "Agenda published" ? "Ready" : "Warning"} label={meeting.stage} />
      </div>
      <form className="schedule-form" onSubmit={submitUpdate}>
        <label>
          Meeting body
          <select value={bodyId} onChange={(event) => setBodyId(event.target.value)} required>
            {meetingBodies.filter((body) => body.isActive || body.id === bodyId).map((body) => (
              <option key={body.id} value={body.id}>{body.name}</option>
            ))}
          </select>
        </label>
        <label>
          Title
          <input value={title} onChange={(event) => setTitle(event.target.value)} required />
        </label>
        <label>
          Type
          <select value={meetingType} onChange={(event) => setMeetingType(event.target.value)} required>
            <option value="regular">Regular</option>
            <option value="special">Special</option>
            <option value="emergency">Emergency</option>
            <option value="closed_session">Closed session</option>
          </select>
        </label>
        <label>
          Starts
          <input type="datetime-local" value={scheduledStart} onChange={(event) => setScheduledStart(event.target.value)} required />
        </label>
        <label>
          Location
          <input value={location} onChange={(event) => setLocation(event.target.value)} required />
        </label>
        <button type="submit">Save schedule</button>
      </form>
      {message && <p className="form-message">{message}</p>}
    </section>
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

function StateMessage({ state, context, apiError }: { state: ViewState; context: string; apiError: string | null }) {
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
      body: apiError
        ? `${apiError} Confirm the backend is running, verify staff auth mode, then retry.`
        : "The staff API did not respond. Confirm the backend is running, verify staff auth mode, then retry.",
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
