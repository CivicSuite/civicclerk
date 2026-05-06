from __future__ import annotations

from datetime import UTC, datetime
from itertools import product
from pathlib import Path
from random import Random

import pytest
from httpx import ASGITransport, AsyncClient

from civicclerk.main import app
from civicclerk.meeting_lifecycle import MeetingStore

ROOT = Path(__file__).resolve().parents[1]


MEETING_LIFECYCLE = [
    "SCHEDULED",
    "NOTICED",
    "PACKET_POSTED",
    "IN_PROGRESS",
    "RECESSED",
    "ADJOURNED",
    "TRANSCRIPT_READY",
    "MINUTES_DRAFTED",
    "MINUTES_POSTED",
    "MINUTES_ADOPTED",
    "MINUTES_SIGNED",
    "ARCHIVED",
]

VALID_EDGES = set(zip(MEETING_LIFECYCLE[:-1], MEETING_LIFECYCLE[1:], strict=True))
SPECIAL_EDGES = {
    ("IN_PROGRESS", "RECESSED"),
    ("RECESSED", "IN_PROGRESS"),
    ("SCHEDULED", "CANCELLED"),
    ("NOTICED", "CANCELLED"),
}


def assert_persisted_audit_entry(entry: dict, expected: dict[str, str]) -> None:
    for key, value in expected.items():
        assert entry[key] == value
    assert len(entry["timestamp"]) >= 20
    assert len(entry["previous_hash"]) == 64
    assert len(entry["entry_hash"]) == 64
    assert entry["action"].startswith("meeting.")


@pytest.mark.parametrize(("from_status", "to_status"), product(MEETING_LIFECYCLE, repeat=2))
def test_meeting_lifecycle_matrix_allows_only_canonical_edges(
    from_status: str,
    to_status: str,
) -> None:
    from civicclerk.meeting_lifecycle import validate_meeting_transition

    result = validate_meeting_transition(
        meeting_id="meeting-123",
        from_status=from_status,
        to_status=to_status,
        actor="clerk@example.gov",
        meeting_type="regular",
        statutory_basis=None,
    )

    if (from_status, to_status) in VALID_EDGES:
        assert result.allowed is True
        assert result.http_status == 200
        assert result.audit_entry["outcome"] == "allowed"
    elif (from_status, to_status) in SPECIAL_EDGES:
        assert result.allowed is True
        assert result.http_status == 200
        assert result.audit_entry["outcome"] == "allowed"
    else:
        assert result.allowed is False
        assert result.http_status == 409
        assert result.audit_entry["outcome"] == "rejected"
        assert result.audit_entry["from_status"] == from_status
        assert result.audit_entry["to_status"] == to_status
        assert "canonical next status" in result.message


def test_meeting_lifecycle_generated_sequences_are_ordered_and_hash_chained() -> None:
    from civicclerk.meeting_lifecycle import (
        CANCELLED_STATUS,
        VALID_TRANSITIONS,
        verify_meeting_audit_entries,
        validate_meeting_transition,
    )

    seed = 94155
    rng = Random(seed)
    meeting_types = ["regular", "special", "emergency", "closed_session"]
    current_status = "SCHEDULED"
    meeting_type = rng.choice(meeting_types)
    entries: list[dict[str, object]] = []

    for step in range(1400):
        if current_status in {"ARCHIVED", CANCELLED_STATUS}:
            current_status = "SCHEDULED"
            meeting_type = rng.choice(meeting_types)
            entries = []
        canonical_next = VALID_TRANSITIONS.get(current_status)
        valid_targets = []
        if canonical_next is not None:
            valid_targets.append(canonical_next)
        if current_status == "RECESSED":
            valid_targets.append("IN_PROGRESS")
        if current_status in {"SCHEDULED", "NOTICED"}:
            valid_targets.append(CANCELLED_STATUS)

        if rng.random() < 0.62 and valid_targets:
            target = rng.choice(valid_targets)
        else:
            invalid_targets = [
                status
                for status in [*MEETING_LIFECYCLE, CANCELLED_STATUS]
                if status not in valid_targets and status != current_status
            ]
            target = rng.choice(invalid_targets)

        statutory_basis = None
        if meeting_type in {"special", "emergency"} and current_status == "SCHEDULED" and target == "NOTICED":
            statutory_basis = "Synthetic statute for generated emergency or special notice."
        if meeting_type == "closed_session" and current_status == "PACKET_POSTED" and target == "IN_PROGRESS":
            statutory_basis = "Synthetic closed-session statute."

        result = validate_meeting_transition(
            meeting_id=f"meeting-sequence-{seed}",
            from_status=current_status,
            to_status=target,
            actor=f"sequence-{seed}@example.gov",
            meeting_type=meeting_type,
            statutory_basis=statutory_basis,
            previous_audit_hash=entries[-1]["entry_hash"] if entries else "0" * 64,
        )
        entries.append(result.audit_entry)

        if target in valid_targets:
            assert result.allowed is True
            current_status = target
        else:
            assert result.allowed is False
            assert result.fix

        ok, checked, message = verify_meeting_audit_entries(entries)
        assert ok, f"seed={seed} step={step} {message}"
        assert checked == len(entries)


