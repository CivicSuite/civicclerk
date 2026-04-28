"""FastAPI runtime foundation for CivicClerk."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from civicclerk import __version__
from civicclerk.agenda_intake import AgendaIntakeRepository
from civicclerk.agenda_lifecycle import AgendaItemStore
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
_agenda_intake_repository: AgendaIntakeRepository | None = None
_agenda_intake_db_url: str | None = None
_packet_assembly_repository: PacketAssemblyRepository | None = None
_packet_assembly_db_url: str | None = None
_notice_checklist_repository: NoticeChecklistRepository | None = None
_notice_checklist_db_url: str | None = None
_meeting_store: MeetingStore | None = None
_meeting_db_url: str | None = None


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
        "status": "v0.1.0 runtime foundation release",
        "message": (
            "CivicClerk agenda item, meeting lifecycle, packet snapshot, and notice compliance "
            "enforcement are online with immutable motion, vote, action-item, and citation-gated "
            "minutes draft capture plus permission-aware public calendar and archive endpoints; "
            "prompt YAML and offline evaluation gates protect policy-bearing prompt changes; "
            "local-first Granicus, Legistar, PrimeGov, and NovusAGENDA imports now normalize "
            "source provenance; CivicCore v0.3.0 packet export bundles now include manifests, "
            "checksums, provenance, and hash-chained audit evidence; accessibility and browser QA "
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
            "meeting records can now persist through the configured meeting database; "
            "CivicClerk remains versioned as v0.1.0 while production-depth service slices continue; "
            "live clerk-console form submission for the remaining workflows is not implemented yet."
        ),
        "next_step": "Production-depth remaining live clerk-console actions for minutes, archive, connector imports, and packet exports",
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


@app.get("/staff", response_class=HTMLResponse)
async def staff_dashboard() -> str:
    """Render the staff-facing workflow foundation."""
    return render_staff_dashboard()


@app.post("/agenda-items", status_code=201)
async def create_agenda_item(payload: AgendaItemCreate) -> dict[str, str]:
    """Create a draft agenda item for lifecycle enforcement."""
    return agenda_items.create(
        title=payload.title,
        department_name=payload.department_name,
    ).public_dict()


@app.get("/agenda-items/{item_id}")
async def get_agenda_item(item_id: str) -> dict[str, str]:
    """Return the current agenda item state."""
    item = agenda_items.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Agenda item not found.")
    return item.public_dict()


@app.post("/agenda-items/{item_id}/transitions")
async def transition_agenda_item(
    item_id: str,
    payload: AgendaItemTransitionRequest,
) -> dict[str, str]:
    """Apply a canonical agenda item lifecycle transition."""
    item = agenda_items.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Agenda item not found.")
    result = agenda_items.transition(
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
    return item.public_dict()


@app.get("/agenda-items/{item_id}/audit")
async def get_agenda_item_audit(item_id: str) -> dict[str, list[dict[str, str]]]:
    """Return lifecycle audit entries for an agenda item."""
    item = agenda_items.get(item_id)
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
    return record.public_dict(
        include_closed=can_view_closed_sessions("clerk")
        and record.visibility != "public"
    )


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
    role: str = "anonymous",
) -> dict[str, int | list[dict]]:
    """Search public archives with permission-aware closed-session filtering."""
    include_closed = can_view_closed_sessions(role)
    results = [
        record.public_dict(include_closed=include_closed)
        for record in public_archive.search(query=q, role=role)
    ]
    return {
        "total_count": len(results),
        "results": results,
        "suggestions": [],
    }


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
