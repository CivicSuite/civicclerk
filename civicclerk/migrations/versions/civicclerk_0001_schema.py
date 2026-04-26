"""Create CivicClerk canonical schema."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from civiccore.migrations.guards import idempotent_create_table


revision = "civicclerk_0001_schema"
down_revision = None
branch_labels = None
depends_on = None


def _id_column() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS civicclerk")

    idempotent_create_table("meeting_bodies", _id_column(), sa.Column("name", sa.String(255), nullable=False), sa.Column("body_type", sa.String(100), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")), *_timestamps(), schema="civicclerk")
    idempotent_create_table("meetings", _id_column(), sa.Column("meeting_body_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("title", sa.String(255), nullable=False), sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False), sa.Column("status", sa.String(80), nullable=False), *_timestamps(), sa.ForeignKeyConstraint(["meeting_body_id"], ["civicclerk.meeting_bodies.id"]), schema="civicclerk")
    idempotent_create_table("agenda_items", _id_column(), sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("title", sa.String(500), nullable=False), sa.Column("status", sa.String(80), nullable=False), sa.Column("department_name", sa.String(255), nullable=False), *_timestamps(), sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]), schema="civicclerk")
    idempotent_create_table("staff_reports", _id_column(), sa.Column("agenda_item_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("title", sa.String(500), nullable=False), sa.Column("body", sa.Text(), nullable=False), *_timestamps(), sa.ForeignKeyConstraint(["agenda_item_id"], ["civicclerk.agenda_items.id"]), schema="civicclerk")
    idempotent_create_table("motions", _id_column(), sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("agenda_item_id", postgresql.UUID(as_uuid=True), nullable=True), sa.Column("text", sa.Text(), nullable=False), sa.Column("correction_of_id", postgresql.UUID(as_uuid=True), nullable=True), *_timestamps(), sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]), sa.ForeignKeyConstraint(["agenda_item_id"], ["civicclerk.agenda_items.id"]), sa.ForeignKeyConstraint(["correction_of_id"], ["civicclerk.motions.id"]), schema="civicclerk")
    idempotent_create_table("votes", _id_column(), sa.Column("motion_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("voter_name", sa.String(255), nullable=False), sa.Column("vote", sa.String(50), nullable=False), sa.Column("correction_of_id", postgresql.UUID(as_uuid=True), nullable=True), *_timestamps(), sa.ForeignKeyConstraint(["motion_id"], ["civicclerk.motions.id"]), sa.ForeignKeyConstraint(["correction_of_id"], ["civicclerk.votes.id"]), schema="civicclerk")
    idempotent_create_table("public_comments", _id_column(), sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("agenda_item_id", postgresql.UUID(as_uuid=True), nullable=True), sa.Column("commenter_name", sa.String(255), nullable=False), sa.Column("body", sa.Text(), nullable=False), sa.Column("visibility", sa.String(80), nullable=False), *_timestamps(), sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]), sa.ForeignKeyConstraint(["agenda_item_id"], ["civicclerk.agenda_items.id"]), schema="civicclerk")
    idempotent_create_table("notices", _id_column(), sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("notice_type", sa.String(120), nullable=False), sa.Column("due_at", sa.DateTime(timezone=True), nullable=False), sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True), sa.Column("statutory_basis", sa.Text(), nullable=False), *_timestamps(), sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]), schema="civicclerk")
    idempotent_create_table("minutes", _id_column(), sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("status", sa.String(80), nullable=False), sa.Column("body", sa.Text(), nullable=False), *_timestamps(), sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]), schema="civicclerk")
    idempotent_create_table("transcripts", _id_column(), sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("source_uri", sa.Text(), nullable=False), sa.Column("status", sa.String(80), nullable=False), *_timestamps(), sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]), schema="civicclerk")
    idempotent_create_table("action_items", _id_column(), sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("status", sa.String(80), nullable=False), *_timestamps(), sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]), schema="civicclerk")
    idempotent_create_table("packet_versions", _id_column(), sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("snapshot_uri", sa.Text(), nullable=False), *_timestamps(), sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]), schema="civicclerk")
    idempotent_create_table("ordinances_adopted", _id_column(), sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("agenda_item_id", postgresql.UUID(as_uuid=True), nullable=True), sa.Column("ordinance_number", sa.String(120), nullable=False), *_timestamps(), sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]), sa.ForeignKeyConstraint(["agenda_item_id"], ["civicclerk.agenda_items.id"]), schema="civicclerk")
    idempotent_create_table("closed_sessions", _id_column(), sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("statutory_basis", sa.Text(), nullable=False), sa.Column("access_level", sa.String(120), nullable=False), *_timestamps(), sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]), schema="civicclerk")


def downgrade() -> None:
    for table_name in ["closed_sessions", "ordinances_adopted", "packet_versions", "action_items", "transcripts", "minutes", "notices", "public_comments", "votes", "motions", "staff_reports", "agenda_items", "meetings", "meeting_bodies"]:
        op.drop_table(table_name, schema="civicclerk")
