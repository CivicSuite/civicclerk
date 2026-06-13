"""Create public_meeting_records for the persisted public archive."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from civicclerk.migrations.guards import idempotent_create_table


revision = "civicclerk_0014_public_records"
down_revision = "civicclerk_0013_minutes_model"
branch_labels = None
depends_on = None

SCHEMA = "civicclerk"


def upgrade() -> None:
    idempotent_create_table(
        "public_meeting_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("meeting_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("visibility", sa.String(80), nullable=False),
        sa.Column("posted_agenda", sa.Text(), nullable=False),
        sa.Column("posted_packet", sa.Text(), nullable=False),
        sa.Column("approved_minutes", sa.Text(), nullable=False),
        sa.Column("public_comment_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("plain_language_summary", sa.Text(), nullable=True),
        sa.Column("agenda_download_url", sa.Text(), nullable=True),
        sa.Column("packet_download_url", sa.Text(), nullable=True),
        sa.Column("minutes_download_url", sa.Text(), nullable=True),
        sa.Column("minutes_adopted_at", sa.String(120), nullable=True),
        sa.Column("minutes_signed_by", sa.String(255), nullable=True),
        sa.Column("closed_session_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["meeting_id"], ["civicclerk.meetings.id"]),
        schema=SCHEMA,
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("public_meeting_records", schema=SCHEMA):
        op.drop_table("public_meeting_records", schema=SCHEMA)
