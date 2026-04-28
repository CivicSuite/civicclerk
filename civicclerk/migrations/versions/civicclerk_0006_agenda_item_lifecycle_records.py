"""Create persisted agenda item lifecycle records."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from civicclerk.migrations.guards import idempotent_create_table


revision = "civicclerk_0006_agenda_items"
down_revision = "civicclerk_0005_meetings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    idempotent_create_table(
        "agenda_item_lifecycle_records",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("department_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(80), nullable=False),
        sa.Column("audit_entries", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="civicclerk",
    )


def downgrade() -> None:
    op.drop_table("agenda_item_lifecycle_records", schema="civicclerk")
