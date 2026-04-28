"""Agenda item lifecycle enforcement for CivicClerk."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy import Engine, create_engine


AGENDA_ITEM_LIFECYCLE = (
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
)

VALID_TRANSITIONS = dict(zip(AGENDA_ITEM_LIFECYCLE[:-1], AGENDA_ITEM_LIFECYCLE[1:], strict=True))


@dataclass(frozen=True)
class TransitionResult:
    allowed: bool
    http_status: int
    message: str
    audit_entry: dict[str, str]


@dataclass
class AgendaItemRecord:
    id: str
    title: str
    department_name: str
    status: str = "DRAFTED"
    audit_entries: list[dict[str, str]] = field(default_factory=list)

    def public_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "title": self.title,
            "department_name": self.department_name,
            "status": self.status,
        }


class AgendaItemStore:
    """Small in-memory store used when no agenda item database URL is configured."""

    def __init__(self) -> None:
        self._items: dict[str, AgendaItemRecord] = {}

    def create(self, *, title: str, department_name: str) -> AgendaItemRecord:
        item = AgendaItemRecord(
            id=str(uuid4()),
            title=title,
            department_name=department_name,
        )
        self._items[item.id] = item
        return item

    def get(self, item_id: str) -> AgendaItemRecord | None:
        return self._items.get(item_id)

    def transition(self, *, item_id: str, to_status: str, actor: str) -> TransitionResult | None:
        item = self.get(item_id)
        if item is None:
            return None
        result = validate_agenda_item_transition(
            agenda_item_id=item_id,
            from_status=item.status,
            to_status=to_status,
            actor=actor,
        )
        item.audit_entries.append(result.audit_entry)
        if result.allowed:
            item.status = to_status
        return result


metadata = sa.MetaData()

agenda_item_lifecycle_records = sa.Table(
    "agenda_item_lifecycle_records",
    metadata,
    sa.Column("id", sa.String(64), primary_key=True),
    sa.Column("title", sa.String(500), nullable=False),
    sa.Column("department_name", sa.String(255), nullable=False),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("audit_entries", sa.JSON(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    schema="civicclerk",
)


class AgendaItemRepository:
    """SQLAlchemy-backed agenda item lifecycle records.

    Configure with `CIVICCLERK_AGENDA_ITEM_DB_URL` in the FastAPI runtime or pass
    a SQLAlchemy URL directly in tests and local smoke checks.
    """

    def __init__(self, *, db_url: str | None = None, engine: Engine | None = None) -> None:
        base_engine = engine or create_engine(db_url or "sqlite+pysqlite:///:memory:", future=True)
        if base_engine.dialect.name == "sqlite":
            self.engine = base_engine.execution_options(schema_translate_map={"civicclerk": None})
        else:
            self.engine = base_engine
            with self.engine.begin() as connection:
                connection.execute(sa.text("CREATE SCHEMA IF NOT EXISTS civicclerk"))
        metadata.create_all(self.engine)

    def create(self, *, title: str, department_name: str) -> AgendaItemRecord:
        now = datetime.now(UTC)
        item = AgendaItemRecord(id=str(uuid4()), title=title, department_name=department_name)
        with self.engine.begin() as connection:
            connection.execute(
                agenda_item_lifecycle_records.insert().values(
                    id=item.id,
                    title=item.title,
                    department_name=item.department_name,
                    status=item.status,
                    audit_entries=item.audit_entries,
                    created_at=now,
                    updated_at=now,
                )
            )
        return item

    def get(self, item_id: str) -> AgendaItemRecord | None:
        with self.engine.begin() as connection:
            row = connection.execute(
                sa.select(agenda_item_lifecycle_records).where(
                    agenda_item_lifecycle_records.c.id == item_id
                )
            ).mappings().first()
        return _row_to_item(row) if row is not None else None

    def transition(self, *, item_id: str, to_status: str, actor: str) -> TransitionResult | None:
        item = self.get(item_id)
        if item is None:
            return None
        result = validate_agenda_item_transition(
            agenda_item_id=item_id,
            from_status=item.status,
            to_status=to_status,
            actor=actor,
        )
        audit_entries = [*item.audit_entries, result.audit_entry]
        status = to_status if result.allowed else item.status
        with self.engine.begin() as connection:
            connection.execute(
                agenda_item_lifecycle_records.update()
                .where(agenda_item_lifecycle_records.c.id == item_id)
                .values(
                    status=status,
                    audit_entries=audit_entries,
                    updated_at=datetime.now(UTC),
                )
            )
        return result


def validate_agenda_item_transition(
    *,
    agenda_item_id: str,
    from_status: str,
    to_status: str,
    actor: str,
) -> TransitionResult:
    """Validate one agenda item lifecycle transition and produce an audit entry."""
    base_entry = {
        "agenda_item_id": agenda_item_id,
        "actor": actor,
        "from_status": from_status,
        "to_status": to_status,
    }

    if from_status not in AGENDA_ITEM_LIFECYCLE:
        return TransitionResult(
            allowed=False,
            http_status=422,
            message=f"Unknown current status {from_status}. Use one of {', '.join(AGENDA_ITEM_LIFECYCLE)}.",
            audit_entry={
                **base_entry,
                "outcome": "rejected",
                "reason": "unknown current agenda item status",
            },
        )

    if to_status not in AGENDA_ITEM_LIFECYCLE:
        return TransitionResult(
            allowed=False,
            http_status=422,
            message=f"Unknown requested status {to_status}. Use one of {', '.join(AGENDA_ITEM_LIFECYCLE)}.",
            audit_entry={
                **base_entry,
                "outcome": "rejected",
                "reason": "unknown requested agenda item status",
            },
        )

    expected = VALID_TRANSITIONS.get(from_status)
    if expected == to_status:
        return TransitionResult(
            allowed=True,
            http_status=200,
            message="transition allowed",
            audit_entry={
                **base_entry,
                "outcome": "allowed",
                "reason": "transition allowed",
            },
        )

    next_status = expected if expected is not None else "no further status"
    return TransitionResult(
        allowed=False,
        http_status=409,
        message=(
            f"Invalid agenda item lifecycle transition. The canonical next status "
            f"from {from_status} is {next_status}. Next valid status is {next_status}."
        ),
        audit_entry={
            **base_entry,
            "outcome": "rejected",
            "reason": "invalid agenda item lifecycle transition",
        },
    )


def _row_to_item(row) -> AgendaItemRecord:
    data = dict(row)
    return AgendaItemRecord(
        id=data["id"],
        title=data["title"],
        department_name=data["department_name"],
        status=data["status"],
        audit_entries=list(data["audit_entries"]),
    )


__all__ = [
    "AGENDA_ITEM_LIFECYCLE",
    "VALID_TRANSITIONS",
    "AgendaItemRepository",
    "AgendaItemRecord",
    "AgendaItemStore",
    "TransitionResult",
    "agenda_item_lifecycle_records",
    "validate_agenda_item_transition",
]
