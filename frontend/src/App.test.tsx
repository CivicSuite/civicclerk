import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

describe("CivicClerk staff workspace", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockImplementation((url: string, init?: RequestInit) => {
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
    expect(await screen.findByRole("heading", { name: "Meeting bodies" })).toBeInTheDocument();
    expect(screen.getByText("Partial install")).toBeInTheDocument();
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

  it("opens the meeting calendar and a meeting detail workspace", async () => {
    render(<App />);

    await screen.findByRole("heading", { name: "Good morning, City Clerk." });
    fireEvent.click(screen.getByRole("button", { name: /Meetings/ }));
    expect(screen.getByRole("heading", { name: "May 2026 clerk calendar" })).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: /City Council/ })[0]);
    expect(screen.getByRole("heading", { name: "Regular Meeting" })).toBeInTheDocument();
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
    window.history.replaceState({}, "", "/?page=meeting-detail&state=partial&audit=1&source=demo");
    render(<App />);

    expect(screen.getByRole("status")).toHaveTextContent("meeting detail is partially available");
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
});
