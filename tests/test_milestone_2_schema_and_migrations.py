from __future__ import annotations

import ast
from contextlib import nullcontext
import importlib
import os
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.runtime.environment import EnvironmentContext
from sqlalchemy import ForeignKeyConstraint


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
    "civiccore.audit",
    "civiccore.ingestion",
    "civiccore.search",
    "civiccore.notifications",
    "civiccore.connectors",
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
                    "CivicClerk may only FK into CivicCore tables that exist in v0.2.0; "
                    f"unexpected target: {target}"
                )


def test_alembic_scaffold_exists_for_civicclerk_schema_chain() -> None:
    expected = [
        ROOT / "civicclerk" / "migrations" / "alembic.ini",
        ROOT / "civicclerk" / "migrations" / "env.py",
        migration_path(),
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
    assert "version_table=\"alembic_version_civicclerk\"" in text or "version_table = \"alembic_version_civicclerk\"" in text
    assert "target_metadata = Base.metadata" in text


def test_alembic_command_boots_with_one_database_url_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise Alembic's env.py path, not just source text.

    PostgreSQL-only DDL is covered by the migration source and later container
    gates. This smoke test proves the env bootstrap no longer fails before
    migrations start: one Config URL feeds both CivicClerk's engine and
    CivicCore's runner.
    """
    seen: dict[str, object] = {"configured": False, "ran": False}
    db_url = "postgresql+psycopg2://clerk:test@localhost:5432/civicclerk_test"

    class FakeConnection:
        def __enter__(self) -> "FakeConnection":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    class FakeEngine:
        def connect(self) -> FakeConnection:
            return FakeConnection()

    def fake_engine_from_config(
        section: dict[str, object],
        prefix: str,
        poolclass: type[object],
    ) -> FakeEngine:
        seen["engine_url"] = section["sqlalchemy.url"]
        seen["prefix"] = prefix
        seen["poolclass"] = poolclass
        return FakeEngine()

    def fake_configure(self: EnvironmentContext, **kwargs: object) -> None:
        seen["configured"] = True
        seen["version_table"] = kwargs["version_table"]

    def fake_run_migrations(self: EnvironmentContext, **kwargs: object) -> None:
        seen["ran"] = True

    def fake_begin_transaction(self: EnvironmentContext) -> nullcontext[None]:
        return nullcontext()

    def fake_civiccore_upgrade_to_head() -> None:
        seen["civiccore_url"] = os.environ["DATABASE_URL"]

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(sa, "engine_from_config", fake_engine_from_config)
    monkeypatch.setattr(EnvironmentContext, "configure", fake_configure)
    monkeypatch.setattr(EnvironmentContext, "begin_transaction", fake_begin_transaction)
    monkeypatch.setattr(EnvironmentContext, "run_migrations", fake_run_migrations)
    monkeypatch.setattr(
        "civiccore.migrations.runner.upgrade_to_head",
        fake_civiccore_upgrade_to_head,
    )

    cfg = Config(str(ROOT / "civicclerk" / "migrations" / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(cfg, "head")

    assert seen["engine_url"] == db_url
    assert seen["civiccore_url"] == db_url
    assert seen["version_table"] == "alembic_version_civicclerk"
    assert seen["configured"] is True
    assert seen["ran"] is True


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


def test_docs_and_changelog_record_schema_milestone_without_claiming_lifecycle_behavior() -> None:
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").lower()
    manual = (ROOT / "USER-MANUAL.md").read_text(encoding="utf-8").lower()
    landing = (ROOT / "docs" / "index.html").read_text(encoding="utf-8").lower()

    for text in [changelog, manual, landing]:
        assert "canonical schema" in text
        assert "alembic" in text
        assert "agenda lifecycle enforcement shipped" not in text
        assert "meeting workflows are implemented" not in text
