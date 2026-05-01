"""Seed a believable local CivicClerk demo for Docker-based product rehearsal."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TypedDict

from civicclerk.agenda_intake import AgendaIntakeRepository
from civicclerk.agenda_lifecycle import AgendaItemRepository, AgendaItemStore
from civicclerk.meeting_body import MeetingBodyRepository
from civicclerk.meeting_lifecycle import MeetingStore
from civicclerk.minutes import MinutesDraftStore, MinutesSentence, SourceMaterial
from civicclerk.motion_vote import MotionVoteStore
from civicclerk.notice_checklist import NoticeChecklistRepository
from civicclerk.packet_assembly import PacketAssemblyRepository
from civicclerk.public_archive import PublicArchiveStore


DEMO_CLERK = "brookfield.clerk@example.gov"
DEMO_CITY = "City of Brookfield"


class DemoSeedSummary(TypedDict):
    """Counts and representative ids produced by the demo seed."""

    city: str
    meeting_body_count: int
    meeting_count: int
    agenda_intake_count: int
    packet_count: int
    notice_count: int
    motion_count: int
    minutes_draft_count: int
    public_record_count: int
    primary_meeting_id: str


def seed_demo_data(
    *,
    meeting_bodies: MeetingBodyRepository,
    meetings: MeetingStore,
    agenda_intake: AgendaIntakeRepository,
    agenda_items: AgendaItemRepository | AgendaItemStore,
    packet_assemblies: PacketAssemblyRepository,
    notice_checklists: NoticeChecklistRepository,
    motion_votes: MotionVoteStore,
    minutes_drafts: MinutesDraftStore,
    public_archive: PublicArchiveStore,
    now: datetime | None = None,
) -> DemoSeedSummary:
    """Populate the current runtime with deterministic Brookfield demo work.

    The seed is intentionally idempotent for database-backed records so a
    restarted Compose stack does not create duplicate staff work. The current
    motion, minutes, and public archive stores are in-memory, so they are seeded
    once per API process when empty.
    """

    anchor = now or datetime.now(UTC)
    council = _ensure_meeting_body(
        meeting_bodies,
        name="Brookfield City Council",
        body_type="Council",
    )
    planning = _ensure_meeting_body(
        meeting_bodies,
        name="Brookfield Planning Commission",
        body_type="Commission",
    )

    upcoming = _ensure_meeting(
        meetings,
        title="Brookfield City Council Regular Meeting",
        meeting_type="regular",
        meeting_body_id=str(council.id),
        scheduled_start=anchor + timedelta(days=8),
        location="Council Chambers, 100 Civic Plaza",
        target_status="PACKET_POSTED",
    )
    work_session = _ensure_meeting(
        meetings,
        title="Planning Commission Work Session",
        meeting_type="regular",
        meeting_body_id=str(planning.id),
        scheduled_start=anchor + timedelta(days=15),
        location="Brookfield Development Services Conference Room",
        target_status="NOTICED",
    )
    completed = _ensure_meeting(
        meetings,
        title="Brookfield City Council Prior Meeting",
        meeting_type="regular",
        meeting_body_id=str(council.id),
        scheduled_start=anchor - timedelta(days=7),
        location="Council Chambers, 100 Civic Plaza",
        target_status="ADJOURNED",
    )

    intake = _ensure_ready_intake(
        agenda_intake,
        agenda_items,
        title="Award sidewalk repair contract",
        department_name="Public Works",
        submitted_by="pw.director@example.gov",
        summary=(
            "Authorize the city manager to execute the FY2026 sidewalk repair "
            "contract for the Oak Street and Civic Plaza segments."
        ),
    )

    packet = _ensure_packet(
        packet_assemblies,
        meeting_id=upcoming.id,
        agenda_item_id=intake.promoted_agenda_item_id or "demo-agenda-item",
    )
    notice = _ensure_notice(
        notice_checklists,
        meeting_id=upcoming.id,
        scheduled_start=upcoming.scheduled_start or anchor + timedelta(days=8),
    )

    _seed_in_memory_outcomes(
        motion_votes,
        meeting_id=completed.id,
        agenda_item_id=intake.promoted_agenda_item_id,
    )
    _seed_in_memory_minutes(minutes_drafts, meeting_id=completed.id)
    _seed_in_memory_public_archive(public_archive, meeting_id=completed.id)

    return {
        "city": DEMO_CITY,
        "meeting_body_count": len(meeting_bodies.list()),
        "meeting_count": len(meetings.list()),
        "agenda_intake_count": len(agenda_intake.list_queue()),
        "packet_count": len(packet_assemblies.list_recent(limit=50)),
        "notice_count": len(notice_checklists.list_recent(limit=50)),
        "motion_count": len(motion_votes.list_motions(completed.id)),
        "minutes_draft_count": len(minutes_drafts.list_drafts(completed.id)),
        "public_record_count": len(public_archive.public_calendar()),
        "primary_meeting_id": upcoming.id,
    }


def _ensure_meeting_body(
    repo: MeetingBodyRepository,
    *,
    name: str,
    body_type: str,
):
    for body in repo.list():
        if body.name == name:
            return body
    return repo.create(name=name, body_type=body_type)


def _ensure_meeting(
    store: MeetingStore,
    *,
    title: str,
    meeting_type: str,
    meeting_body_id: str,
    scheduled_start: datetime,
    location: str,
    target_status: str,
):
    for meeting in store.list():
        if meeting.title == title:
            return meeting
    meeting = store.create(
        title=title,
        meeting_type=meeting_type,
        meeting_body_id=meeting_body_id,
        scheduled_start=scheduled_start,
        location=location,
    )
    for status in ("NOTICED", "PACKET_POSTED", "IN_PROGRESS", "RECESSED", "ADJOURNED"):
        if meeting.status == target_status:
            break
        store.transition(
            meeting_id=meeting.id,
            to_status=status,
            actor=DEMO_CLERK,
            statutory_basis=None,
        )
        meeting = store.get(meeting.id) or meeting
    return meeting


def _ensure_ready_intake(
    intake_repo: AgendaIntakeRepository,
    agenda_repo: AgendaItemRepository | AgendaItemStore,
    *,
    title: str,
    department_name: str,
    submitted_by: str,
    summary: str,
):
    for item in intake_repo.list_queue():
        if item.title == title:
            return item
    item = intake_repo.submit(
        title=title,
        department_name=department_name,
        submitted_by=submitted_by,
        summary=summary,
        source_references=[
            {
                "type": "staff_report",
                "label": "Public Works contract memo",
                "uri": "demo://brookfield/contracts/sidewalk-repair",
            }
        ],
    )
    reviewed = intake_repo.review(
        item_id=item.id,
        reviewer=DEMO_CLERK,
        ready=True,
        notes="Demo seed: staff report, fiscal note, and draft motion are complete.",
    )
    agenda_item = agenda_repo.create(title=title, department_name=department_name)
    agenda_repo.transition(item_id=agenda_item.id, to_status="SUBMITTED", actor=DEMO_CLERK)
    agenda_repo.transition(item_id=agenda_item.id, to_status="DEPT_APPROVED", actor=DEMO_CLERK)
    agenda_repo.transition(item_id=agenda_item.id, to_status="LEGAL_REVIEWED", actor=DEMO_CLERK)
    agenda_repo.transition(item_id=agenda_item.id, to_status="CLERK_ACCEPTED", actor=DEMO_CLERK)
    return intake_repo.promote_to_agenda_item(
        item_id=(reviewed or item).id,
        reviewer=DEMO_CLERK,
        agenda_item_id=agenda_item.id,
        notes="Demo seed: promoted into the council agenda packet.",
    ) or item


def _ensure_packet(
    repo: PacketAssemblyRepository,
    *,
    meeting_id: str,
    agenda_item_id: str,
):
    existing = repo.list_for_meeting(meeting_id)
    if existing:
        return existing[0]
    packet = repo.create_draft(
        meeting_id=meeting_id,
        packet_snapshot_id="brookfield-demo-packet-v1",
        packet_version=1,
        title="Brookfield Council Packet - Sidewalk Repair Contract",
        actor=DEMO_CLERK,
        agenda_item_ids=[agenda_item_id],
        source_references=[
            {
                "source_id": "staff-report-1",
                "label": "Public Works staff report",
                "uri": "demo://brookfield/packet/public-works-report",
            }
        ],
        citations=[
            {
                "source_id": "staff-report-1",
                "page": "2",
                "note": "Contract award recommendation and fiscal impact.",
            }
        ],
    )
    return repo.finalize(record_id=packet.id, actor=DEMO_CLERK) or packet


def _ensure_notice(
    repo: NoticeChecklistRepository,
    *,
    meeting_id: str,
    scheduled_start: datetime,
):
    existing = repo.list_for_meeting(meeting_id)
    if existing:
        return existing[0]
    record = repo.record_check(
        meeting_id=meeting_id,
        notice_type="regular",
        compliant=True,
        http_status=200,
        warnings=[],
        deadline_at=scheduled_start - timedelta(hours=72),
        posted_at=scheduled_start - timedelta(hours=96),
        minimum_notice_hours=72,
        statutory_basis="Brookfield open meeting ordinance: 72-hour public notice.",
        approved_by=DEMO_CLERK,
        actor=DEMO_CLERK,
    )
    return repo.attach_posting_proof(
        record_id=record.id,
        actor=DEMO_CLERK,
        posting_proof={
            "posted_url": "https://brookfield.example.gov/agendas/council-sidewalk-repair",
            "location": "City Hall lobby bulletin board",
            "hash_note": "Demo seed posting proof for local rehearsal only.",
        },
    ) or record


def _seed_in_memory_outcomes(
    store: MotionVoteStore,
    *,
    meeting_id: str,
    agenda_item_id: str | None,
) -> None:
    if store.list_motions(meeting_id):
        return
    motion = store.capture_motion(
        meeting_id=meeting_id,
        agenda_item_id=agenda_item_id,
        text="Move to approve the Oak Street sidewalk repair contract award.",
        actor=DEMO_CLERK,
    )
    for voter_name, vote in (
        ("Mayor Ellis", "yes"),
        ("Councilmember Park", "yes"),
        ("Councilmember Rivera", "yes"),
        ("Councilmember Chen", "no"),
    ):
        store.capture_vote(
            motion_id=motion.id,
            voter_name=voter_name,
            vote=vote,
            actor=DEMO_CLERK,
        )
    store.create_action_item(
        meeting_id=meeting_id,
        description="Publish signed contract award notice after vendor counter-signature.",
        assigned_to="Public Works",
        source_motion_id=motion.id,
        actor=DEMO_CLERK,
    )


def _seed_in_memory_minutes(store: MinutesDraftStore, *, meeting_id: str) -> None:
    if store.list_drafts(meeting_id):
        return
    source = SourceMaterial(
        source_id="motion-sidewalk-contract",
        label="Captured motion and roll-call vote",
        text="Council approved the Oak Street sidewalk repair contract award by a 3-1 vote.",
    )
    store.create_draft(
        meeting_id=meeting_id,
        model="ollama/gemma4",
        prompt_version="minutes_draft@0.1.0",
        human_approver=DEMO_CLERK,
        source_materials=[source],
        sentences=[
            MinutesSentence(
                text="Council approved the Oak Street sidewalk repair contract award by a 3-1 vote.",
                citations=("motion-sidewalk-contract",),
            )
        ],
    )


def _seed_in_memory_public_archive(store: PublicArchiveStore, *, meeting_id: str) -> None:
    if store.public_calendar():
        return
    store.publish(
        meeting_id=meeting_id,
        title="Brookfield City Council Prior Meeting",
        visibility="public",
        posted_agenda="Agenda included sidewalk repair contract award, public comment, and consent calendar.",
        posted_packet="Packet included Public Works memo, bid tabulation, and fiscal note.",
        approved_minutes="Approved minutes record the sidewalk repair contract vote and action item.",
    )
