from __future__ import annotations

import ast
import importlib
from pathlib import Path
import subprocess
import time
import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import ForeignKeyConstraint, create_engine, text


ROOT = Path(__file__).resolve().parents[1]

CANONICAL_TABLES = [
    "meeting_bodies",
    "meetings",
    "agenda_items",
    "staff_reports",
    "motions",
    "votes",
    "public_comments",
    "notices",
    "minutes",
    "transcripts",
    "action_items",
    "packet_versions",
    "ordinances_adopted",
    "closed_sessions",
]

REQUIRED_COLUMNS = {
    "meeting_bodies": {"id", "name", "body_type", "is_active", "created_at", "updated_at"},
    "meetings": {"id", "meeting_body_id", "title", "scheduled_start", "status", "created_at", "updated_at"},
    "agenda_items": {"id", "meeting_id", "title", "status", "department_name", "created_at", "updated_at"},
    "staff_reports": {"id", "agenda_item_id", "title", "body", "created_at", "updated_at"},
    "motions": {"id", "meeting_id", "agenda_item_id", "text", "correction_of_id", "created_at", "updated_at"},
    "votes": {"id", "motion_id", "voter_name", "vote", "correction_of_id", "created_at", "updated_at"},
    "public_comments": {"id", "meeting_id", "agenda_item_id", "commenter_name", "body", "visibility", "created_at", "updated_at"},
    "notices": {"id", "meeting_id", "notice_type", "due_at", "posted_at", "statutory_basis", "created_at", "updated_at"},
    "minutes": {"id", "meeting_id", "status", "body", "created_at", "updated_at"},
    "transcripts": {"id", "meeting_id", "source_uri", "status", "created_at", "updated_at"},
    "action_items": {"id", "meeting_id", "description", "status", "created_at", "updated_at"},
    "packet_versions": {"id", "meeting_id", "version", "snapshot_uri", "created_at", "updated_at"},
    "ordinances_adopted": {"id", "meeting_id", "agenda_item_id", "ordinance_number", "created_at", "updated_at"},
    "closed_sessions": {"id", "meeting_id", "statutory_basis", "access_level", "created_at", "updated_at"},
}

PLACEHOLDER_TARGET_PREFIXES = {
    "civiccore.auth",
    "civiccore.rbac",
    "civiccore.ingestion",
    "civiccore.search",
    "civiccore.notifications",
    "civiccore.exemptions",
    "civiccore.onboarding",
    "civiccore.catalog",
    "civiccore.verification",
}


def model_module():
    try:
        return importlib.import_module("civicclerk.models")
    except ModuleNotFoundError as exc:
        pytest.fail(f"civicclerk.models must exist for Milestone 2 schema work: {exc}")


def migration_path() -> Path:
    return ROOT / "civicclerk" / "migrations" / "versions" / "civicclerk_0001_schema.py"


def agenda_intake_migration_path() -> Path:
    return ROOT / "civicclerk" / "migrations" / "versions" / "civicclerk_0002_agenda_intake_queue.py"


def packet_assembly_migration_path() -> Path:
    return ROOT / "civicclerk" / "migrations" / "versions" / "civicclerk_0003_packet_assembly_records.py"


def test_canonical_table_models_exist_and_no_tables_are_missing_or_extra() -> None:
    models = model_module()
    metadata = models.Base.metadata

    assert sorted(metadata.tables) == sorted(f"civicclerk.{name}" for name in CANONICAL_TABLES)


def test_models_use_civicclerk_schema_and_civiccore_shared_base() -> None:
    models = model_module()
    civiccore_db = importlib.import_module("civiccore.db")

    assert models.Base is civiccore_db.Base
    for table_name in CANONICAL_TABLES:
        table = models.Base.metadata.tables[f"civicclerk.{table_name}"]
        assert table.schema == "civicclerk"


def test_models_do_not_declare_a_competing_sqlalchemy_base() -> None:
    model_files = list((ROOT / "civicclerk").glob("**/*.py"))
    offenders: list[str] = []
    for path in model_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if getattr(base, "id", None) == "DeclarativeBase":
                        offenders.append(str(path.relative_to(ROOT)))
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "declarative_base":
                offenders.append(str(path.relative_to(ROOT)))

    assert offenders == []


def test_each_canonical_table_has_required_foundation_columns() -> None:
    models = model_module()

    for table_name, expected_columns in REQUIRED_COLUMNS.items():
        table = models.Base.metadata.tables[f"civicclerk.{table_name}"]
        assert expected_columns <= set(table.columns.keys()), table_name


def test_no_foreign_keys_target_civiccore_placeholder_packages_or_unreleased_shared_tables() -> None:
    models = model_module()

    for table in models.Base.metadata.tables.values():
        for constraint in table.constraints:
            if not isinstance(constraint, ForeignKeyConstraint):
                continue
            for element in constraint.elements:
                target = str(element.target_fullname)
                assert not any(target.startswith(prefix) for prefix in PLACEHOLDER_TARGET_PREFIXES)
                assert not target.startswith("civiccore."), (
                    "CivicClerk may only FK into CivicCore tables that exist in v0.3.0; "
                    f"unexpected target: {target}"
                )


def test_alembic_scaffold_exists_for_civicclerk_schema_chain() -> None:
    expected = [
        ROOT / "civicclerk" / "migrations" / "alembic.ini",
        ROOT / "civicclerk" / "migrations" / "env.py",
        migration_path(),
        agenda_intake_migration_path(),
        packet_assembly_migration_path(),
    ]

    for path in expected:
        assert path.exists(), f"Missing migration scaffold file: {path.relative_to(ROOT)}"


