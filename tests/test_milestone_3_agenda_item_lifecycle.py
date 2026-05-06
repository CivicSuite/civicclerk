from __future__ import annotations

from itertools import product
from pathlib import Path
from random import Random

import pytest
from httpx import ASGITransport, AsyncClient

from civicclerk.main import app

ROOT = Path(__file__).resolve().parents[1]


AGENDA_ITEM_LIFECYCLE = [
    "DRAFTED",
    "SUBMITTED",
    "DEPT_APPROVED",
    "LEGAL_REVIEWED",
    "CLERK_ACCEPTED",
    "ON_AGENDA",
    "IN_PACKET",
    "POSTED",
    "HEARD",
    "DISPOSED",
    "ARCHIVED",
]

VALID_EDGES = set(zip(AGENDA_ITEM_LIFECYCLE[:-1], AGENDA_ITEM_LIFECYCLE[1:], strict=True))


def assert_persisted_audit_entry(entry: dict, expected: dict[str, str]) -> None:
    for key, value in expected.items():
        assert entry[key] == value
    assert len(entry["timestamp"]) >= 20
    assert len(entry["previous_hash"]) == 64
    assert len(entry["entry_hash"]) == 64
    assert entry["action"].startswith("agenda_item.lifecycle_transition.")


@pytest.mark.parametrize(("from_status", "to_status"), product(AGENDA_ITEM_LIFECYCLE, repeat=2))
def test_agenda_item_lifecycle_matrix_allows_only_canonical_edges(
    from_status: str,
    to_status: str,
) -> None:
    from civicclerk.agenda_lifecycle import validate_agenda_item_transition

    result = validate_agenda_item_transition(
        agenda_item_id="agenda-123",
        from_status=from_status,
        to_status=to_status,
        actor="clerk@example.gov",
    )

    if (from_status, to_status) in VALID_EDGES:
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


def test_agenda_item_lifecycle_generated_sequences_are_ordered_and_hash_chained() -> None:
    from civicclerk.agenda_lifecycle import (
        AgendaItemStore,
        verify_agenda_item_audit_entries,
    )

    seed = 93411
    rng = Random(seed)
    store = AgendaItemStore()
    items = [store.create(title="Generated agenda item 0", department_name="Clerk")]

    for step in range(1200):
        item = items[-1]
        current_index = AGENDA_ITEM_LIFECYCLE.index(item.status)
        if item.status == "ARCHIVED":
            item = store.create(title=f"Generated agenda item {len(items)}", department_name="Clerk")
            items.append(item)
            current_index = 0
        next_status = (
            AGENDA_ITEM_LIFECYCLE[current_index + 1]
            if current_index + 1 < len(AGENDA_ITEM_LIFECYCLE)
            else "ARCHIVED"
        )
        if rng.random() < 0.58:
            target = next_status
            expected_allowed = current_index + 1 < len(AGENDA_ITEM_LIFECYCLE)
        else:
            invalid_targets = [status for status in AGENDA_ITEM_LIFECYCLE if status != next_status]
            target = rng.choice(invalid_targets)
            expected_allowed = False
        before = item.status

        result = store.transition(item_id=item.id, to_status=target, actor=f"sequence-{seed}@example.gov")

        assert result is not None
        assert result.allowed is expected_allowed
        if expected_allowed:
            assert item.status == target
            assert result.audit_entry["outcome"] == "allowed"
        else:
            assert item.status == before
            assert result.audit_entry["outcome"] == "rejected"
            assert result.fix

    total_entries = 0
    for item in items:
        ok, checked, message = verify_agenda_item_audit_entries(item.audit_entries)
        assert ok, f"seed={seed} item={item.id} {message}"
        assert checked == len(item.audit_entries)
        total_entries += checked
    assert total_entries == 1200


def test_agenda_item_terminal_status_refusal_has_correction_fix() -> None:
    from civicclerk.agenda_lifecycle import validate_agenda_item_transition

    result = validate_agenda_item_transition(
        agenda_item_id="agenda-terminal",
        from_status="ARCHIVED",
        to_status="SUBMITTED",
        actor="clerk@example.gov",
    )

    assert result.allowed is False
    assert result.http_status == 409
    assert "terminal" in result.fix
    assert "correction record" in result.fix


