import { useEffect, useMemo, useState, type FormEvent } from "react";

type ViewState = "success" | "loading" | "empty" | "error" | "partial";
type Page = "dashboard" | "meetings" | "meeting-detail" | "agenda" | "packet" | "notice" | "outcomes" | "minutes" | "public";
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

type AgendaIntakeItem = {
  id: string;
  title: string;
  departmentName: string;
  submittedBy: string;
  summary: string;
  readinessStatus: "PENDING" | "READY" | "NEEDS_REVISION";
  status: string;
  sourceReferences: Array<Record<string, string>>;
  reviewer?: string | null;
  reviewNotes?: string | null;
  promotedAgendaItemId?: string | null;
  promotedAt?: string | null;
  promotionAuditHash?: string | null;
  lastAuditHash: string;
  createdAt: string;
  updatedAt: string;
};

type ApiAgendaIntakeItem = {
  id: string;
  title: string;
  department_name: string;
  submitted_by: string;
  summary: string;
  readiness_status: "PENDING" | "READY" | "NEEDS_REVISION";
  status: string;
  source_references: Array<Record<string, string>>;
  reviewer?: string | null;
  review_notes?: string | null;
  promoted_agenda_item_id?: string | null;
  promoted_at?: string | null;
  promotion_audit_hash?: string | null;
  last_audit_hash: string;
  created_at: string;
  updated_at: string;
};

type AgendaIntakePayload = {
  title: string;
  department_name: string;
  submitted_by: string;
  summary: string;
  source_references: Array<Record<string, string>>;
};

type AgendaReviewPayload = {
  reviewer: string;
  ready: boolean;
  notes: string;
};

type AgendaPromotionPayload = {
  reviewer: string;
  notes: string;
};

type AgendaPromotionResult = {
  intake_item: ApiAgendaIntakeItem;
  agenda_item: {
    id: string;
    title: string;
    department_name: string;
    status: string;
  } | null;
  next_step: string;
  message: string;
};

type PacketAssemblyRecord = {
  id: string;
  meetingId: string;
  title: string;
  status: "DRAFT" | "FINALIZED";
  packetVersion: number;
  agendaItemIds: string[];
  auditHash: string;
  finalizedAt?: string | null;
};

type ApiPacketAssemblyRecord = {
  id: string;
  meeting_id: string;
  title: string;
  status: "DRAFT" | "FINALIZED";
  packet_version: number;
  agenda_item_ids: string[];
  audit_hash?: string;
  last_audit_hash?: string;
  finalized_at?: string | null;
};

type PacketAssemblyPayload = {
  title: string;
  agenda_item_ids: string[];
  actor: string;
  source_references: Array<Record<string, string>>;
  citations: Array<Record<string, string>>;
};

type NoticeChecklistRecord = {
  id: string;
  meetingId: string;
  noticeType: string;
  status: "CHECKED" | "POSTED";
  compliant: boolean;
  httpStatus: number;
  warnings: Array<Record<string, string>>;
  deadlineAt: string;
  postedAt: string;
  minimumNoticeHours: number;
  statutoryBasis?: string | null;
  approvedBy?: string | null;
  postingProof?: Record<string, string> | null;
  lastAuditHash: string;
  createdAt: string;
  updatedAt: string;
};

type ApiNoticeChecklistRecord = {
  id: string;
  meeting_id: string;
  notice_type: string;
  status: "CHECKED" | "POSTED";
  compliant: boolean;
  http_status: number;
  warnings: Array<Record<string, string>>;
  deadline_at: string;
  posted_at: string;
  minimum_notice_hours: number;
  statutory_basis?: string | null;
  approved_by?: string | null;
  posting_proof?: Record<string, string> | null;
  last_audit_hash: string;
  created_at: string;
  updated_at: string;
};

type NoticeChecklistPayload = {
  notice_type: string;
  posted_at: string;
  minimum_notice_hours: number;
  statutory_basis: string;
  approved_by: string;
  actor: string;
};

type NoticePostingProofPayload = {
  actor: string;
  posting_proof: Record<string, string>;
};

type MotionRecord = {
  id: string;
  meetingId: string;
  agendaItemId?: string | null;
  text: string;
  actor: string;
  correctionOfId?: string | null;
  correctionReason?: string | null;
  captured: boolean;
};

type ApiMotionRecord = {
  id: string;
  meeting_id: string;
  agenda_item_id?: string | null;
  text: string;
  actor: string;
  correction_of_id?: string | null;
  correction_reason?: string | null;
  captured: boolean;
};

type VoteRecord = {
  id: string;
  motionId: string;
  voterName: string;
  vote: string;
  actor: string;
  correctionOfId?: string | null;
  correctionReason?: string | null;
  captured: boolean;
};

type ApiVoteRecord = {
  id: string;
  motion_id: string;
  voter_name: string;
  vote: string;
  actor: string;
  correction_of_id?: string | null;
  correction_reason?: string | null;
  captured: boolean;
};

type ActionItemRecord = {
  id: string;
  meetingId: string;
  description: string;
  actor: string;
  assignedTo?: string | null;
  sourceMotionId?: string | null;
  status: string;
};

type ApiActionItemRecord = {
  id: string;
  meeting_id: string;
  description: string;
  actor: string;
  assigned_to?: string | null;
  source_motion_id?: string | null;
  status: string;
};

type MotionPayload = {
  text: string;
  actor: string;
  agenda_item_id?: string;
};

type VotePayload = {
  voter_name: string;
  vote: string;
  actor: string;
};

type ActionItemPayload = {
  description: string;
  actor: string;
  assigned_to?: string;
  source_motion_id: string;
};

type SourceMaterialRecord = {
  sourceId: string;
  label: string;
  text: string;
};

type ApiSourceMaterialRecord = {
  source_id: string;
  label: string;
  text: string;
};

type MinutesSentenceRecord = {
  text: string;
  citations: string[];
};

type ApiMinutesSentenceRecord = {
  text: string;
  citations: string[];
};

type MinutesProvenanceRecord = {
  model: string;
  promptVersion: string;
  dataSources: string[];
  humanApprover: string;
};

type ApiMinutesProvenanceRecord = {
  model: string;
  prompt_version: string;
  data_sources: string[];
  human_approver: string;
};

type MinutesDraftRecord = {
  id: string;
  meetingId: string;
  status: string;
  sentences: MinutesSentenceRecord[];
  sourceMaterials: SourceMaterialRecord[];
  provenance: MinutesProvenanceRecord;
  adopted: boolean;
  posted: boolean;
};

type ApiMinutesDraftRecord = {
  id: string;
  meeting_id: string;
  status: string;
  sentences: ApiMinutesSentenceRecord[];
  source_materials: ApiSourceMaterialRecord[];
  provenance: ApiMinutesProvenanceRecord;
  adopted: boolean;
  posted: boolean;
};

type MinutesDraftPayload = {
  model: string;
  prompt_version: string;
  human_approver: string;
  source_materials: ApiSourceMaterialRecord[];
  sentences: ApiMinutesSentenceRecord[];
};

type PublicMeetingRecord = {
  id: string;
  meetingId: string;
  title: string;
  postedAgenda: string;
  postedPacket: string;
  approvedMinutes: string;
};

