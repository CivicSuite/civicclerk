"""CivicClerk canonical schema metadata."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from civiccore.db import Base


SCHEMA = "civicclerk"


def id_column() -> sa.Column:
    return sa.Column(
        "id",
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


meeting_bodies = sa.Table(
    "meeting_bodies",
    Base.metadata,
    id_column(),
    sa.Column("name", sa.String(255), nullable=False),
    sa.Column("body_type", sa.String(100), nullable=False),
    sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    *timestamps(),
    schema=SCHEMA,
)

meetings = sa.Table(
    "meetings",
    Base.metadata,
    id_column(),
    sa.Column("meeting_body_id", UUID(as_uuid=True), nullable=False),
    sa.Column("title", sa.String(255), nullable=False),
    sa.Column("meeting_type", sa.String(80), nullable=False, server_default=sa.text("'regular'")),
    sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
    sa.Column("location", sa.String(255), nullable=True),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("statutory_basis", sa.Text(), nullable=True),
    sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("cancellation_reason", sa.Text(), nullable=True),
    *timestamps(),
    sa.ForeignKeyConstraint(["meeting_body_id"], ["civicclerk.meeting_bodies.id"]),
    schema=SCHEMA,
)

agenda_items = sa.Table(
    "agenda_items",
    Base.metadata,
    id_column(),
    sa.Column("meeting_id", UUID(as_uuid=True), nullable=False),
    sa.Column("title", sa.String(500), nullable=False),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("department_name", sa.String(255), nullable=False),
    sa.Column("source_references", sa.JSON(), nullable=True),
    sa.Column("staff_report_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    *timestamps(),
    sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]),
    schema=SCHEMA,
)

staff_reports = sa.Table(
    "staff_reports",
    Base.metadata,
    id_column(),
    sa.Column("agenda_item_id", UUID(as_uuid=True), nullable=False),
    sa.Column("title", sa.String(500), nullable=False),
    sa.Column("body", sa.Text(), nullable=False),
    sa.Column("document_ref", sa.Text(), nullable=True),
    sa.Column("source_references", sa.JSON(), nullable=True),
    sa.Column("sensitivity_label", sa.String(80), nullable=False, server_default=sa.text("'staff_only'")),
    sa.Column("staff_acl_roles", sa.JSON(), nullable=True),
    *timestamps(),
    sa.ForeignKeyConstraint(["agenda_item_id"], ["civicclerk.agenda_items.id"]),
    schema=SCHEMA,
)

motions = sa.Table(
    "motions",
    Base.metadata,
    id_column(),
    sa.Column("meeting_id", UUID(as_uuid=True), nullable=False),
    sa.Column("agenda_item_id", UUID(as_uuid=True), nullable=True),
    sa.Column("text", sa.Text(), nullable=False),
    sa.Column("seconded_by", sa.String(255), nullable=True),
    sa.Column("captured_by", sa.String(255), nullable=True),
    sa.Column("correction_of_id", UUID(as_uuid=True), nullable=True),
    sa.Column("correction_reason", sa.Text(), nullable=True),
    sa.Column("immutable_hash", sa.String(128), nullable=True),
    sa.Column("capture_seq", sa.BigInteger(), nullable=False),
    *timestamps(),
    sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]),
    sa.ForeignKeyConstraint(["agenda_item_id"], ["civicclerk.agenda_items.id"]),
    sa.ForeignKeyConstraint(["correction_of_id"], ["civicclerk.motions.id"]),
    schema=SCHEMA,
)

votes = sa.Table(
    "votes",
    Base.metadata,
    id_column(),
    sa.Column("motion_id", UUID(as_uuid=True), nullable=False),
    sa.Column("voter_name", sa.String(255), nullable=False),
    sa.Column("vote", sa.String(50), nullable=False),
    sa.Column("actor", sa.String(255), nullable=True),
    sa.Column("correction_of_id", UUID(as_uuid=True), nullable=True),
    sa.Column("correction_reason", sa.Text(), nullable=True),
    sa.Column("immutable_hash", sa.String(128), nullable=True),
    sa.Column("capture_seq", sa.BigInteger(), nullable=False),
    *timestamps(),
    sa.ForeignKeyConstraint(["motion_id"], ["civicclerk.motions.id"]),
    sa.ForeignKeyConstraint(["correction_of_id"], ["civicclerk.votes.id"]),
    schema=SCHEMA,
)

public_comments = sa.Table(
    "public_comments",
    Base.metadata,
    id_column(),
    sa.Column("meeting_id", UUID(as_uuid=True), nullable=False),
    sa.Column("agenda_item_id", UUID(as_uuid=True), nullable=True),
    sa.Column("public_record_id", UUID(as_uuid=True), nullable=True),
    sa.Column("commenter_name", sa.String(255), nullable=False),
    sa.Column("body", sa.Text(), nullable=False),
    sa.Column("visibility", sa.String(80), nullable=False),
    sa.Column("status", sa.String(80), nullable=False, server_default=sa.text("'RECEIVED'")),
    sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("moderation_notes", sa.Text(), nullable=True),
    sa.Column("capture_seq", sa.BigInteger(), nullable=False),
    *timestamps(),
    sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]),
    sa.ForeignKeyConstraint(["agenda_item_id"], ["civicclerk.agenda_items.id"]),
    schema=SCHEMA,
)

notices = sa.Table(
    "notices",
    Base.metadata,
    id_column(),
    sa.Column("meeting_id", UUID(as_uuid=True), nullable=False),
    sa.Column("notice_type", sa.String(120), nullable=False),
    sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("statutory_basis", sa.Text(), nullable=False),
    sa.Column("posting_proof", sa.JSON(), nullable=True),
    sa.Column("document_ref", sa.Text(), nullable=True),
    *timestamps(),
    sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]),
    schema=SCHEMA,
)

minutes = sa.Table(
    "minutes",
    Base.metadata,
    id_column(),
    sa.Column("meeting_id", UUID(as_uuid=True), nullable=False),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("body", sa.Text(), nullable=False),
    sa.Column("source_materials", sa.JSON(), nullable=True),
    sa.Column("sentence_citations", sa.JSON(), nullable=True),
    sa.Column("prompt_version", sa.String(120), nullable=True),
    sa.Column("human_approver", sa.String(255), nullable=True),
    sa.Column("model", sa.String(255), nullable=True),
    sa.Column("adopted_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("signed_by", sa.String(255), nullable=True),
    sa.Column("document_ref", sa.Text(), nullable=True),
    sa.Column("capture_seq", sa.BigInteger(), nullable=False),
    *timestamps(),
    sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]),
    schema=SCHEMA,
)

transcripts = sa.Table(
    "transcripts",
    Base.metadata,
    id_column(),
    sa.Column("meeting_id", UUID(as_uuid=True), nullable=False),
    sa.Column("source_uri", sa.Text(), nullable=False),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("document_ref", sa.Text(), nullable=True),
    sa.Column("sensitivity_label", sa.String(80), nullable=False, server_default=sa.text("'staff_only'")),
    sa.Column("staff_acl_roles", sa.JSON(), nullable=True),
    *timestamps(),
    sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]),
    schema=SCHEMA,
)

action_items = sa.Table(
    "action_items",
    Base.metadata,
    id_column(),
    sa.Column("meeting_id", UUID(as_uuid=True), nullable=False),
    sa.Column("description", sa.Text(), nullable=False),
    sa.Column("status", sa.String(80), nullable=False),
    sa.Column("assigned_to", sa.String(255), nullable=True),
    sa.Column("source_motion_id", UUID(as_uuid=True), nullable=True),
    sa.Column("actor", sa.String(255), nullable=True),
    sa.Column("capture_seq", sa.BigInteger(), nullable=False),
    *timestamps(),
    sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]),
    sa.ForeignKeyConstraint(["source_motion_id"], ["civicclerk.motions.id"]),
    schema=SCHEMA,
)

packet_versions = sa.Table(
    "packet_versions",
    Base.metadata,
    id_column(),
    sa.Column("meeting_id", UUID(as_uuid=True), nullable=False),
    sa.Column("version", sa.Integer(), nullable=False),
    sa.Column("snapshot_uri", sa.Text(), nullable=False),
    sa.Column("agenda_item_ids", sa.JSON(), nullable=True),
    sa.Column("snapshot_hash", sa.String(128), nullable=True),
    sa.Column("actor", sa.String(255), nullable=True),
    *timestamps(),
    sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]),
    sa.UniqueConstraint("meeting_id", "version", name="uq_packet_versions_meeting_version"),
    schema=SCHEMA,
)

ordinances_adopted = sa.Table(
    "ordinances_adopted",
    Base.metadata,
    id_column(),
    sa.Column("meeting_id", UUID(as_uuid=True), nullable=False),
    sa.Column("agenda_item_id", UUID(as_uuid=True), nullable=True),
    sa.Column("ordinance_number", sa.String(120), nullable=False),
    sa.Column("title", sa.String(500), nullable=True),
    sa.Column("adopted_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("civiccode_handoff_status", sa.String(80), nullable=True),
    sa.Column("document_ref", sa.Text(), nullable=True),
    *timestamps(),
    sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]),
    sa.ForeignKeyConstraint(["agenda_item_id"], ["civicclerk.agenda_items.id"]),
    schema=SCHEMA,
)

closed_sessions = sa.Table(
    "closed_sessions",
    Base.metadata,
    id_column(),
    sa.Column("meeting_id", UUID(as_uuid=True), nullable=False),
    sa.Column("statutory_basis", sa.Text(), nullable=False),
    sa.Column("access_level", sa.String(120), nullable=False),
    sa.Column("staff_acl_roles", sa.JSON(), nullable=True),
    sa.Column("material_uri", sa.Text(), nullable=True),
    sa.Column("public_redaction", sa.Text(), nullable=True),
    sa.Column("sensitivity_label", sa.String(80), nullable=False, server_default=sa.text("'closed_session'")),
    *timestamps(),
    sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]),
    schema=SCHEMA,
)


__all__ = [
    "Base",
    "SCHEMA",
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
