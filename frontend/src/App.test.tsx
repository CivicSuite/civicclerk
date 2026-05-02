import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

describe("CivicClerk staff workspace", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string, init?: RequestInit) => {
        if (url === "/staff/session") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              mode: "oidc",
              authenticated: true,
              auth_method: "oidc_browser_session",
              subject: "clerk@example.gov",
              provider: "Brookfield Entra ID",
              roles: ["clerk_admin", "meeting_editor"],
              message: "Staff browser session is active.",
              fix: "Continue with clerk workflow actions.",
            }),
          });
        }
        if (url === "/api/meeting-bodies" && init?.method === "POST") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              id: "body-3",
              name: "Library Board",
              body_type: "board",
              is_active: true,
            }),
          });
        }
        if (url === "/api/meeting-bodies/body-1" && init?.method === "PATCH") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              id: "body-1",
              name: "Brookfield City Council",
              body_type: "city_council",
              is_active: true,
            }),
          });
        }
        if (url === "/api/meeting-bodies/body-1" && init?.method === "DELETE") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              id: "body-1",
              name: "City Council",
              body_type: "city_council",
              is_active: false,
            }),
          });
        }
        if (url === "/api/meeting-bodies") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              meeting_bodies: [
                {
                  id: "body-1",
                  name: "City Council",
                  body_type: "city_council",
                  is_active: true,
                },
                {
                  id: "body-2",
                  name: "Planning Commission",
                  body_type: "commission",
                  is_active: true,
                },
              ],
            }),
          });
        }
        if (url === "/api/meetings" && init?.method === "POST") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              id: "meeting-3",
              title: "Library Board Regular Meeting",
              meeting_type: "regular",
              meeting_body_id: "body-2",
              status: "SCHEDULED",
              scheduled_start: "2026-05-10T18:00:00Z",
              location: "Library Community Room",
            }),
          });
        }
        if (url === "/api/meetings/meeting-1" && init?.method === "PATCH") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              id: "meeting-1",
              title: "Updated Regular Meeting",
              meeting_type: "special",
              meeting_body_id: "body-2",
              status: "PACKET_POSTED",
              scheduled_start: "2026-05-08T19:00:00Z",
              location: "Room 204",
            }),
          });
        }
        if (url === "/api/meetings/meeting-1/packet-assemblies" && init?.method === "POST") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              id: "packet-1",
              meeting_id: "meeting-1",
              packet_snapshot_id: "snapshot-1",
              packet_version: 1,
              title: "Council packet draft",
              status: "DRAFT",
              agenda_item_ids: ["agenda-99"],
              source_references: [{ source_id: "fee-table", title: "Fee table", kind: "spreadsheet" }],
              citations: [{ agenda_item_id: "agenda-99", citation: "Fee table" }],
              last_audit_hash: "abc123abc123abc123abc123abc123abc123abc123abc123abc123abc123abcd",
              created_at: "2026-05-01T12:20:00Z",
              updated_at: "2026-05-01T12:20:00Z",
              finalized_at: null,
            }),
          });
        }
        if (url === "/api/meetings/meeting-1/packet-assemblies") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              packet_assemblies: [
                {
                  id: "packet-existing",
                  meeting_id: "meeting-1",
                  packet_snapshot_id: "snapshot-existing",
                  packet_version: 1,
                  title: "Existing finalized packet",
                  status: "FINALIZED",
                  agenda_item_ids: ["agenda-99"],
                  source_references: [{ source_id: "fee-table", title: "Fee table", kind: "spreadsheet" }],
                  citations: [{ agenda_item_id: "agenda-99", citation: "Fee table" }],
                  last_audit_hash: "fed456fed456fed456fed456fed456fed456fed456fed456fed456fed456abcd",
                  created_at: "2026-05-01T12:00:00Z",
                  updated_at: "2026-05-01T12:05:00Z",
                  finalized_at: "2026-05-01T12:05:00Z",
                },
              ],
            }),
          });
        }
        if (url === "/api/packet-assemblies/packet-1/finalize" && init?.method === "POST") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              id: "packet-1",
              meeting_id: "meeting-1",
              packet_snapshot_id: "snapshot-1",
              packet_version: 1,
              title: "Council packet draft",
              status: "FINALIZED",
              agenda_item_ids: ["agenda-99"],
              source_references: [{ source_id: "fee-table", title: "Fee table", kind: "spreadsheet" }],
              citations: [{ agenda_item_id: "agenda-99", citation: "Fee table" }],
              last_audit_hash: "def456def456def456def456def456def456def456def456def456def456abcd",
              created_at: "2026-05-01T12:20:00Z",
              updated_at: "2026-05-01T12:25:00Z",
              finalized_at: "2026-05-01T12:25:00Z",
            }),
          });
        }
        if (url === "/api/meetings/meeting-1/notice-checklists" && init?.method === "POST") {
          const body = JSON.parse(String(init.body ?? "{}")) as { minimum_notice_hours?: number };
          const blocked = Number(body.minimum_notice_hours) > 100;
          return Promise.resolve({
            ok: true,
            json: async () => ({
              id: blocked ? "notice-blocked" : "notice-1",
              meeting_id: "meeting-1",
              notice_type: blocked ? "special" : "regular",
              status: "CHECKED",
              compliant: !blocked,
              http_status: blocked ? 422 : 200,
              warnings: blocked ? [{ code: "notice_deadline_missed", fix: "Reschedule the meeting or document the lawful emergency basis before proceeding." }] : [],
              deadline_at: "2026-05-02T18:00:00Z",
              posted_at: blocked ? "2026-05-05T18:00:00Z" : "2026-05-01T18:00:00Z",
              minimum_notice_hours: body.minimum_notice_hours ?? 72,
              statutory_basis: "Local open meeting law requires posted notice.",
              approved_by: "clerk@example.gov",
              posting_proof: null,
              last_audit_hash: blocked
                ? "bad123bad123bad123bad123bad123bad123bad123bad123bad123bad123abcd"
                : "notice1234567890notice1234567890notice1234567890notice123456abcd",
              created_at: "2026-05-01T12:30:00Z",
              updated_at: "2026-05-01T12:30:00Z",
            }),
          });
        }
        if (url === "/api/meetings/meeting-1/notice-checklists") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              notice_checklists: [],
            }),
          });
        }
        if (url === "/api/notice-checklists/notice-1/posting-proof" && init?.method === "POST") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              id: "notice-1",
              meeting_id: "meeting-1",
              notice_type: "regular",
              status: "POSTED",
              compliant: true,
              http_status: 200,
              warnings: [],
              deadline_at: "2026-05-02T18:00:00Z",
              posted_at: "2026-05-01T18:00:00Z",
              minimum_notice_hours: 72,
              statutory_basis: "Local open meeting law requires posted notice.",
              approved_by: "clerk@example.gov",
              posting_proof: { posted_url: "https://city.example.gov/agendas/meeting-notice", location: "City Hall notice board" },
              last_audit_hash: "proof1234567890proof1234567890proof1234567890proof123456abcd",
              created_at: "2026-05-01T12:30:00Z",
              updated_at: "2026-05-01T12:35:00Z",
            }),
          });
        }
        if (url === "/api/meetings/meeting-1/motions" && init?.method === "POST") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              id: "motion-1",
              meeting_id: "meeting-1",
              agenda_item_id: null,
              text: "Move to adopt the annual fee schedule as presented.",
              actor: "clerk@example.gov",
              correction_of_id: null,
              correction_reason: null,
              captured: true,
            }),
          });
        }
        if (url === "/api/meetings/meeting-1/motions") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              motions: [
                {
                  id: "motion-existing",
                  meeting_id: "meeting-1",
                  agenda_item_id: "agenda-99",
                  text: "Move to approve sidewalk repairs.",
                  actor: "clerk@example.gov",
                  correction_of_id: null,
                  correction_reason: null,
                  captured: true,
                },
              ],
            }),
          });
        }
        if (url === "/api/motions/motion-existing/votes" && init?.method === "POST") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              id: "vote-2",
              motion_id: "motion-existing",
              voter_name: "Council Member Rivera",
              vote: "aye",
              actor: "clerk@example.gov",
              correction_of_id: null,
              correction_reason: null,
              captured: true,
            }),
          });
        }
        if (url === "/api/motions/motion-1/votes" && init?.method === "POST") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              id: "vote-1",
              motion_id: "motion-1",
              voter_name: "Council Member Rivera",
              vote: "aye",
              actor: "clerk@example.gov",
              correction_of_id: null,
              correction_reason: null,
              captured: true,
            }),
          });
        }
        if (url === "/api/motions/motion-existing/votes") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              votes: [
                {
                  id: "vote-existing",
                  motion_id: "motion-existing",
                  voter_name: "Council Member Patel",
                  vote: "aye",
                  actor: "clerk@example.gov",
                  correction_of_id: null,
                  correction_reason: null,
                  captured: true,
                },
              ],
            }),
          });
        }
        if (url === "/api/meetings/meeting-1/action-items" && init?.method === "POST") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              id: "action-1",
              meeting_id: "meeting-1",
              description: "Staff to prepare the signed resolution and publish the adopted action.",
              actor: "clerk@example.gov",
              assigned_to: "Clerk's Office",
              source_motion_id: "motion-1",
              status: "OPEN",
            }),
          });
        }
        if (url === "/api/meetings/meeting-1/action-items") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              action_items: [],
            }),
          });
        }
        if (url === "/api/meetings/meeting-1/minutes/drafts" && init?.method === "POST") {
          const body = JSON.parse(String(init.body ?? "{}"));
          return Promise.resolve({
            ok: true,
            json: async () => ({
              id: "minutes-1",
              meeting_id: "meeting-1",
              status: "DRAFT",
              adopted: false,
              posted: false,
              source_materials: body.source_materials,
              sentences: body.sentences,
              provenance: {
                model: body.model,
                prompt_version: body.prompt_version,
                data_sources: body.source_materials.map((source: { source_id: string }) => source.source_id),
                human_approver: body.human_approver,
              },
            }),
          });
        }
        if (url === "/api/meetings/meeting-1/minutes/drafts") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              drafts: [
                {
                  id: "minutes-existing",
                  meeting_id: "meeting-1",
                  status: "DRAFT",
                  adopted: false,
                  posted: false,
                  source_materials: [
                    {
                      source_id: "motion-existing",
                      label: "Motion text",
                      text: "Move to approve sidewalk repairs.",
                    },
                    {
                      source_id: "vote-existing",
                      label: "Vote record",
                      text: "Council Member Patel voted aye.",
                    },
                  ],
                  sentences: [
                    {
                      text: "Council approved sidewalk repairs.",
                      citations: ["motion-existing"],
                    },
                  ],
                  provenance: {
                    model: "ollama/gemma4",
                    prompt_version: "minutes_draft@0.1.0",
                    data_sources: ["motion-existing", "vote-existing"],
                    human_approver: "clerk@example.gov",
                  },
                },
              ],
            }),
          });
        }
        if (url === "/api/minutes/minutes-existing/post" || url === "/api/minutes/minutes-1/post") {
          return Promise.resolve({
            ok: false,
            status: 409,
            json: async () => ({
              detail: {
                message: "AI-drafted minutes cannot be posted automatically.",
                fix: "Review, cite-check, and adopt minutes through a human approval workflow before public posting.",
              },
            }),
          });
        }
        if (url === "/api/public/meetings") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              total_count: 1,
              meetings: [
                {
                  id: "public-1",
                  meeting_id: "meeting-1",
                  title: "City Council Regular Meeting",
                  posted_agenda: "Agenda: approve sidewalk repairs.",
                  posted_packet: "Packet: staff report and fiscal note.",
                  approved_minutes: "Approved minutes: motion passed 5-0.",
                },
              ],
            }),
          });
        }
        if (url === "/api/public/meetings/public-1") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              id: "public-1",
              meeting_id: "meeting-1",
              title: "City Council Regular Meeting",
              posted_agenda: "Agenda: approve sidewalk repairs.",
              posted_packet: "Packet: staff report and fiscal note.",
              approved_minutes: "Approved minutes: motion passed 5-0.",
            }),
          });
        }
        if (url === "/api/public/archive/search?q=sidewalk") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              total_count: 1,
              results: [
                {
                  id: "public-1",
                  meeting_id: "meeting-1",
                  title: "City Council Regular Meeting",
                  posted_agenda: "Agenda: approve sidewalk repairs.",
                  posted_packet: "Packet: staff report and fiscal note.",
                  approved_minutes: "Approved minutes: motion passed 5-0.",
                },
              ],
              suggestions: [],
            }),
          });
        }
        if (url === "/api/agenda-intake" && init?.method === "POST") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              id: "intake-2",
              title: "Approve downtown zoning study",
              department_name: "Planning",
              submitted_by: "planning@example.gov",
              summary: "Authorize the downtown zoning study.",
              readiness_status: "PENDING",
              status: "SUBMITTED",
              source_references: [{ source_id: "planning-staff-report", title: "Planning staff report", kind: "document" }],
              reviewer: null,
              review_notes: null,
              last_audit_hash: "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
              created_at: "2026-05-01T12:00:00Z",
              updated_at: "2026-05-01T12:00:00Z",
            }),
          });
        }
        if (url === "/api/agenda-intake/intake-1/review" && init?.method === "POST") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              id: "intake-1",
              title: "Approve zoning study",
              department_name: "Planning",
              submitted_by: "planning@example.gov",
              summary: "Study authorization for downtown zoning.",
              readiness_status: "READY",
              status: "READY_FOR_CLERK",
              source_references: [{ source_id: "zoning-memo", title: "Planning memo", kind: "document" }],
              reviewer: "clerk@example.gov",
              review_notes: "Complete for packet assembly.",
              last_audit_hash: "123456abcdef7890123456abcdef7890123456abcdef7890123456abcdef7890",
              created_at: "2026-05-01T11:00:00Z",
              updated_at: "2026-05-01T12:10:00Z",
            }),
          });
        }
        if (url === "/api/agenda-intake/intake-1/promote" && init?.method === "POST") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              message: "Agenda intake item promoted into the agenda lifecycle.",
              next_step: "Add the agenda item to the target meeting packet assembly.",
              intake_item: {
                id: "intake-1",
                title: "Approve zoning study",
                department_name: "Planning",
                submitted_by: "planning@example.gov",
                summary: "Study authorization for downtown zoning.",
                readiness_status: "READY",
                status: "PROMOTED_TO_AGENDA",
                source_references: [{ source_id: "zoning-memo", title: "Planning memo", kind: "document" }],
                reviewer: "clerk@example.gov",
                review_notes: "Complete for packet assembly.",
                promoted_agenda_item_id: "agenda-77",
                promoted_at: "2026-05-01T12:15:00Z",
                promotion_audit_hash: "fedcba1234567890fedcba1234567890fedcba1234567890fedcba1234567890",
                last_audit_hash: "fedcba1234567890fedcba1234567890fedcba1234567890fedcba1234567890",
                created_at: "2026-05-01T11:00:00Z",
                updated_at: "2026-05-01T12:15:00Z",
              },
              agenda_item: {
                id: "agenda-77",
                title: "Approve zoning study",
                department_name: "Planning",
                status: "CLERK_ACCEPTED",
              },
            }),
          });
        }
        if (url === "/api/agenda-intake") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              items: [
                {
                  id: "intake-1",
                  title: "Approve zoning study",
                  department_name: "Planning",
                  submitted_by: "planning@example.gov",
                  summary: "Study authorization for downtown zoning.",
                  readiness_status: "PENDING",
                  status: "SUBMITTED",
                  source_references: [{ source_id: "zoning-memo", title: "Planning memo", kind: "document" }],
                  reviewer: null,
                  review_notes: null,
                  promoted_agenda_item_id: null,
                  promoted_at: null,
                  promotion_audit_hash: null,
                  last_audit_hash: "abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd",
                  created_at: "2026-05-01T11:00:00Z",
                  updated_at: "2026-05-01T11:00:00Z",
                },
                {
                  id: "intake-ready",
                  title: "Adopt annual fee schedule",
                  department_name: "Finance",
                  submitted_by: "finance@example.gov",
                  summary: "Annual update to city service fees.",
                  readiness_status: "READY",
                  status: "PROMOTED_TO_AGENDA",
                  source_references: [{ source_id: "fee-table", title: "Fee table", kind: "spreadsheet" }],
                  reviewer: "clerk@example.gov",
                  review_notes: "Attorney review attached.",
                  promoted_agenda_item_id: "agenda-99",
                  promoted_at: "2026-05-01T12:15:00Z",
                  promotion_audit_hash: "fedcba1234567890fedcba1234567890fedcba1234567890fedcba1234567890",
                  last_audit_hash: "fedcba1234567890fedcba1234567890fedcba1234567890fedcba1234567890",
                  created_at: "2026-05-01T10:00:00Z",
                  updated_at: "2026-05-01T12:15:00Z",
                },
              ],
            }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({
            meetings: [
              {
                id: "meeting-1",
                title: "Regular Meeting",
                meeting_type: "city_council",
                meeting_body_id: "body-1",
                status: "PACKET_POSTED",
                scheduled_start: "2026-05-05T18:00:00Z",
                location: "Council Chambers",
              },
              {
                id: "meeting-2",
                title: "Special Session",
                meeting_type: "planning_commission",
                meeting_body_id: "body-2",
                status: "NOTICED",
                scheduled_start: "2026-05-07T18:00:00Z",
                location: "Room 204",
              },
            ],
          }),
        });
      }),
    );
  });

  afterEach(() => {
    window.history.replaceState({}, "", "/");
    vi.unstubAllGlobals();
  });

  it("renders the CivicSuite staff shell and dashboard from the live meeting API", async () => {
    render(<App />);

    expect(screen.getByText("CivicSuite")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Good morning, City Clerk." })).toBeInTheDocument();
    expect(screen.getByText("Live from CivicClerk meeting API")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Meeting runbook" })).toBeInTheDocument();
    expect(screen.getByText("End-to-end clerk runbook")).toBeInTheDocument();
    expect(screen.getAllByText("Notice legally proved").length).toBeGreaterThan(0);
    expect(screen.getByText(/Run the statutory notice checklist/)).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Meeting bodies" })).toBeInTheDocument();
    expect(screen.getByText("Partial install")).toBeInTheDocument();
  });

  it("shows the active municipal SSO session in the staff dashboard", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Signed in with municipal SSO" })).toBeInTheDocument();
    expect(screen.getByText("clerk@example.gov")).toBeInTheDocument();
    expect(screen.getByText("Brookfield Entra ID")).toBeInTheDocument();
    expect(screen.getByText("oidc browser session")).toBeInTheDocument();
    expect(screen.getByText("clerk admin")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign out" })).toHaveAttribute("href", "/staff/logout");
    expect(screen.getByRole("link", { name: "IT auth readiness" })).toHaveAttribute("href", "/staff/auth-readiness");
  });

  it("gives clerks and IT an actionable path when staff session verification fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url === "/staff/session") {
          return Promise.resolve({
            ok: false,
            status: 401,
            json: async () => ({
              detail: {
                message: "Staff browser session is missing or expired.",
                fix: "Sign in again or ask IT to verify OIDC browser login configuration.",
              },
            }),
          });
        }
        if (url === "/api/meeting-bodies") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              meeting_bodies: [{ id: "body-1", name: "City Council", body_type: "city_council", is_active: true }],
            }),
          });
        }
        if (url === "/api/meetings") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              meetings: [{
                id: "meeting-1",
                title: "Regular Meeting",
                meeting_type: "regular",
                meeting_body_id: "body-1",
                status: "SCHEDULED",
                scheduled_start: "2026-05-05T18:00:00Z",
                location: "Council Chambers",
              }],
            }),
          });
        }
        if (url === "/api/agenda-intake") {
          return Promise.resolve({ ok: true, json: async () => ({ items: [] }) });
        }
        if (url === "/api/meetings/meeting-1/packet-assemblies") {
          return Promise.resolve({ ok: true, json: async () => ({ packet_assemblies: [] }) });
        }
        if (url === "/api/meetings/meeting-1/notice-checklists") {
          return Promise.resolve({ ok: true, json: async () => ({ notice_checklists: [] }) });
        }
        if (url === "/api/meetings/meeting-1/motions") {
          return Promise.resolve({ ok: true, json: async () => ({ motions: [] }) });
        }
        if (url === "/api/meetings/meeting-1/action-items") {
          return Promise.resolve({ ok: true, json: async () => ({ action_items: [] }) });
        }
        if (url === "/api/meetings/meeting-1/minutes/drafts") {
          return Promise.resolve({ ok: true, json: async () => ({ drafts: [] }) });
        }
        if (url === "/api/public/meetings") {
          return Promise.resolve({ ok: true, json: async () => ({ meetings: [] }) });
        }
        return Promise.resolve({ ok: true, json: async () => ({}) });
      }),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Staff sign-in needed" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Staff browser session is missing or expired");
    expect(screen.getByRole("alert")).toHaveTextContent("Sign in again or ask IT to verify OIDC browser login configuration");
    expect(screen.getByRole("alert")).toHaveTextContent("/staff/auth-readiness");
    expect(screen.getByRole("link", { name: "Sign in with municipal SSO" })).toHaveAttribute("href", "/staff/login");
  });

  it("routes clerks from the meeting runbook into the next safe workspace", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Meeting runbook" })).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Open next runbook action: Notice legally proved" }));

    expect(await screen.findByRole("heading", { name: "Prove statutory public notice before the meeting proceeds." })).toBeInTheDocument();
    expect(screen.getByText(/The checklist is the city record that proves public notice/)).toBeInTheDocument();
  });

  it("creates, updates, and deactivates meeting bodies from the staff dashboard", async () => {
    render(<App />);

    expect(await screen.findByLabelText("Rename City Council")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Body name"), { target: { value: "Library Board" } });
    fireEvent.change(screen.getByLabelText("Body type"), { target: { value: "board" } });
    fireEvent.click(screen.getByRole("button", { name: "Create meeting body" }));
    expect(await screen.findByText("Meeting body created. It is now available for scheduling.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Rename City Council"), { target: { value: "Brookfield City Council" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Save name" })[0]);
    expect(await screen.findByText("Meeting body updated without changing its record identity.")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Deactivate" })[0]);
    expect(await screen.findByText("Brookfield City Council was deactivated. Existing meeting history is preserved.")).toBeInTheDocument();
  });

  it("schedules a meeting from the staff dashboard", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Schedule a meeting" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Meeting body"), { target: { value: "body-2" } });
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Library Board Regular Meeting" } });
    fireEvent.change(screen.getByLabelText("Starts"), { target: { value: "2026-05-10T18:00" } });
    fireEvent.change(screen.getByLabelText("Location"), { target: { value: "Library Community Room" } });
    fireEvent.click(screen.getByRole("button", { name: "Schedule meeting" }));

    expect(await screen.findByText("Meeting scheduled. It now appears on the staff calendar and can be opened for detail work.")).toBeInTheDocument();
  });

  it("edits a meeting schedule from the detail workspace", async () => {
    render(<App />);

    await screen.findByRole("heading", { name: "Good morning, City Clerk." });
    fireEvent.click(screen.getByRole("button", { name: /Meetings/ }));
    fireEvent.click(screen.getAllByRole("button", { name: /City Council/ })[0]);

    expect(screen.getByRole("heading", { name: "Edit schedule" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Updated Regular Meeting" } });
    fireEvent.change(screen.getByLabelText("Meeting body"), { target: { value: "body-2" } });
    fireEvent.change(screen.getByLabelText("Type"), { target: { value: "special" } });
    fireEvent.change(screen.getByLabelText("Starts"), { target: { value: "2026-05-08T19:00" } });
    fireEvent.change(screen.getByLabelText("Location"), { target: { value: "Room 204" } });
    fireEvent.click(screen.getByRole("button", { name: "Save schedule" }));

    expect(await screen.findByText("Meeting schedule updated. The audit trail records who changed the scheduling fields.")).toBeInTheDocument();
  });

  it("submits and reviews agenda intake from the staff workspace", async () => {
    render(<App />);

    await screen.findByRole("heading", { name: "Good morning, City Clerk." });
    fireEvent.click(screen.getByRole("button", { name: /Agenda intake/ }));

    expect(screen.getByRole("heading", { name: "Department requests, clerk decisions." })).toBeInTheDocument();
    expect(screen.getByText("Approve zoning study")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Agenda title"), { target: { value: "Approve downtown zoning study" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit to review queue" }));
    expect(await screen.findByText("Agenda item submitted. It is now in the clerk review queue with audit provenance.")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Mark ready" })[1]);
    expect(await screen.findByText("Marked ready for clerk packet work. The audit hash changed for this review.")).toBeInTheDocument();
  });

  it("promotes a ready agenda intake item into agenda lifecycle work", async () => {
    render(<App />);

    await screen.findByRole("heading", { name: "Good morning, City Clerk." });
    fireEvent.click(screen.getByRole("button", { name: /Agenda intake/ }));
    fireEvent.click(screen.getByRole("button", { name: "Mark ready" }));
    expect(await screen.findByText("Marked ready for clerk packet work. The audit hash changed for this review.")).toBeInTheDocument();

    fireEvent.click(await screen.findByRole("button", { name: "Promote to agenda" }));

    expect(await screen.findByText(/Agenda item agenda-77 is now CLERK_ACCEPTED/)).toBeInTheDocument();
    expect(screen.getByText(/Next step: Add the agenda item to the target meeting packet assembly/)).toBeInTheDocument();
    expect(screen.getByText(/Agenda lifecycle: agenda-77 promoted/)).toBeInTheDocument();
  });

  it("creates and finalizes a packet assembly from promoted agenda work", async () => {
    render(<App />);

    await screen.findByRole("heading", { name: "Good morning, City Clerk." });
    fireEvent.click(screen.getByRole("button", { name: /Packet builder/ }));

    expect(screen.getByRole("heading", { name: "Assemble packet evidence before posting." })).toBeInTheDocument();
    expect(screen.getByText("Adopt annual fee schedule - Finance")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Create packet draft" }));
    expect(await screen.findByText(/Packet draft packet-1 created at version 1/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Finalize packet" }));
    expect(await screen.findByText(/Packet packet-1 finalized with audit hash def456def456/)).toBeInTheDocument();
    expect(screen.getByText("Ready for notice checklist")).toBeInTheDocument();
  });

  it("runs notice compliance and attaches posting proof only after a passing check", async () => {
    render(<App />);

    await screen.findByRole("heading", { name: "Good morning, City Clerk." });
    fireEvent.click(screen.getByRole("button", { name: /Notice checklist/ }));

    expect(screen.getByRole("heading", { name: "Prove statutory public notice before the meeting proceeds." })).toBeInTheDocument();
    expect(screen.getByText(/The checklist is the city record that proves public notice/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Official notice record" })).toBeInTheDocument();
    expect(screen.getByText(/Not legally noticed yet/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Legal readiness proof chain" })).toBeInTheDocument();
    expect(screen.getAllByText("Packet finalized").length).toBeGreaterThan(0);
    expect(screen.getByText("Statutory deadline met")).toBeInTheDocument();
    expect(screen.getByText("Human approval recorded")).toBeInTheDocument();
    expect(screen.getByText(/Computed deadline/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Run notice checklist" }));
    expect(await screen.findByText(/Notice checklist notice-1 passed/)).toBeInTheDocument();
    expect(screen.getByText(/Attach posting proof before treating notice as posted/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Attach posting proof" }));
    expect(await screen.findByText(/Posting proof attached for notice-1/)).toBeInTheDocument();
    expect(screen.getByText(/immutable audit hash proof123456/)).toBeInTheDocument();
    expect(screen.getByText(/Meeting may proceed to posted-public-meeting steps/)).toBeInTheDocument();
    expect(screen.getByText("Proceed allowed")).toBeInTheDocument();
  });

  it("plainly blocks posting proof when the statutory notice deadline has passed", async () => {
    render(<App />);

    await screen.findByRole("heading", { name: "Good morning, City Clerk." });
    fireEvent.click(screen.getByRole("button", { name: /Notice checklist/ }));
    fireEvent.change(screen.getByLabelText("Minimum notice hours"), { target: { value: "200" } });
    fireEvent.click(screen.getByRole("button", { name: "Run notice checklist" }));

    expect(await screen.findByText(/statutory deadline was/)).toBeInTheDocument();
    expect(screen.getByRole("alert", { name: "Notice legal blocker" })).toHaveTextContent("Statutory notice is blocked");
    expect(screen.getByText(/Meeting cannot proceed as lawfully noticed/)).toBeInTheDocument();
    expect(screen.getByText("Proceed blocked")).toBeInTheDocument();
    expect(screen.getByText(/Deadline missed: required by/)).toBeInTheDocument();
    expect(screen.getByText(/You cannot attach posting proof until this is corrected/)).toBeInTheDocument();
    expect(screen.getAllByText(/Reschedule the meeting or document the lawful emergency basis/).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole("button", { name: "Attach posting proof" })).toBeDisabled();
  });

  it("shows each official notice proof obligation before legal proof is complete", async () => {
    render(<App />);

    await screen.findByRole("heading", { name: "Good morning, City Clerk." });
    expect(await screen.findByRole("heading", { name: "Signed in with municipal SSO" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Notice checklist/ }));

    expect(await screen.findByRole("heading", { name: "Official notice record" })).toBeInTheDocument();
    expect(screen.getAllByText("Proof incomplete").length).toBeGreaterThan(0);
    expect(screen.getByText("Finalized packet available before notice proof.")).toBeInTheDocument();
    expect(screen.getByText(/Computed deadline/)).toBeInTheDocument();
    expect(screen.getByText("Missing statutory basis. Enter the law, ordinance, or emergency/special basis.")).toBeInTheDocument();
    expect(screen.getByText("No clerk or authorized approver recorded yet.")).toBeInTheDocument();
    expect(screen.getByText("No public URL or physical posting location attached yet.")).toBeInTheDocument();
    expect(screen.getByText("No audit hash visible yet.")).toBeInTheDocument();
    expect(screen.getAllByText("Packet finalized").length).toBeGreaterThan(0);
    expect(screen.getByText("Statutory deadline met")).toBeInTheDocument();
    expect(screen.getByText("Human approval")).toBeInTheDocument();
    expect(screen.getByText("Posting proof")).toBeInTheDocument();
  });

  it("shows resident-safe public posted meeting records and archive search", async () => {
    render(<App />);

    await screen.findByRole("heading", { name: "Good morning, City Clerk." });
    fireEvent.click(screen.getByRole("button", { name: /Public posting/ }));

    expect(screen.getByRole("heading", { name: "Find posted meetings without needing to understand clerk workflows." })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Official meeting materials, in one place." })).toBeInTheDocument();
    expect(screen.getByText(/Restricted or closed-session material is never exposed/)).toBeInTheDocument();
    expect(screen.getByText("What residents can do here")).toBeInTheDocument();
    expect(screen.getAllByText("Agenda: approve sidewalk repairs.")).toHaveLength(2);
    expect(screen.getByText("Packet: staff report and fiscal note.")).toBeInTheDocument();
    expect(screen.getByText(/This portal does not reveal restricted-session existence/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Search public records" }));
    expect(await screen.findByText(/1 public record matched/)).toBeInTheDocument();
    expect(screen.getAllByText("Packet: staff report and fiscal note.")).toHaveLength(2);
    expect(screen.getAllByRole("button", { name: "Open public record" }).length).toBeGreaterThan(0);
  });

  it("opens the resident public portal directly from the /public product route", async () => {
    window.history.replaceState({}, "", "/public");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Find posted meetings without needing to understand clerk workflows." })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Good morning, City Clerk." })).not.toBeInTheDocument();
    expect(screen.getByText(/Only public archive API records appear here/)).toBeInTheDocument();
  });

  it("opens the React staff dashboard directly from the /staff product route", async () => {
    window.history.replaceState({}, "", "/staff");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Good morning, City Clerk." })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Meeting runbook" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Find posted meetings without needing to understand clerk workflows." })).not.toBeInTheDocument();
  });

  it("captures motions, votes, and action items from the meeting outcomes workspace", async () => {
    render(<App />);

    await screen.findByRole("heading", { name: "Good morning, City Clerk." });
    fireEvent.click(screen.getByRole("button", { name: /Outcomes/ }));

    expect(screen.getByRole("heading", { name: "Capture motions, roll-call votes, and follow-up actions." })).toBeInTheDocument();
    expect(screen.getByText(/Motions and votes are immutable/)).toBeInTheDocument();
    expect(await screen.findAllByText("Move to approve sidewalk repairs.")).toHaveLength(2);
    expect(screen.getByText("Council Member Patel: aye")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Capture motion" }));
    expect(await screen.findByText(/Motion motion-1 captured as an immutable meeting outcome/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Record vote" }));
    expect(await screen.findByText(/Vote vote-1 captured for Council Member Rivera/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Create action item" }));
    expect(await screen.findByText(/Action item action-1 opened for Clerk's Office/)).toBeInTheDocument();
    expect(screen.getAllByText(/Staff to prepare the signed resolution/)).toHaveLength(2);
  });

  it("keeps meeting outcomes visibly append-only and source-linked", async () => {
    render(<App />);

    await screen.findByRole("heading", { name: "Good morning, City Clerk." });
    fireEvent.click(screen.getByRole("button", { name: /Outcomes/ }));

    expect(screen.getByRole("heading", { name: "Outcome ledger" })).toBeInTheDocument();
    expect(screen.getByText("Append-only")).toBeInTheDocument();
    expect(screen.getByText(/Motions and votes are immutable/)).toBeInTheDocument();
    expect(await screen.findAllByText("Move to approve sidewalk repairs.")).toHaveLength(2);
    expect(screen.getByText(/Motion ID: motion-existing/)).toBeInTheDocument();
    expect(screen.getByLabelText("Votes for Move to approve sidewalk repairs.")).toHaveTextContent("Council Member Patel: aye");
    expect(screen.getByText(/action items linked/)).toBeInTheDocument();
  });

  it("creates citation-gated minutes drafts and shows the human posting gate", async () => {
    render(<App />);

    await screen.findByRole("heading", { name: "Good morning, City Clerk." });
    fireEvent.click(screen.getByRole("button", { name: /Minutes/ }));

    expect(screen.getByRole("heading", { name: "Create cited minutes without letting AI become the official record." })).toBeInTheDocument();
    expect(screen.getByText(/Every sentence must point back to source material/)).toBeInTheDocument();
    expect(await screen.findByText("Council approved sidewalk repairs.")).toBeInTheDocument();
    expect(screen.getByText(/Prompt minutes_draft@0.1.0 via ollama\/gemma4/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Create cited draft" }));
    expect(await screen.findByText(/Draft minutes-1 created with 2 cited sentences/)).toBeInTheDocument();
    expect(screen.getAllByText(/AI-drafted minutes cannot be auto-posted/).length).toBeGreaterThan(0);

    fireEvent.click(screen.getAllByRole("button", { name: "Try public posting gate" })[0]);
    expect(await screen.findByText(/AI-drafted minutes cannot be posted automatically/)).toBeInTheDocument();
    expect(screen.getByText(/human approval workflow/)).toBeInTheDocument();
  });

  it("blocks minutes draft creation when any material sentence lacks a citation", async () => {
    render(<App />);

    await screen.findByRole("heading", { name: "Good morning, City Clerk." });
    fireEvent.click(screen.getByRole("button", { name: /Minutes/ }));
    expect(screen.getByText(/Every sentence must point back to source material/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Citations for sentence 2"), { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "Create cited draft" }));

    expect(await screen.findByRole("status")).toHaveTextContent("every material sentence needs at least one citation");
    expect(screen.getByRole("status")).toHaveTextContent("Add a source ID to each citation field");
    expect(screen.getByText("Human approval required")).toBeInTheDocument();
  });

  it("opens the meeting calendar and a meeting detail workspace", async () => {
    render(<App />);

    await screen.findByRole("heading", { name: "Good morning, City Clerk." });
    expect(await screen.findByRole("heading", { name: "Signed in with municipal SSO" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Meetings/ }));
    expect(await screen.findByRole("heading", { name: "May 2026 clerk calendar" })).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: /City Council/ })[0]);
    expect(await screen.findByRole("heading", { name: "Regular Meeting" })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Meeting lifecycle stages" })).toBeInTheDocument();
  });

  it("shows actionable error and empty states for frontend QA", async () => {
    window.history.replaceState({}, "", "/?state=success&source=demo");
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "error" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Confirm the backend is running");
    expect(screen.getByRole("button", { name: "Retry after checking API" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "empty" }));
    expect(screen.getByRole("status")).toHaveTextContent("Create a meeting body");
  });

  it("toggles the audit evidence drawer", async () => {
    window.history.replaceState({}, "", "/?source=demo");
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Show audit" }));
    expect(screen.getByLabelText("Audit and evidence drawer")).toHaveTextContent("Agenda published");
  });

  it("supports direct URL entry into QA states for browser evidence", () => {
    window.history.replaceState({}, "", "/?page=agenda&state=partial&audit=1&source=demo");
    render(<App />);

    expect(screen.getByRole("status")).toHaveTextContent("agenda intake is partially available");
    expect(screen.getByLabelText("Audit and evidence drawer")).toBeInTheDocument();
  });

  it("shows an actionable API error when live meeting loading fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
      }),
    );

    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Meeting API returned 503");
    expect(screen.getByRole("button", { name: "Retry after checking API" })).toBeInTheDocument();
  });

  it("keeps the staff shell usable when only packet assembly loading fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string) => {
        if (url === "/api/meeting-bodies") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              meeting_bodies: [{ id: "body-1", name: "City Council", body_type: "city_council", is_active: true }],
            }),
          });
        }
        if (url === "/api/meetings") {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              meetings: [{
                id: "meeting-1",
                title: "Regular Meeting",
                meeting_type: "regular",
                meeting_body_id: "body-1",
                status: "SCHEDULED",
                scheduled_start: "2026-05-05T18:00:00Z",
                location: "Council Chambers",
              }],
            }),
          });
        }
        if (url === "/api/agenda-intake") {
          return Promise.resolve({
            ok: true,
            json: async () => ({ items: [] }),
          });
        }
        if (url === "/api/meetings/meeting-1/packet-assemblies") {
          return Promise.resolve({ ok: false, status: 503 });
        }
        if (url === "/api/meetings/meeting-1/notice-checklists") {
          return Promise.resolve({
            ok: true,
            json: async () => ({ notice_checklists: [] }),
          });
        }
        return Promise.resolve({ ok: true, json: async () => ({}) });
      }),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Good morning, City Clerk." })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Packet builder/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Packet assembly API returned 503");
  });
});
