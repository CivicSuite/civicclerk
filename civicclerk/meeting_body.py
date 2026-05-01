"""Database-backed meeting body records for Sprint 1 staff workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import Engine, create_engine


metadata = sa.MetaData()

meeting_bodies = sa.Table(
    "meeting_bodies",
    metadata,
    sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
    sa.Column("name", sa.String(255), nullable=False),
    sa.Column("body_type", sa.String(100), nullable=False),
    sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civicclerk",
)


@dataclass(frozen=True)
class MeetingBodyRecord:
    """One municipal body that can own public meetings."""

    id: UUID
    name: str
    body_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    def public_dict(self) -> dict[str, str | bool]:
        return {
            "id": str(self.id),
            "name": self.name,
            "body_type": self.body_type,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class MeetingBodyRepository:
    """SQLAlchemy-backed repository for meeting body CRUD."""

    def __init__(self, *, db_url: str | None = None, engine: Engine | None = None) -> None:
        base_engine = engine or create_engine(db_url or "sqlite+pysqlite:///:memory:", future=True)
        if base_engine.dialect.name == "sqlite":
            self.engine = base_engine.execution_options(schema_translate_map={"civicclerk": None})
        else:
            self.engine = base_engine
            with self.engine.begin() as connection:
                connection.execute(sa.text("CREATE SCHEMA IF NOT EXISTS civicclerk"))
        metadata.create_all(self.engine)

    def create(self, *, name: str, body_type: str, is_active: bool = True) -> MeetingBodyRecord:
        now = datetime.now(UTC)
        body_id = uuid4()
        values = {
            "id": body_id,
            "name": name,
            "body_type": body_type,
            "is_active": is_active,
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            connection.execute(meeting_bodies.insert().values(**values))
        return self.get(str(body_id)) or _row_to_record(values)

    def get(self, body_id: str) -> MeetingBodyRecord | None:
        parsed_id = _parse_body_id(body_id)
        if parsed_id is None:
            return None
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(meeting_bodies).where(meeting_bodies.c.id == parsed_id)
            ).mappings().first()
        return _row_to_record(row) if row is not None else None

    def list(self, *, active_only: bool = False) -> list[MeetingBodyRecord]:
        statement = sa.select(meeting_bodies).order_by(meeting_bodies.c.name)
        if active_only:
            statement = statement.where(meeting_bodies.c.is_active.is_(True))
        with self.engine.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_row_to_record(row) for row in rows]

    def update(
        self,
        *,
        body_id: str,
        name: str | None = None,
        body_type: str | None = None,
        is_active: bool | None = None,
    ) -> MeetingBodyRecord | None:
        existing = self.get(body_id)
        if existing is None:
            return None
        values: dict[str, str | bool | datetime] = {"updated_at": datetime.now(UTC)}
        if name is not None:
            values["name"] = name
        if body_type is not None:
            values["body_type"] = body_type
        if is_active is not None:
            values["is_active"] = is_active
        with self.engine.begin() as connection:
            connection.execute(
                meeting_bodies.update().where(meeting_bodies.c.id == existing.id).values(**values)
            )
        return self.get(body_id)

    def deactivate(self, body_id: str) -> MeetingBodyRecord | None:
        """Deactivate rather than hard-delete a legal meeting body."""

        return self.update(body_id=body_id, is_active=False)


def _parse_body_id(body_id: str) -> UUID | None:
    try:
        return UUID(body_id)
    except ValueError:
        return None


def _row_to_record(row) -> MeetingBodyRecord:
    data = dict(row)
    return MeetingBodyRecord(
        id=data["id"],
        name=data["name"],
        body_type=data["body_type"],
        is_active=bool(data["is_active"]),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


__all__ = ["MeetingBodyRecord", "MeetingBodyRepository", "meeting_bodies"]
