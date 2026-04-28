from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from civicclerk.main import app
from civicclerk.packet_assembly import PacketAssemblyRepository, PacketAssemblyStatus


def _source_refs() -> list[dict]:
    return [
        {
            "source_id": "staff-report-1",
            "title": "Staff report",
            "kind": "document",
            "source_system": "local_file",
            "checksum": "abc123",
        }
    ]


def _citations() -> list[dict]:
    return [
        {
            "source_id": "staff-report-1",
            "locator": "p. 4",
            "claim": "Budget impact summary",
        }
    ]


def test_packet_assembly_records_persist_with_sources_citations_and_audit(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path / 'packet-assembly.db'}"
    first = PacketAssemblyRepository(db_url=db_url)
    created = first.create_draft(
        meeting_id="meeting-123",
        packet_snapshot_id="snapshot-1",
        packet_version=1,
        title="May 5 regular packet",
        actor="clerk@example.gov",
        agenda_item_ids=["item-1", "item-2"],
        source_references=_source_refs(),
        citations=_citations(),
    )

    second = PacketAssemblyRepository(db_url=db_url)
    records = second.list_for_meeting("meeting-123")

    assert [record.id for record in records] == [created.id]
    assert records[0].status == PacketAssemblyStatus.DRAFT.value
    assert records[0].source_references[0]["checksum"] == "abc123"
    assert records[0].citations[0]["locator"] == "p. 4"
    assert len(records[0].last_audit_hash) == 64


def test_packet_assembly_finalize_updates_status_and_audit_hash(tmp_path) -> None:
    repo = PacketAssemblyRepository(db_url=f"sqlite:///{tmp_path / 'packet-assembly.db'}")
    created = repo.create_draft(
        meeting_id="meeting-123",
        packet_snapshot_id="snapshot-1",
        packet_version=1,
        title="May 5 regular packet",
        actor="clerk@example.gov",
        agenda_item_ids=["item-1"],
        source_references=_source_refs(),
        citations=_citations(),
    )

    finalized = repo.finalize(record_id=created.id, actor="clerk@example.gov")

    assert finalized is not None
    assert finalized.status == PacketAssemblyStatus.FINALIZED.value
    assert finalized.finalized_by == "clerk@example.gov"
    assert finalized.finalized_at is not None
    assert finalized.last_audit_hash != created.last_audit_hash
    assert repo.audit_chain.verify()
    assert [event.action for event in repo.audit_chain.events] == [
        "packet_assembly.created",
        "packet_assembly.finalized",
    ]


async def test_api_packet_assembly_create_list_finalize_and_export(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CIVICCLERK_PACKET_ASSEMBLY_DB_URL", f"sqlite:///{tmp_path / 'api-assembly.db'}")
    monkeypatch.setenv("CIVICCLERK_EXPORT_ROOT", str(tmp_path / "exports"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        meeting = await client.post(
            "/meetings",
            json={
                "title": "Packet Assembly Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        meeting_id = meeting.json()["id"]
        created = await client.post(
            f"/meetings/{meeting_id}/packet-assemblies",
            json={
                "title": "May 5 regular packet",
                "agenda_item_ids": ["item-1"],
                "actor": "clerk@example.gov",
                "source_references": _source_refs(),
                "citations": _citations(),
            },
        )
        listed = await client.get(f"/meetings/{meeting_id}/packet-assemblies")
        finalized = await client.post(
            f"/packet-assemblies/{created.json()['id']}/finalize",
            json={"actor": "clerk@example.gov"},
        )
        exported = await client.post(
            f"/meetings/{meeting_id}/export-bundle",
            json={
                "bundle_name": "assembly-export",
                "actor": "clerk@example.gov",
                "sources": _source_refs(),
            },
        )

    assert created.status_code == 201
    assert created.json()["packet_version"] == 1
    assert len(created.json()["last_audit_hash"]) == 64
    assert listed.status_code == 200
    assert listed.json()["packet_assemblies"][0]["source_references"][0]["source_id"] == "staff-report-1"
    assert finalized.status_code == 200
    assert finalized.json()["status"] == "FINALIZED"
    assert exported.status_code == 201
    assert exported.json()["packet_version"] == 1


async def test_api_packet_assembly_finalize_unknown_record_is_actionable(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CIVICCLERK_PACKET_ASSEMBLY_DB_URL", f"sqlite:///{tmp_path / 'api-assembly.db'}")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/packet-assemblies/missing/finalize",
            json={"actor": "clerk@example.gov"},
        )

    assert response.status_code == 404
    assert response.json()["detail"]["fix"] == "Create the packet assembly record before finalizing it."