def test_meeting_terminal_status_refusal_has_replacement_fix() -> None:
    from civicclerk.meeting_lifecycle import validate_meeting_transition

    result = validate_meeting_transition(
        meeting_id="meeting-terminal",
        from_status="ARCHIVED",
        to_status="NOTICED",
        actor="clerk@example.gov",
        meeting_type="regular",
        statutory_basis=None,
    )

    assert result.allowed is False
    assert result.http_status == 409
    assert "terminal" in result.fix
    assert "replacement meeting" in result.fix


@pytest.mark.parametrize("meeting_type", ["emergency", "special"])
def test_emergency_and_special_meetings_require_statutory_basis_for_notice(
    meeting_type: str,
) -> None:
    from civicclerk.meeting_lifecycle import validate_meeting_transition

    rejected = validate_meeting_transition(
        meeting_id="meeting-123",
        from_status="SCHEDULED",
        to_status="NOTICED",
        actor="clerk@example.gov",
        meeting_type=meeting_type,
        statutory_basis=None,
    )
    assert rejected.allowed is False
    assert rejected.http_status == 422
    assert "statutory basis" in rejected.message.lower()
    assert rejected.audit_entry["outcome"] == "rejected"

    accepted = validate_meeting_transition(
        meeting_id="meeting-123",
        from_status="SCHEDULED",
        to_status="NOTICED",
        actor="clerk@example.gov",
        meeting_type=meeting_type,
        statutory_basis="Emergency posting authorized by local open meeting statute.",
    )
    assert accepted.allowed is True
    assert accepted.http_status == 200
    assert accepted.audit_entry["statutory_basis"] == (
        "Emergency posting authorized by local open meeting statute."
    )


@pytest.mark.parametrize("meeting_type", ["Emergency", "SPECIAL"])
def test_emergency_and_special_meeting_type_casing_cannot_bypass_notice_basis(
    meeting_type: str,
) -> None:
    from civicclerk.meeting_lifecycle import validate_meeting_transition

    result = validate_meeting_transition(
        meeting_id="meeting-123",
        from_status="SCHEDULED",
        to_status="NOTICED",
        actor="clerk@example.gov",
        meeting_type=meeting_type,
        statutory_basis=None,
    )

    assert result.allowed is False
    assert result.http_status == 422
    assert "statutory basis" in result.message.lower()
    assert result.audit_entry["meeting_type"] == meeting_type.lower()


def test_closed_executive_session_requires_statutory_basis_before_in_progress() -> None:
    from civicclerk.meeting_lifecycle import validate_meeting_transition

    rejected = validate_meeting_transition(
        meeting_id="meeting-123",
        from_status="PACKET_POSTED",
        to_status="IN_PROGRESS",
        actor="clerk@example.gov",
        meeting_type="closed_session",
        statutory_basis=None,
    )
    assert rejected.allowed is False
    assert rejected.http_status == 422
    assert "closed" in rejected.message.lower()
    assert "statutory basis" in rejected.message.lower()

    accepted = validate_meeting_transition(
        meeting_id="meeting-123",
        from_status="PACKET_POSTED",
        to_status="IN_PROGRESS",
        actor="clerk@example.gov",
        meeting_type="executive",
        statutory_basis="Personnel matter under state closed-session statute.",
    )
    assert accepted.allowed is True
    assert accepted.audit_entry["statutory_basis"] == (
        "Personnel matter under state closed-session statute."
    )


@pytest.mark.parametrize("meeting_type", ["Closed_Session", "Executive"])
def test_closed_executive_meeting_type_casing_cannot_bypass_session_basis(
    meeting_type: str,
) -> None:
    from civicclerk.meeting_lifecycle import validate_meeting_transition

    result = validate_meeting_transition(
        meeting_id="meeting-123",
        from_status="PACKET_POSTED",
        to_status="IN_PROGRESS",
        actor="clerk@example.gov",
        meeting_type=meeting_type,
        statutory_basis=None,
    )

    assert result.allowed is False
    assert result.http_status == 422
    assert "statutory basis" in result.message.lower()
    assert result.audit_entry["meeting_type"] == meeting_type.lower()