type ApiPublicMeetingRecord = {
  id: string;
  meeting_id: string;
  title: string;
  posted_agenda: string;
  posted_packet: string;
  approved_minutes: string;
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

const demoAgendaItems: AgendaIntakeItem[] = [
  {
    id: "AI-1042",
    title: "Approve downtown zoning study",
    departmentName: "Planning",
    submittedBy: "planning@example.gov",
    summary: "Authorize the downtown zoning study scope, consultant agreement, and public engagement calendar.",
    readinessStatus: "PENDING",
    status: "SUBMITTED",
    sourceReferences: [{ source_id: "zoning-memo", title: "Planning memo", kind: "document" }],
    reviewer: null,
    reviewNotes: null,
    lastAuditHash: "f7b9b7c4e5f2b8c8c1e3a2d0b9a4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2",
    createdAt: "2026-05-01T15:30:00Z",
    updatedAt: "2026-05-01T15:30:00Z",
  },
  {
    id: "AI-1040",
    title: "Adopt annual fee schedule",
    departmentName: "Finance",
    submittedBy: "finance@example.gov",
    summary: "Annual update to city service fees with attorney-reviewed exhibit table.",
    readinessStatus: "READY",
    status: "READY_FOR_CLERK",
    sourceReferences: [{ source_id: "fee-table", title: "Fee table", kind: "spreadsheet" }],
    reviewer: "clerk@example.gov",
    reviewNotes: "Attorney review attached. Ready for packet assembly.",
    promotedAgendaItemId: "agenda-fee-schedule",
    promotedAt: "2026-05-01T16:15:00Z",
    promotionAuditHash: "90123456789abcdef0123456789abcdef0123456789abcdef0123456789abcd",
    lastAuditHash: "a0b1c2d3e4f506172839405162738495a6b7c8d9e0f112233445566778899001",
    createdAt: "2026-04-30T21:10:00Z",
    updatedAt: "2026-05-01T16:00:00Z",
  },
];

const demoPacketAssemblies: PacketAssemblyRecord[] = [
  {
    id: "packet-demo-1",
    meetingId: "M-2026-053",
    title: "City Council packet draft",
    status: "DRAFT",
    packetVersion: 1,
    agendaItemIds: ["agenda-fee-schedule"],
    auditHash: "b123456789abcdef0123456789abcdef0123456789abcdef0123456789abcde",
    finalizedAt: null,
  },
];

const demoNoticeChecklists: NoticeChecklistRecord[] = [
  {
    id: "notice-demo-1",
    meetingId: "M-2026-053",
    noticeType: "regular",
    status: "CHECKED",
    compliant: true,
    httpStatus: 200,
    warnings: [],
    deadlineAt: "2026-05-02T18:00:00Z",
    postedAt: "2026-05-01T18:00:00Z",
    minimumNoticeHours: 72,
    statutoryBasis: "Local open meeting law requires 72 hours posted notice.",
    approvedBy: "clerk@example.gov",
    postingProof: null,
    lastAuditHash: "c123456789abcdef0123456789abcdef0123456789abcdef0123456789abcde",
    createdAt: "2026-05-01T12:30:00Z",
    updatedAt: "2026-05-01T12:30:00Z",
  },
  {
    id: "notice-demo-2",
    meetingId: "M-2026-049",
    noticeType: "special",
    status: "CHECKED",
    compliant: false,
    httpStatus: 422,
    warnings: [{ code: "notice_deadline_missed", fix: "Reschedule the meeting or document the lawful emergency basis before proceeding." }],
    deadlineAt: "2026-05-06T16:30:00Z",
    postedAt: "2026-05-07T09:00:00Z",
    minimumNoticeHours: 24,
    statutoryBasis: "",
    approvedBy: "",
    postingProof: null,
    lastAuditHash: "d123456789abcdef0123456789abcdef0123456789abcdef0123456789abcde",
    createdAt: "2026-05-07T09:05:00Z",
    updatedAt: "2026-05-07T09:05:00Z",
  },
];

const demoMotions: MotionRecord[] = [
  {
    id: "motion-demo-1",
    meetingId: "M-2026-053",
    agendaItemId: "agenda-fee-schedule",
    text: "Move to adopt the annual fee schedule as presented in the packet.",
    actor: "clerk@example.gov",
    correctionOfId: null,
    correctionReason: null,
    captured: true,
  },
  {
    id: "motion-demo-2",
    meetingId: "M-2026-053",
    agendaItemId: null,
    text: "Move to direct Public Works to inspect sidewalk repair segments and report back.",
    actor: "clerk@example.gov",
    correctionOfId: null,
    correctionReason: null,
    captured: true,
  },
];

const demoVotes: VoteRecord[] = [
  { id: "vote-demo-1", motionId: "motion-demo-1", voterName: "Council Member Rivera", vote: "aye", actor: "clerk@example.gov", captured: true },
  { id: "vote-demo-2", motionId: "motion-demo-1", voterName: "Council Member Patel", vote: "aye", actor: "clerk@example.gov", captured: true },
  { id: "vote-demo-3", motionId: "motion-demo-1", voterName: "Council Member Owens", vote: "abstain", actor: "clerk@example.gov", captured: true },
];

const demoActionItems: ActionItemRecord[] = [
  {
    id: "action-demo-1",
    meetingId: "M-2026-053",
    description: "Public Works to inspect sidewalk repair segments and return with a completion schedule.",
    actor: "clerk@example.gov",
    assignedTo: "Public Works",
    sourceMotionId: "motion-demo-2",
    status: "OPEN",
  },
];

const demoMinutesDrafts: MinutesDraftRecord[] = [
  {
    id: "minutes-demo-1",
    meetingId: "M-2026-053",
    status: "DRAFT",
    adopted: false,
    posted: false,
    provenance: {
      model: "ollama/gemma4",
      promptVersion: "minutes_draft@0.1.0",
      dataSources: ["motion-demo-1", "vote-demo-1"],
      humanApprover: "clerk@example.gov",
    },
    sourceMaterials: [
      {
        sourceId: "motion-demo-1",
        label: "Motion text",
        text: "Move to adopt the annual fee schedule as presented in the packet.",
      },
      {
        sourceId: "vote-demo-1",
        label: "Vote record",
        text: "The motion carried with two ayes and one abstention in the demo roll call.",
      },
    ],
    sentences: [
      {
        text: "Council considered and adopted the annual fee schedule as presented in the packet.",
        citations: ["motion-demo-1"],
      },
      {
        text: "The recorded roll call supported adoption with ayes from Rivera and Patel and an abstention from Owens.",
        citations: ["vote-demo-1"],
      },
    ],
  },
];

const demoPublicRecords: PublicMeetingRecord[] = [
  {
    id: "public-demo-1",
    meetingId: "M-2026-053",
    title: "City Council Regular Meeting",
    postedAgenda: "Agenda: consent calendar, downtown sidewalk repair award, and public comment.",
    postedPacket: "Packet: staff report, fiscal note, bid tabulation, and notice proof.",
    approvedMinutes: "Approved minutes: motion passed 5-0; packet and notice proof accepted into the public record.",
  },
  {
    id: "public-demo-2",
    meetingId: "M-2026-041",
    title: "Parks Advisory Board Monthly Meeting",
    postedAgenda: "Agenda: trail grant update, summer program schedule, and resident comment.",
    postedPacket: "Packet: grant memo, program calendar, and accessibility checklist.",
    approvedMinutes: "Approved minutes: board recommended grant application submission.",
  },
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
  const [agendaItems, setAgendaItems] = useState<AgendaIntakeItem[]>([]);
  const [packetAssemblies, setPacketAssemblies] = useState<PacketAssemblyRecord[]>([]);
  const [loadedPacketMeetingIds, setLoadedPacketMeetingIds] = useState<string[]>([]);
  const [noticeChecklists, setNoticeChecklists] = useState<NoticeChecklistRecord[]>([]);
  const [loadedNoticeMeetingIds, setLoadedNoticeMeetingIds] = useState<string[]>([]);
  const [motions, setMotions] = useState<MotionRecord[]>([]);
  const [votes, setVotes] = useState<VoteRecord[]>([]);
  const [actionItems, setActionItems] = useState<ActionItemRecord[]>([]);
  const [loadedOutcomeMeetingIds, setLoadedOutcomeMeetingIds] = useState<string[]>([]);
  const [minutesDrafts, setMinutesDrafts] = useState<MinutesDraftRecord[]>([]);
  const [loadedMinutesMeetingIds, setLoadedMinutesMeetingIds] = useState<string[]>([]);
  const [publicRecords, setPublicRecords] = useState<PublicMeetingRecord[]>([]);
  const [publicRecordDetail, setPublicRecordDetail] = useState<PublicMeetingRecord | null>(null);
  const [apiState, setApiState] = useState<ViewState>("loading");
  const [apiError, setApiError] = useState<string | null>(null);
  const [bodyState, setBodyState] = useState<ViewState>("loading");
  const [bodyError, setBodyError] = useState<string | null>(null);
  const [packetState, setPacketState] = useState<ViewState>("loading");
  const [packetError, setPacketError] = useState<string | null>(null);
  const [noticeState, setNoticeState] = useState<ViewState>("loading");
  const [noticeError, setNoticeError] = useState<string | null>(null);
  const [outcomeState, setOutcomeState] = useState<ViewState>("loading");
  const [outcomeError, setOutcomeError] = useState<string | null>(null);
  const [minutesState, setMinutesState] = useState<ViewState>("loading");
  const [minutesError, setMinutesError] = useState<string | null>(null);
  const [publicState, setPublicState] = useState<ViewState>("loading");
  const [publicError, setPublicError] = useState<string | null>(null);
  const [activeMeetingId, setActiveMeetingId] = useState(demoMeetings[0].id);
  const [auditOpen, setAuditOpen] = useState(initial.audit);
  const viewState = qaState ?? apiState;
  const visibleMeetings = qaState === null ? meetings : demoMeetings;
  const visibleBodies = qaState === null ? meetingBodies : demoBodies;
  const visibleAgendaItems = qaState === null ? agendaItems : demoAgendaItems;
  const visiblePacketAssemblies = qaState === null ? packetAssemblies : demoPacketAssemblies;
  const visibleNoticeChecklists = qaState === null ? noticeChecklists : demoNoticeChecklists;
  const visibleMotions = qaState === null ? motions : demoMotions;
  const visibleVotes = qaState === null ? votes : demoVotes;
  const visibleActionItems = qaState === null ? actionItems : demoActionItems;
  const visibleMinutesDrafts = qaState === null ? minutesDrafts : demoMinutesDrafts;
  const visiblePublicRecords = qaState === null ? publicRecords : demoPublicRecords;
  const visiblePublicDetail = qaState === null ? publicRecordDetail : demoPublicRecords[0];
  const activeMeeting = visibleMeetings.find((meeting) => meeting.id === activeMeetingId) ?? visibleMeetings[0] ?? demoMeetings[0];

  async function loadWorkspaceData(cancelled: () => boolean) {
    setApiState("loading");
    setBodyState("loading");
    const [apiMeetings, apiBodies, apiAgendaItems] = await Promise.all([
      fetchMeetings(),
      fetchMeetingBodies(),
      fetchAgendaIntakeItems(),
    ]);
    if (cancelled()) return;
    const mappedBodies = apiBodies.map(mapApiMeetingBody);
    const mappedMeetings = apiMeetings.map((meeting) => mapApiMeeting(meeting, mappedBodies));
    const mappedAgendaItems = apiAgendaItems.map(mapApiAgendaIntakeItem);
    setMeetingBodies(mappedBodies);
    setMeetings(mappedMeetings);
    setAgendaItems(mappedAgendaItems);
    if (mappedMeetings[0]) {
      try {
        const apiPackets = await fetchPacketAssemblies(mappedMeetings[0].id);
        if (cancelled()) return;
        setPacketAssemblies(apiPackets.map(mapApiPacketAssemblyRecord));
        setLoadedPacketMeetingIds([mappedMeetings[0].id]);
        setPacketError(null);
        setPacketState("success");
      } catch (error) {
        if (cancelled()) return;
        setPacketAssemblies([]);
        setLoadedPacketMeetingIds([]);
        setPacketError(error instanceof Error ? error.message : "Packet assembly API failed.");
        setPacketState("error");
      }
      try {
        const apiNotices = await fetchNoticeChecklists(mappedMeetings[0].id);
        if (cancelled()) return;
        setNoticeChecklists(sortNoticeChecklistRecords(apiNotices.map(mapApiNoticeChecklistRecord)));
        setLoadedNoticeMeetingIds([mappedMeetings[0].id]);
        setNoticeError(null);
        setNoticeState("success");
      } catch (error) {
        if (cancelled()) return;
        setNoticeChecklists([]);
        setLoadedNoticeMeetingIds([]);
        setNoticeError(error instanceof Error ? error.message : "Notice checklist API failed.");
        setNoticeState("error");
      }
      try {
        const outcomeBundle = await fetchMeetingOutcomes(mappedMeetings[0].id);
        if (cancelled()) return;
        setMotions(outcomeBundle.motions.map(mapApiMotionRecord));
        setVotes(outcomeBundle.votes.map(mapApiVoteRecord));
        setActionItems(outcomeBundle.actionItems.map(mapApiActionItemRecord));
        setLoadedOutcomeMeetingIds([mappedMeetings[0].id]);
        setOutcomeError(null);
        setOutcomeState(outcomeBundle.motions.length === 0 && outcomeBundle.actionItems.length === 0 ? "empty" : "success");
      } catch (error) {
        if (cancelled()) return;
        setMotions([]);
        setVotes([]);
        setActionItems([]);
        setLoadedOutcomeMeetingIds([]);
        setOutcomeError(error instanceof Error ? error.message : "Meeting outcomes API failed.");
        setOutcomeState("error");
      }
      try {
        const apiMinutesDrafts = await fetchMinutesDrafts(mappedMeetings[0].id);
        if (cancelled()) return;
        const mappedMinutes = apiMinutesDrafts.map(mapApiMinutesDraftRecord);
        setMinutesDrafts(mappedMinutes);
        setLoadedMinutesMeetingIds([mappedMeetings[0].id]);
        setMinutesError(null);
        setMinutesState(mappedMinutes.length === 0 ? "empty" : "success");
      } catch (error) {
        if (cancelled()) return;
        setMinutesDrafts([]);
        setLoadedMinutesMeetingIds([]);
        setMinutesError(error instanceof Error ? error.message : "Minutes draft API failed.");
        setMinutesState("error");
      }
      try {
        const apiPublicRecords = await fetchPublicMeetings();
        if (cancelled()) return;
        const mappedPublicRecords = apiPublicRecords.map(mapApiPublicMeetingRecord);
        setPublicRecords(mappedPublicRecords);
        setPublicRecordDetail(mappedPublicRecords[0] ?? null);
        setPublicError(null);
        setPublicState(mappedPublicRecords.length === 0 ? "empty" : "success");
      } catch (error) {
        if (cancelled()) return;
        setPublicRecords([]);
        setPublicRecordDetail(null);
        setPublicError(error instanceof Error ? error.message : "Public meeting API failed.");
        setPublicState("error");
      }
    } else {
      setPacketAssemblies([]);
      setLoadedPacketMeetingIds([]);
      setPacketState("empty");
      setNoticeChecklists([]);
      setLoadedNoticeMeetingIds([]);
      setNoticeState("empty");
      setMotions([]);
      setVotes([]);
      setActionItems([]);
      setLoadedOutcomeMeetingIds([]);
      setOutcomeState("empty");
      setMinutesDrafts([]);
      setLoadedMinutesMeetingIds([]);
      setMinutesState("empty");
      setPublicRecords([]);
      setPublicRecordDetail(null);
      setPublicState("empty");
    }
    setBodyState(mappedBodies.length === 0 ? "empty" : "success");
    setApiState(mappedMeetings.length === 0 && mappedAgendaItems.length === 0 ? "empty" : "success");
    if (mappedMeetings[0]) {
      setActiveMeetingId(mappedMeetings[0].id);
    }
  }

  useEffect(() => {
    if (initial.source === "demo") {
      setMeetings(demoMeetings);
      setMeetingBodies(demoBodies);
      setAgendaItems(demoAgendaItems);
      setPacketAssemblies(demoPacketAssemblies);
      setLoadedPacketMeetingIds(demoMeetings.map((meeting) => meeting.id));
      setNoticeChecklists(sortNoticeChecklistRecords(demoNoticeChecklists));
      setLoadedNoticeMeetingIds(demoMeetings.map((meeting) => meeting.id));
      setMotions(demoMotions);
      setVotes(demoVotes);
      setActionItems(demoActionItems);
      setLoadedOutcomeMeetingIds(demoMeetings.map((meeting) => meeting.id));
      setMinutesDrafts(demoMinutesDrafts);
      setLoadedMinutesMeetingIds(demoMeetings.map((meeting) => meeting.id));
      setPublicRecords(demoPublicRecords);
      setPublicRecordDetail(demoPublicRecords[0]);
      setApiState("success");
      setBodyState("success");
      setPacketState("success");
      setNoticeState("success");
      setOutcomeState("success");
      setMinutesState("success");
      setPublicState("success");
      setActiveMeetingId(demoMeetings[0].id);
      return;
    }
    let cancelled = false;
    loadWorkspaceData(() => cancelled)
      .catch((error: Error) => {
        if (cancelled) return;
        setBodyError(error.message);
        setApiError(error.message);
        setPacketError(error.message);
        setNoticeError(error.message);
        setOutcomeError(error.message);
        setMinutesError(error.message);
        setPublicError(error.message);
        setApiState("error");
        setBodyState("error");
        setPacketState("error");
        setNoticeState("error");
        setOutcomeState("error");
        setMinutesState("error");
        setPublicState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [initial.source]);

  useEffect(() => {
    if (initial.source === "demo" || qaState !== null || meetings.length === 0 || !activeMeetingId) {
      return;
    }
    if (!meetings.some((meeting) => meeting.id === activeMeetingId) || loadedPacketMeetingIds.includes(activeMeetingId)) {
      return;
    }
    let cancelled = false;
    setPacketState("loading");
    setPacketError(null);
    fetchPacketAssemblies(activeMeetingId)
      .then((apiPackets) => {
        if (cancelled) return;
        const mappedPackets = apiPackets.map(mapApiPacketAssemblyRecord);
        setPacketAssemblies((current) => [
          ...mappedPackets,
          ...current.filter((record) => record.meetingId !== activeMeetingId),
        ]);
        setLoadedPacketMeetingIds((current) => current.includes(activeMeetingId) ? current : [...current, activeMeetingId]);
        setPacketState("success");
      })
      .catch((error: Error) => {
        if (cancelled) return;
        setPacketError(error.message);
        setPacketState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [activeMeetingId, initial.source, loadedPacketMeetingIds, meetings, qaState]);

  useEffect(() => {
    if (initial.source === "demo" || qaState !== null || meetings.length === 0 || !activeMeetingId) {
      return;
    }
    if (!meetings.some((meeting) => meeting.id === activeMeetingId) || loadedNoticeMeetingIds.includes(activeMeetingId)) {
      return;
    }
    let cancelled = false;
    setNoticeState("loading");
    setNoticeError(null);
    fetchNoticeChecklists(activeMeetingId)
      .then((apiNotices) => {
        if (cancelled) return;
        const mappedNotices = sortNoticeChecklistRecords(apiNotices.map(mapApiNoticeChecklistRecord));
        setNoticeChecklists((current) => sortNoticeChecklistRecords([
          ...mappedNotices,
          ...current.filter((record) => record.meetingId !== activeMeetingId),
        ]));
        setLoadedNoticeMeetingIds((current) => current.includes(activeMeetingId) ? current : [...current, activeMeetingId]);
        setNoticeState("success");
      })
      .catch((error: Error) => {
        if (cancelled) return;
        setNoticeError(error.message);
        setNoticeState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [activeMeetingId, initial.source, loadedNoticeMeetingIds, meetings, qaState]);

  useEffect(() => {
    if (initial.source === "demo" || qaState !== null || meetings.length === 0 || !activeMeetingId) {
      return;
    }
    if (!meetings.some((meeting) => meeting.id === activeMeetingId) || loadedOutcomeMeetingIds.includes(activeMeetingId)) {
      return;
    }
    let cancelled = false;
    setOutcomeState("loading");
    setOutcomeError(null);
    fetchMeetingOutcomes(activeMeetingId)
      .then((outcomeBundle) => {
        if (cancelled) return;
        const mappedMotions = outcomeBundle.motions.map(mapApiMotionRecord);
        const mappedVotes = outcomeBundle.votes.map(mapApiVoteRecord);
        const mappedActionItems = outcomeBundle.actionItems.map(mapApiActionItemRecord);
        setMotions((current) => [
          ...mappedMotions,
          ...current.filter((record) => record.meetingId !== activeMeetingId),
        ]);
        setVotes((current) => [
          ...mappedVotes,
          ...current.filter((record) => !mappedMotions.some((motion) => motion.id === record.motionId)),
        ]);
        setActionItems((current) => [
          ...mappedActionItems,
          ...current.filter((record) => record.meetingId !== activeMeetingId),
        ]);
        setLoadedOutcomeMeetingIds((current) => current.includes(activeMeetingId) ? current : [...current, activeMeetingId]);
        setOutcomeState(mappedMotions.length === 0 && mappedActionItems.length === 0 ? "empty" : "success");
      })
      .catch((error: Error) => {
        if (cancelled) return;
        setOutcomeError(error.message);
        setOutcomeState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [activeMeetingId, initial.source, loadedOutcomeMeetingIds, meetings, qaState]);

  useEffect(() => {
    if (initial.source === "demo" || qaState !== null || meetings.length === 0 || !activeMeetingId) {
      return;
    }
    if (!meetings.some((meeting) => meeting.id === activeMeetingId) || loadedMinutesMeetingIds.includes(activeMeetingId)) {
      return;
    }
    let cancelled = false;
    setMinutesState("loading");
    setMinutesError(null);
    fetchMinutesDrafts(activeMeetingId)
      .then((apiDrafts) => {
        if (cancelled) return;
        const mappedDrafts = apiDrafts.map(mapApiMinutesDraftRecord);
        setMinutesDrafts((current) => [
          ...mappedDrafts,
          ...current.filter((record) => record.meetingId !== activeMeetingId),
        ]);
        setLoadedMinutesMeetingIds((current) => current.includes(activeMeetingId) ? current : [...current, activeMeetingId]);
        setMinutesState(mappedDrafts.length === 0 ? "empty" : "success");
      })
      .catch((error: Error) => {
        if (cancelled) return;
        setMinutesError(error.message);
        setMinutesState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [activeMeetingId, initial.source, loadedMinutesMeetingIds, meetings, qaState]);

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
          <button className={page === "meetings" || page === "meeting-detail" ? "active" : ""} onClick={() => setPage("meetings")}>
            <Icon label="Meetings" /> Meetings
          </button>
          <button className={page === "agenda" ? "active" : ""} onClick={() => setPage("agenda")}>
            <Icon label="Agenda" /> Agenda intake
          </button>
          <button className={page === "packet" ? "active" : ""} onClick={() => setPage("packet")}>
            <Icon label="Packet" /> Packet builder
          </button>
          <button className={page === "notice" ? "active" : ""} onClick={() => setPage("notice")}>
            <Icon label="Notice" /> Notice checklist
          </button>
          <button className={page === "outcomes" ? "active" : ""} onClick={() => setPage("outcomes")}>
            <Icon label="Outcomes" /> Outcomes
          </button>
          <button className={page === "public" ? "active" : ""} onClick={() => setPage("public")}>
            <Icon label="Public" /> Public posting
          </button>
          <button className={page === "minutes" ? "active" : ""} onClick={() => setPage("minutes")}>
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
          {page === "agenda" && (
            <AgendaIntakeWorkspace
              viewState={viewState}
              apiError={apiError}
              items={visibleAgendaItems}
              onSubmitItem={async (payload) => {
                const item = await submitAgendaIntakeItem(payload);
                setAgendaItems((current) => [mapApiAgendaIntakeItem(item), ...current]);
                setApiState("success");
              }}
              onReviewItem={async (itemId, payload) => {
                const item = await reviewAgendaIntakeItem(itemId, payload);
                setAgendaItems((current) => current.map((entry) => entry.id === item.id ? mapApiAgendaIntakeItem(item) : entry));
              }}
              onPromoteItem={async (itemId, payload) => {
                const result = await promoteAgendaIntakeItem(itemId, payload);
                setAgendaItems((current) => current.map((entry) => entry.id === result.intake_item.id ? mapApiAgendaIntakeItem(result.intake_item) : entry));
                return result;
              }}
            />
          )}
          {page === "packet" && (
            <PacketBuilderWorkspace
              viewState={qaState ?? packetState}
              apiError={packetError}
              meetings={visibleMeetings}
              activeMeeting={activeMeeting}
              agendaItems={visibleAgendaItems}
              packetAssemblies={visiblePacketAssemblies.filter((record) => record.meetingId === activeMeeting.id)}
              setActiveMeetingId={setActiveMeetingId}
              onCreatePacket={async (meetingId, payload) => {
                const record = await createPacketAssembly(meetingId, payload);
                const mapped = mapApiPacketAssemblyRecord(record);
                setPacketAssemblies((current) => [mapped, ...current.filter((item) => item.id !== mapped.id)]);
                setLoadedPacketMeetingIds((current) => current.includes(meetingId) ? current : [...current, meetingId]);
                setPacketState("success");
                return mapped;
              }}
              onFinalizePacket={async (recordId, actor) => {
                const record = await finalizePacketAssembly(recordId, actor);
                const mapped = mapApiPacketAssemblyRecord(record);
                setPacketAssemblies((current) => current.map((item) => item.id === mapped.id ? mapped : item));
                return mapped;
              }}
            />
          )}
          {page === "notice" && (
            <NoticeChecklistWorkspace
              viewState={qaState ?? noticeState}
              apiError={noticeError}
              meetings={visibleMeetings}
              activeMeeting={activeMeeting}
              noticeChecklists={visibleNoticeChecklists.filter((record) => record.meetingId === activeMeeting.id)}
              finalizedPackets={visiblePacketAssemblies.filter((record) => record.meetingId === activeMeeting.id && record.status === "FINALIZED")}
              setActiveMeetingId={setActiveMeetingId}
              onCreateNotice={async (meetingId, payload) => {
                const record = await createNoticeChecklist(meetingId, payload);
                const mapped = mapApiNoticeChecklistRecord(record);
                setNoticeChecklists((current) => sortNoticeChecklistRecords([mapped, ...current.filter((item) => item.id !== mapped.id)]));
                setLoadedNoticeMeetingIds((current) => current.includes(meetingId) ? current : [...current, meetingId]);
                setNoticeState("success");
                return mapped;
              }}
              onAttachProof={async (recordId, payload) => {
                const record = await attachNoticePostingProof(recordId, payload);
                const mapped = mapApiNoticeChecklistRecord(record);
                setNoticeChecklists((current) => sortNoticeChecklistRecords(current.map((item) => item.id === mapped.id ? mapped : item)));
                return mapped;
              }}
            />
          )}
          {page === "outcomes" && (
            <MeetingOutcomesWorkspace
              viewState={qaState ?? outcomeState}
              apiError={outcomeError}
              meetings={visibleMeetings}
              activeMeeting={activeMeeting}
              motions={visibleMotions.filter((record) => record.meetingId === activeMeeting.id)}
              votes={visibleVotes}
              actionItems={visibleActionItems.filter((record) => record.meetingId === activeMeeting.id)}
              setActiveMeetingId={setActiveMeetingId}
              onCaptureMotion={async (meetingId, payload) => {
                const record = await captureMotion(meetingId, payload);
                const mapped = mapApiMotionRecord(record);
                setMotions((current) => [mapped, ...current.filter((item) => item.id !== mapped.id)]);
                setLoadedOutcomeMeetingIds((current) => current.includes(meetingId) ? current : [...current, meetingId]);
                setOutcomeState("success");
                return mapped;
              }}
              onCaptureVote={async (motionId, payload) => {
                const record = await captureVote(motionId, payload);
                const mapped = mapApiVoteRecord(record);
                setVotes((current) => [...current.filter((item) => item.id !== mapped.id), mapped]);
                return mapped;
              }}
              onCreateActionItem={async (meetingId, payload) => {
                const record = await createActionItem(meetingId, payload);
                const mapped = mapApiActionItemRecord(record);
                setActionItems((current) => [mapped, ...current.filter((item) => item.id !== mapped.id)]);
                return mapped;
              }}
            />
          )}
          {page === "minutes" && (
            <MinutesDraftWorkspace
              viewState={qaState ?? minutesState}
              apiError={minutesError}
              meetings={visibleMeetings}
              activeMeeting={activeMeeting}
              drafts={(qaState === "empty" ? [] : visibleMinutesDrafts).filter((record) => record.meetingId === activeMeeting.id)}
              motions={visibleMotions.filter((record) => record.meetingId === activeMeeting.id)}
              votes={visibleVotes}
              setActiveMeetingId={setActiveMeetingId}
              onCreateDraft={async (meetingId, payload) => {
                const record = await createMinutesDraft(meetingId, payload);
                const mapped = mapApiMinutesDraftRecord(record);
                setMinutesDrafts((current) => [mapped, ...current.filter((item) => item.id !== mapped.id)]);
                setLoadedMinutesMeetingIds((current) => current.includes(meetingId) ? current : [...current, meetingId]);
                setMinutesState("success");
                return mapped;
              }}
              onPostDraft={async (draftId) => rejectAutomaticMinutesPosting(draftId)}
            />
          )}
          {page === "public" && (
            <PublicPostedMeetingWorkspace
              viewState={qaState ?? publicState}
              apiError={publicError}
              records={visiblePublicRecords}
              selectedRecord={visiblePublicDetail}
              onSelectRecord={async (recordId) => {
                if (initial.source === "demo" || qaState !== null) {
                  setPublicRecordDetail(demoPublicRecords.find((record) => record.id === recordId) ?? demoPublicRecords[0]);
                  return;
                }
                const detail = mapApiPublicMeetingRecord(await fetchPublicMeetingDetail(recordId));
                setPublicRecordDetail(detail);
              }}
              onSearch={async (query) => {
                if (initial.source === "demo" || qaState !== null) {
                  const normalized = query.toLowerCase().trim();
                  return demoPublicRecords.filter((record) =>
                    `${record.title} ${record.postedAgenda} ${record.postedPacket} ${record.approvedMinutes}`.toLowerCase().includes(normalized),
                  );
                }
                return (await searchPublicArchive(query)).map(mapApiPublicMeetingRecord);
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

async function fetchAgendaIntakeItems(): Promise<ApiAgendaIntakeItem[]> {
  const response = await fetch("/api/agenda-intake", {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Agenda intake API returned ${response.status}.`);
  }
  const payload = (await response.json()) as { items?: ApiAgendaIntakeItem[] };
  return Array.isArray(payload.items) ? payload.items : [];
}

async function fetchPacketAssemblies(meetingId: string): Promise<ApiPacketAssemblyRecord[]> {
  const response = await fetch(`/api/meetings/${meetingId}/packet-assemblies`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Packet assembly API returned ${response.status}.`);
  }
  const payload = (await response.json()) as { packet_assemblies?: ApiPacketAssemblyRecord[] };
  return Array.isArray(payload.packet_assemblies) ? payload.packet_assemblies : [];
}

async function fetchNoticeChecklists(meetingId: string): Promise<ApiNoticeChecklistRecord[]> {
  const response = await fetch(`/api/meetings/${meetingId}/notice-checklists`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Notice checklist API returned ${response.status}.`);
  }
  const payload = (await response.json()) as { notice_checklists?: ApiNoticeChecklistRecord[] };
  return Array.isArray(payload.notice_checklists) ? payload.notice_checklists : [];
}

async function fetchMeetingOutcomes(meetingId: string): Promise<{ motions: ApiMotionRecord[]; votes: ApiVoteRecord[]; actionItems: ApiActionItemRecord[] }> {
  const motionResponse = await fetch(`/api/meetings/${meetingId}/motions`, {
    headers: { Accept: "application/json" },
  });
  if (!motionResponse.ok) {
    throw new Error(`Meeting outcomes API returned ${motionResponse.status}.`);
  }
  const motionPayload = (await motionResponse.json()) as { motions?: ApiMotionRecord[] };
  const motions = Array.isArray(motionPayload.motions) ? motionPayload.motions : [];
  const [voteGroups, actionResponse] = await Promise.all([
    Promise.all(motions.map((motion) => fetchVotes(motion.id))),
    fetch(`/api/meetings/${meetingId}/action-items`, { headers: { Accept: "application/json" } }),
  ]);
  if (!actionResponse.ok) {
    throw new Error(`Action item API returned ${actionResponse.status}.`);
  }
  const actionPayload = (await actionResponse.json()) as { action_items?: ApiActionItemRecord[] };
  return {
    motions,
    votes: voteGroups.flat(),
    actionItems: Array.isArray(actionPayload.action_items) ? actionPayload.action_items : [],
  };
}

async function fetchVotes(motionId: string): Promise<ApiVoteRecord[]> {
  const response = await fetch(`/api/motions/${motionId}/votes`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Vote API returned ${response.status}.`);
  }
  const payload = (await response.json()) as { votes?: ApiVoteRecord[] };
  return Array.isArray(payload.votes) ? payload.votes : [];
}

async function fetchMinutesDrafts(meetingId: string): Promise<ApiMinutesDraftRecord[]> {
  const response = await fetch(`/api/meetings/${meetingId}/minutes/drafts`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Minutes draft API returned ${response.status}.`);
  }
  const payload = (await response.json()) as { drafts?: ApiMinutesDraftRecord[] };
  return Array.isArray(payload.drafts) ? payload.drafts : [];
}

async function fetchPublicMeetings(): Promise<ApiPublicMeetingRecord[]> {
  const response = await fetch("/api/public/meetings", {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Public meetings API returned ${response.status}.`);
  }
  const payload = (await response.json()) as { meetings?: ApiPublicMeetingRecord[] };
  return Array.isArray(payload.meetings) ? payload.meetings : [];
}

async function fetchPublicMeetingDetail(recordId: string): Promise<ApiPublicMeetingRecord> {
  const response = await fetch(`/api/public/meetings/${recordId}`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await formatApiError(response, "Public meeting detail"));
  }
  return response.json();
}

async function searchPublicArchive(query: string): Promise<ApiPublicMeetingRecord[]> {
  const response = await fetch(`/api/public/archive/search?q=${encodeURIComponent(query)}`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await formatApiError(response, "Public archive search"));
  }
  const payload = (await response.json()) as { results?: ApiPublicMeetingRecord[] };
  return Array.isArray(payload.results) ? payload.results : [];
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

async function submitAgendaIntakeItem(payload: AgendaIntakePayload): Promise<ApiAgendaIntakeItem> {
  const response = await fetch("/api/agenda-intake", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Agenda intake submit returned ${response.status}.`);
  }
  return response.json();
}

async function reviewAgendaIntakeItem(itemId: string, payload: AgendaReviewPayload): Promise<ApiAgendaIntakeItem> {
  const response = await fetch(`/api/agenda-intake/${itemId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Agenda intake review returned ${response.status}.`);
  }
  return response.json();
}

async function promoteAgendaIntakeItem(itemId: string, payload: AgendaPromotionPayload): Promise<AgendaPromotionResult> {
  const response = await fetch(`/api/agenda-intake/${itemId}/promote`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Agenda promotion returned ${response.status}.`);
  }
  return response.json();
}

async function createPacketAssembly(meetingId: string, payload: PacketAssemblyPayload): Promise<ApiPacketAssemblyRecord> {
  const response = await fetch(`/api/meetings/${meetingId}/packet-assemblies`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Packet assembly create returned ${response.status}.`);
  }
  return response.json();
}

async function finalizePacketAssembly(recordId: string, actor: string): Promise<ApiPacketAssemblyRecord> {
  const response = await fetch(`/api/packet-assemblies/${recordId}/finalize`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ actor }),
  });
  if (!response.ok) {
    throw new Error(`Packet assembly finalize returned ${response.status}.`);
  }
  return response.json();
}

async function createNoticeChecklist(meetingId: string, payload: NoticeChecklistPayload): Promise<ApiNoticeChecklistRecord> {
  const response = await fetch(`/api/meetings/${meetingId}/notice-checklists`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await formatApiError(response, "Notice checklist create"));
  }
  return response.json();
}

async function attachNoticePostingProof(recordId: string, payload: NoticePostingProofPayload): Promise<ApiNoticeChecklistRecord> {
  const response = await fetch(`/api/notice-checklists/${recordId}/posting-proof`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await formatApiError(response, "Posting proof"));
  }
  return response.json();
}

async function captureMotion(meetingId: string, payload: MotionPayload): Promise<ApiMotionRecord> {
  const response = await fetch(`/api/meetings/${meetingId}/motions`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await formatApiError(response, "Motion capture"));
  }
  return response.json();
}

async function captureVote(motionId: string, payload: VotePayload): Promise<ApiVoteRecord> {
  const response = await fetch(`/api/motions/${motionId}/votes`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await formatApiError(response, "Vote capture"));
  }
  return response.json();
}

async function createActionItem(meetingId: string, payload: ActionItemPayload): Promise<ApiActionItemRecord> {
  const response = await fetch(`/api/meetings/${meetingId}/action-items`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await formatApiError(response, "Action item create"));
  }
  return response.json();
}

async function createMinutesDraft(meetingId: string, payload: MinutesDraftPayload): Promise<ApiMinutesDraftRecord> {
  const response = await fetch(`/api/meetings/${meetingId}/minutes/drafts`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(await formatApiError(response, "Minutes draft create"));
  }
  return response.json();
}

async function rejectAutomaticMinutesPosting(draftId: string): Promise<void> {
  const response = await fetch(`/api/minutes/${draftId}/post`, {
    method: "POST",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(await formatApiError(response, "Minutes public posting"));
  }
}

async function formatApiError(response: Response, context: string): Promise<string> {
  try {
    const payload = await response.json();
    const detail = payload.detail;
    if (typeof detail === "string") {
      return `${context} returned ${response.status}: ${detail}`;
    }
    if (detail && typeof detail === "object") {
      const message = typeof detail.message === "string" ? detail.message : `${context} returned ${response.status}.`;
      const fix = typeof detail.fix === "string" ? ` ${detail.fix}` : "";
      return `${message}${fix}`;
    }
  } catch {
    // Fall through to the generic status message when the backend body is not JSON.
  }
  return `${context} returned ${response.status}.`;
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

function mapApiAgendaIntakeItem(item: ApiAgendaIntakeItem): AgendaIntakeItem {
  return {
    id: item.id,
    title: item.title,
    departmentName: item.department_name,
    submittedBy: item.submitted_by,
    summary: item.summary,
    readinessStatus: item.readiness_status,
    status: item.status,
    sourceReferences: item.source_references,
    reviewer: item.reviewer,
    reviewNotes: item.review_notes,
    promotedAgendaItemId: item.promoted_agenda_item_id,
    promotedAt: item.promoted_at,
    promotionAuditHash: item.promotion_audit_hash,
    lastAuditHash: item.last_audit_hash,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  };
}

function mapApiPacketAssemblyRecord(record: ApiPacketAssemblyRecord): PacketAssemblyRecord {
  const auditHash = record.audit_hash ?? record.last_audit_hash ?? "audit-hash-pending";
  return {
    id: record.id,
    meetingId: record.meeting_id,
    title: record.title,
    status: record.status,
    packetVersion: record.packet_version,
    agendaItemIds: record.agenda_item_ids,
    auditHash,
    finalizedAt: record.finalized_at,
  };
}

function mapApiNoticeChecklistRecord(record: ApiNoticeChecklistRecord): NoticeChecklistRecord {
  return {
    id: record.id,
    meetingId: record.meeting_id,
    noticeType: record.notice_type,
    status: record.status,
    compliant: record.compliant,
    httpStatus: record.http_status,
    warnings: record.warnings,
    deadlineAt: record.deadline_at,
    postedAt: record.posted_at,
    minimumNoticeHours: record.minimum_notice_hours,
    statutoryBasis: record.statutory_basis,
    approvedBy: record.approved_by,
    postingProof: record.posting_proof,
    lastAuditHash: record.last_audit_hash,
    createdAt: record.created_at,
    updatedAt: record.updated_at,
  };
}

function mapApiMotionRecord(record: ApiMotionRecord): MotionRecord {
  return {
    id: record.id,
    meetingId: record.meeting_id,
    agendaItemId: record.agenda_item_id,
    text: record.text,
    actor: record.actor,
    correctionOfId: record.correction_of_id,
    correctionReason: record.correction_reason,
    captured: record.captured,
  };
}

function mapApiVoteRecord(record: ApiVoteRecord): VoteRecord {
  return {
    id: record.id,
    motionId: record.motion_id,
    voterName: record.voter_name,
    vote: record.vote,
    actor: record.actor,
    correctionOfId: record.correction_of_id,
    correctionReason: record.correction_reason,
    captured: record.captured,
  };
}

function mapApiActionItemRecord(record: ApiActionItemRecord): ActionItemRecord {
  return {
    id: record.id,
    meetingId: record.meeting_id,
    description: record.description,
    actor: record.actor,
    assignedTo: record.assigned_to,
    sourceMotionId: record.source_motion_id,
    status: record.status,
  };
}

function mapApiMinutesDraftRecord(record: ApiMinutesDraftRecord): MinutesDraftRecord {
  return {
    id: record.id,
    meetingId: record.meeting_id,
    status: record.status,
    adopted: record.adopted,
    posted: record.posted,
    sourceMaterials: record.source_materials.map((source) => ({
      sourceId: source.source_id,
      label: source.label,
      text: source.text,
    })),
    sentences: record.sentences.map((sentence) => ({
      text: sentence.text,
      citations: sentence.citations,
    })),
    provenance: {
      model: record.provenance.model,
      promptVersion: record.provenance.prompt_version,
      dataSources: record.provenance.data_sources,
      humanApprover: record.provenance.human_approver,
    },
  };
}

function mapApiPublicMeetingRecord(record: ApiPublicMeetingRecord): PublicMeetingRecord {
  return {
    id: record.id,
    meetingId: record.meeting_id,
    title: record.title,
    postedAgenda: record.posted_agenda,
    postedPacket: record.posted_packet,
    approvedMinutes: record.approved_minutes,
  };
}

function sortNoticeChecklistRecords(records: NoticeChecklistRecord[]): NoticeChecklistRecord[] {
  return [...records].sort((left, right) => {
    const rightTime = new Date(right.updatedAt || right.createdAt).getTime();
    const leftTime = new Date(left.updatedAt || left.createdAt).getTime();
    return (Number.isNaN(rightTime) ? 0 : rightTime) - (Number.isNaN(leftTime) ? 0 : leftTime);
  });
}

function sortBodies(a: MeetingBody, b: MeetingBody) {
  return a.name.localeCompare(b.name);
}

function sortMeetings(a: Meeting, b: Meeting) {
  const left = a.scheduledStart ? new Date(a.scheduledStart).getTime() : Number.MAX_SAFE_INTEGER;
  const right = b.scheduledStart ? new Date(b.scheduledStart).getTime() : Number.MAX_SAFE_INTEGER;
  return left - right || a.title.localeCompare(b.title);
}

function parseCitationList(value: string): string[] {
  return value
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
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
  const pages: Page[] = ["dashboard", "meetings", "meeting-detail", "agenda", "packet", "notice", "outcomes", "minutes", "public"];
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

function AgendaIntakeWorkspace({
  viewState,
  apiError,
  items,
  onSubmitItem,
  onReviewItem,
  onPromoteItem,
}: {
  viewState: ViewState;
  apiError: string | null;
  items: AgendaIntakeItem[];
  onSubmitItem: (payload: AgendaIntakePayload) => Promise<void>;
  onReviewItem: (itemId: string, payload: AgendaReviewPayload) => Promise<void>;
  onPromoteItem: (itemId: string, payload: AgendaPromotionPayload) => Promise<AgendaPromotionResult>;
}) {
  const [title, setTitle] = useState("Approve downtown zoning study");
  const [departmentName, setDepartmentName] = useState("Planning");
  const [submittedBy, setSubmittedBy] = useState("planning@example.gov");
  const [summary, setSummary] = useState("Authorize the downtown zoning study scope, consultant agreement, and public engagement calendar.");
  const [sourceTitle, setSourceTitle] = useState("Planning staff report");
  const [reviewer, setReviewer] = useState("clerk@example.gov");
  const [reviewNotes, setReviewNotes] = useState("Complete for packet assembly.");
  const [message, setMessage] = useState<string | null>(null);
  const [promotionMessages, setPromotionMessages] = useState<Record<string, string>>({});
  const pendingCount = items.filter((item) => item.readinessStatus === "PENDING").length;
  const readyCount = items.filter((item) => item.readinessStatus === "READY").length;
  const revisionCount = items.filter((item) => item.readinessStatus === "NEEDS_REVISION").length;

  if (viewState !== "success") {
    return <StateMessage state={viewState} context="agenda intake" apiError={apiError} />;
  }

  async function submitItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      await onSubmitItem({
        title: title.trim(),
        department_name: departmentName.trim(),
        submitted_by: submittedBy.trim(),
        summary: summary.trim(),
        source_references: [
          {
            source_id: sourceTitle.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "source",
            title: sourceTitle.trim(),
            kind: "document",
          },
        ],
      });
    } catch (error) {
      setMessage(`${error instanceof Error ? error.message : "Agenda intake submit failed."} Check the API/auth mode, confirm every field has content, then retry.`);
      return;
    }
    setMessage("Agenda item submitted. It is now in the clerk review queue with audit provenance.");
  }

  async function reviewItem(itemId: string, ready: boolean) {
    setMessage(null);
    try {
      await onReviewItem(itemId, {
        reviewer: reviewer.trim(),
        ready,
        notes: reviewNotes.trim(),
      });
    } catch (error) {
      setMessage(`${error instanceof Error ? error.message : "Agenda intake review failed."} Reload the queue, confirm the item still exists, then retry.`);
      return;
    }
    setMessage(ready ? "Marked ready for clerk packet work. The audit hash changed for this review." : "Sent back for revision with clerk notes and audit evidence.");
  }

  async function promoteItem(item: AgendaIntakeItem) {
    setMessage(null);
    if (item.readinessStatus !== "READY") {
      setPromotionMessages((current) => ({
        ...current,
        [item.id]: "This item must be marked ready before promotion. Use Mark ready, confirm the audit hash changes, then promote it.",
      }));
      return;
    }
    try {
      const result = await onPromoteItem(item.id, {
        reviewer: reviewer.trim(),
        notes: reviewNotes.trim(),
      });
      const agendaId = result.agenda_item?.id ?? result.intake_item.promoted_agenda_item_id ?? "created agenda item";
      const status = result.agenda_item?.status ?? "agenda lifecycle";
      setPromotionMessages((current) => ({
        ...current,
        [item.id]: `${result.message} Agenda item ${agendaId} is now ${status}. Next step: ${result.next_step}`,
      }));
    } catch (error) {
      setPromotionMessages((current) => ({
        ...current,
        [item.id]: `${error instanceof Error ? error.message : "Agenda promotion failed."} Mark the item ready, confirm the API is running, then retry promotion.`,
      }));
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Agenda intake"
        title="Department requests, clerk decisions."
        description="Submit agenda items, review completeness, and move ready work toward packet assembly without leaving the staff app."
      />
      <div className="metric-grid">
        <MetricCard label="Pending review" value={String(pendingCount)} note="Needs clerk completeness check" tone={pendingCount ? "warn" : undefined} />
        <MetricCard label="Ready for packet" value={String(readyCount)} note="Can move into packet assembly" />
        <MetricCard label="Needs revision" value={String(revisionCount)} note="Waiting on department fixes" tone={revisionCount ? "warn" : undefined} />
      </div>
      <div className="agenda-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Department submission</h2>
              <p>Capture the request, submitter, summary, and source material in one clerk-visible record.</p>
            </div>
            <StatusBadge tone="Ready" label="Live API" />
          </div>
          <form className="intake-form" onSubmit={submitItem}>
            <label>
              Agenda title
              <input value={title} onChange={(event) => setTitle(event.target.value)} required />
            </label>
            <label>
              Department
              <input value={departmentName} onChange={(event) => setDepartmentName(event.target.value)} required />
            </label>
            <label>
              Submitted by
              <input type="email" value={submittedBy} onChange={(event) => setSubmittedBy(event.target.value)} required />
            </label>
            <label>
              Source title
              <input value={sourceTitle} onChange={(event) => setSourceTitle(event.target.value)} required />
            </label>
            <label className="wide">
              Summary
              <textarea value={summary} onChange={(event) => setSummary(event.target.value)} required />
            </label>
            <button type="submit">Submit to review queue</button>
          </form>
          {message && <p className="form-message">{message}</p>}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Clerk review queue</h2>
              <p>Use notes that tell the department exactly what is ready or what must be fixed.</p>
            </div>
            <StatusBadge tone={pendingCount ? "Warning" : "Ready"} label={`${items.length} items`} />
          </div>
          <div className="review-controls">
            <label>
              Reviewer
              <input value={reviewer} onChange={(event) => setReviewer(event.target.value)} required />
            </label>
            <label>
              Review notes
              <input value={reviewNotes} onChange={(event) => setReviewNotes(event.target.value)} required />
            </label>
          </div>
          <div className="agenda-list">
            {items.length === 0 && (
              <p className="empty-inline">No agenda intake items yet. Submit a department item on the left, then review it here.</p>
            )}
            {items.map((item) => (
              <article key={item.id} className="agenda-row">
                {(() => {
                  const isPromoted = Boolean(item.promotedAgendaItemId);
                  const cannotPromote = item.readinessStatus !== "READY" || isPromoted;
                  const promotionLabel = item.promotedAgendaItemId
                    ? "Promoted"
                    : item.readinessStatus === "READY"
                      ? "Promote to agenda"
                      : "Review first";
                  return (
                    <>
                <div>
                  <div className="row-title">
                    <h3>{item.title}</h3>
                    <StatusBadge tone={isPromoted ? "Ready" : statusTone(item.readinessStatus)} label={isPromoted ? "Promoted" : readinessLabel(item.readinessStatus)} />
                  </div>
                  <p>{item.departmentName} - {item.submittedBy}</p>
                  <p>{item.summary}</p>
                  <small>Audit hash: {item.lastAuditHash.slice(0, 12)}... Source: {item.sourceReferences[0]?.title ?? "No source title"}</small>
                  {item.reviewNotes && <small>Last review: {item.reviewNotes}</small>}
                  {item.promotedAgendaItemId && (
                    <small>Agenda lifecycle: {item.promotedAgendaItemId} promoted {item.promotedAt ? new Date(item.promotedAt).toLocaleString() : "today"}</small>
                  )}
                  {promotionMessages[item.id] && <p className="handoff-message">{promotionMessages[item.id]}</p>}
                </div>
                <div className="row-actions">
                  <button
                    className="secondary"
                    type="button"
                    onClick={() => reviewItem(item.id, true)}
                    disabled={isPromoted}
                    title={isPromoted ? "This item is already promoted. Continue in Packet Builder." : undefined}
                  >
                    {isPromoted ? "Ready locked" : "Mark ready"}
                  </button>
                  <button
                    className="secondary ghost"
                    type="button"
                    onClick={() => reviewItem(item.id, false)}
                    disabled={isPromoted}
                    title={isPromoted ? "This item is already promoted. Continue in Packet Builder." : undefined}
                  >
                    Needs revision
                  </button>
                  <button
                    className="secondary"
                    type="button"
                    onClick={() => promoteItem(item)}
                    disabled={cannotPromote}
                    title={isPromoted ? "This item is already in agenda lifecycle work." : item.readinessStatus !== "READY" ? "Mark this item ready before promotion." : undefined}
                  >
                    {promotionLabel}
                  </button>
                </div>
                    </>
                  );
                })()}
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function PacketBuilderWorkspace({
  viewState,
  apiError,
  meetings,
  activeMeeting,
  agendaItems,
  packetAssemblies,
  setActiveMeetingId,
  onCreatePacket,
  onFinalizePacket,
}: {
  viewState: ViewState;
  apiError: string | null;
  meetings: Meeting[];
  activeMeeting: Meeting;
  agendaItems: AgendaIntakeItem[];
  packetAssemblies: PacketAssemblyRecord[];
  setActiveMeetingId: (id: string) => void;
  onCreatePacket: (meetingId: string, payload: PacketAssemblyPayload) => Promise<PacketAssemblyRecord>;
  onFinalizePacket: (recordId: string, actor: string) => Promise<PacketAssemblyRecord>;
}) {
  const promotedItems = agendaItems.filter((item) => item.promotedAgendaItemId);
  const [packetTitle, setPacketTitle] = useState("Council packet draft");
  const [actor, setActor] = useState("clerk@example.gov");
  const [selectedIds, setSelectedIds] = useState<string[]>(promotedItems[0]?.promotedAgendaItemId ? [promotedItems[0].promotedAgendaItemId] : []);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (selectedIds.length === 0 && promotedItems[0]?.promotedAgendaItemId) {
      setSelectedIds([promotedItems[0].promotedAgendaItemId]);
    }
  }, [promotedItems, selectedIds.length]);

  if (viewState !== "success") {
    return <StateMessage state={viewState} context="packet builder" apiError={apiError} />;
  }

  function toggleAgendaItem(agendaItemId: string) {
    setSelectedIds((current) => current.includes(agendaItemId)
      ? current.filter((item) => item !== agendaItemId)
      : [...current, agendaItemId]);
  }

  async function createDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    if (selectedIds.length === 0) {
      setMessage("Choose at least one promoted agenda item before creating a packet draft. Promote an intake item first if this list is empty.");
      return;
    }
    const selectedItems = promotedItems.filter((item) => item.promotedAgendaItemId && selectedIds.includes(item.promotedAgendaItemId));
    try {
      const record = await onCreatePacket(activeMeeting.id, {
        title: packetTitle.trim(),
        agenda_item_ids: selectedIds,
        actor: actor.trim(),
        source_references: selectedItems.flatMap((item) => item.sourceReferences),
        citations: selectedItems.map((item) => ({
          agenda_item_id: item.promotedAgendaItemId ?? "",
          citation: item.sourceReferences[0]?.title ?? item.title,
        })),
      });
      setMessage(`Packet draft ${record.id} created at version ${record.packetVersion}. Review source evidence, then finalize when ready to post.`);
    } catch (error) {
      setMessage(`${error instanceof Error ? error.message : "Packet assembly create failed."} Confirm the meeting exists, choose promoted agenda items, then retry.`);
    }
  }

  async function finalizeDraft(record: PacketAssemblyRecord) {
    setMessage(null);
    try {
      const finalized = await onFinalizePacket(record.id, actor.trim());
      setMessage(`Packet ${finalized.id} finalized with audit hash ${finalized.auditHash.slice(0, 12)}. Next step: run notice checklist before public posting.`);
    } catch (error) {
      setMessage(`${error instanceof Error ? error.message : "Packet finalization failed."} Create a packet draft first, confirm it still exists, then retry.`);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Packet builder"
        title="Assemble packet evidence before posting."
        description="Choose a meeting, pull in promoted agenda items, create the packet draft, and finalize it with audit evidence."
      />
      <div className="metric-grid">
        <MetricCard label="Promoted agenda items" value={String(promotedItems.length)} note="Ready to add to packet drafts" />
        <MetricCard label="Packet drafts" value={String(packetAssemblies.filter((record) => record.status === "DRAFT").length)} note="Need final review" />
        <MetricCard label="Finalized packets" value={String(packetAssemblies.filter((record) => record.status === "FINALIZED").length)} note="Ready for notice checklist" />
      </div>
      <div className="agenda-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Create packet draft</h2>
              <p>Attach promoted agenda items and source citations to the meeting packet.</p>
            </div>
            <StatusBadge tone={promotedItems.length ? "Ready" : "Blocked"} label={promotedItems.length ? "Ready" : "Needs promoted item"} />
          </div>
          <form className="intake-form" onSubmit={createDraft}>
            <label>
              Meeting
              <select value={activeMeeting.id} onChange={(event) => setActiveMeetingId(event.target.value)} required>
                {meetings.map((meeting) => (
                  <option key={meeting.id} value={meeting.id}>{meeting.body} - {meeting.title}</option>
                ))}
              </select>
            </label>
            <label>
              Packet title
              <input value={packetTitle} onChange={(event) => setPacketTitle(event.target.value)} required />
            </label>
            <label>
              Actor
              <input value={actor} onChange={(event) => setActor(event.target.value)} required />
            </label>
            <fieldset className="wide checklist-fieldset">
              <legend>Promoted agenda items</legend>
              {promotedItems.length === 0 && (
                <p className="empty-inline">No promoted agenda items yet. Open Agenda Intake, mark an item ready, then promote it into agenda lifecycle work.</p>
              )}
              {promotedItems.map((item) => (
                <label key={item.id} className="checkbox-row">
                  <input
                    type="checkbox"
                    checked={Boolean(item.promotedAgendaItemId && selectedIds.includes(item.promotedAgendaItemId))}
                    onChange={() => item.promotedAgendaItemId && toggleAgendaItem(item.promotedAgendaItemId)}
                  />
                  <span>{item.title} - {item.departmentName}</span>
                </label>
              ))}
            </fieldset>
            <button type="submit">Create packet draft</button>
          </form>
          {message && <p className="form-message">{message}</p>}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Packet assembly queue</h2>
              <p>Finalize drafts only after source evidence and citations are attached.</p>
            </div>
            <StatusBadge tone={packetAssemblies.length ? "Ready" : "Warning"} label={`${packetAssemblies.length} packets`} />
          </div>
          <div className="agenda-list">
            {packetAssemblies.length === 0 && (
              <p className="empty-inline">No packet drafts exist for this meeting yet. Choose promoted agenda items and create the first draft.</p>
            )}
            {packetAssemblies.map((record) => (
              <article key={record.id} className="agenda-row">
                <div>
                  <div className="row-title">
                    <h3>{record.title}</h3>
                    <StatusBadge tone={record.status === "FINALIZED" ? "Ready" : "Warning"} label={record.status === "FINALIZED" ? "Finalized" : "Draft"} />
                  </div>
                  <p>Version {record.packetVersion} - {record.agendaItemIds.length} agenda item(s)</p>
                  <small>Audit hash: {record.auditHash.slice(0, 12)}...</small>
                  {record.finalizedAt && <small>Finalized: {new Date(record.finalizedAt).toLocaleString()}</small>}
                </div>
                <div className="row-actions">
                  <button
                    className="secondary"
                    type="button"
                    disabled={record.status === "FINALIZED"}
                    onClick={() => finalizeDraft(record)}
                  >
                    {record.status === "FINALIZED" ? "Finalized" : "Finalize packet"}
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function NoticeChecklistWorkspace({
  viewState,
  apiError,
  meetings,
  activeMeeting,
  noticeChecklists,
  finalizedPackets,
  setActiveMeetingId,
  onCreateNotice,
  onAttachProof,
}: {
  viewState: ViewState;
  apiError: string | null;
  meetings: Meeting[];
  activeMeeting: Meeting;
  noticeChecklists: NoticeChecklistRecord[];
  finalizedPackets: PacketAssemblyRecord[];
  setActiveMeetingId: (id: string) => void;
  onCreateNotice: (meetingId: string, payload: NoticeChecklistPayload) => Promise<NoticeChecklistRecord>;
  onAttachProof: (recordId: string, payload: NoticePostingProofPayload) => Promise<NoticeChecklistRecord>;
}) {
  const [noticeType, setNoticeType] = useState(activeMeeting.meetingType === "special" ? "special" : "regular");
  const [postedAt, setPostedAt] = useState(suggestedNoticePostedAt(activeMeeting.scheduledStart, activeMeeting.meetingType === "special" ? 24 : 72));
  const [minimumNoticeHours, setMinimumNoticeHours] = useState(activeMeeting.meetingType === "special" ? "24" : "72");
  const [statutoryBasis, setStatutoryBasis] = useState("Local open meeting law requires posted public notice before the meeting.");
  const [approvedBy, setApprovedBy] = useState("clerk@example.gov");
  const [actor, setActor] = useState("clerk@example.gov");
  const [proofUrl, setProofUrl] = useState("https://city.example.gov/agendas/meeting-notice");
  const [proofLocation, setProofLocation] = useState("City Hall notice board");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setNoticeType(activeMeeting.meetingType === "special" ? "special" : "regular");
    setMinimumNoticeHours(activeMeeting.meetingType === "special" ? "24" : "72");
    setPostedAt(suggestedNoticePostedAt(activeMeeting.scheduledStart, activeMeeting.meetingType === "special" ? 24 : 72));
    setMessage(null);
  }, [activeMeeting]);

  if (viewState !== "success") {
    return <StateMessage state={viewState} context="notice checklist" apiError={apiError} />;
  }

  const latestRecord = noticeChecklists[0];
  const compliantCount = noticeChecklists.filter((record) => record.compliant).length;
  const postedCount = noticeChecklists.filter((record) => record.status === "POSTED").length;
  const hasFinalizedPacket = finalizedPackets.length > 0;
  const noticeDeadline = activeMeeting.scheduledStart
    ? new Date(new Date(activeMeeting.scheduledStart).getTime() - Number(minimumNoticeHours || "0") * 60 * 60 * 1000)
    : null;

  async function submitNoticeCheck(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      const record = await onCreateNotice(activeMeeting.id, {
        notice_type: noticeType.trim(),
        posted_at: new Date(postedAt).toISOString(),
        minimum_notice_hours: Number(minimumNoticeHours),
        statutory_basis: statutoryBasis.trim(),
        approved_by: approvedBy.trim(),
        actor: actor.trim(),
      });
      if (record.compliant) {
        setMessage(`Notice checklist ${record.id} passed. Deadline: ${formatDateTime(record.deadlineAt)}. Audit hash ${record.lastAuditHash.slice(0, 12)}. Attach posting proof before treating notice as posted.`);
      } else {
        setMessage(`Notice checklist ${record.id} is blocked. The statutory deadline was ${formatDateTime(record.deadlineAt)}, but posting was recorded at ${formatDateTime(record.postedAt)}. Fix: ${noticeWarningText(record)}`);
      }
    } catch (error) {
      setMessage(`${error instanceof Error ? error.message : "Notice checklist failed."} If the statutory deadline has passed, reschedule the meeting or document a lawful emergency/special-meeting basis before posting proof.`);
    }
  }

  async function attachProof(record: NoticeChecklistRecord) {
    setMessage(null);
    if (!record.compliant) {
      setMessage(`Posting proof is blocked because this notice did not meet the statutory checklist. Deadline: ${formatDateTime(record.deadlineAt)}. Fix: ${noticeWarningText(record)}`);
      return;
    }
    try {
      const posted = await onAttachProof(record.id, {
        actor: actor.trim(),
        posting_proof: {
          posted_url: proofUrl.trim(),
          location: proofLocation.trim(),
        },
      });
      setMessage(`Posting proof attached for ${posted.id}. Status is ${posted.status}; immutable audit hash ${posted.lastAuditHash.slice(0, 12)} proves who attached proof and where it was posted.`);
    } catch (error) {
      setMessage(`${error instanceof Error ? error.message : "Posting proof failed."} Confirm the checklist exists, passed compliance, and proof URL/location are available, then retry.`);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Notice checklist"
        title="Prove statutory public notice before the meeting proceeds."
        description="Check the deadline, statutory basis, human approval, posting time, proof location, and audit hash before the city treats a meeting as lawfully noticed."
      />
      <div className="metric-grid">
        <MetricCard label="Finalized packets" value={String(finalizedPackets.length)} note={hasFinalizedPacket ? "Ready for notice review" : "Finalize packet before posting"} tone={hasFinalizedPacket ? undefined : "warn"} />
        <MetricCard label="Passing checks" value={String(compliantCount)} note="Deadline, basis, and approval met" />
        <MetricCard label="Posted proof" value={String(postedCount)} note="Immutable proof attached" tone={postedCount ? undefined : "warn"} />
      </div>
      <div className="notice-legal-callout">
        <strong>Legal gate</strong>
        <span>
          The checklist is the city record that proves public notice. If deadline, statutory basis, or approval fails, do not attach posting proof; reschedule or document the lawful exception first.
        </span>
      </div>
      <div className="agenda-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Run statutory check</h2>
              <p>Record exactly when notice was posted and why this meeting can legally proceed.</p>
            </div>
            <StatusBadge tone={hasFinalizedPacket ? "Ready" : "Warning"} label={hasFinalizedPacket ? "Packet finalized" : "Packet first"} />
          </div>
          <form className="intake-form" onSubmit={submitNoticeCheck}>
            <label>
              Meeting
              <select value={activeMeeting.id} onChange={(event) => setActiveMeetingId(event.target.value)} required>
                {meetings.map((meeting) => (
                  <option key={meeting.id} value={meeting.id}>{meeting.body} - {meeting.title}</option>
                ))}
              </select>
            </label>
            <label>
              Notice type
              <select value={noticeType} onChange={(event) => setNoticeType(event.target.value)} required>
                <option value="regular">regular</option>
                <option value="special">special</option>
                <option value="emergency">emergency</option>
              </select>
            </label>
            <label>
              Minimum notice hours
              <input value={minimumNoticeHours} onChange={(event) => setMinimumNoticeHours(event.target.value)} inputMode="numeric" required />
            </label>
            <label>
              Posted at
              <input type="datetime-local" value={postedAt} onChange={(event) => setPostedAt(event.target.value)} required />
            </label>
            <label>
              Approved by
              <input value={approvedBy} onChange={(event) => setApprovedBy(event.target.value)} required />
            </label>
            <label>
              Actor
              <input value={actor} onChange={(event) => setActor(event.target.value)} required />
            </label>
            <label className="wide">
              Statutory basis
              <textarea value={statutoryBasis} onChange={(event) => setStatutoryBasis(event.target.value)} required />
            </label>
            <div className="wide compliance-preview">
              <strong>Computed deadline</strong>
              <span>{noticeDeadline ? formatDateTime(noticeDeadline.toISOString()) : "Select a scheduled meeting and required notice hours."}</span>
              <small>Notice must be posted at or before this deadline unless a lawful emergency/special basis applies.</small>
            </div>
            <button type="submit">Run notice checklist</button>
          </form>
          {message && <p className="form-message">{message}</p>}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Compliance record and proof</h2>
              <p>Attach proof only after a passing checklist. Failed checks explain the legal blocker.</p>
            </div>
            <StatusBadge tone={latestRecord?.compliant ? "Ready" : "Blocked"} label={latestRecord?.compliant ? "May post proof" : "No passing check"} />
          </div>
          <div className="review-controls">
            <label>
              Posting URL
              <input value={proofUrl} onChange={(event) => setProofUrl(event.target.value)} />
            </label>
            <label>
              Posting location
              <input value={proofLocation} onChange={(event) => setProofLocation(event.target.value)} />
            </label>
          </div>
          <div className="agenda-list">
            {noticeChecklists.length === 0 && (
              <p className="empty-inline">No notice checklist exists for this meeting. Finalize the packet, run the statutory check, then attach proof from the public posting location.</p>
            )}
            {noticeChecklists.map((record) => (
              <article key={record.id} className={record.compliant ? "agenda-row" : "agenda-row blocked-row"}>
                <div>
                  <div className="row-title">
                    <h3>{record.noticeType} notice</h3>
                    <StatusBadge tone={record.status === "POSTED" ? "Ready" : record.compliant ? "Warning" : "Blocked"} label={record.status === "POSTED" ? "Proof posted" : record.compliant ? "Passed check" : "Blocked"} />
                  </div>
                  <p>{record.minimumNoticeHours} hours required. Deadline: {formatDateTime(record.deadlineAt)}. Posted: {formatDateTime(record.postedAt)}.</p>
                  <small>Basis: {record.statutoryBasis || "Missing statutory basis"}</small>
                  <small>Approved by: {record.approvedBy || "No human approval recorded"}</small>
                  {record.warnings.length > 0 && <p className="legal-warning">Legal blocker: {noticeWarningText(record)}</p>}
                  {record.postingProof && <small>Proof: {record.postingProof.location ?? "location not recorded"} {record.postingProof.posted_url ?? ""}</small>}
                  <small>Audit hash: {record.lastAuditHash.slice(0, 12)}...</small>
                </div>
                <div className="row-actions">
                  <button
                    className="secondary"
                    type="button"
                    disabled={!record.compliant || record.status === "POSTED"}
                    title={!record.compliant ? "Fix the statutory notice blocker before attaching proof." : record.status === "POSTED" ? "Posting proof is already attached." : undefined}
                    onClick={() => attachProof(record)}
                  >
                    {record.status === "POSTED" ? "Proof attached" : "Attach posting proof"}
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function MeetingOutcomesWorkspace({
  viewState,
  apiError,
  meetings,
  activeMeeting,
  motions,
  votes,
  actionItems,
  setActiveMeetingId,
  onCaptureMotion,
  onCaptureVote,
  onCreateActionItem,
}: {
  viewState: ViewState;
  apiError: string | null;
  meetings: Meeting[];
  activeMeeting: Meeting;
  motions: MotionRecord[];
  votes: VoteRecord[];
  actionItems: ActionItemRecord[];
  setActiveMeetingId: (id: string) => void;
  onCaptureMotion: (meetingId: string, payload: MotionPayload) => Promise<MotionRecord>;
  onCaptureVote: (motionId: string, payload: VotePayload) => Promise<VoteRecord>;
  onCreateActionItem: (meetingId: string, payload: ActionItemPayload) => Promise<ActionItemRecord>;
}) {
  const [motionText, setMotionText] = useState("Move to adopt the annual fee schedule as presented.");
  const [actor, setActor] = useState("clerk@example.gov");
  const [selectedMotionId, setSelectedMotionId] = useState(motions[0]?.id ?? "");
  const [voterName, setVoterName] = useState("Council Member Rivera");
  const [vote, setVote] = useState("aye");
  const [actionDescription, setActionDescription] = useState("Staff to prepare the signed resolution and publish the adopted action.");
  const [assignedTo, setAssignedTo] = useState("Clerk's Office");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setSelectedMotionId((current) => current && motions.some((motion) => motion.id === current) ? current : motions[0]?.id ?? "");
    setMessage(null);
  }, [activeMeeting, motions]);

  if (viewState !== "success") {
    return <StateMessage state={viewState} context="meeting outcomes" apiError={apiError} />;
  }

  const selectedMotion = motions.find((motion) => motion.id === selectedMotionId) ?? motions[0];
  const meetingVotes = votes.filter((record) => motions.some((motion) => motion.id === record.motionId));
  const correctionCount = motions.filter((motion) => motion.correctionOfId).length + meetingVotes.filter((record) => record.correctionOfId).length;

  async function submitMotion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      const record = await onCaptureMotion(activeMeeting.id, {
        text: motionText.trim(),
        actor: actor.trim(),
      });
      setSelectedMotionId(record.id);
      setMessage(`Motion ${record.id} captured as an immutable meeting outcome. To fix wording later, append a correction record instead of editing this entry.`);
    } catch (error) {
      setMessage(`${error instanceof Error ? error.message : "Motion capture failed."} Confirm the meeting exists, the clerk actor is present, and the motion text is ready for the official record, then retry.`);
    }
  }

  async function submitVote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    if (!selectedMotion) {
      setMessage("Vote capture is blocked because no motion exists yet. Capture the motion first, then record votes against that motion.");
      return;
    }
    try {
      const record = await onCaptureVote(selectedMotion.id, {
        voter_name: voterName.trim(),
        vote: vote.trim(),
        actor: actor.trim(),
      });
      setMessage(`Vote ${record.id} captured for ${record.voterName}. The vote is immutable; use a correction record if the roll call is clarified.`);
    } catch (error) {
      setMessage(`${error instanceof Error ? error.message : "Vote capture failed."} Confirm the selected motion still exists, choose aye/nay/abstain/absent, then retry.`);
    }
  }

  async function submitActionItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    if (!selectedMotion) {
      setMessage("Action item creation is blocked because action items must reference a captured meeting outcome. Capture the motion first, then create the follow-up.");
      return;
    }
    try {
      const record = await onCreateActionItem(activeMeeting.id, {
        description: actionDescription.trim(),
        actor: actor.trim(),
        assigned_to: assignedTo.trim(),
        source_motion_id: selectedMotion.id,
      });
      setMessage(`Action item ${record.id} opened for ${record.assignedTo ?? "unassigned staff"} and linked to motion ${selectedMotion.id}.`);
    } catch (error) {
      setMessage(`${error instanceof Error ? error.message : "Action item create failed."} Capture the related motion first and verify the action source belongs to this meeting.`);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Meeting outcomes"
        title="Capture motions, roll-call votes, and follow-up actions."
        description="Build the official meeting record while the clerk can still see what is captured, what is missing, and why corrections must be append-only."
      />
      <div className="metric-grid">
        <MetricCard label="Motions" value={String(motions.length)} note={motions.length ? "Captured in official sequence" : "Capture first motion"} tone={motions.length ? undefined : "warn"} />
        <MetricCard label="Votes" value={String(meetingVotes.length)} note={meetingVotes.length ? voteSummary(meetingVotes) : "Roll call not started"} tone={meetingVotes.length ? undefined : "warn"} />
        <MetricCard label="Action items" value={String(actionItems.length)} note={actionItems.length ? "Linked to outcomes" : "No follow-ups yet"} />
      </div>
      <div className="outcome-ledger-callout">
        <strong>Official record behavior</strong>
        <span>Motions and votes are immutable. If the clerk needs to fix wording or a roll call, append a correction record that references the original; do not silently rewrite the meeting record.</span>
      </div>
      <div className="agenda-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Live capture</h2>
              <p>Record the motion first, then attach votes and action items to that outcome.</p>
            </div>
            <StatusBadge tone={motions.length ? "Ready" : "Warning"} label={motions.length ? "Outcome selected" : "Motion first"} />
          </div>
          <form className="intake-form" onSubmit={submitMotion}>
            <label>
              Meeting
              <select value={activeMeeting.id} onChange={(event) => setActiveMeetingId(event.target.value)} required>
                {meetings.map((meeting) => (
                  <option key={meeting.id} value={meeting.id}>{meeting.body} - {meeting.title}</option>
                ))}
              </select>
            </label>
            <label>
              Clerk actor
              <input value={actor} onChange={(event) => setActor(event.target.value)} required />
            </label>
            <label className="wide">
              Motion text
              <textarea value={motionText} onChange={(event) => setMotionText(event.target.value)} required />
            </label>
            <button type="submit">Capture motion</button>
          </form>
          <form className="intake-form stacked-form" onSubmit={submitVote}>
            <label>
              Motion for vote
              <select value={selectedMotion?.id ?? ""} onChange={(event) => setSelectedMotionId(event.target.value)} required>
                {motions.length === 0 && <option value="">Capture a motion first</option>}
                {motions.map((motion) => (
                  <option key={motion.id} value={motion.id}>{motion.text.slice(0, 72)}</option>
                ))}
              </select>
            </label>
            <label>
              Voter name
              <input value={voterName} onChange={(event) => setVoterName(event.target.value)} required />
            </label>
            <label>
              Vote
              <select value={vote} onChange={(event) => setVote(event.target.value)} required>
                <option value="aye">aye</option>
                <option value="nay">nay</option>
                <option value="abstain">abstain</option>
                <option value="absent">absent</option>
              </select>
            </label>
            <button type="submit">Record vote</button>
          </form>
          <form className="intake-form stacked-form" onSubmit={submitActionItem}>
            <label className="wide">
              Action item
              <textarea value={actionDescription} onChange={(event) => setActionDescription(event.target.value)} required />
            </label>
            <label>
              Assigned to
              <input value={assignedTo} onChange={(event) => setAssignedTo(event.target.value)} />
            </label>
            <button type="submit">Create action item</button>
          </form>
          {message && <p className="form-message">{message}</p>}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Outcome ledger</h2>
              <p>Review captured motions, vote totals, correction lineage, and open follow-ups.</p>
            </div>
            <StatusBadge tone={correctionCount ? "Warning" : "Ready"} label={correctionCount ? `${correctionCount} corrections` : "Append-only"} />
          </div>
          <div className="agenda-list">
            {motions.length === 0 && (
              <p className="empty-inline">No meeting outcomes captured yet. Capture a motion before recording votes, action items, or minutes draft source material.</p>
            )}
            {motions.map((motion) => {
              const motionVotes = votes.filter((record) => record.motionId === motion.id);
              const linkedActions = actionItems.filter((record) => record.sourceMotionId === motion.id);
              return (
                <article key={motion.id} className="agenda-row outcome-row">
                  <div>
                    <div className="row-title">
                      <h3>{motion.text}</h3>
                      <StatusBadge tone={motion.correctionOfId ? "Warning" : "Ready"} label={motion.correctionOfId ? "Correction" : "Captured"} />
                    </div>
                    <p>{motionVotes.length} votes recorded. {linkedActions.length} action items linked.</p>
                    <small>Actor: {motion.actor}. Motion ID: {motion.id}.</small>
                    {motion.correctionOfId && <p className="legal-warning">Correction of {motion.correctionOfId}: {motion.correctionReason}</p>}
                    <div className="vote-strip" aria-label={`Votes for ${motion.text}`}>
                      {motionVotes.length === 0 && <span className="vote-pill missing">No votes recorded</span>}
                      {motionVotes.map((record) => (
                        <span key={record.id} className={`vote-pill ${record.vote.toLowerCase()}`}>{record.voterName}: {record.vote}</span>
                      ))}
                    </div>
                    {linkedActions.map((item) => (
                      <small key={item.id}>Action: {item.description} ({item.status}) - {item.assignedTo ?? "unassigned"}</small>
                    ))}
                  </div>
                  <div className="row-actions">
                    <button className="secondary" type="button" onClick={() => setSelectedMotionId(motion.id)}>
                      Select outcome
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}

function MinutesDraftWorkspace({
  viewState,
  apiError,
  meetings,
  activeMeeting,
  drafts,
  motions,
  votes,
  setActiveMeetingId,
  onCreateDraft,
  onPostDraft,
}: {
  viewState: ViewState;
  apiError: string | null;
  meetings: Meeting[];
  activeMeeting: Meeting;
  drafts: MinutesDraftRecord[];
  motions: MotionRecord[];
  votes: VoteRecord[];
  setActiveMeetingId: (id: string) => void;
  onCreateDraft: (meetingId: string, payload: MinutesDraftPayload) => Promise<MinutesDraftRecord>;
  onPostDraft: (draftId: string) => Promise<void>;
}) {
  const firstMotion = motions[0];
  const firstVote = firstMotion ? votes.find((record) => record.motionId === firstMotion.id) : undefined;
  const [model, setModel] = useState("ollama/gemma4");
  const [promptVersion, setPromptVersion] = useState("minutes_draft@0.1.0");
  const [humanApprover, setHumanApprover] = useState("clerk@example.gov");
  const [sourceOneId, setSourceOneId] = useState(firstMotion?.id ?? "motion-1");
  const [sourceOneLabel, setSourceOneLabel] = useState("Motion text");
  const [sourceOneText, setSourceOneText] = useState(firstMotion?.text ?? "Council approved the sidewalk repair packet.");
  const [sourceTwoId, setSourceTwoId] = useState(firstVote?.id ?? "vote-1");
  const [sourceTwoLabel, setSourceTwoLabel] = useState("Vote record");
  const [sourceTwoText, setSourceTwoText] = useState(firstVote ? `${firstVote.voterName} voted ${firstVote.vote}.` : "The motion passed 5-0.");
  const [sentenceOne, setSentenceOne] = useState("Council approved the sidewalk repair packet.");
  const [sentenceOneCitations, setSentenceOneCitations] = useState(firstMotion?.id ?? "motion-1");
  const [sentenceTwo, setSentenceTwo] = useState("The recorded vote supports the action described in the minutes.");
  const [sentenceTwoCitations, setSentenceTwoCitations] = useState(firstVote?.id ?? "vote-1");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setMessage(null);
    if (firstMotion) {
      setSourceOneId(firstMotion.id);
      setSourceOneText(firstMotion.text);
      setSentenceOneCitations(firstMotion.id);
    }
    if (firstVote) {
      setSourceTwoId(firstVote.id);
      setSourceTwoText(`${firstVote.voterName} voted ${firstVote.vote}.`);
      setSentenceTwoCitations(firstVote.id);
    }
  }, [activeMeeting, firstMotion, firstVote]);

  if (viewState === "loading" || viewState === "error" || viewState === "partial") {
    return <StateMessage state={viewState} context="minutes draft" apiError={apiError} />;
  }

  const citationCount = drafts.reduce((total, draft) => total + draft.sentences.reduce((sum, sentence) => sum + sentence.citations.length, 0), 0);
  const unpostedCount = drafts.filter((draft) => !draft.posted).length;

  async function submitDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    const sources = [
      { source_id: sourceOneId.trim(), label: sourceOneLabel.trim(), text: sourceOneText.trim() },
      { source_id: sourceTwoId.trim(), label: sourceTwoLabel.trim(), text: sourceTwoText.trim() },
    ].filter((source) => source.source_id && source.label && source.text);
    const sentences = [
      { text: sentenceOne.trim(), citations: parseCitationList(sentenceOneCitations) },
      { text: sentenceTwo.trim(), citations: parseCitationList(sentenceTwoCitations) },
    ].filter((sentence) => sentence.text);
    if (sentences.some((sentence) => sentence.citations.length === 0)) {
      setMessage("Minutes draft is blocked because every material sentence needs at least one citation. Add a source ID to each citation field, then create the draft again.");
      return;
    }
    try {
      const record = await onCreateDraft(activeMeeting.id, {
        model: model.trim(),
        prompt_version: promptVersion.trim(),
        human_approver: humanApprover.trim(),
        source_materials: sources,
        sentences,
      });
      setMessage(`Draft ${record.id} created with ${record.sentences.length} cited sentences. It is not adopted or posted until a human approval workflow accepts it.`);
    } catch (error) {
      setMessage(`${error instanceof Error ? error.message : "Minutes draft create failed."} Verify every citation exactly matches a source ID, the prompt version exists, and the human approver is filled in before retrying.`);
    }
  }

  async function attemptPost(draftId: string) {
    setMessage(null);
    try {
      await onPostDraft(draftId);
      setMessage("Posting completed. If this appears in production, verify the adoption workflow because AI minutes should not bypass human approval.");
    } catch (error) {
      setMessage(`${error instanceof Error ? error.message : "Minutes posting was blocked."} This is expected until the minutes are cite-checked, adopted, and released through the human approval workflow.`);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Minutes draft"
        title="Create cited minutes without letting AI become the official record."
        description="Every sentence must point back to source material, every draft records prompt provenance, and public posting stays blocked until a clerk-approved adoption workflow completes."
      />
      <div className="metric-grid">
        <MetricCard label="Drafts" value={String(drafts.length)} note={drafts.length ? "Citation-gated records" : "Create first draft"} tone={drafts.length ? undefined : "warn"} />
        <MetricCard label="Citations" value={String(citationCount)} note={citationCount ? "Sentence-level evidence" : "No cited sentences yet"} tone={citationCount ? undefined : "warn"} />
        <MetricCard label="Not posted" value={String(unpostedCount)} note="AI drafts require human adoption" />
      </div>
      <div className="minutes-guardrail">
        <strong>Legal record guardrail</strong>
        <span>Draft minutes are evidence-linked working records. The clerk must be able to explain each sentence from cited motion, vote, packet, or transcript sources before adoption.</span>
      </div>
      <div className="agenda-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Draft builder</h2>
              <p>Create the AI-assisted draft only after source material and human approver are explicit.</p>
            </div>
            <StatusBadge tone="Warning" label="Human approval required" />
          </div>
          <form className="intake-form minutes-form" onSubmit={submitDraft}>
            <label>
              Meeting
              <select value={activeMeeting.id} onChange={(event) => setActiveMeetingId(event.target.value)} required>
                {meetings.map((meeting) => (
                  <option key={meeting.id} value={meeting.id}>{meeting.body} - {meeting.title}</option>
                ))}
              </select>
            </label>
            <label>
              Model
              <input value={model} onChange={(event) => setModel(event.target.value)} required />
            </label>
            <label>
              Prompt version
              <input value={promptVersion} onChange={(event) => setPromptVersion(event.target.value)} required />
            </label>
            <label>
              Human approver
              <input value={humanApprover} onChange={(event) => setHumanApprover(event.target.value)} required />
            </label>
            <fieldset className="wide source-fieldset">
              <legend>Source material</legend>
              <div className="source-grid">
                <label>
                  Source ID
                  <input value={sourceOneId} onChange={(event) => setSourceOneId(event.target.value)} required />
                </label>
                <label>
                  Label
                  <input value={sourceOneLabel} onChange={(event) => setSourceOneLabel(event.target.value)} required />
                </label>
                <label className="wide">
                  Text
                  <textarea value={sourceOneText} onChange={(event) => setSourceOneText(event.target.value)} required />
                </label>
              </div>
              <div className="source-grid">
                <label>
                  Source ID
                  <input value={sourceTwoId} onChange={(event) => setSourceTwoId(event.target.value)} required />
                </label>
                <label>
                  Label
                  <input value={sourceTwoLabel} onChange={(event) => setSourceTwoLabel(event.target.value)} required />
                </label>
                <label className="wide">
                  Text
                  <textarea value={sourceTwoText} onChange={(event) => setSourceTwoText(event.target.value)} required />
                </label>
              </div>
            </fieldset>
            <label className="wide">
              Minutes sentence 1
              <textarea value={sentenceOne} onChange={(event) => setSentenceOne(event.target.value)} required />
            </label>
            <label>
              Citations for sentence 1
              <input value={sentenceOneCitations} onChange={(event) => setSentenceOneCitations(event.target.value)} required />
            </label>
            <label className="wide">
              Minutes sentence 2
              <textarea value={sentenceTwo} onChange={(event) => setSentenceTwo(event.target.value)} required />
            </label>
            <label>
              Citations for sentence 2
              <input value={sentenceTwoCitations} onChange={(event) => setSentenceTwoCitations(event.target.value)} required />
            </label>
            <button type="submit">Create cited draft</button>
          </form>
          {message && <p className="form-message" role="status">{message}</p>}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Draft review</h2>
              <p>Show provenance, citations, and blocked posting behavior before minutes become public.</p>
            </div>
            <StatusBadge tone={drafts.length ? "Ready" : "Warning"} label={drafts.length ? "Evidence visible" : "No draft"} />
          </div>
          <div className="agenda-list">
            {drafts.length === 0 && (
              <p className="empty-inline">No minutes draft exists for this meeting. Create a cited draft after motions and votes are captured.</p>
            )}
            {drafts.map((draft) => (
              <article key={draft.id} className="agenda-row minutes-row">
                <div>
                  <div className="row-title">
                    <h3>{draft.status} minutes draft</h3>
                    <StatusBadge tone={draft.posted ? "Ready" : "Warning"} label={draft.posted ? "Posted" : "Not posted"} />
                  </div>
                  <p>Prompt {draft.provenance.promptVersion} via {draft.provenance.model}. Human approver: {draft.provenance.humanApprover}.</p>
                  <small>Sources: {draft.provenance.dataSources.join(", ")}</small>
                  <div className="citation-list">
                    {draft.sentences.map((sentence, index) => (
                      <blockquote key={`${draft.id}-${index}`}>
                        <span>{sentence.text}</span>
                        <cite>Citations: {sentence.citations.join(", ")}</cite>
                      </blockquote>
                    ))}
                  </div>
                  <p className="legal-warning">Adopted: {draft.adopted ? "yes" : "no"}. Posted: {draft.posted ? "yes" : "no"}. AI-drafted minutes cannot be auto-posted.</p>
                </div>
                <div className="row-actions">
                  <button className="secondary" type="button" onClick={() => attemptPost(draft.id)}>
                    Try public posting gate
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function PublicPostedMeetingWorkspace({
  viewState,
  apiError,
  records,
  selectedRecord,
  onSelectRecord,
  onSearch,
}: {
  viewState: ViewState;
  apiError: string | null;
  records: PublicMeetingRecord[];
  selectedRecord: PublicMeetingRecord | null;
  onSelectRecord: (recordId: string) => Promise<void>;
  onSearch: (query: string) => Promise<PublicMeetingRecord[]>;
}) {
  const [query, setQuery] = useState("sidewalk");
  const [searchResults, setSearchResults] = useState<PublicMeetingRecord[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  if (viewState !== "success") {
    return <StateMessage state={viewState} context="public posted meeting" apiError={apiError} />;
  }

  async function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      const results = await onSearch(query);
      setSearchResults(results);
      setMessage(results.length === 0
        ? "No public records matched. Try a broader term or ask the clerk whether the meeting has been posted."
        : `${results.length} public record${results.length === 1 ? "" : "s"} matched. Restricted or closed-session records are not shown to anonymous visitors.`);
    } catch (error) {
      setMessage(`${error instanceof Error ? error.message : "Public archive search failed."} Confirm the public API is running, then retry or ask the clerk for the posted record link.`);
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Public posting"
        title="Show residents the posted agenda, packet, and approved minutes."
        description="This resident-safe page reads only public meeting records. Closed-session material and restricted records are not displayed or hinted to anonymous visitors."
      />
      <div className="metric-grid">
        <MetricCard label="Public records" value={String(records.length)} note="Visible to residents" />
        <MetricCard label="Selected meeting" value={selectedRecord ? "1" : "0"} note={selectedRecord ? "Ready for detail view" : "Pick a posted record"} tone={selectedRecord ? undefined : "warn"} />
        <MetricCard label="Restricted material" value="0" note="Never shown here" />
      </div>
      <div className="notice-legal-callout public-callout">
        <strong>Resident-safe view</strong>
        <span>Only records returned by the public archive API appear here. If a meeting is missing, staff must publish a public-safe record from the clerk workflow before residents can see it.</span>
      </div>
      <div className="agenda-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Posted meetings</h2>
              <p>Choose the record residents should inspect. Missing meetings are a staff publishing task, not a resident error.</p>
            </div>
            <StatusBadge tone={records.length ? "Ready" : "Warning"} label={records.length ? "Public" : "No records"} />
          </div>
          <div className="agenda-list">
            {records.length === 0 && (
              <p className="empty-inline">No public meeting records are posted yet. Staff should publish a public-safe archive record from the clerk workflow, then residents can refresh this page.</p>
            )}
            {records.map((record) => (
              <article key={record.id} className="agenda-row">
                <div>
                  <div className="row-title">
                    <h3>{record.title}</h3>
                    <StatusBadge tone="Ready" label="Posted" />
                  </div>
                  <p>{record.postedAgenda}</p>
                  <small>Meeting id: {record.meetingId}</small>
                </div>
                <div className="row-actions">
                  <button className="secondary" type="button" onClick={() => onSelectRecord(record.id)}>
                    View public record
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Resident detail</h2>
              <p>Agenda, packet, and minutes copy are safe to show publicly.</p>
            </div>
            <StatusBadge tone={selectedRecord ? "Ready" : "Warning"} label={selectedRecord ? "Selected" : "Pick record"} />
          </div>
          {selectedRecord ? (
            <div className="public-record-card">
              <h3>{selectedRecord.title}</h3>
              <dl>
                <dt>Posted agenda</dt>
                <dd>{selectedRecord.postedAgenda}</dd>
                <dt>Posted packet</dt>
                <dd>{selectedRecord.postedPacket}</dd>
                <dt>Approved minutes</dt>
                <dd>{selectedRecord.approvedMinutes}</dd>
              </dl>
              <p className="legal-warning muted-warning">Closed-session content is not displayed here. Ask the clerk for the public record link if expected material is missing.</p>
            </div>
          ) : (
            <p className="empty-inline">Select a posted meeting to show resident-safe detail.</p>
          )}
          <form className="search-form" onSubmit={submitSearch}>
            <label>
              Search public archive
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search posted public records" />
            </label>
            <button type="submit">Search public records</button>
          </form>
          {message && <p className="form-message">{message}</p>}
          {searchResults.length > 0 && (
            <div className="agenda-list">
              {searchResults.map((record) => (
                <article key={record.id} className="agenda-row">
                  <div>
                    <h3>{record.title}</h3>
                    <p>{record.postedPacket}</p>
                  </div>
                  <div className="row-actions">
                    <button className="secondary" type="button" onClick={() => onSelectRecord(record.id)}>
                      Open
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
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

function suggestedNoticePostedAt(scheduledStart: string | null | undefined, minimumHours: number): string {
  if (!scheduledStart) {
    return "";
  }
  const scheduled = new Date(scheduledStart);
  if (Number.isNaN(scheduled.getTime())) {
    return "";
  }
  const suggested = new Date(scheduled.getTime() - (minimumHours + 24) * 60 * 60 * 1000);
  return toDateTimeLocalValue(suggested.toISOString());
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
  if (context === "notice checklist" && state === "empty") {
    copy.body = "Finalize the packet, run the statutory notice check, then attach posting proof from the public posting location before treating the meeting as lawfully noticed.";
    copy.action = "Run statutory check";
  }
  if (context === "notice checklist" && state === "partial") {
    copy.body = "Notice checklist data is only partially available. Do not treat the meeting as noticed until deadline, statutory basis, human approval, posting proof, and audit hash are all visible; check the notice store configuration, then reload.";
    copy.action = "Check notice store";
  }
  if (context === "notice checklist" && state === "error") {
    copy.body = apiError
      ? `${apiError} Do not attach posting proof from this workspace until the notice API is reachable; confirm the backend, notice store, and staff auth mode, then retry.`
      : "The notice API did not respond. Do not treat the meeting as noticed until deadline, statutory basis, approval, proof, and audit hash are visible; confirm the backend, notice store, and staff auth mode, then retry.";
  }
  if (context === "meeting outcomes" && state === "empty") {
    copy.body = "No motions, votes, or action items are captured for this meeting yet. Capture the first motion, then record roll-call votes and any follow-up action item tied to that motion.";
    copy.action = "Capture motion";
  }
  if (context === "meeting outcomes" && state === "partial") {
    copy.body = "Meeting outcome data is only partially available. Do not draft minutes from this workspace until motions, votes, action items, and correction lineage are visible; check the outcomes API and reload.";
    copy.action = "Check outcomes API";
  }
  if (context === "meeting outcomes" && state === "error") {
    copy.body = apiError
      ? `${apiError} Confirm the motion/vote/action-item APIs are reachable, then retry before relying on this meeting record.`
      : "The outcomes API did not respond. Confirm the motion/vote/action-item APIs are reachable, then retry before relying on this meeting record.";
  }
  if (context === "minutes draft" && state === "empty") {
    copy.body = "No minutes draft exists for this meeting yet. Capture motions and votes, then create a cited draft with a human approver and prompt provenance.";
    copy.action = "Create cited draft";
  }
  if (context === "minutes draft" && state === "partial") {
    copy.body = "Minutes drafting is partially available, but citation or provenance data is missing. Check source IDs, prompt version, model name, and human approver before treating the draft as review-ready.";
    copy.action = "Check citation sources";
  }
  if (context === "minutes draft" && state === "error") {
    copy.body = apiError
      ? `${apiError} Do not accept AI-drafted minutes until every material sentence cites a known source and a human approver is recorded.`
      : "The minutes draft API did not respond. Do not accept AI-drafted minutes until every material sentence cites a known source and a human approver is recorded; confirm CivicClerk is running, then retry after verifying citation sources.";
  }
  if (context === "public posted meeting" && state === "empty") {
    copy.body = "No public meeting records are posted yet. Staff should publish a public-safe record from the clerk workflow before residents can see agendas, packets, or approved minutes here.";
    copy.action = "Ask clerk to publish";
  }
  if (context === "public posted meeting" && state === "partial") {
    copy.body = "Public meeting records are only partially available. Residents should not assume a missing meeting is closed or nonexistent; confirm the public archive API and ask the clerk for the posted record link.";
    copy.action = "Check public archive";
  }
  if (context === "public posted meeting" && state === "error") {
    copy.body = apiError
      ? `${apiError} Confirm the public API is running and retry; if the meeting is time-sensitive, ask the clerk for the official posted record link.`
      : "The public archive API did not respond. Confirm the public API is running and retry; if the meeting is time-sensitive, ask the clerk for the official posted record link.";
  }

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

function readinessLabel(status: AgendaIntakeItem["readinessStatus"]): string {
  const labels = {
    PENDING: "Pending review",
    READY: "Ready",
    NEEDS_REVISION: "Needs revision",
  };
  return labels[status];
}

function noticeWarningText(record: NoticeChecklistRecord): string {
  if (record.warnings.length === 0) {
    return "No backend warning text was returned. Confirm the deadline, statutory basis, and approval before proceeding.";
  }
  return record.warnings
    .map((warning) => {
      const code = warning.code ? `${warning.code}: ` : "";
      return `${code}${warning.fix ?? warning.message ?? "Review the notice record and correct the statutory blocker."}`;
    })
    .join(" ");
}

function voteSummary(votes: VoteRecord[]): string {
  const counts = votes.reduce<Record<string, number>>((current, record) => {
    current[record.vote] = (current[record.vote] ?? 0) + 1;
    return current;
  }, {});
  return ["aye", "nay", "abstain", "absent"]
    .filter((key) => counts[key])
    .map((key) => `${counts[key]} ${key}`)
    .join(", ");
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function statusTone(status: AgendaIntakeItem["readinessStatus"]): Meeting["noticeStatus"] {
  if (status === "READY") return "Ready";
  if (status === "NEEDS_REVISION") return "Blocked";
  return "Warning";
}

function StatusBadge({ tone, label }: { tone: Meeting["noticeStatus"]; label: string }) {
  return <span className={`status ${tone.toLowerCase()}`}>{label}</span>;
}
