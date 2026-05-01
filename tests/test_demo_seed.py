from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from civicclerk.agenda_intake import AgendaIntakeRepository
from civicclerk.agenda_lifecycle import AgendaItemRepository
from civicclerk.demo_seed import DEMO_CITY, seed_demo_data
from civicclerk.meeting_body import MeetingBodyRepository
from civicclerk.meeting_lifecycle import MeetingStore
from civicclerk.minutes import MinutesDraftStore
from civicclerk.motion_vote import MotionVoteStore
from civicclerk.notice_checklist import NoticeChecklistRepository
from civicclerk.packet_assembly import PacketAssemblyRepository
from civicclerk.public_archive import PublicArchiveStore

ROOT = Path(__file__).resolve().parents[1]


def test_demo_seed_populates_visible_product_workflows(tmp_path) -> None:
    stores = _stores(tmp_path)
    summary = seed_demo_data(now=datetime(2026, 5, 1, 16, 0, tzinfo=UTC), **stores)

    assert summary["city"] == DEMO_CITY
    assert summary["meeting_body_count"] == 2
    assert summary["meeting_count"] == 3
    assert summary["agenda_intake_count"] == 1
    assert summary["packet_count"] == 1
    assert summary["notice_count"] == 1
    assert summary["motion_count"] == 1
    assert summary["minutes_draft_count"] == 1
    assert summary["public_record_count"] == 1

    meetings = stores["meetings"].list()
    assert {meeting.status for meeting in meetings} >= {"NOTICED", "PACKET_POSTED", "ADJOURNED"}
    assert stores["packet_assemblies"].list_recent(limit=5)[0].status == "FINALIZED"
    notice = stores["notice_checklists"].list_recent(limit=5)[0]
    assert notice.compliant is True
    assert notice.posting_proof is not None
    assert notice.statutory_basis


def test_demo_seed_is_idempotent_for_persistent_demo_records(tmp_path) -> None:
    stores = _stores(tmp_path)
    seed_demo_data(now=datetime(2026, 5, 1, 16, 0, tzinfo=UTC), **stores)
    second = seed_demo_data(now=datetime(2026, 5, 1, 16, 0, tzinfo=UTC), **stores)

    assert second["meeting_body_count"] == 2
    assert second["meeting_count"] == 3
    assert second["agenda_intake_count"] == 1
    assert second["packet_count"] == 1
    assert second["notice_count"] == 1
    assert second["motion_count"] == 1
    assert second["minutes_draft_count"] == 1
    assert second["public_record_count"] == 1


def test_compose_enables_demo_seed_but_documents_empty_database_escape_hatch() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    env_example = (ROOT / "docs" / "examples" / "docker.env.example").read_text(
        encoding="utf-8"
    )

    assert "CIVICCLERK_DEMO_SEED: ${CIVICCLERK_DEMO_SEED:-1}" in compose
    assert "CIVICCLERK_DEMO_SEED=1" in env_example
    assert "Set to 0 for an empty local rehearsal database." in env_example


def _stores(tmp_path):
    return {
        "meeting_bodies": MeetingBodyRepository(
            db_url=f"sqlite:///{tmp_path / 'meeting-bodies.db'}"
        ),
        "meetings": MeetingStore(db_url=f"sqlite:///{tmp_path / 'meetings.db'}"),
        "agenda_intake": AgendaIntakeRepository(
            db_url=f"sqlite:///{tmp_path / 'agenda-intake.db'}"
        ),
        "agenda_items": AgendaItemRepository(
            db_url=f"sqlite:///{tmp_path / 'agenda-items.db'}"
        ),
        "packet_assemblies": PacketAssemblyRepository(
            db_url=f"sqlite:///{tmp_path / 'packet-assemblies.db'}"
        ),
        "notice_checklists": NoticeChecklistRepository(
            db_url=f"sqlite:///{tmp_path / 'notice-checklists.db'}"
        ),
        "motion_votes": MotionVoteStore(),
        "minutes_drafts": MinutesDraftStore(),
        "public_archive": PublicArchiveStore(),
    }
