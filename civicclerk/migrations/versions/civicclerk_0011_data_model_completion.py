"""Complete CivicMeetings canonical data model contracts."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "civicclerk_0011_data_model"
down_revision = "civicclerk_0010_vendor_cursor"
branch_labels = None
depends_on = None


SCHEMA = "civicclerk"
PACKET_VERSION_UNIQUE = "uq_packet_versions_meeting_version"
ACTION_ITEM_MOTION_FK = "fk_action_items_source_motion_id_motions"


def upgrade() -> None:
    _add_columns(
        "meetings",
        [
            sa.Column("meeting_type", sa.String(80), nullable=False, server_default=sa.text("'regular'")),
            sa.Column("location", sa.String(255), nullable=True),
            sa.Column("statutory_basis", sa.Text(), nullable=True),
            sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("cancellation_reason", sa.Text(), nullable=True),
        ],
    )
    _add_columns(
        "agenda_items",
        [
            sa.Column("source_references", postgresql.JSONB(), nullable=True),
            sa.Column("staff_report_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        ],
    )
    _add_columns(
        "staff_reports",
        [
            sa.Column("document_ref", sa.Text(), nullable=True),
            sa.Column("source_references", postgresql.JSONB(), nullable=True),
            sa.Column("sensitivity_label", sa.String(80), nullable=False, server_default=sa.text("'staff_only'")),
            sa.Column("staff_acl_roles", postgresql.JSONB(), nullable=True),
        ],
    )
    _add_columns(
        "motions",
        [
            sa.Column("seconded_by", sa.String(255), nullable=True),
            sa.Column("captured_by", sa.String(255), nullable=True),
            sa.Column("correction_reason", sa.Text(), nullable=True),
            sa.Column("immutable_hash", sa.String(128), nullable=True),
        ],
    )
    _add_columns(
        "votes",
        [
            sa.Column("actor", sa.String(255), nullable=True),
            sa.Column("correction_reason", sa.Text(), nullable=True),
            sa.Column("immutable_hash", sa.String(128), nullable=True),
        ],
    )
    _add_columns(
        "public_comments",
        [
            sa.Column("public_record_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("status", sa.String(80), nullable=False, server_default=sa.text("'RECEIVED'")),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("moderation_notes", sa.Text(), nullable=True),
        ],
    )
    _add_columns(
        "notices",
        [
            sa.Column("posting_proof", postgresql.JSONB(), nullable=True),
            sa.Column("document_ref", sa.Text(), nullable=True),
        ],
    )
    _add_columns(
        "minutes",
        [
            sa.Column("source_materials", postgresql.JSONB(), nullable=True),
            sa.Column("sentence_citations", postgresql.JSONB(), nullable=True),
            sa.Column("prompt_version", sa.String(120), nullable=True),
            sa.Column("human_approver", sa.String(255), nullable=True),
            sa.Column("adopted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("signed_by", sa.String(255), nullable=True),
            sa.Column("document_ref", sa.Text(), nullable=True),
        ],
    )
    _add_columns(
        "transcripts",
        [
            sa.Column("document_ref", sa.Text(), nullable=True),
            sa.Column("sensitivity_label", sa.String(80), nullable=False, server_default=sa.text("'staff_only'")),
            sa.Column("staff_acl_roles", postgresql.JSONB(), nullable=True),
        ],
    )
    _add_columns(
        "action_items",
        [
            sa.Column("assigned_to", sa.String(255), nullable=True),
            sa.Column("source_motion_id", postgresql.UUID(as_uuid=True), nullable=True),
        ],
    )
    _add_foreign_key_if_missing(
        ACTION_ITEM_MOTION_FK,
        "action_items",
        "motions",
        ["source_motion_id"],
        ["id"],
    )
    _add_columns(
        "packet_versions",
        [
            sa.Column("agenda_item_ids", postgresql.JSONB(), nullable=True),
            sa.Column("snapshot_hash", sa.String(128), nullable=True),
            sa.Column("actor", sa.String(255), nullable=True),
        ],
    )
    _add_unique_constraint_if_missing(PACKET_VERSION_UNIQUE, "packet_versions", ["meeting_id", "version"])
    _add_columns(
        "ordinances_adopted",
        [
            sa.Column("title", sa.String(500), nullable=True),
            sa.Column("adopted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("civiccode_handoff_status", sa.String(80), nullable=True),
            sa.Column("document_ref", sa.Text(), nullable=True),
        ],
    )
    _add_columns(
        "closed_sessions",
        [
            sa.Column("staff_acl_roles", postgresql.JSONB(), nullable=True),
            sa.Column("material_uri", sa.Text(), nullable=True),
            sa.Column("public_redaction", sa.Text(), nullable=True),
            sa.Column("sensitivity_label", sa.String(80), nullable=False, server_default=sa.text("'closed_session'")),
        ],
    )


def downgrade() -> None:
    _drop_columns("closed_sessions", ["sensitivity_label", "public_redaction", "material_uri", "staff_acl_roles"])
    _drop_columns("ordinances_adopted", ["document_ref", "civiccode_handoff_status", "adopted_at", "title"])
    _drop_unique_constraint_if_present(PACKET_VERSION_UNIQUE, "packet_versions")
    _drop_columns("packet_versions", ["actor", "snapshot_hash", "agenda_item_ids"])
    _drop_foreign_key_if_present(ACTION_ITEM_MOTION_FK, "action_items")
    _drop_columns("action_items", ["source_motion_id", "assigned_to"])
    _drop_columns("transcripts", ["staff_acl_roles", "sensitivity_label", "document_ref"])
    _drop_columns(
        "minutes",
        [
            "document_ref",
            "signed_by",
            "adopted_at",
            "human_approver",
            "prompt_version",
            "sentence_citations",
            "source_materials",
        ],
    )
    _drop_columns("notices", ["document_ref", "posting_proof"])
    _drop_columns("public_comments", ["moderation_notes", "submitted_at", "status", "public_record_id"])
    _drop_columns("votes", ["immutable_hash", "correction_reason", "actor"])
    _drop_columns("motions", ["immutable_hash", "correction_reason", "captured_by", "seconded_by"])
    _drop_columns("staff_reports", ["staff_acl_roles", "sensitivity_label", "source_references", "document_ref"])
    _drop_columns("agenda_items", ["staff_report_required", "source_references"])
    _drop_columns("meetings", ["cancellation_reason", "cancelled_at", "statutory_basis", "location", "meeting_type"])


def _add_columns(table_name: str, columns: list[sa.Column]) -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {item["name"] for item in inspector.get_columns(table_name, schema=SCHEMA)}
    for column in columns:
        if column.name not in existing:
            op.add_column(table_name, column, schema=SCHEMA)


def _drop_columns(table_name: str, column_names: list[str]) -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {item["name"] for item in inspector.get_columns(table_name, schema=SCHEMA)}
    for column_name in column_names:
        if column_name in existing:
            op.drop_column(table_name, column_name, schema=SCHEMA)


def _add_unique_constraint_if_missing(name: str, table_name: str, columns: list[str]) -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {constraint["name"] for constraint in inspector.get_unique_constraints(table_name, schema=SCHEMA)}
    if name not in existing:
        op.create_unique_constraint(name, table_name, columns, schema=SCHEMA)


def _drop_unique_constraint_if_present(name: str, table_name: str) -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {constraint["name"] for constraint in inspector.get_unique_constraints(table_name, schema=SCHEMA)}
    if name in existing:
        op.drop_constraint(name, table_name, type_="unique", schema=SCHEMA)


def _add_foreign_key_if_missing(
    name: str,
    source_table: str,
    referent_table: str,
    local_cols: list[str],
    remote_cols: list[str],
) -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {constraint["name"] for constraint in inspector.get_foreign_keys(source_table, schema=SCHEMA)}
    if name not in existing:
        op.create_foreign_key(
            name,
            source_table,
            referent_table,
            local_cols,
            remote_cols,
            source_schema=SCHEMA,
            referent_schema=SCHEMA,
        )


def _drop_foreign_key_if_present(name: str, table_name: str) -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {constraint["name"] for constraint in inspector.get_foreign_keys(table_name, schema=SCHEMA)}
    if name in existing:
        op.drop_constraint(name, table_name, type_="foreignkey", schema=SCHEMA)
