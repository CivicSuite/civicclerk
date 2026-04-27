"""FastAPI runtime foundation for CivicClerk."""

from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from civicclerk import __version__
from civicclerk.agenda_lifecycle import AgendaItemStore
from civicclerk.meeting_lifecycle import MeetingStore
from civicclerk.packet_notice import NoticeStore, PacketStore, evaluate_notice_compliance
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


class AgendaItemCreate(BaseModel):
    title: str = Field(min_length=1)
    department_name: str = Field(min_length=1)


class AgendaItemTransitionRequest(BaseModel):
    to_status: str = Field(min_length=1)
    actor: str = Field(min_length=1)


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


class NoticeComplianceRequest(BaseModel):
    notice_type: str = Field(min_length=1)
    posted_at: datetime
    minimum_notice_hours: int = Field(gt=0)
    statutory_basis: str | None = Field(default=None, min_length=1)
    approved_by: str | None = Field(default=None, min_length=1)


@app.get("/")
async def root() -> dict[str, str]:
    """Describe what the runtime foundation currently provides."""
    return {
        "name": "CivicClerk",
        "status": "packet notice foundation",
        "message": (
            "CivicClerk agenda item, meeting lifecycle, packet snapshot, and notice compliance "
            "enforcement are online; vote, minutes, archive, and UI workflows are not implemented yet."
        ),
        "next_step": "Milestone 6: motion, vote, and action-item capture",
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


@app.post("/meetings", status_code=201)
async def create_meeting(payload: MeetingCreate) -> dict[str, str]:
    """Create a scheduled meeting for lifecycle enforcement."""
    return meetings.create(
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
    meeting = meetings.get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return meeting.public_dict()


@app.post("/meetings/{meeting_id}/transitions")
async def transition_meeting(
    meeting_id: str,
    payload: MeetingTransitionRequest,
) -> dict[str, str]:
    """Apply a canonical meeting lifecycle transition."""
    meeting = meetings.get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    result = meetings.transition(
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
    return meeting.public_dict()


@app.get("/meetings/{meeting_id}/audit")
async def get_meeting_audit(meeting_id: str) -> dict[str, list[dict[str, str]]]:
    """Return lifecycle audit entries for a meeting."""
    meeting = meetings.get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return {"entries": meeting.audit_entries}


@app.post("/meetings/{meeting_id}/packet-snapshots", status_code=201)
async def create_packet_snapshot(
    meeting_id: str,
    payload: PacketSnapshotCreate,
) -> dict:
    """Create an immutable packet snapshot version for a meeting."""
    meeting = meetings.get(meeting_id)
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
    meeting = meetings.get(meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    return {
        "snapshots": [
            snapshot.public_dict()
            for snapshot in packet_snapshots.list_snapshots(meeting_id)
        ]
    }


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


def _evaluate_notice_or_404(
    meeting_id: str,
    payload: NoticeComplianceRequest,
):
    meeting = meetings.get(meeting_id)
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
