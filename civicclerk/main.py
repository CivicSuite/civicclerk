"""FastAPI runtime foundation for CivicClerk."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from civiccore.auth import (
    AuthenticatedPrincipal,
    authorize_bearer_roles,
    parse_token_role_map,
    authorize_trusted_header_roles,
    enforce_trusted_proxy_source,
    load_trusted_header_auth_config,
    resolve_optional_bearer_roles,
)
from civiccore.security import normalize_trusted_proxy_cidrs
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from civicclerk import __version__
from civicclerk.agenda_intake import AgendaIntakeRepository
from civicclerk.agenda_lifecycle import AgendaItemRepository, AgendaItemStore
from civicclerk.connectors import ConnectorImportError, import_meeting_payload
from civicclerk.meeting_lifecycle import MeetingStore
from civicclerk.minutes import MinutesDraftStore, MinutesSentence, SourceMaterial
from civicclerk.motion_vote import MotionVoteStore
from civicclerk.notice_checklist import NoticeChecklistRepository
from civicclerk.packet_assembly import PacketAssemblyRepository
from civicclerk.packet_notice import (
    NoticeStore,
    PacketExportError,
    PacketSource,
    PacketStore,
    evaluate_notice_compliance,
)
from civicclerk.public_archive import PublicArchiveStore, can_view_closed_sessions
from civicclerk.staff_ui import render_staff_dashboard
from civiccore import __version__ as CIVICCORE_VERSION

app = FastAPI(
    title="CivicClerk",
    version=__version__,
    summary="Runtime foundation for CivicClerk municipal meeting workflows.",
)

agenda_items = AgendaItemStore()
meetings = MeetingStore()
packet_snapshots = PacketStore()
notices = NoticeStore()
motion_votes = MotionVoteStore()
minutes_drafts = MinutesDraftStore()
public_archive = PublicArchiveStore()
_archive_search_bearer = HTTPBearer(auto_error=False)
STAFF_AUTH_MODE_ENV_VAR = "CIVICCLERK_STAFF_AUTH_MODE"
STAFF_AUTH_TOKEN_ROLES_ENV_VAR = "CIVICCLERK_STAFF_AUTH_TOKEN_ROLES"
STAFF_AUTH_SSO_PROVIDER_ENV_VAR = "CIVICCLERK_STAFF_SSO_PROVIDER"
STAFF_AUTH_SSO_PRINCIPAL_HEADER_ENV_VAR = "CIVICCLERK_STAFF_SSO_PRINCIPAL_HEADER"
STAFF_AUTH_SSO_ROLES_HEADER_ENV_VAR = "CIVICCLERK_STAFF_SSO_ROLES_HEADER"
STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR = "CIVICCLERK_STAFF_SSO_TRUSTED_PROXIES"
STAFF_OPEN_MODE = "open"
STAFF_BEARER_MODE = "bearer"
STAFF_TRUSTED_HEADER_MODE = "trusted_header"
DEFAULT_STAFF_SSO_PROVIDER = "trusted reverse proxy"
DEFAULT_STAFF_SSO_PRINCIPAL_HEADER = "X-Forwarded-Email"
DEFAULT_STAFF_SSO_ROLES_HEADER = "X-Forwarded-Roles"
LOCAL_TRUSTED_HEADER_PROXY_SCRIPT_PATH = "scripts/local_trusted_header_proxy.py"
LOCAL_TRUSTED_HEADER_PROXY_UPSTREAM_ENV_VAR = "CIVICCLERK_LOCAL_PROXY_UPSTREAM"
LOCAL_TRUSTED_HEADER_PROXY_LISTEN_HOST_ENV_VAR = "CIVICCLERK_LOCAL_PROXY_LISTEN_HOST"
LOCAL_TRUSTED_HEADER_PROXY_LISTEN_PORT_ENV_VAR = "CIVICCLERK_LOCAL_PROXY_LISTEN_PORT"
LOCAL_TRUSTED_HEADER_PROXY_PRINCIPAL_ENV_VAR = "CIVICCLERK_LOCAL_PROXY_PRINCIPAL"
LOCAL_TRUSTED_HEADER_PROXY_ROLES_ENV_VAR = "CIVICCLERK_LOCAL_PROXY_ROLES"
LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_PROVIDER = "local trusted-header rehearsal proxy"
LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_HOST = "127.0.0.1"
LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_PORT = 8010
LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_UPSTREAM = "http://127.0.0.1:8000"
LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_PRINCIPAL = "clerk@example.gov"
LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_ROLES = "clerk_admin,meeting_editor"
LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_TRUSTED_PROXY = "127.0.0.1/32"
TRUSTED_PROXY_REFERENCE_CONFIG_PATH = "docs/examples/trusted-header-nginx.conf"
STAFF_ALLOWED_ROLES = frozenset({"clerk_admin", "clerk_editor", "meeting_editor", "city_attorney"})
_agenda_intake_repository: AgendaIntakeRepository | None = None
_agenda_intake_db_url: str | None = None
_agenda_item_repository: AgendaItemRepository | None = None
_agenda_item_db_url: str | None = None
_packet_assembly_repository: PacketAssemblyRepository | None = None
_packet_assembly_db_url: str | None = None
_notice_checklist_repository: NoticeChecklistRepository | None = None
_notice_checklist_db_url: str | None = None
_meeting_store: MeetingStore | None = None
_meeting_db_url: str | None = None


@app.middleware("http")
async def enforce_staff_api_access(request: Request, call_next):
    """Protect internal staff APIs when bearer mode is enabled."""

    try:
        mode = _get_staff_auth_mode()
    except HTTPException as exc:
        payload = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content={"detail": payload})

    if not _is_staff_protected_path(request.url.path) or mode == STAFF_OPEN_MODE:
        return await call_next(request)

    try:
        request.state.staff_principal = _authorize_staff_principal(request)
    except HTTPException as exc:
        payload = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": payload},
            headers=exc.headers or None,
        )

    return await call_next(request)


class AgendaItemCreate(BaseModel):
    title: str = Field(min_length=1)
    department_name: str = Field(min_length=1)


class AgendaItemTransitionRequest(BaseModel):
    to_status: str = Field(min_length=1)
    actor: str = Field(min_length=1)


class AgendaIntakeCreate(BaseModel):
    title: str = Field(min_length=1)
    department_name: str = Field(min_length=1)
    submitted_by: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    source_references: list[dict] = Field(min_length=1)


class AgendaIntakeReviewRequest(BaseModel):
    reviewer: str = Field(min_length=1)
    ready: bool
    notes: str = Field(min_length=1)


class MeetingCreate(BaseModel):
    title: str = Field(min_length=1)
    meeting_type: str = Field(min_length=1)
    scheduled_start: str | None = None


class MeetingTransitionRequest(BaseModel):
    to_status: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    statutory_basis: str | None = Field(default=None, min_length=1)


class PacketSnapshotCreate(BaseModel):
    agenda_item_ids: list[str] = Field(min_length=1)
    actor: str = Field(min_length=1)


class PacketAssemblyCreate(BaseModel):
    title: str = Field(min_length=1)
    agenda_item_ids: list[str] = Field(min_length=1)
    actor: str = Field(min_length=1)
    source_references: list[dict] = Field(min_length=1)
    citations: list[dict] = Field(min_length=1)


class PacketAssemblyFinalizeRequest(BaseModel):
    actor: str = Field(min_length=1)


class PacketSourceCreate(BaseModel):
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    kind: str = Field(default="document", min_length=1)
    source_system: str | None = Field(default=None, min_length=1)
    source_path: str | None = Field(default=None, min_length=1)
    checksum: str | None = Field(default=None, min_length=1)
    sensitivity_label: str | None = Field(default=None, min_length=1)
    citation_label: str | None = Field(default=None, min_length=1)


class PacketExportCreate(BaseModel):
    bundle_name: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    sources: list[PacketSourceCreate] = Field(min_length=1)
    public_bundle: bool = True


class NoticeComplianceRequest(BaseModel):
    notice_type: str = Field(min_length=1)
    posted_at: datetime
    minimum_notice_hours: int = Field(gt=0)
    statutory_basis: str | None = Field(default=None, min_length=1)
    approved_by: str | None = Field(default=None, min_length=1)


class NoticeChecklistCreate(NoticeComplianceRequest):
    actor: str = Field(min_length=1)


class NoticePostingProofCreate(BaseModel):
    actor: str = Field(min_length=1)
    posting_proof: dict = Field(min_length=1)


class MotionCreate(BaseModel):
    text: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    agenda_item_id: str | None = Field(default=None, min_length=1)


class MotionCorrectionCreate(BaseModel):
    text: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class VoteCreate(BaseModel):
    voter_name: str = Field(min_length=1)
    vote: str = Field(min_length=1)
    actor: str = Field(min_length=1)


class VoteCorrectionCreate(BaseModel):
    vote: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class ActionItemCreate(BaseModel):
    description: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    assigned_to: str | None = Field(default=None, min_length=1)
    source_motion_id: str | None = Field(default=None, min_length=1)


class SourceMaterialCreate(BaseModel):
    source_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    text: str = Field(min_length=1)


class MinutesSentenceCreate(BaseModel):
    text: str = Field(min_length=1)
    citations: list[str] = Field(default_factory=list)


class MinutesDraftCreate(BaseModel):
    model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    human_approver: str = Field(min_length=1)
    source_materials: list[SourceMaterialCreate] = Field(min_length=1)
    sentences: list[MinutesSentenceCreate] = Field(min_length=1)


class PublicMeetingRecordCreate(BaseModel):
    title: str = Field(min_length=1)
    visibility: str = Field(min_length=1)
    posted_agenda: str = Field(min_length=1)
    posted_packet: str = Field(min_length=1)
    approved_minutes: str = Field(min_length=1)
    closed_session_notes: str | None = Field(default=None, min_length=1)


@app.get("/")
async def root() -> dict[str, str]:
    """Describe what the runtime foundation currently provides."""
    return {
        "name": "CivicClerk",
        "status": f"v{__version__} runtime foundation release",
        "message": (
            "CivicClerk agenda item, meeting lifecycle, packet snapshot, and notice compliance "
            "enforcement are online with immutable motion, vote, action-item, and citation-gated "
            "minutes draft capture plus permission-aware public calendar and archive endpoints; "
            "prompt YAML and offline evaluation gates protect policy-bearing prompt changes; "
            "local-first Granicus, Legistar, PrimeGov, and NovusAGENDA imports now normalize "
            f"source provenance; CivicCore v{CIVICCORE_VERSION} packet export bundles now include manifests, "
            "checksums, provenance, and hash-chained audit evidence; "
            "CivicClerk notice checks now reuse the shared CivicCore notice compliance helper while preserving "
            "meeting-specific warning and posting flows; "
            "accessibility and browser QA "
            "gates now verify loading, success, empty, error, partial, keyboard, focus, contrast, "
            "and console evidence; the first database-backed agenda intake queue now supports "
            "department submission, clerk readiness review, and durable audit-hash evidence; "
            "database-backed packet assembly records now tie packet versions to source files, "
            "citations, and durable audit-hash evidence; "
            "database-backed notice checklist records now persist compliance checks and posting "
            "proof metadata; "
            "staff workflow screens now guide agenda intake, packet assembly, and notice checklist "
            "work with visible rendered states and actionable next steps; "
            "the staff agenda intake screen can now submit items and record readiness review "
            "through the live API; "
            "packet assembly and notice checklist staff screens can now create/finalize packet "
            "records and persist posting proof through live API actions; "
            "meeting outcome staff screens can now capture motions, votes, and action items "
            "through live API actions; "
            "minutes draft staff screens can now create citation-gated draft records through "
            "live API actions; "
            "public archive staff screens can now publish public-safe records and verify "
            "anonymous archive visibility through live API actions; "
            "connector import staff screens can now normalize local agenda-platform exports "
            "through live API actions; "
            "packet export staff screens can now create records-ready bundles with manifests "
            "and checksums through live API actions; "
            "meeting records can now persist through the configured meeting database; "
            f"CivicClerk is versioned as v{__version__} with the production-depth service slices included; "
            "staff workflow APIs now support a local-open rehearsal mode, a bearer-protected bridge mode, "
            "and a trusted-header reverse-proxy mode with a required trusted-proxy CIDR allowlist, "
            "with the /staff screen showing the current access "
            "state while full OIDC login remains future work; "
            "all current production-depth clerk-console form submissions are live for the released "
            "API foundation, while the full integrated clerk console remains future work."
        ),
        "next_step": "Production-depth consolidation and next CivicSuite module planning",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    """Provide a simple operational health check for IT staff."""
    return {
        "status": "ok",
        "service": "civicclerk",
        "version": __version__,
        "civiccore": CIVICCORE_VERSION,
    }


@app.get("/favicon.ico", response_class=Response)
async def favicon() -> Response:
    """Return an empty public favicon response so browser QA stays console-clean."""
    return Response(status_code=204)


@app.get("/staff", response_class=HTMLResponse)
async def staff_dashboard() -> str:
    """Render the staff-facing workflow foundation."""
    return render_staff_dashboard()


@app.get("/staff/session")
async def staff_session(request: Request) -> dict[str, object]:
    """Describe the current staff access mode for the browser workflow shell."""

    mode = _get_staff_auth_mode()
    if mode == STAFF_OPEN_MODE:
        return {
            "mode": STAFF_OPEN_MODE,
            "authenticated": True,
            "roles": ["open_access"],
            "message": "Staff workflow access is running in local open mode.",
            "fix": (
                f"Set {STAFF_AUTH_MODE_ENV_VAR}={STAFF_BEARER_MODE} and configure "
                f"{STAFF_AUTH_TOKEN_ROLES_ENV_VAR}, or switch to "
                f"{STAFF_AUTH_MODE_ENV_VAR}={STAFF_TRUSTED_HEADER_MODE} behind a trusted reverse proxy."
            ),
        }

    principal = getattr(request.state, "staff_principal", None)
    if principal is None:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Staff session principal is missing.",
                "fix": "Retry the request with a configured bearer token or review staff auth middleware setup.",
            },
        )

    response: dict[str, object] = {
        "mode": mode,
        "authenticated": True,
        "roles": sorted(principal.roles),
        "token_fingerprint": principal.token_fingerprint,
        "auth_method": principal.auth_method,
    }
    if principal.subject:
        response["subject"] = principal.subject
    if principal.provider:
        response["provider"] = principal.provider
    if mode == STAFF_BEARER_MODE:
        response["message"] = "Bearer token accepted for staff workflow access."
        response["fix"] = (
            "Keep this token scoped to clerk workflow roles until the trusted-header SSO bridge is ready."
        )
        return response

    trusted_header_config = _get_staff_trusted_header_config()
    response["message"] = "Trusted staff identity accepted from the configured reverse proxy."
    response["fix"] = (
        f"Keep {trusted_header_config.provider_name} stripping client-supplied copies of "
        f"{trusted_header_config.principal_header_name} and {trusted_header_config.roles_header_name} "
        "before CivicClerk."
    )
    response["principal_header"] = trusted_header_config.principal_header_name
    response["roles_header"] = trusted_header_config.roles_header_name
    return response


@app.get("/staff/auth-readiness")
async def staff_auth_readiness() -> dict[str, object]:
    """Report whether the current staff auth mode is configured for safe use."""

    mode = _get_staff_auth_mode()
    if mode == STAFF_OPEN_MODE:
        return {
            "mode": STAFF_OPEN_MODE,
            "ready": True,
            "deployment_ready": False,
            "checks": [
                {
                    "name": "staff auth mode",
                    "status": "configured",
                    "value": STAFF_OPEN_MODE,
                },
                {
                    "name": "deployment posture",
                    "status": "warning",
                    "value": "local rehearsal only",
                },
            ],
            "message": "Local open mode is ready for rehearsal, but not for real staff deployment.",
            "fix": (
                f"Set {STAFF_AUTH_MODE_ENV_VAR}={STAFF_BEARER_MODE} with "
                f"{STAFF_AUTH_TOKEN_ROLES_ENV_VAR}, or switch to "
                f"{STAFF_AUTH_MODE_ENV_VAR}={STAFF_TRUSTED_HEADER_MODE} behind a trusted reverse proxy."
            ),
        }
    if mode == STAFF_BEARER_MODE:
        return _get_staff_bearer_auth_readiness()
    return _get_staff_trusted_header_readiness()


@app.post("/agenda-items", status_code=201)
async def create_agenda_item(payload: AgendaItemCreate) -> dict[str, str]:
    """Create a draft agenda item for lifecycle enforcement."""
    return _get_agenda_items().create(
        title=payload.title,
        department_name=payload.department_name,
    ).public_dict()


@app.get("/agenda-items/{item_id}")
async def get_agenda_item(item_id: str) -> dict[str, str]:
    """Return the current agenda item state."""
    item = _get_agenda_items().get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Agenda item not found.")
    return item.public_dict()


@app.post("/agenda-items/{item_id}/transitions")
async def transition_agenda_item(
    item_id: str,
    payload: AgendaItemTransitionRequest,
) -> dict[str, str]:
    """Apply a canonical agenda item lifecycle transition."""
    store = _get_agenda_items()
    item = store.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Agenda item not found.")
    result = store.transition(
        item_id=item_id,
        to_status=payload.to_status,
        actor=payload.actor,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Agenda item not found.")
    if not result.allowed:
        raise HTTPException(
            status_code=result.http_status,
            detail={
                "message": result.message,
                "current_status": item.status,
                "requested_status": payload.to_status,
            },
        )
    updated = store.get(item_id)
    return (updated or item).public_dict()


@app.get("/agenda-items/{item_id}/audit")
async def get_agenda_item_audit(item_id: str) -> dict[str, list[dict[str, str]]]:
    """Return lifecycle audit entries for an agenda item."""
    item = _get_agenda_items().get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Agenda item not found.")
    return {"entries": item.audit_entries}


@app.post("/agenda-intake", status_code=201)
async def submit_agenda_intake_item(payload: AgendaIntakeCreate) -> dict:
    """Submit a department agenda item into the database-backed staff queue."""
    item = _get_agenda_intake_repository().submit(
        title=payload.title,
        department_name=payload.department_name,
        submitted_by=payload.submitted_by,
        summary=payload.summary,
        source_references=payload.source_references,
    )
    return item.public_dict()


@app.get("/agenda-intake")
async def list_agenda_intake_items(readiness_status: str | None = None) -> dict[str, list[dict]]:
    """List department-submitted agenda intake items awaiting staff review."""
    return {
        "items": [
            item.public_dict()
            for item in _get_agenda_intake_repository().list_queue(
                readiness_status=readiness_status,
            )
        ]
    }


@app.post("/agenda-intake/{item_id}/review")
async def review_agenda_intake_item(
    item_id: str,
    payload: AgendaIntakeReviewRequest,
) -> dict:
    """Record clerk readiness review for an intake queue item."""
    item = _get_agenda_intake_repository().review(
        item_id=item_id,
        reviewer=payload.reviewer,
        ready=payload.ready,
        notes=payload.notes,
    )
    if item is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Agenda intake item not found.",
                "fix": "Submit the agenda item into the intake queue before review.",
            },
        )
    return item.public_dict()


@app.post("/meetings", status_code=201)
async def create_meeting(payload: MeetingCreate) -> dict[str, str]:
    """Create a scheduled meeting for lifecycle enforcement."""
    return _get_meeting_store().create(
        title=payload.title,
        meeting_type=payload.meeting_type,
        scheduled_start=_parse_timezone_aware_datetime(
            payload.scheduled_start,
            field_name="scheduled_start",
        ),
    ).public_dict()


@app.get("/meetings/{meeting_id}")
async def get_meeting(meeting_id: str) -> dict[str, str]:
    """Return the current meeting state."""
    meeting = _get_meeting_store().get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return meeting.public_dict()


@app.post("/meetings/{meeting_id}/transitions")
async def transition_meeting(
    meeting_id: str,
    payload: MeetingTransitionRequest,
) -> dict[str, str]:
    """Apply a canonical meeting lifecycle transition."""
    meeting = _get_meeting_store().get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    result = _get_meeting_store().transition(
        meeting_id=meeting_id,
        to_status=payload.to_status,
        actor=payload.actor,
        statutory_basis=payload.statutory_basis,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    if not result.allowed:
        raise HTTPException(
            status_code=result.http_status,
            detail={
                "message": result.message,
                "current_status": meeting.status,
                "requested_status": payload.to_status,
            },
        )
    updated_meeting = _get_meeting_store().get(meeting_id)
    if updated_meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return updated_meeting.public_dict()


@app.get("/meetings/{meeting_id}/audit")
async def get_meeting_audit(meeting_id: str) -> dict[str, list[dict[str, str]]]:
    """Return lifecycle audit entries for a meeting."""
    meeting = _get_meeting_store().get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return {"entries": meeting.audit_entries}


@app.post("/meetings/{meeting_id}/packet-snapshots", status_code=201)
async def create_packet_snapshot(
    meeting_id: str,
    payload: PacketSnapshotCreate,
) -> dict:
    """Create an immutable packet snapshot version for a meeting."""
    meeting = _get_meeting_store().get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return packet_snapshots.create_snapshot(
        meeting_id=meeting_id,
        agenda_item_ids=payload.agenda_item_ids,
        actor=payload.actor,
    ).public_dict()


@app.get("/meetings/{meeting_id}/packet-snapshots")
async def list_packet_snapshots(meeting_id: str) -> dict[str, list[dict]]:
    """Return packet snapshot versions for a meeting."""
    meeting = _get_meeting_store().get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return {
        "snapshots": [
            snapshot.public_dict()
            for snapshot in packet_snapshots.list_snapshots(meeting_id)
        ]
    }


@app.post("/meetings/{meeting_id}/packet-assemblies", status_code=201)
async def create_packet_assembly_record(
    meeting_id: str,
    payload: PacketAssemblyCreate,
) -> dict:
    """Create a persisted packet assembly record tied to a packet snapshot."""
    meeting = _get_meeting_store().get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    snapshot = packet_snapshots.create_snapshot(
        meeting_id=meeting_id,
        agenda_item_ids=payload.agenda_item_ids,
        actor=payload.actor,
    )
    return _get_packet_assembly_repository().create_draft(
        meeting_id=meeting_id,
        packet_snapshot_id=snapshot.id,
        packet_version=snapshot.version,
        title=payload.title,
        actor=payload.actor,
        agenda_item_ids=payload.agenda_item_ids,
        source_references=payload.source_references,
        citations=payload.citations,
    ).public_dict()


@app.get("/meetings/{meeting_id}/packet-assemblies")
async def list_packet_assembly_records(meeting_id: str) -> dict[str, list[dict]]:
    """List persisted packet assembly records for a meeting."""
    meeting = _get_meeting_store().get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return {
        "packet_assemblies": [
            record.public_dict()
            for record in _get_packet_assembly_repository().list_for_meeting(meeting_id)
        ]
    }


@app.post("/packet-assemblies/{record_id}/finalize")
async def finalize_packet_assembly_record(
    record_id: str,
    payload: PacketAssemblyFinalizeRequest,
) -> dict:
    """Finalize a persisted packet assembly record."""
    record = _get_packet_assembly_repository().finalize(
        record_id=record_id,
        actor=payload.actor,
    )
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Packet assembly record not found.",
                "fix": "Create the packet assembly record before finalizing it.",
            },
        )
    return record.public_dict()


@app.post("/meetings/{meeting_id}/export-bundle", status_code=201)
async def create_packet_export_bundle(
    meeting_id: str,
    payload: PacketExportCreate,
) -> dict:
    """Create a records-ready packet export bundle with manifest, checksums, and audit."""
    meeting = _get_meeting_store().get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    try:
        return packet_snapshots.create_export_bundle(
            meeting_id=meeting_id,
            meeting_title=meeting.title,
            bundle_path=_resolve_packet_export_path(payload.bundle_name),
            actor=payload.actor,
            sources=[
                PacketSource(
                    source_id=source.source_id,
                    title=source.title,
                    kind=source.kind,
                    source_system=source.source_system,
                    source_path=source.source_path,
                    checksum=source.checksum,
                    sensitivity_label=source.sensitivity_label,
                    citation_label=source.citation_label,
                )
                for source in payload.sources
            ],
            notices=[notice.public_dict() for notice in notices.list_notices(meeting_id)],
            public_bundle=payload.public_bundle,
        ).public_dict()
    except PacketExportError as error:
        raise HTTPException(status_code=error.http_status, detail=error.public_dict()) from error


@app.post("/meetings/{meeting_id}/notices/check")
async def check_notice_compliance(
    meeting_id: str,
    payload: NoticeComplianceRequest,
) -> dict:
    """Check public notice compliance without posting."""
    result = _evaluate_notice_or_404(meeting_id, payload)
    if not result.compliant:
        raise HTTPException(
            status_code=result.http_status,
            detail={
                "message": "Notice is not ready for public posting. Review the warnings and fix each item.",
                "warnings": result.warnings,
            },
        )
    return result.public_dict()


@app.post("/meetings/{meeting_id}/notice-checklists", status_code=201)
async def create_notice_checklist_record(
    meeting_id: str,
    payload: NoticeChecklistCreate,
) -> dict:
    """Persist a notice compliance checklist record for staff review."""
    result = _evaluate_notice_or_404(meeting_id, payload)
    return _get_notice_checklist_repository().record_check(
        meeting_id=meeting_id,
        notice_type=result.notice_type,
        compliant=result.compliant,
        http_status=result.http_status,
        warnings=result.warnings,
        deadline_at=result.deadline_at,
        posted_at=result.posted_at,
        minimum_notice_hours=result.minimum_notice_hours,
        statutory_basis=result.statutory_basis,
        approved_by=result.approved_by,
        actor=payload.actor,
    ).public_dict()


@app.get("/meetings/{meeting_id}/notice-checklists")
async def list_notice_checklist_records(meeting_id: str) -> dict[str, list[dict]]:
    """List persisted notice checklist records for a meeting."""
    meeting = _get_meeting_store().get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return {
        "notice_checklists": [
            record.public_dict()
            for record in _get_notice_checklist_repository().list_for_meeting(meeting_id)
        ]
    }


@app.post("/notice-checklists/{record_id}/posting-proof")
async def attach_notice_posting_proof(
    record_id: str,
    payload: NoticePostingProofCreate,
) -> dict:
    """Attach posting proof metadata to a persisted notice checklist record."""
    record = _get_notice_checklist_repository().attach_posting_proof(
        record_id=record_id,
        actor=payload.actor,
        posting_proof=payload.posting_proof,
    )
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": "Notice checklist record not found.",
                "fix": "Create the notice checklist record before attaching posting proof.",
            },
        )
    return record.public_dict()


@app.post("/meetings/{meeting_id}/notices/post", status_code=201)
async def post_notice(
    meeting_id: str,
    payload: NoticeComplianceRequest,
) -> dict:
    """Post a public notice after deadline and human-approval checks pass."""
    result = _evaluate_notice_or_404(meeting_id, payload)
    if not result.compliant:
        raise HTTPException(
            status_code=result.http_status,
            detail={
                "message": "Notice cannot be posted publicly. Review the warnings and fix each item.",
                "warnings": result.warnings,
            },
        )
    return notices.create(result).public_dict()


@app.post("/meetings/{meeting_id}/motions", status_code=201)
async def capture_motion(meeting_id: str, payload: MotionCreate) -> dict:
    """Capture an immutable motion for a meeting."""
    meeting = _get_meeting_store().get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return motion_votes.capture_motion(
        meeting_id=meeting_id,
        agenda_item_id=payload.agenda_item_id,
        text=payload.text,
        actor=payload.actor,
    ).public_dict()


@app.get("/meetings/{meeting_id}/motions")
async def list_motions(meeting_id: str) -> dict[str, list[dict]]:
    """List captured motions and correction records for a meeting."""
    meeting = _get_meeting_store().get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return {
        "motions": [
            motion.public_dict()
            for motion in motion_votes.list_motions(meeting_id)
        ]
    }


@app.put("/motions/{motion_id}")
@app.patch("/motions/{motion_id}")
async def reject_motion_mutation(motion_id: str) -> None:
    """Reject edits to captured motions; corrections must be append-only."""
    if motion_votes.get_motion(motion_id) is None:
        raise HTTPException(status_code=404, detail="Motion not found.")
    raise HTTPException(
        status_code=409,
        detail={
            "message": "Captured motions are immutable.",
            "fix": "Use POST /motions/{motion_id}/corrections to add a correction record that references the original motion.",
        },
    )


@app.post("/motions/{motion_id}/corrections", status_code=201)
async def correct_motion(motion_id: str, payload: MotionCorrectionCreate) -> dict:
    """Create an append-only correction record for a captured motion."""
    correction = motion_votes.correct_motion(
        original_motion_id=motion_id,
        text=payload.text,
        actor=payload.actor,
        reason=payload.reason,
    )
    if correction is None:
        raise HTTPException(status_code=404, detail="Motion not found.")
    return correction.public_dict()


@app.post("/motions/{motion_id}/votes", status_code=201)
async def capture_vote(motion_id: str, payload: VoteCreate) -> dict:
    """Capture an immutable vote for a motion."""
    if motion_votes.get_motion(motion_id) is None:
        raise HTTPException(status_code=404, detail="Motion not found.")
    return motion_votes.capture_vote(
        motion_id=motion_id,
        voter_name=payload.voter_name,
        vote=payload.vote,
        actor=payload.actor,
    ).public_dict()


@app.get("/motions/{motion_id}/votes")
async def list_votes(motion_id: str) -> dict[str, list[dict]]:
    """List captured votes and correction records for a motion."""
    if motion_votes.get_motion(motion_id) is None:
        raise HTTPException(status_code=404, detail="Motion not found.")
    return {
        "votes": [
            vote.public_dict()
            for vote in motion_votes.list_votes(motion_id)
        ]
    }


@app.put("/votes/{vote_id}")
@app.patch("/votes/{vote_id}")
async def reject_vote_mutation(vote_id: str) -> None:
    """Reject edits to captured votes; corrections must be append-only."""
    if motion_votes.get_vote(vote_id) is None:
        raise HTTPException(status_code=404, detail="Vote not found.")
    raise HTTPException(
        status_code=409,
        detail={
            "message": "Captured votes are immutable.",
            "fix": "Use POST /votes/{vote_id}/corrections to add a correction record that references the original vote.",
        },
    )


@app.post("/votes/{vote_id}/corrections", status_code=201)
async def correct_vote(vote_id: str, payload: VoteCorrectionCreate) -> dict:
    """Create an append-only correction record for a captured vote."""
    correction = motion_votes.correct_vote(
        original_vote_id=vote_id,
        vote=payload.vote,
        actor=payload.actor,
        reason=payload.reason,
    )
    if correction is None:
        raise HTTPException(status_code=404, detail="Vote not found.")
    return correction.public_dict()


@app.post("/meetings/{meeting_id}/action-items", status_code=201)
async def create_action_item(meeting_id: str, payload: ActionItemCreate) -> dict:
    """Create an action item linked to a meeting outcome."""
    meeting = _get_meeting_store().get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    if payload.source_motion_id is None:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Action items must reference a captured meeting outcome.",
                "fix": "Capture the related motion first, then send its id as source_motion_id.",
            },
        )
    source_motion = motion_votes.get_motion(payload.source_motion_id)
    if source_motion is None:
        raise HTTPException(status_code=404, detail="Source motion not found.")
    if source_motion.meeting_id != meeting_id:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Action item source motion belongs to a different meeting.",
                "fix": "Use a motion captured for this meeting as source_motion_id.",
            },
        )
    return motion_votes.create_action_item(
        meeting_id=meeting_id,
        description=payload.description,
        assigned_to=payload.assigned_to,
        source_motion_id=payload.source_motion_id,
        actor=payload.actor,
    ).public_dict()


@app.get("/meetings/{meeting_id}/action-items")
async def list_action_items(meeting_id: str) -> dict[str, list[dict]]:
    """List action items linked to a meeting."""
    meeting = _get_meeting_store().get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return {
        "action_items": [
            action_item.public_dict()
            for action_item in motion_votes.list_action_items(meeting_id)
        ]
    }


@app.post("/meetings/{meeting_id}/minutes/drafts", status_code=201)
async def create_minutes_draft(meeting_id: str, payload: MinutesDraftCreate) -> dict:
    """Create an AI-assisted minutes draft only when every sentence is cited."""
    meeting = _get_meeting_store().get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    result = minutes_drafts.create_draft(
        meeting_id=meeting_id,
        model=payload.model,
        prompt_version=payload.prompt_version,
        human_approver=payload.human_approver,
        source_materials=[
            SourceMaterial(
                source_id=source.source_id,
                label=source.label,
                text=source.text,
            )
            for source in payload.source_materials
        ],
        sentences=[
            MinutesSentence(
                text=sentence.text,
                citations=tuple(sentence.citations),
            )
            for sentence in payload.sentences
        ],
    )
    if not hasattr(result, "public_dict"):
        raise HTTPException(
            status_code=422,
            detail={
                "message": result.message,
                "fix": result.fix,
            },
        )
    return result.public_dict()


@app.get("/meetings/{meeting_id}/minutes/drafts")
async def list_minutes_drafts(meeting_id: str) -> dict[str, list[dict]]:
    """List citation-gated minutes drafts for a meeting."""
    meeting = _get_meeting_store().get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return {
        "drafts": [
            draft.public_dict()
            for draft in minutes_drafts.list_drafts(meeting_id)
        ]
    }


@app.post("/minutes/{minute_id}/post")
async def reject_automatic_minutes_posting(minute_id: str) -> None:
    """Reject automatic public posting of AI-drafted minutes."""
    if minutes_drafts.get_draft(minute_id) is None:
        raise HTTPException(status_code=404, detail="Minutes draft not found.")
    raise HTTPException(
        status_code=409,
        detail={
            "message": "AI-drafted minutes cannot be posted automatically.",
            "fix": "Review, cite-check, and adopt minutes through a human approval workflow before public posting.",
        },
    )


@app.post("/meetings/{meeting_id}/public-record", status_code=201)
async def publish_public_record(
    meeting_id: str,
    payload: PublicMeetingRecordCreate,
) -> dict:
    """Create a public or restricted archive record for a meeting."""
    meeting = _get_meeting_store().get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    record = public_archive.publish(
        meeting_id=meeting_id,
        title=payload.title,
        visibility=payload.visibility,
        posted_agenda=payload.posted_agenda,
        posted_packet=payload.posted_packet,
        approved_minutes=payload.approved_minutes,
        closed_session_notes=payload.closed_session_notes,
    )
    return record.public_dict()


@app.post("/imports/{connector_name}/meetings", status_code=201)
async def import_connector_meeting(connector_name: str, payload: dict) -> dict:
    """Import a local connector export payload without outbound network calls."""
    try:
        return import_meeting_payload(
            connector_name=connector_name,
            payload=payload,
        ).public_dict()
    except ConnectorImportError as error:
        status_code = 404 if connector_name.strip().lower() not in {
            "granicus",
            "legistar",
            "novusagenda",
            "primegov",
        } else 422
        raise HTTPException(status_code=status_code, detail=error.public_dict()) from error


@app.get("/public/meetings")
async def public_meetings() -> dict[str, int | list[dict]]:
    """Return public meeting calendar records only."""
    records = [record.public_dict() for record in public_archive.public_calendar()]
    return {
        "total_count": len(records),
        "meetings": records,
    }


@app.get("/public/meetings/{record_id}")
async def public_meeting_detail(record_id: str) -> dict:
    """Return one public meeting record without revealing restricted records."""
    record = public_archive.public_detail(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Public meeting record not found.")
    return record.public_dict()


@app.get("/public/archive/search")
async def public_archive_search(
    q: str,
    credentials: HTTPAuthorizationCredentials | None = Depends(_archive_search_bearer),
) -> dict[str, int | list[dict]]:
    """Search public archives with permission-aware closed-session filtering."""
    principal = _resolve_archive_search_principal(credentials)
    include_closed = principal is not None and can_view_closed_sessions(principal.roles)
    results = [
        record.public_dict(include_closed=include_closed)
        for record in public_archive.search(query=q, include_closed=include_closed)
    ]
    return {
        "total_count": len(results),
        "results": results,
        "suggestions": [],
    }


def _resolve_archive_search_principal(
    credentials: HTTPAuthorizationCredentials | None,
) -> AuthenticatedPrincipal | None:
    return resolve_optional_bearer_roles(
        credentials,
        service_name="CivicClerk",
        feature_name="archive search staff access",
        token_roles_env_var="CIVICCLERK_AUTH_TOKEN_ROLES",
        allowed_roles={"archive_reader", "clerk_admin", "city_attorney"},
    )


def _authorize_staff_principal(request: Request) -> AuthenticatedPrincipal:
    mode = _get_staff_auth_mode()
    if mode == STAFF_BEARER_MODE:
        authorization = request.headers.get("authorization", "").strip()
        credentials: HTTPAuthorizationCredentials | None = None
        if authorization:
            scheme, _, token = authorization.partition(" ")
            credentials = HTTPAuthorizationCredentials(
                scheme=scheme,
                credentials=token.strip(),
            )
        return authorize_bearer_roles(
            credentials,
            service_name="CivicClerk",
            feature_name="staff workflow access",
            token_roles_env_var=STAFF_AUTH_TOKEN_ROLES_ENV_VAR,
            allowed_roles=STAFF_ALLOWED_ROLES,
        )
    if mode == STAFF_TRUSTED_HEADER_MODE:
        trusted_header_config = _get_staff_trusted_header_config()
        enforce_trusted_proxy_source(
            request.client.host if request.client is not None else None,
            service_name="CivicClerk",
            feature_name="staff workflow access",
            config=trusted_header_config,
            trusted_proxy_env_var=STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR,
        )
        return authorize_trusted_header_roles(
            request.headers,
            service_name="CivicClerk",
            feature_name="staff workflow access",
            principal_header_name=trusted_header_config.principal_header_name,
            roles_header_name=trusted_header_config.roles_header_name,
            allowed_roles=STAFF_ALLOWED_ROLES,
            provider_name=trusted_header_config.provider_name,
        )
    raise HTTPException(
        status_code=500,
        detail={
            "message": "Staff auth mode was not resolved before principal authorization.",
            "fix": f"Set {STAFF_AUTH_MODE_ENV_VAR} to a supported value and retry.",
        },
    )


def _get_staff_auth_mode() -> str:
    raw_mode = os.environ.get(STAFF_AUTH_MODE_ENV_VAR, STAFF_OPEN_MODE).strip().lower()
    if raw_mode in {STAFF_OPEN_MODE, STAFF_BEARER_MODE, STAFF_TRUSTED_HEADER_MODE}:
        return raw_mode
    raise HTTPException(
        status_code=503,
        detail={
            "message": "CivicClerk staff auth mode is invalid.",
            "fix": (
                f"Set {STAFF_AUTH_MODE_ENV_VAR} to '{STAFF_OPEN_MODE}' for local rehearsal "
                f"or '{STAFF_BEARER_MODE}' for bearer-protected staff APIs, "
                f"or '{STAFF_TRUSTED_HEADER_MODE}' for trusted reverse-proxy SSO headers."
            ),
        },
    )


def _get_staff_trusted_header_config():
    return load_trusted_header_auth_config(
        provider_env_var=STAFF_AUTH_SSO_PROVIDER_ENV_VAR,
        provider_default=DEFAULT_STAFF_SSO_PROVIDER,
        principal_header_env_var=STAFF_AUTH_SSO_PRINCIPAL_HEADER_ENV_VAR,
        principal_header_default=DEFAULT_STAFF_SSO_PRINCIPAL_HEADER,
        roles_header_env_var=STAFF_AUTH_SSO_ROLES_HEADER_ENV_VAR,
        roles_header_default=DEFAULT_STAFF_SSO_ROLES_HEADER,
        trusted_proxy_env_var=STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR,
    )


def _get_local_trusted_header_proxy_rehearsal(
    *,
    principal_header_name: str,
    roles_header_name: str,
) -> dict[str, object]:
    listen_url = (
        f"http://{LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_HOST}:"
        f"{LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_PORT}"
    )
    return {
        "scope": "loopback_only",
        "script_path": LOCAL_TRUSTED_HEADER_PROXY_SCRIPT_PATH,
        "listen_url": listen_url,
        "upstream_url": LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_UPSTREAM,
        "trusted_proxy_cidrs": [LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_TRUSTED_PROXY],
        "command": [
            "python",
            LOCAL_TRUSTED_HEADER_PROXY_SCRIPT_PATH,
            "--upstream",
            LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_UPSTREAM,
            "--listen-host",
            LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_HOST,
            "--listen-port",
            str(LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_PORT),
        ],
        "app_env": {
            STAFF_AUTH_MODE_ENV_VAR: STAFF_TRUSTED_HEADER_MODE,
            STAFF_AUTH_SSO_PROVIDER_ENV_VAR: LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_PROVIDER,
            STAFF_AUTH_SSO_PRINCIPAL_HEADER_ENV_VAR: principal_header_name,
            STAFF_AUTH_SSO_ROLES_HEADER_ENV_VAR: roles_header_name,
            STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR: LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_TRUSTED_PROXY,
        },
        "proxy_env": {
            LOCAL_TRUSTED_HEADER_PROXY_UPSTREAM_ENV_VAR: LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_UPSTREAM,
            LOCAL_TRUSTED_HEADER_PROXY_LISTEN_HOST_ENV_VAR: LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_HOST,
            LOCAL_TRUSTED_HEADER_PROXY_LISTEN_PORT_ENV_VAR: str(
                LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_PORT
            ),
            LOCAL_TRUSTED_HEADER_PROXY_PRINCIPAL_ENV_VAR: LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_PRINCIPAL,
            LOCAL_TRUSTED_HEADER_PROXY_ROLES_ENV_VAR: LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_ROLES,
        },
        "headers": {
            principal_header_name: LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_PRINCIPAL,
            roles_header_name: LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_ROLES,
        },
        "steps": [
            "Start CivicClerk on loopback with the app_env values shown here.",
            "Run the helper command on the same workstation to inject placeholder trusted headers.",
            "Browse or call the helper listen_url instead of the upstream URL so the backend only trusts loopback proxy traffic.",
        ],
        "warnings": [
            "This helper is for localhost rehearsal only and does not terminate TLS or manage an identity provider.",
            "The helper strips client-supplied trusted identity headers before forwarding to CivicClerk.",
        ],
    }


def _get_staff_bearer_auth_readiness() -> dict[str, object]:
    raw_value = os.environ.get(STAFF_AUTH_TOKEN_ROLES_ENV_VAR, "").strip()
    token_map = (
        parse_token_role_map(raw_value, env_var=STAFF_AUTH_TOKEN_ROLES_ENV_VAR)
        if raw_value
        else {}
    )
    if not token_map:
        return {
            "mode": STAFF_BEARER_MODE,
            "ready": False,
            "deployment_ready": False,
            "checks": [
                {
                    "name": "staff auth mode",
                    "status": "configured",
                    "value": STAFF_BEARER_MODE,
                },
                {
                    "name": STAFF_AUTH_TOKEN_ROLES_ENV_VAR,
                    "status": "missing",
                    "value": "no token-to-role mappings configured",
                },
            ],
            "message": "Bearer staff auth is enabled, but no staff token mappings are configured yet.",
            "fix": (
                f"Set {STAFF_AUTH_TOKEN_ROLES_ENV_VAR} to JSON like "
                '\'{"clerk-token":["clerk_admin","meeting_editor"]}\' before testing staff APIs.'
            ),
        }
    return {
        "mode": STAFF_BEARER_MODE,
        "ready": True,
        "deployment_ready": True,
        "checks": [
            {
                "name": "staff auth mode",
                "status": "configured",
                "value": STAFF_BEARER_MODE,
            },
            {
                "name": STAFF_AUTH_TOKEN_ROLES_ENV_VAR,
                "status": "configured",
                "value": f"{len(token_map)} token mapping(s)",
            },
        ],
        "message": "Bearer staff auth is configured and ready for token-based staff access checks.",
        "fix": "Use a configured bearer token below to confirm the current browser session can reach staff routes.",
        "session_probe": {
            "method": "GET",
            "path": "/staff/session",
            "headers": {"Authorization": "Bearer <configured token>"},
            "note": "Run this through the same browser, proxy, or API client that will reach protected staff pages.",
        },
        "write_probe": {
            "method": "POST",
            "path": "/agenda-intake",
            "headers": {"Authorization": "Bearer <configured token>"},
            "body": {
                "title": "Protected deployment smoke check",
                "department_name": "Clerk",
                "submitted_by": "clerk@example.gov",
                "summary": "Confirm bearer-protected staff writes succeed after the session probe passes.",
                "source_references": [{"label": "Smoke check memo", "url": "https://city.example.gov/memo"}],
            },
            "note": "This write probe should return 201 only after the bearer session probe proves the operator token is mapped to a staff role.",
        },
    }


def _get_staff_trusted_header_readiness() -> dict[str, object]:
    trusted_header_config = _get_staff_trusted_header_config()
    local_proxy_rehearsal = _get_local_trusted_header_proxy_rehearsal(
        principal_header_name=trusted_header_config.principal_header_name,
        roles_header_name=trusted_header_config.roles_header_name,
    )
    reverse_proxy_reference = {
        "kind": "nginx_trusted_header_bridge",
        "path": TRUSTED_PROXY_REFERENCE_CONFIG_PATH,
        "headers": {
            trusted_header_config.principal_header_name: "<authenticated staff email>",
            trusted_header_config.roles_header_name: "<comma-separated mapped staff roles>",
        },
        "steps": [
            "Authenticate the operator before CivicClerk and map the trusted staff principal plus roles into proxy-controlled headers.",
            "Strip any client-supplied copies of the trusted staff headers before setting the proxy-owned values shown here.",
            f"Set {STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR} to the proxy CIDRs that are allowed to forward those headers to CivicClerk.",
        ],
        "warnings": [
            "This reference config is a starting point; replace the placeholder TLS paths and authenticated identity variables with your real deployment values.",
            "Do not trust direct browser requests that bypass the reverse proxy, even if they contain matching header names.",
        ],
    }
    checks: list[dict[str, str]] = [
        {
            "name": "staff auth mode",
            "status": "configured",
            "value": STAFF_TRUSTED_HEADER_MODE,
        },
        {
            "name": STAFF_AUTH_SSO_PROVIDER_ENV_VAR,
            "status": "configured" if trusted_header_config.provider_name else "missing",
            "value": trusted_header_config.provider_name or DEFAULT_STAFF_SSO_PROVIDER,
        },
        {
            "name": STAFF_AUTH_SSO_PRINCIPAL_HEADER_ENV_VAR,
            "status": "configured",
            "value": trusted_header_config.principal_header_name,
        },
        {
            "name": STAFF_AUTH_SSO_ROLES_HEADER_ENV_VAR,
            "status": "configured",
            "value": trusted_header_config.roles_header_name,
        },
    ]
    if not trusted_header_config.trusted_proxy_cidrs:
        checks.append(
            {
                "name": STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR,
                "status": "missing",
                "value": "no trusted proxy CIDRs configured",
            }
        )
        return {
            "mode": STAFF_TRUSTED_HEADER_MODE,
            "ready": False,
            "deployment_ready": False,
            "provider": trusted_header_config.provider_name,
            "principal_header": trusted_header_config.principal_header_name,
            "roles_header": trusted_header_config.roles_header_name,
            "local_proxy_rehearsal": local_proxy_rehearsal,
            "reverse_proxy_reference": reverse_proxy_reference,
            "checks": checks,
            "message": "Trusted-header staff auth is selected, but the reverse-proxy allowlist is missing.",
            "fix": (
                f"Set {STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR} to the CIDRs allowed to inject "
                f"{trusted_header_config.principal_header_name} and "
                f"{trusted_header_config.roles_header_name}, for example "
                f"'10.0.0.0/24,192.168.1.8/32'. For a loopback rehearsal, use "
                f"'{LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_TRUSTED_PROXY}' and run "
                f"{LOCAL_TRUSTED_HEADER_PROXY_SCRIPT_PATH}. For a real proxy deployment, start from "
                f"{TRUSTED_PROXY_REFERENCE_CONFIG_PATH}."
            ),
        }
    try:
        normalize_trusted_proxy_cidrs(trusted_header_config.trusted_proxy_cidrs)
    except ValueError as exc:
        checks.append(
            {
                "name": STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR,
                "status": "invalid",
                "value": ", ".join(trusted_header_config.trusted_proxy_cidrs),
            }
        )
        return {
            "mode": STAFF_TRUSTED_HEADER_MODE,
            "ready": False,
            "deployment_ready": False,
            "provider": trusted_header_config.provider_name,
            "principal_header": trusted_header_config.principal_header_name,
            "roles_header": trusted_header_config.roles_header_name,
            "local_proxy_rehearsal": local_proxy_rehearsal,
            "reverse_proxy_reference": reverse_proxy_reference,
            "checks": checks,
            "message": "Trusted-header staff auth has an invalid reverse-proxy allowlist.",
            "fix": (
                f"{STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR}: {exc}. For a loopback rehearsal, use "
                f"'{LOCAL_TRUSTED_HEADER_PROXY_DEFAULT_TRUSTED_PROXY}' and run "
                f"{LOCAL_TRUSTED_HEADER_PROXY_SCRIPT_PATH}. For a real proxy deployment, start from "
                f"{TRUSTED_PROXY_REFERENCE_CONFIG_PATH}."
            ),
        }
    checks.append(
        {
            "name": STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR,
            "status": "configured",
            "value": ", ".join(trusted_header_config.trusted_proxy_cidrs),
        }
    )
    return {
        "mode": STAFF_TRUSTED_HEADER_MODE,
        "ready": True,
        "deployment_ready": True,
        "provider": trusted_header_config.provider_name,
        "principal_header": trusted_header_config.principal_header_name,
        "roles_header": trusted_header_config.roles_header_name,
        "trusted_proxy_cidrs": list(trusted_header_config.trusted_proxy_cidrs),
        "local_proxy_rehearsal": local_proxy_rehearsal,
        "reverse_proxy_reference": reverse_proxy_reference,
        "checks": checks,
        "message": "Trusted-header staff auth is configured for reverse-proxy deployment readiness.",
        "fix": (
            f"Send staff traffic through {trusted_header_config.provider_name}, strip client-supplied "
            f"{trusted_header_config.principal_header_name} and {trusted_header_config.roles_header_name}, "
            f"and test authenticated staff requests through that proxy path. Start from "
            f"{TRUSTED_PROXY_REFERENCE_CONFIG_PATH} for the first nginx bridge contract."
        ),
        "session_probe": {
            "method": "GET",
            "path": "/staff/session",
            "headers": {
                trusted_header_config.principal_header_name: "clerk@example.gov",
                trusted_header_config.roles_header_name: "clerk_admin,meeting_editor",
            },
            "note": (
                f"Only send these headers through {trusted_header_config.provider_name} from a source inside "
                f"{STAFF_AUTH_SSO_TRUSTED_PROXIES_ENV_VAR}; direct browser requests should not be trusted."
            ),
        },
        "write_probe": {
            "method": "POST",
            "path": "/agenda-intake",
            "headers": {
                trusted_header_config.principal_header_name: "clerk@example.gov",
                trusted_header_config.roles_header_name: "clerk_admin,meeting_editor",
            },
            "body": {
                "title": "Trusted proxy deployment smoke check",
                "department_name": "Clerk",
                "submitted_by": "clerk@example.gov",
                "summary": "Confirm trusted-header protected staff writes succeed after the session probe passes.",
                "source_references": [{"label": "Smoke check memo", "url": "https://city.example.gov/memo"}],
            },
            "note": (
                "Use this only behind the trusted reverse proxy after it strips client-supplied identity headers."
            ),
        },
    }


def _is_staff_protected_path(path: str) -> bool:
    if path in {"/", "/health", "/staff", "/staff/auth-readiness", "/favicon.ico"}:
        return False
    if path.startswith("/public/"):
        return False
    if path in {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}:
        return False
    return True


def _evaluate_notice_or_404(
    meeting_id: str,
    payload: NoticeComplianceRequest,
):
    meeting = _get_meeting_store().get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    if meeting.scheduled_start is None:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Meeting needs scheduled_start before notice compliance can be checked.",
                "fix": "Create or update the meeting with scheduled_start before checking notice compliance.",
            },
        )
    return evaluate_notice_compliance(
        meeting_id=meeting_id,
        notice_type=payload.notice_type,
        scheduled_start=meeting.scheduled_start,
        posted_at=payload.posted_at,
        minimum_notice_hours=payload.minimum_notice_hours,
        statutory_basis=payload.statutory_basis,
        approved_by=payload.approved_by,
    )


def _parse_timezone_aware_datetime(
    value: str | None,
    *,
    field_name: str,
) -> datetime | None:
    if value is None:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"{field_name} must be a valid ISO 8601 timestamp.",
                "fix": f"Use an ISO 8601 timestamp with Z or an explicit offset for {field_name}.",
            },
        ) from exc
    if parsed.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"{field_name} must include a timezone offset.",
                "fix": f"Use an ISO 8601 timestamp with Z or an explicit offset for {field_name}, for example 2026-05-05T19:00:00Z.",
            },
        )
    return parsed


def _resolve_packet_export_path(bundle_name: str) -> Path:
    """Resolve an API-provided bundle name under the configured export root."""
    requested = Path(bundle_name)
    if str(requested) == "." or requested.is_absolute() or ".." in requested.parts:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "bundle_name must be a relative folder name under CIVICCLERK_EXPORT_ROOT.",
                "fix": "Use a simple bundle name such as council-2026-05-05-packet-v1; configure CIVICCLERK_EXPORT_ROOT for the parent export directory.",
            },
        )
    export_root = Path(os.environ.get("CIVICCLERK_EXPORT_ROOT", "exports")).resolve()
    return export_root / requested


def _get_agenda_intake_repository() -> AgendaIntakeRepository:
    global _agenda_intake_db_url, _agenda_intake_repository
    db_url = os.environ.get("CIVICCLERK_AGENDA_INTAKE_DB_URL")
    if _agenda_intake_repository is None or db_url != _agenda_intake_db_url:
        _agenda_intake_db_url = db_url
        _agenda_intake_repository = AgendaIntakeRepository(db_url=db_url)
    return _agenda_intake_repository


def _get_agenda_items() -> AgendaItemRepository | AgendaItemStore:
    global _agenda_item_db_url, _agenda_item_repository
    db_url = os.environ.get("CIVICCLERK_AGENDA_ITEM_DB_URL")
    if db_url is None:
        return agenda_items
    if _agenda_item_repository is None or db_url != _agenda_item_db_url:
        _agenda_item_db_url = db_url
        _agenda_item_repository = AgendaItemRepository(db_url=db_url)
    return _agenda_item_repository


def _get_packet_assembly_repository() -> PacketAssemblyRepository:
    global _packet_assembly_db_url, _packet_assembly_repository
    db_url = os.environ.get("CIVICCLERK_PACKET_ASSEMBLY_DB_URL")
    if _packet_assembly_repository is None or db_url != _packet_assembly_db_url:
        _packet_assembly_db_url = db_url
        _packet_assembly_repository = PacketAssemblyRepository(db_url=db_url)
    return _packet_assembly_repository


def _get_notice_checklist_repository() -> NoticeChecklistRepository:
    global _notice_checklist_db_url, _notice_checklist_repository
    db_url = os.environ.get("CIVICCLERK_NOTICE_CHECKLIST_DB_URL")
    if _notice_checklist_repository is None or db_url != _notice_checklist_db_url:
        _notice_checklist_db_url = db_url
        _notice_checklist_repository = NoticeChecklistRepository(db_url=db_url)
    return _notice_checklist_repository


def _get_meeting_store() -> MeetingStore:
    global _meeting_db_url, _meeting_store
    db_url = os.environ.get("CIVICCLERK_MEETING_DB_URL")
    if db_url is None:
        return meetings
    if _meeting_store is None or db_url != _meeting_db_url:
        _meeting_db_url = db_url
        _meeting_store = MeetingStore(db_url=db_url)
    return _meeting_store
