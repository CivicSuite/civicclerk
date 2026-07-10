import { expect, test, type Page, type Route } from "@playwright/test";

const meetingOne = {
  id: "meeting-1",
  title: "Regular Meeting",
  meeting_type: "regular",
  meeting_body_id: "body-1",
  status: "PACKET_POSTED",
  scheduled_start: "2026-05-05T18:00:00Z",
  location: "Council Chambers",
};

async function fulfillJson(route: Route, payload: unknown, status = 200) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(payload),
  });
}

async function installCivicMeetingsApiMocks(page: Page) {
  await page.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();

    if (path === "/staff/session") {
      return fulfillJson(route, {
        mode: "oidc",
        authenticated: true,
        auth_method: "oidc_browser_session",
        subject: "clerk@example.gov",
        provider: "Brookfield Entra ID",
        roles: ["clerk_admin", "meeting_editor"],
        message: "Staff browser session is active.",
        fix: "Continue with clerk workflow actions.",
      });
    }

    if (path === "/api/meeting-bodies") {
      return fulfillJson(route, {
        meeting_bodies: [
          { id: "body-1", name: "City Council", body_type: "city_council", is_active: true },
          { id: "body-2", name: "Planning Commission", body_type: "commission", is_active: true },
        ],
      });
    }

    if (path === "/api/meetings") {
      return fulfillJson(route, {
        meetings: [
          meetingOne,
          {
            id: "meeting-2",
            title: "Special Session",
            meeting_type: "special",
            meeting_body_id: "body-2",
            status: "NOTICED",
            scheduled_start: "2026-05-07T18:00:00Z",
            location: "Room 204",
          },
        ],
      });
    }

    if (path === "/api/agenda-intake") {
      if (method === "POST") {
        return fulfillJson(route, {
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
        });
      }
      return fulfillJson(route, {
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
        ],
      });
    }

    if (path === "/api/agenda-intake/intake-1/review" && method === "POST") {
      return fulfillJson(route, {
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
      });
    }

    if (path === "/api/meetings/meeting-1/packet-assemblies") {
      return fulfillJson(route, {
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
      });
    }

    if (path === "/api/meetings/meeting-1/notice-checklists") {
      if (method === "POST") {
        return fulfillJson(route, {
          id: "notice-1",
          meeting_id: "meeting-1",
          notice_type: "regular",
          status: "CHECKED",
          compliant: true,
          http_status: 200,
          warnings: [],
          deadline_at: "2026-05-02T18:00:00Z",
          posted_at: "2026-05-01T18:00:00Z",
          minimum_notice_hours: 72,
          statutory_basis: "Local open meeting law requires posted notice.",
          approved_by: "clerk@example.gov",
          posting_proof: null,
          last_audit_hash: "notice1234567890notice1234567890notice1234567890notice123456abcd",
          created_at: "2026-05-01T12:30:00Z",
          updated_at: "2026-05-01T12:30:00Z",
        });
      }
      return fulfillJson(route, { notice_checklists: [] });
    }

    if (path === "/api/notice-checklists/notice-1/posting-proof" && method === "POST") {
      return fulfillJson(route, {
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
      });
    }

    if (path === "/api/meetings/meeting-1/motions") {
      return fulfillJson(route, { motions: [] });
    }
    if (path === "/api/meetings/meeting-1/action-items") {
      return fulfillJson(route, { action_items: [] });
    }
    if (path === "/api/meetings/meeting-1/minutes/drafts") {
      return fulfillJson(route, { drafts: [] });
    }
    if (path === "/api/public/meetings") {
      return fulfillJson(route, {
        total_count: 1,
        meetings: [
          {
            id: "public-1",
            meeting_id: "meeting-1",
            title: "City Council Regular Meeting",
            posted_agenda: "Agenda: approve sidewalk repairs.",
            posted_packet: "Packet: staff report and fiscal note.",
            approved_minutes: "Approved minutes: motion passed 5-0.",
            public_comment_enabled: true,
            plain_language_summary: "Council will decide whether to advance sidewalk repairs.",
            agenda_download_url: "/api/public/meetings/public-1/agenda.txt",
            packet_download_url: "/api/public/meetings/public-1/packet.txt",
            minutes_download_url: "/api/public/meetings/public-1/minutes.txt",
            minutes_adopted_at: "2026-05-12T19:30:00Z",
            minutes_signed_by: "City Clerk",
          },
        ],
      });
    }
    if (path === "/api/public/archive/search") {
      return fulfillJson(route, {
        total_count: 1,
        results: [
          {
            id: "public-1",
            meeting_id: "meeting-1",
            title: "City Council Regular Meeting",
            posted_agenda: "Agenda: approve sidewalk repairs.",
            posted_packet: "Packet: staff report and fiscal note.",
            approved_minutes: "Approved minutes: motion passed 5-0.",
            public_comment_enabled: true,
            plain_language_summary: "Council will decide whether to advance sidewalk repairs.",
            agenda_download_url: "/api/public/meetings/public-1/agenda.txt",
            packet_download_url: "/api/public/meetings/public-1/packet.txt",
            minutes_download_url: "/api/public/meetings/public-1/minutes.txt",
            minutes_adopted_at: "2026-05-12T19:30:00Z",
            minutes_signed_by: "City Clerk",
          },
        ],
        suggestions: [],
      });
    }
    if (path === "/api/vendor-live-sync/sources") {
      return fulfillJson(route, { sources: [] });
    }
    if (path === "/api/integrations/readiness") {
      return fulfillJson(route, {
        readiness: "ready",
        proof_model: "live_or_in_process_boundary_validation",
        network_calls: true,
        dependent_modules_required: true,
        message: "CivicMeetings integration depth requires live-wire or in-process boundary validation.",
        fix: "Keep adversarial mocks as regression coverage.",
        contracts: [],
      });
    }

    return route.continue();
  });
}

