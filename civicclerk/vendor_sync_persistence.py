"""Persistent vendor live-sync source, run, and failure records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Engine, create_engine

from civicclerk.vendor_live_sync import (
    VendorLiveSyncConfig,
    VendorSyncRunResult,
    VendorSyncState,
    apply_vendor_sync_result,
    live_sync_config_ready,
    operator_status,
    validate_live_sync_config,
)


metadata = sa.MetaData()

vendor_sync_sources = sa.Table(
    "vendor_sync_sources",
    metadata,
    sa.Column("id", sa.String(64), primary_key=True),
    sa.Column("connector", sa.String(80), nullable=False),
    sa.Column("source_name", sa.String(255), nullable=False),
    sa.Column("source_url", sa.Text(), nullable=False),
    sa.Column("auth_method", sa.String(80), nullable=False),
    sa.Column("consecutive_failure_count", sa.Integer(), nullable=False, default=0),
    sa.Column("active_failure_count", sa.Integer(), nullable=False, default=0),
    sa.Column("sync_paused", sa.Boolean(), nullable=False, default=False),
    sa.Column("sync_paused_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("sync_paused_reason", sa.String(255), nullable=True),
    sa.Column("last_sync_status", sa.String(80), nullable=True),
    sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("last_success_cursor_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civicclerk",
)

vendor_sync_run_log = sa.Table(
    "vendor_sync_run_log",
    metadata,
    sa.Column("id", sa.String(64), primary_key=True),
    sa.Column("source_id", sa.String(64), nullable=False),
    sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("records_discovered", sa.Integer(), nullable=False),
    sa.Column("records_succeeded", sa.Integer(), nullable=False),
    sa.Column("records_failed", sa.Integer(), nullable=False),
    sa.Column("retries_attempted", sa.Integer(), nullable=False),
    sa.Column("error_summary", sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(["source_id"], ["civicclerk.vendor_sync_sources.id"], ondelete="CASCADE"),
    schema="civicclerk",
)

vendor_sync_failures = sa.Table(
    "vendor_sync_failures",
    metadata,
    sa.Column("id", sa.String(64), primary_key=True),
    sa.Column("source_id", sa.String(64), nullable=False),
    sa.Column("run_id", sa.String(64), nullable=False),
    sa.Column("source_path", sa.Text(), nullable=False),
    sa.Column("error_message", sa.Text(), nullable=False),
    sa.Column("error_class", sa.String(200), nullable=False),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("first_failed_at", sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(["source_id"], ["civicclerk.vendor_sync_sources.id"], ondelete="CASCADE"),
    sa.ForeignKeyConstraint(["run_id"], ["civicclerk.vendor_sync_run_log.id"], ondelete="CASCADE"),
    schema="civicclerk",
)


@dataclass(frozen=True)
class VendorSyncSourceRecord:
    id: str
    connector: str
    source_name: str
    source_url: str
    auth_method: str
    consecutive_failure_count: int
    active_failure_count: int
    sync_paused: bool
    sync_paused_at: datetime | None
    sync_paused_reason: str | None
    last_sync_status: str | None
    last_error_at: datetime | None
    last_success_cursor_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def state(self) -> VendorSyncState:
        return VendorSyncState(
            connector=self.connector,
            source_name=self.source_name,
            consecutive_failure_count=self.consecutive_failure_count,
            active_failure_count=self.active_failure_count,
            sync_paused=self.sync_paused,
            sync_paused_at=self.sync_paused_at,
            sync_paused_reason=self.sync_paused_reason,
            last_sync_status=self.last_sync_status,
            last_error_at=self.last_error_at,
        )

    def public_dict(self) -> dict:
        status = operator_status(self.state())
        return {
            "id": self.id,
            "connector": self.connector,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "auth_method": self.auth_method,
            "health_status": status["health_status"],
            "consecutive_failure_count": self.consecutive_failure_count,
            "active_failure_count": self.active_failure_count,
            "sync_paused": self.sync_paused,
            "sync_paused_at": self.sync_paused_at.isoformat() if self.sync_paused_at else None,
            "sync_paused_reason": self.sync_paused_reason,
            "last_sync_status": self.last_sync_status,
            "last_error_at": self.last_error_at.isoformat() if self.last_error_at else None,
            "last_success_cursor_at": self.last_success_cursor_at.isoformat()
            if self.last_success_cursor_at
            else None,
            "message": status["message"],
            "fix": status["fix"],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass(frozen=True)
class VendorSyncRunRecord:
    id: str
    source_id: str
    status: str
    records_discovered: int
    records_succeeded: int
    records_failed: int
    retries_attempted: int
    error_summary: str | None
    started_at: datetime
    finished_at: datetime

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "status": self.status,
            "records_discovered": self.records_discovered,
            "records_succeeded": self.records_succeeded,
            "records_failed": self.records_failed,
            "retries_attempted": self.retries_attempted,
            "error_summary": self.error_summary,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
        }


class VendorSyncConfigError(ValueError):
    def __init__(self, checks: list[dict]) -> None:
        super().__init__("Vendor live-sync source configuration is not ready.")
        self.checks = checks

    def public_dict(self) -> dict:
        return {
            "message": "Vendor live-sync source configuration is not ready.",
            "fix": "Fix each failed readiness check, then save the source again.",
            "checks": self.checks,
        }


class VendorSyncRepository:
    """SQLAlchemy-backed vendor live-sync source and run-history store."""

    def __init__(self, *, db_url: str | None = None, engine: Engine | None = None) -> None:
        base_engine = engine or create_engine(db_url or "sqlite+pysqlite:///:memory:", future=True)
        if base_engine.dialect.name == "sqlite":
            self.engine = base_engine.execution_options(schema_translate_map={"civicclerk": None})
        else:
            self.engine = base_engine
            with self.engine.begin() as connection:
                connection.execute(sa.text("CREATE SCHEMA IF NOT EXISTS civicclerk"))
        metadata.create_all(self.engine)
        self._ensure_cursor_columns()

    def _ensure_cursor_columns(self) -> None:
        schema = None if self.engine.dialect.name == "sqlite" else "civicclerk"
        table_name = "vendor_sync_sources"
        with self.engine.begin() as connection:
            inspector = sa.inspect(connection)
            column_names = {column["name"] for column in inspector.get_columns(table_name, schema=schema)}
            if "last_success_cursor_at" in column_names:
                return
            if self.engine.dialect.name == "postgresql":
                connection.execute(
                    sa.text(
                        "ALTER TABLE civicclerk.vendor_sync_sources "
                        "ADD COLUMN IF NOT EXISTS last_success_cursor_at TIMESTAMP WITH TIME ZONE"
                    )
                )
            else:
                connection.execute(sa.text("ALTER TABLE vendor_sync_sources ADD COLUMN last_success_cursor_at DATETIME"))

    def create_source(
        self,
        *,
        connector: str,
        source_name: str,
        source_url: str,
        auth_method: str,
    ) -> VendorSyncSourceRecord:
        checks = validate_live_sync_config(
            VendorLiveSyncConfig(
                connector=connector,
                source_url=source_url,
                auth_method=auth_method,  # type: ignore[arg-type]
            )
        )
        public_checks = [check.__dict__ for check in checks]
        if not live_sync_config_ready(checks):
            raise VendorSyncConfigError(public_checks)
        now = datetime.now(UTC)
        source_id = str(uuid4())
        values = {
            "id": source_id,
            "connector": connector.strip().lower(),
            "source_name": source_name,
            "source_url": source_url,
            "auth_method": auth_method,
            "consecutive_failure_count": 0,
            "active_failure_count": 0,
            "sync_paused": False,
            "sync_paused_at": None,
            "sync_paused_reason": None,
            "last_sync_status": None,
            "last_error_at": None,
            "last_success_cursor_at": None,
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            connection.execute(vendor_sync_sources.insert().values(**values))
        return self.get_source(source_id) or _row_to_source(values)

    def get_source(self, source_id: str) -> VendorSyncSourceRecord | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(vendor_sync_sources).where(vendor_sync_sources.c.id == source_id)
            ).mappings().first()
        return _row_to_source(row) if row is not None else None

    def list_sources(self) -> list[VendorSyncSourceRecord]:
        with self.engine.begin() as connection:
            rows = connection.execute(
                sa.select(vendor_sync_sources).order_by(vendor_sync_sources.c.updated_at.desc())
            ).mappings().all()
        return [_row_to_source(row) for row in rows]

    def reset_success_cursor(
        self,
        *,
        source_id: str,
        cursor_at: datetime | None = None,
        reset_reason: str,
    ) -> tuple[VendorSyncSourceRecord, VendorSyncRunRecord] | None:
        """Move or clear the delta cursor so operators can force safe reconciliation."""

        source = self.get_source(source_id)
        if source is None:
            return None
        now = datetime.now(UTC)
        run_id = str(uuid4())
        if cursor_at is not None and cursor_at.tzinfo is None:
            cursor_at = cursor_at.replace(tzinfo=UTC)
        with self.engine.begin() as connection:
            connection.execute(
                vendor_sync_run_log.insert().values(
                    id=run_id,
                    source_id=source_id,
                    started_at=now,
                    finished_at=now,
                    status="cursor_reset",
                    records_discovered=0,
                    records_succeeded=0,
                    records_failed=0,
                    retries_attempted=0,
                    error_summary=reset_reason.strip(),
                )
            )
            connection.execute(
                vendor_sync_sources.update()
                .where(vendor_sync_sources.c.id == source_id)
                .values(last_success_cursor_at=cursor_at, updated_at=now)
            )
        updated_source = self.get_source(source_id)
        reset_event = self.get_run(run_id)
        if updated_source is None or reset_event is None:
            return None
        return updated_source, reset_event

    def record_run(
        self,
        *,
        source_id: str,
        result: VendorSyncRunResult,
        advance_success_cursor: bool = False,
        cursor_at: datetime | None = None,
    ) -> tuple[VendorSyncSourceRecord, VendorSyncRunRecord] | None:
        source = self.get_source(source_id)
        if source is None:
            return None
        now = datetime.now(UTC)
        updated_state = apply_vendor_sync_result(source.state(), result, now=now)
        active_failure_count = source.active_failure_count
        if result.records_failed > 0:
            active_failure_count += result.records_failed
        elif result.records_succeeded > 0:
            active_failure_count = 0
        run_id = str(uuid4())
        status = updated_state.last_sync_status or "success"
        last_success_cursor_at = source.last_success_cursor_at
        if advance_success_cursor and result.records_failed == 0 and result.records_succeeded > 0:
            last_success_cursor_at = cursor_at or now
        with self.engine.begin() as connection:
            connection.execute(
                vendor_sync_run_log.insert().values(
                    id=run_id,
                    source_id=source_id,
                    started_at=now,
                    finished_at=now,
                    status=status,
                    records_discovered=result.records_discovered,
                    records_succeeded=result.records_succeeded,
                    records_failed=result.records_failed,
                    retries_attempted=result.retries_attempted,
                    error_summary=result.error_summary,
                )
            )
            if result.records_failed > 0:
                connection.execute(
                    vendor_sync_failures.insert().values(
                        id=str(uuid4()),
                        source_id=source_id,
                        run_id=run_id,
                        source_path="full-run",
                        error_message=result.error_summary or "Vendor sync run failed.",
                        error_class="VendorSyncRunFailure",
                        status="retrying",
                        first_failed_at=now,
                    )
                )
            connection.execute(
                vendor_sync_sources.update()
                .where(vendor_sync_sources.c.id == source_id)
                .values(
                    consecutive_failure_count=updated_state.consecutive_failure_count,
                    active_failure_count=active_failure_count,
                    sync_paused=updated_state.sync_paused,
                    sync_paused_at=updated_state.sync_paused_at,
                    sync_paused_reason=updated_state.sync_paused_reason,
                    last_sync_status=status,
                    last_error_at=updated_state.last_error_at,
                    last_success_cursor_at=last_success_cursor_at,
                    updated_at=now,
                )
            )
        updated_source = self.get_source(source_id)
        run = self.get_run(run_id)
        if updated_source is None or run is None:
            return None
        return updated_source, run

    def get_run(self, run_id: str) -> VendorSyncRunRecord | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(vendor_sync_run_log).where(vendor_sync_run_log.c.id == run_id)
            ).mappings().first()
        return _row_to_run(row) if row is not None else None

    def list_runs(self, source_id: str, *, limit: int = 10) -> list[VendorSyncRunRecord]:
        with self.engine.begin() as connection:
            rows = connection.execute(
                sa.select(vendor_sync_run_log)
                .where(vendor_sync_run_log.c.source_id == source_id)
                .order_by(vendor_sync_run_log.c.started_at.desc())
                .limit(limit)
            ).mappings().all()
        return [_row_to_run(row) for row in rows]


def _row_to_source(row) -> VendorSyncSourceRecord:
    data = dict(row)
    cursor = data.get("last_success_cursor_at")
    if isinstance(cursor, datetime) and cursor.tzinfo is None:
        data["last_success_cursor_at"] = cursor.replace(tzinfo=UTC)
    return VendorSyncSourceRecord(**data)


def _row_to_run(row) -> VendorSyncRunRecord:
    data = dict(row)
    return VendorSyncRunRecord(**data)


__all__ = [
    "VendorSyncConfigError",
    "VendorSyncRepository",
    "VendorSyncRunRecord",
    "VendorSyncSourceRecord",
    "vendor_sync_failures",
    "vendor_sync_run_log",
    "vendor_sync_sources",
]