@pytest.mark.asyncio
async def test_api_valid_transition_returns_2xx_and_writes_audit_entry() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/agenda-items",
            json={
                "title": "Adopt safe streets resolution",
                "department_name": "Public Works",
            },
        )
        assert created.status_code == 201
        item_id = created.json()["id"]

        transitioned = await client.post(
            f"/agenda-items/{item_id}/transitions",
            json={
                "to_status": "SUBMITTED",
                "actor": "clerk@example.gov",
            },
        )
        assert transitioned.status_code == 200
        assert transitioned.json()["status"] == "SUBMITTED"

        audit = await client.get(f"/agenda-items/{item_id}/audit")
        assert audit.status_code == 200
        entry = audit.json()["entries"][-1]
        assert_persisted_audit_entry(
            entry,
            {
                "agenda_item_id": item_id,
                "actor": "clerk@example.gov",
                "from_status": "DRAFTED",
                "to_status": "SUBMITTED",
                "outcome": "allowed",
                "reason": "transition allowed",
            },
        )


@pytest.mark.asyncio
async def test_api_invalid_transition_returns_4xx_and_writes_audit_entry() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/agenda-items",
            json={
                "title": "Approve zoning text amendment",
                "department_name": "Planning",
            },
        )
        assert created.status_code == 201
        item_id = created.json()["id"]

        rejected = await client.post(
            f"/agenda-items/{item_id}/transitions",
            json={
                "to_status": "POSTED",
                "actor": "clerk@example.gov",
            },
        )
        assert rejected.status_code == 409
        payload = rejected.json()
        assert payload["detail"]["current_status"] == "DRAFTED"
        assert payload["detail"]["requested_status"] == "POSTED"
        assert "Next valid status is SUBMITTED" in payload["detail"]["message"]
        assert payload["detail"]["fix"] == (
            "Move the agenda item to SUBMITTED first, then retry the requested transition."
        )

        audit = await client.get(f"/agenda-items/{item_id}/audit")
        assert audit.status_code == 200
        entry = audit.json()["entries"][-1]
        assert_persisted_audit_entry(
            entry,
            {
                "agenda_item_id": item_id,
                "actor": "clerk@example.gov",
                "from_status": "DRAFTED",
                "to_status": "POSTED",
                "outcome": "rejected",
                "reason": "invalid agenda item lifecycle transition",
            },
        )


@pytest.mark.asyncio
async def test_api_unknown_status_returns_actionable_422_without_state_change() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/agenda-items",
            json={
                "title": "Set fee schedule hearing",
                "department_name": "Finance",
            },
        )
        item_id = created.json()["id"]

        rejected = await client.post(
            f"/agenda-items/{item_id}/transitions",
            json={
                "to_status": "READY_FOR_COUNCIL",
                "actor": "clerk@example.gov",
            },
        )

        assert rejected.status_code == 422
        assert "Use one of" in rejected.json()["detail"]["message"]
        assert "canonical agenda item statuses" in rejected.json()["detail"]["fix"]
        audit = await client.get(f"/agenda-items/{item_id}/audit")
        assert audit.json()["entries"][-1]["outcome"] == "rejected"
        assert len(audit.json()["entries"][-1]["entry_hash"]) == 64
        current = await client.get(f"/agenda-items/{item_id}")
        assert current.json()["status"] == "DRAFTED"


def test_docs_record_agenda_lifecycle_without_claiming_full_meeting_workflows() -> None:
    docs = {
        "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
        "USER-MANUAL.md": (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
        "docs/index.html": (ROOT / "docs" / "index.html").read_text(encoding="utf-8"),
        "CHANGELOG.md": (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
    }

    for path, text in docs.items():
        lowered = text.lower()
        assert "agenda item lifecycle" in lowered, path
        assert "full meeting workflows are implemented" not in lowered, path
        assert "meeting lifecycle enforcement shipped" not in lowered, path


def test_docs_record_civiccore_verifiable_agenda_lifecycle_audit_hashes() -> None:
    docs = "\n".join(
        [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "README.txt").read_text(encoding="utf-8"),
            (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8"),
            (ROOT / "USER-MANUAL.txt").read_text(encoding="utf-8"),
            (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"),
        ]
    )

    assert "CivicCore-verifiable" in docs
    assert "persisted audit hash" in docs
