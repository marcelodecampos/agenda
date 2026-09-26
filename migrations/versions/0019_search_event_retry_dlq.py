"""Add retry and locking control to search events and create the DLQ.

Revision ID: 0019_search_event_retry_dlq
Revises: 0018_search_event_history
"""

import sqlalchemy as sa
from alembic import op


revision = "0019_search_event_retry_dlq"
down_revision = "0018_search_event_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("search_event", "id", server_default=sa.text("uuidv7()"))
    op.drop_column("search_event", "processed")
    op.add_column("search_event", sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.add_column("search_event", sa.Column("next_run_at", sa.DateTime(timezone=False), server_default=sa.text("now()"), nullable=False))
    op.add_column("search_event", sa.Column("locked_at", sa.DateTime(timezone=False), nullable=True))
    op.add_column("search_event", sa.Column("locked_by", sa.Text(), nullable=True))

    op.alter_column("search_event_history", "processed_at", server_default=None)
    op.add_column("search_event_history", sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.alter_column("search_event_history", "attempts", server_default=None)
    op.add_column("search_event_history", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column("search_event_history", sa.Column("locked_by", sa.Text(), nullable=True))

    op.create_table(
        "search_event_dlq",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("failed_at", sa.DateTime(timezone=False), server_default=sa.text("now()"), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("locked_by", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("search_event_dlq")

    op.drop_column("search_event_history", "locked_by")
    op.drop_column("search_event_history", "last_error")
    op.drop_column("search_event_history", "attempts")
    op.alter_column("search_event_history", "processed_at", server_default=sa.text("now()"))

    op.drop_column("search_event", "locked_by")
    op.drop_column("search_event", "locked_at")
    op.drop_column("search_event", "next_run_at")
    op.drop_column("search_event", "attempts")
    op.add_column("search_event", sa.Column("processed", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.alter_column("search_event", "id", server_default=None)