def test_alembic_env_runs_civiccore_baseline_first_and_uses_separate_version_table() -> None:
    env_py = ROOT / "civicclerk" / "migrations" / "env.py"
    assert env_py.exists(), "civicclerk migrations env.py must exist."
    text = env_py.read_text(encoding="utf-8")

    assert "civiccore.migrations.runner" in text
    assert "upgrade_to_head" in text
    assert "_database_url()" in text
    assert "_run_civiccore_migrations(section[\"sqlalchemy.url\"])" in text
    assert "subprocess.run" in text
    assert "version_table=\"alembic_version_civicclerk\"" in text or "version_table = \"alembic_version_civicclerk\"" in text
    assert "target_metadata = Base.metadata" in text


def test_alembic_command_upgrades_real_pgvector_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run the actual operator migration path against disposable Postgres."""
    name = f"civicclerk-m2-{uuid.uuid4().hex[:12]}"
    subprocess.run(
        [
            "docker",
            "run",
            "--name",
            name,
            "-e",
            "POSTGRES_PASSWORD=postgres",
            "-e",
            "POSTGRES_USER=postgres",
            "-e",
            "POSTGRES_DB=civicclerk_test",
            "-p",
            "5432",
            "-d",
            "pgvector/pgvector:pg17",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    try:
        mapped = subprocess.run(
            ["docker", "port", name, "5432/tcp"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        port = mapped.rsplit(":", maxsplit=1)[-1]
        db_url = f"postgresql+psycopg2://postgres:postgres@localhost:{port}/civicclerk_test"
        engine = create_engine(db_url)

        deadline = time.monotonic() + 30
        while True:
            try:
                with engine.connect() as connection:
                    connection.execute(text("select 1"))
                break
            except Exception:
                if time.monotonic() > deadline:
                    raise
                time.sleep(1)

        monkeypatch.setenv("DATABASE_URL", db_url)
        cfg = Config(str(ROOT / "civicclerk" / "migrations" / "alembic.ini"))

        command.upgrade(cfg, "head")
        command.upgrade(cfg, "head")

        with engine.connect() as connection:
            civiccore_revision = connection.execute(
                text("select version_num from alembic_version_civiccore")
            ).scalar_one()
            civicclerk_revision = connection.execute(
                text("select version_num from alembic_version_civicclerk")
            ).scalar_one()
            civicclerk_tables = set(
                connection.execute(
                    text(
                        """
                        select table_name
                        from information_schema.tables
                        where table_schema = 'civicclerk'
                        """
                    )
                ).scalars()
            )

        assert civiccore_revision == "civiccore_0002_llm"
        assert civicclerk_revision == "civicclerk_0003_packet_asm"
        assert civicclerk_tables == set(CANONICAL_TABLES) | {
            "agenda_intake_queue",
            "packet_assembly_records",
        }
    finally:
        subprocess.run(["docker", "rm", "-f", name], check=False, capture_output=True, text=True)


def test_first_migration_declares_revision_and_creates_all_canonical_tables_idempotently() -> None:
    assert migration_path().exists(), "civicclerk_0001_schema migration must exist."
    text = migration_path().read_text(encoding="utf-8")

    assert 'revision = "civicclerk_0001_schema"' in text
    assert "down_revision = None" in text
    assert "idempotent_create_table" in text
    assert 'op.execute("CREATE SCHEMA IF NOT EXISTS civicclerk")' in text

    for table_name in CANONICAL_TABLES:
        assert f'"{table_name}"' in text or f"'{table_name}'" in text
        assert 'schema="civicclerk"' in text or "schema='civicclerk'" in text


def test_migration_table_list_matches_model_metadata() -> None:
    models = model_module()
    text = migration_path().read_text(encoding="utf-8")

    model_tables = {table.name for table in models.Base.metadata.tables.values()}
    for table_name in model_tables:
        assert f'"{table_name}"' in text or f"'{table_name}'" in text


def test_agenda_intake_migration_declares_persistent_queue_table() -> None:
    text = agenda_intake_migration_path().read_text(encoding="utf-8")

    assert 'revision = "civicclerk_0002_intake_queue"' in text
    assert 'down_revision = "civicclerk_0001_schema"' in text
    assert "idempotent_create_table" in text
    assert '"agenda_intake_queue"' in text
    assert '"last_audit_hash"' in text
    assert "postgresql.JSONB()" in text
    assert 'schema="civicclerk"' in text


def test_packet_assembly_migration_declares_persistent_records_table() -> None:
    text = packet_assembly_migration_path().read_text(encoding="utf-8")

    assert 'revision = "civicclerk_0003_packet_asm"' in text
    assert 'down_revision = "civicclerk_0002_intake_queue"' in text
    assert "idempotent_create_table" in text
    assert '"packet_assembly_records"' in text
    assert '"packet_snapshot_id"' in text
    assert '"source_references"' in text
    assert '"citations"' in text
    assert '"last_audit_hash"' in text
    assert "postgresql.JSONB()" in text
    assert 'schema="civicclerk"' in text


def test_docs_and_changelog_record_schema_milestone_without_claiming_lifecycle_behavior() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").lower()
    manual = (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8").lower()
    landing = (ROOT / "docs" / "index.html").read_text(encoding="utf-8").lower()

    for document_text in [changelog, manual, landing]:
        assert "canonical schema" in document_text
        assert "alembic" in document_text
        assert "agenda lifecycle enforcement shipped" not in document_text
        assert "meeting workflows are implemented" not in document_text
