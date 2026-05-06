"""CC-7 API and frontend completeness contract."""

from __future__ import annotations

from dataclasses import dataclass


REQUIRED_VIEW_STATES = ("loading", "success", "empty", "error", "partial")


@dataclass(frozen=True)
class ApiCategory:
    id: str
    label: str
    paths: tuple[str, ...]
    protected: bool
    auth_scope: str = "staff-only"


@dataclass(frozen=True)
class FrontendPage:
    id: str
    label: str
    surface: str
    evidence_states: tuple[str, ...] = REQUIRED_VIEW_STATES


CC7_API_CATEGORIES: tuple[ApiCategory, ...] = (
    ApiCategory(
        id="meeting-bodies",
        label="Meeting bodies",
        protected=True,
        paths=("/meeting-bodies", "/meeting-bodies/{body_id}"),
    ),
    ApiCategory(
        id="meetings",
        label="Meetings",
        protected=True,
        paths=("/meetings", "/meetings/{meeting_id}", "/meetings/{meeting_id}/transitions"),
    ),
    ApiCategory(
        id="agenda-items",
        label="Agenda items",
        protected=True,
        paths=("/agenda-items", "/agenda-items/{item_id}", "/agenda-intake", "/agenda-intake/{item_id}/promote"),
    ),
    ApiCategory(
        id="staff-reports",
        label="Staff reports",
        protected=True,
        paths=("/meetings/{meeting_id}/staff-reports",),
    ),
    ApiCategory(
        id="packets",
        label="Packets",
        protected=True,
        paths=(
            "/meetings/{meeting_id}/packet-snapshots",
            "/meetings/{meeting_id}/packet-assemblies",
            "/packet-assemblies/{record_id}/finalize",
            "/meetings/{meeting_id}/export-bundle",
        ),
    ),
    ApiCategory(
        id="notices-postings",
        label="Notices and postings",
        protected=True,
        paths=(
            "/meetings/{meeting_id}/notices/check",
            "/meetings/{meeting_id}/notice-checklists",
            "/notice-checklists/{record_id}/posting-proof",
            "/meetings/{meeting_id}/notices/post",
        ),
    ),
    ApiCategory(
        id="motions",
        label="Motions",
        protected=True,
        paths=("/meetings/{meeting_id}/motions", "/motions/{motion_id}/corrections"),
    ),
    ApiCategory(
        id="votes",
        label="Votes",
        protected=True,
        paths=("/motions/{motion_id}/votes", "/votes/{vote_id}/corrections"),
    ),
    ApiCategory(
        id="minutes",
        label="Minutes",
        protected=True,
        paths=("/meetings/{meeting_id}/minutes/drafts", "/minutes/{minute_id}/post"),
    ),
    ApiCategory(
        id="transcripts",
        label="Transcripts",
        protected=True,
        paths=("/meetings/{meeting_id}/transcripts",),
    ),
    ApiCategory(
        id="public-comments",
        label="Public comments",
        protected=False,
        auth_scope="mixed: public intake plus protected staff review queue",
        paths=("/public/meetings/{record_id}/comments", "/public-comments/review-queue"),
    ),
    ApiCategory(
        id="action-items",
        label="Action items",
        protected=True,
        paths=("/meetings/{meeting_id}/action-items",),
    ),
    ApiCategory(
        id="ordinance-resolution-handoff",
        label="Ordinance and resolution handoff",
        protected=True,
        paths=("/meetings/{meeting_id}/ordinance-resolution-handoff",),
    ),
    ApiCategory(
        id="archive-search",
        label="Archive search",
        protected=False,
        auth_scope="public search with optional CivicCore archive bearer expansion",
        paths=("/public/archive/search",),
    ),
    ApiCategory(
        id="admin-prompt-config",
        label="Admin prompt and configuration surfaces",
        protected=True,
        paths=("/admin/config", "/admin/prompts", "/integrations/readiness"),
    ),
    ApiCategory(
        id="connector-import-admin",
        label="Connector and import admin",
        protected=True,
        paths=("/imports/{connector_name}/meetings", "/vendor-live-sync/sources"),
    ),
)


CC7_FRONTEND_PAGES: tuple[FrontendPage, ...] = (
    FrontendPage("staff-dashboard", "Staff dashboard", "staff"),
    FrontendPage("meeting-calendar", "Meeting calendar", "staff"),
    FrontendPage("meeting-detail", "Meeting detail", "staff"),
    FrontendPage("agenda-builder", "Agenda builder", "staff"),
    FrontendPage("agenda-intake", "Agenda item intake", "staff"),
    FrontendPage("staff-report-editor", "Staff report editor", "staff"),
    FrontendPage("packet-builder", "Packet builder", "staff"),
    FrontendPage("notice-checklist", "Notice checklist and posting proof", "staff"),
    FrontendPage("live-meeting-capture", "Live meeting capture", "staff"),
    FrontendPage("minutes-review", "Minutes drafting and review", "staff"),
    FrontendPage("motions-votes-actions", "Motions, votes, and action items", "staff"),
    FrontendPage("transcript-management", "Transcript management", "staff"),
    FrontendPage("public-comment-review", "Public comment review", "staff"),
    FrontendPage("closed-session-workspace", "Closed-session staff-only workspace", "staff"),
    FrontendPage("archive-search", "Archive search", "staff-public"),
    FrontendPage("public-calendar", "Public meeting calendar", "resident"),
    FrontendPage("public-detail", "Public meeting detail", "resident"),
    FrontendPage("admin-settings", "Admin settings", "admin"),
    FrontendPage("prompt-library-admin", "Prompt library admin", "admin"),
    FrontendPage("connector-import-admin", "Connector and import admin", "admin"),
)


def cc7_api_category_payload() -> list[dict[str, object]]:
    return [
        {
            "id": category.id,
            "label": category.label,
            "paths": list(category.paths),
            "protected": category.protected,
            "auth_scope": category.auth_scope,
        }
        for category in CC7_API_CATEGORIES
    ]


def cc7_frontend_page_payload() -> list[dict[str, object]]:
    return [
        {
            "id": page.id,
            "label": page.label,
            "surface": page.surface,
            "evidence_states": list(page.evidence_states),
        }
        for page in CC7_FRONTEND_PAGES
    ]


__all__ = [
    "CC7_API_CATEGORIES",
    "CC7_FRONTEND_PAGES",
    "REQUIRED_VIEW_STATES",
    "cc7_api_category_payload",
    "cc7_frontend_page_payload",
]
