from __future__ import annotations

from pathlib import Path

from httpx import ASGITransport, AsyncClient

from civicclerk.main import app
from civicclerk.packet_notice import PacketExportError, PacketSource, PacketStore
from civiccore import __version__ as CIVICCORE_VERSION
from civiccore.exports import validate_bundle


def test_packet_export_bundle_uses_civiccore_v03_manifest_and_audit(tmp_path: Path) -> None:
    store = PacketStore()
    store.create_snapshot(
        meeting_id="meeting-123",
        agenda_item_ids=["item-1", "item-2"],
        actor="clerk@example.gov",
    )

    result = store.create_export_bundle(
        meeting_id="meeting-123",
        meeting_title="Regular Council",
        bundle_path=tmp_path / "packet-export",
        actor="clerk@example.gov",
        sources=[
            PacketSource(
                source_id="staff-report-1",
                title="Staff report",
                kind="document",
                source_system="local_file",
                source_path="staff-report.pdf",
                citation_label="Staff Report p. 1",
            )
        ],
        notices=[{"notice_type": "regular", "posted": True}],
    )

    manifest = validate_bundle(result.bundle_path)
    assert manifest.module_name == "civicclerk"
    assert manifest.civiccore_version == CIVICCORE_VERSION
    assert sorted(file.path for file in manifest.generated_files) == [
        "notices.json",
        "packet.json",
        "provenance.json",
    ]
    assert result.audit_hash
    assert store.audit_chain.verify()
    assert (tmp_path / "packet-export" / "manifest.json").is_file()
    assert (tmp_path / "packet-export" / "SHA256SUMS.txt").is_file()


def test_public_packet_export_rejects_closed_session_sources(tmp_path: Path) -> None:
    store = PacketStore()
    store.create_snapshot(
        meeting_id="meeting-123",
        agenda_item_ids=["item-1"],
        actor="clerk@example.gov",
    )

    try:
        store.create_export_bundle(
            meeting_id="meeting-123",
            meeting_title="Closed Session Meeting",
            bundle_path=tmp_path / "public-export",
            actor="clerk@example.gov",
            sources=[
                PacketSource(
                    source_id="closed-note",
                    title="Closed session attorney memo",
                    kind="document",
                    sensitivity_label="closed_session",
                )
            ],
        )
    except PacketExportError as exc:
        assert exc.code == "closed_session_source_not_public"
        assert "Remove restricted sources" in exc.fix
    else:  # pragma: no cover - assertion helper
        raise AssertionError("closed-session source must not export into a public bundle")


async def test_api_creates_valid_packet_export_bundle(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CIVICCLERK_EXPORT_ROOT", str(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meetings",
            json={
                "title": "Export Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        meeting_id = created.json()["id"]
        await client.post(
            f"/meetings/{meeting_id}/packet-snapshots",
            json={
                "agenda_item_ids": ["item-1"],
                "actor": "clerk@example.gov",
            },
        )

        exported = await client.post(
            f"/meetings/{meeting_id}/export-bundle",
            json={
                "bundle_name": "api-export",
                "actor": "clerk@example.gov",
                "sources": [
                    {
                        "source_id": "staff-report-1",
                        "title": "Staff report",
                        "kind": "document",
                        "source_system": "local_file",
                        "source_path": "staff-report.pdf",
                    }
                ],
            },
        )

    assert exported.status_code == 201
    payload = exported.json()
    assert payload["civiccore_version"] == CIVICCORE_VERSION
    assert payload["generated_files"] == ["packet.json", "provenance.json", "notices.json"]
    assert Path(payload["bundle_path"]) == tmp_path / "api-export"
    validate_bundle(payload["bundle_path"])


async def test_api_rejects_closed_session_source_in_public_export(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CIVICCLERK_EXPORT_ROOT", str(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meetings",
            json={
                "title": "Closed Export Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        meeting_id = created.json()["id"]
        await client.post(
            f"/meetings/{meeting_id}/packet-snapshots",
            json={
                "agenda_item_ids": ["item-1"],
                "actor": "clerk@example.gov",
            },
        )

        exported = await client.post(
            f"/meetings/{meeting_id}/export-bundle",
            json={
                "bundle_name": "api-public-export",
                "actor": "clerk@example.gov",
                "sources": [
                    {
                        "source_id": "closed-note",
                        "title": "Closed session attorney memo",
                        "kind": "document",
                        "sensitivity_label": "closed_session",
                    }
                ],
            },
        )

    assert exported.status_code == 422
    assert exported.json()["detail"]["code"] == "closed_session_source_not_public"


async def test_api_rejects_absolute_or_parent_packet_export_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CIVICCLERK_EXPORT_ROOT", str(tmp_path))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post(
            "/meetings",
            json={
                "title": "Path Safety Meeting",
                "meeting_type": "regular",
                "scheduled_start": "2026-05-05T19:00:00Z",
            },
        )
        meeting_id = created.json()["id"]
        await client.post(
            f"/meetings/{meeting_id}/packet-snapshots",
            json={
                "agenda_item_ids": ["item-1"],
                "actor": "clerk@example.gov",
            },
        )

        absolute = await client.post(
            f"/meetings/{meeting_id}/export-bundle",
            json={
                "bundle_name": str(tmp_path / "outside"),
                "actor": "clerk@example.gov",
                "sources": [{"source_id": "s1", "title": "Staff report"}],
            },
        )
        traversal = await client.post(
            f"/meetings/{meeting_id}/export-bundle",
            json={
                "bundle_name": "../outside",
                "actor": "clerk@example.gov",
                "sources": [{"source_id": "s1", "title": "Staff report"}],
            },
        )
        root = await client.post(
            f"/meetings/{meeting_id}/export-bundle",
            json={
                "bundle_name": ".",
                "actor": "clerk@example.gov",
                "sources": [{"source_id": "s1", "title": "Staff report"}],
            },
        )

    assert absolute.status_code == 422
    assert traversal.status_code == 422
    assert root.status_code == 422
    assert "CIVICCLERK_EXPORT_ROOT" in absolute.json()["detail"]["message"]