@pytest.mark.asyncio
async def test_api_valid_meeting_transition_returns_2xx_and_writes_audit_entry() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meetings",
            json={
                "title": "City Council Regular Meeting",
                "meeting_type": "regular",
            },
        )
        assert created.status_code == 201
        meeting_id = created.json()["id"]

        transitioned = await client.post(
            f"/meetings/{meeting_id}/transitions",
            json={
                "to_status": "NOTICED",
                "actor": "clerk@example.gov",
            },
        )
        assert transitioned.status_code == 200
        assert transitioned.json()["status"] == "NOTICED"

        audit = await client.get(f"/meetings/{meeting_id}/audit")
        assert audit.status_code == 200
        entry = audit.json()["entries"][-1]
        assert_persisted_audit_entry(
            entry,
            {
                "meeting_id": meeting_id,
                "actor": "clerk@example.gov",
                "from_status": "SCHEDULED",
                "to_status": "NOTICED",
                "meeting_type": "regular",
                "outcome": "allowed",
                "reason": "transition allowed",
            },
        )


@pytest.mark.asyncio
async def test_api_lists_meetings_for_staff_calendar_in_scheduled_order() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        first = await client.post(
            "/meetings",
            json={
                "title": "Planning Commission",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-07T18:00:00Z",
            },
        )
        second = await client.post(
            "/meetings",
            json={
                "title": "City Council",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T18:00:00Z",
            },
        )

        listed = await client.get("/meetings")

        assert listed.status_code == 200
        payload = listed.json()
        ids = [meeting["id"] for meeting in payload["meetings"]]
        assert second.json()["id"] in ids
        assert first.json()["id"] in ids
        assert ids.index(second.json()["id"]) < ids.index(first.json()["id"])
        assert payload["count"] == len(payload["meetings"])


@pytest.mark.asyncio
async def test_api_invalid_meeting_transition_returns_4xx_and_writes_audit_entry() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meetings",
            json={
                "title": "Planning Commission Special Meeting",
                "meeting_type": "special",
            },
        )
        assert created.status_code == 201
        meeting_id = created.json()["id"]

        rejected = await client.post(
            f"/meetings/{meeting_id}/transitions",
            json={
                "to_status": "IN_PROGRESS",
                "actor": "clerk@example.gov",
            },
        )
        assert rejected.status_code == 409
        assert rejected.json()["detail"]["current_status"] == "SCHEDULED"
        assert rejected.json()["detail"]["requested_status"] == "IN_PROGRESS"
        assert rejected.json()["detail"]["fix"] == (
            "Move the meeting to NOTICED first, then retry the requested transition."
        )

        audit = await client.get(f"/meetings/{meeting_id}/audit")
        assert audit.status_code == 200
        assert audit.json()["entries"][-1]["outcome"] == "rejected"
        assert audit.json()["entries"][-1]["reason"] == "invalid meeting lifecycle transition"


@pytest.mark.asyncio
async def test_api_closed_session_precondition_returns_actionable_422() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meetings",
            json={
                "title": "Closed Session",
                "meeting_type": "closed_session",
            },
        )
        meeting_id = created.json()["id"]

        await client.post(
            f"/meetings/{meeting_id}/transitions",
            json={
                "to_status": "NOTICED",
                "actor": "clerk@example.gov",
                "statutory_basis": "Closed-session notice statute.",
            },
        )
        await client.post(
            f"/meetings/{meeting_id}/transitions",
            json={
                "to_status": "PACKET_POSTED",
                "actor": "clerk@example.gov",
            },
        )
        rejected = await client.post(
            f"/meetings/{meeting_id}/transitions",
            json={
                "to_status": "IN_PROGRESS",
                "actor": "clerk@example.gov",
            },
        )

        assert rejected.status_code == 422
        assert "statutory basis" in rejected.json()["detail"]["message"].lower()
        assert "closed-session statutory basis" in rejected.json()["detail"]["fix"]
        current = await client.get(f"/meetings/{meeting_id}")
        assert current.json()["status"] == "PACKET_POSTED"


@pytest.mark.asyncio
async def test_api_meeting_type_casing_cannot_bypass_statutory_basis() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meetings",
            json={
                "title": "Emergency Meeting",
                "meeting_type": "Emergency",
            },
        )
        assert created.status_code == 201
        meeting_id = created.json()["id"]
        assert created.json()["meeting_type"] == "emergency"

        rejected = await client.post(
            f"/meetings/{meeting_id}/transitions",
            json={
                "to_status": "NOTICED",
                "actor": "clerk@example.gov",
            },
        )

        assert rejected.status_code == 422
        assert "statutory basis" in rejected.json()["detail"]["message"].lower()