test.beforeEach(async ({ page }) => {
  await installCivicMeetingsApiMocks(page);
});

test("clerk proves public notice from dashboard to posting proof", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Good morning, City Clerk." })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Signed in with municipal SSO" })).toBeVisible();

  await page.getByRole("button", { name: /Notice checklist/ }).click();
  await expect(page.getByRole("heading", { name: "Prove statutory public notice before the meeting proceeds." })).toBeVisible();
  await page.getByRole("button", { name: "Run notice checklist" }).click();
  await expect(page.getByText(/Notice checklist notice-1 passed/)).toBeVisible();
  await page.getByRole("button", { name: "Attach posting proof" }).click();
  await expect(page.getByText(/Posting proof attached for notice-1/)).toBeVisible();
  await expect(page.getByText("Proceed allowed")).toBeVisible();
  await expect(page.locator("main")).toHaveAttribute("data-current-page", "notice-checklist");
  expect(consoleErrors).toEqual([]);
});

test("unauthenticated first-run staff shell gates protected APIs without repeated 401 noise", async ({ page }) => {
  const consoleErrors: string[] = [];
  let staffSessionRequests = 0;
  let protectedApiRequests = 0;

  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/staff/session") {
      staffSessionRequests += 1;
      return fulfillJson(route, {
        detail: {
          message: "Staff browser session is missing or expired.",
          fix: "Sign in again or ask IT to verify OIDC browser login configuration.",
        },
      }, 401);
    }
    if (url.pathname.startsWith("/api/")) {
      protectedApiRequests += 1;
      return fulfillJson(route, {
        detail: {
          message: "Protected API should stay behind the staff session gate.",
          fix: "Sign in before loading protected clerk data.",
        },
      }, 500);
    }
    return route.fallback();
  });

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Staff sign-in needed" })).toBeVisible();
  await expect(page.getByRole("alert")).toContainText("Staff browser session is missing or expired");
  await expect(page.getByRole("link", { name: "Sign in with municipal SSO" })).toHaveAttribute("href", "/staff/login");
  expect(staffSessionRequests).toBe(1);
  expect(protectedApiRequests).toBe(0);
  expect(consoleErrors.filter((text) => text.includes("401") || text.includes("/staff/session")).length).toBeLessThanOrEqual(1);
});

test("resident public posting stays public and avoids closed-session leakage", async ({ page }) => {
  await page.goto("/?page=public-calendar");
  await expect(page.getByRole("heading", { name: "Find posted meetings without needing to understand clerk workflows." })).toBeVisible();
  await expect(page.getByRole("heading", { name: "City Council Regular Meeting" }).first()).toBeVisible();
  await expect(page.getByText(/Restricted or closed-session material is never exposed/)).toBeVisible();
  await expect(page.getByRole("link", { name: "Download agenda" })).toHaveAttribute("href", "/api/public/meetings/public-1/agenda.txt");
  await page.getByRole("button", { name: "Search public records" }).click();
  await expect(page.getByText(/1 public record matched/)).toBeVisible();
  await expect(page.getByText(/executive session personnel discussion/i)).toHaveCount(0);
});