@pytest.mark.asyncio
async def test_api_cancelled_meeting_is_terminal_and_audited() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meetings",
            json={
                "title": "Cancelled Regular Meeting",
                "meeting_type": "regular",
            },
        )
        meeting_id = created.json()["id"]

        cancelled = await client.post(
            f"/meetings/{meeting_id}/transitions",
            json={
                "to_status": "CANCELLED",
                "actor": "clerk@example.gov",
            },
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "CANCELLED"

        rejected = await client.post(
            f"/meetings/{meeting_id}/transitions",
            json={
                "to_status": "NOTICED",
                "actor": "clerk@example.gov",
            },
        )
        assert rejected.status_code == 409
        assert rejected.json()["detail"]["current_status"] == "CANCELLED"

        audit = await client.get(f"/meetings/{meeting_id}/audit")
        assert audit.status_code == 200
        assert audit.json()["entries"][0]["to_status"] == "CANCELLED"
        assert audit.json()["entries"][0]["outcome"] == "allowed"
        assert audit.json()["entries"][1]["outcome"] == "rejected"


def test_meeting_store_persists_meeting_records_and_audit_entries(tmp_path: Path) -> None:
    db_url = f"sqlite+pysqlite:///{tmp_path / 'meetings.db'}"
    store = MeetingStore(db_url=db_url)
    meeting = store.create(
        title="Persisted Regular Meeting",
        meeting_type="Regular",
        scheduled_start=datetime(2026, 5, 5, 19, 0, tzinfo=UTC),
    )

    result = store.transition(
        meeting_id=meeting.id,
        to_status="NOTICED",
        actor="clerk@example.gov",
        statutory_basis=None,
    )

    assert result is not None
    assert result.allowed is True

    reopened = MeetingStore(db_url=db_url)
    persisted = reopened.get(meeting.id)

    assert persisted is not None
    assert persisted.status == "NOTICED"
    assert persisted.meeting_type == "regular"
    assert persisted.scheduled_start == datetime(2026, 5, 5, 19, 0, tzinfo=UTC)
    assert persisted.audit_entries[-1]["outcome"] == "allowed"
    assert persisted.audit_entries[-1]["actor"] == "clerk@example.gov"
    assert len(persisted.audit_entries[-1]["entry_hash"]) == 64


@pytest.mark.asyncio
async def test_api_uses_configured_meeting_database_for_records_and_audit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import civicclerk.main as main_module

    db_url = f"sqlite+pysqlite:///{tmp_path / 'api-meetings.db'}"
    monkeypatch.setenv("CIVICCLERK_MEETING_DB_URL", db_url)
    main_module._meeting_store = None
    main_module._meeting_db_url = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meetings",
            json={
                "title": "Persisted API Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        assert created.status_code == 201
        meeting_id = created.json()["id"]

        transitioned = await client.post(
            f"/meetings/{meeting_id}/transitions",
            json={
                "to_status": "NOTICED",
                "actor": "clerk@example.gov",
            },
        )
        assert transitioned.status_code == 200
        assert transitioned.json()["status"] == "NOTICED"

    reopened = MeetingStore(db_url=db_url)
    persisted = reopened.get(meeting_id)

    assert persisted is not None
    assert persisted.title == "Persisted API Meeting"
    assert persisted.status == "NOTICED"
    assert persisted.audit_entries[-1]["to_status"] == "NOTICED"

    main_module._meeting_store = None
    main_module._meeting_db_url = None


def test_docs_record_meeting_lifecycle_without_claiming_packet_or_minutes_behavior() -> None:
    docs = {
        "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
        "USER-MANUAL.md": (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
        "docs/index.html": (ROOT / "docs" / "index.html").read_text(encoding="utf-8"),
        "CHANGELOG.md": (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
    }

    for path, text in docs.items():
        lowered = text.lower()
        assert "meeting lifecycle" in lowered, path
        assert "packet assembly shipped" not in lowered, path
        assert "minutes drafting shipped" not in lowered, path


def test_docs_record_generated_meeting_lifecycle_and_audit_hash_coverage() -> None:
    docs = "\n".join(
        [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "README.txt").read_text(encoding="utf-8"),
            (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
            (ROOT / "USER-MANUAL.txt").read_text(encoding="utf-8"),
            (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
        ]
    )

    assert "sequence coverage" in docs
    assert "schedule-edit audit hashes" in docs
