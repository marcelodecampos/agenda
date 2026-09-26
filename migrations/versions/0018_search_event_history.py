"""Create the search indexing event history table.

Revision ID: 0018_search_event_history
Revises: 0017_municipality_search_event
"""

import sqlalchemy as sa
from alembic import op


revision = "0018_search_event_history"
down_revision = "0017_municipality_search_event"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "search_event_history",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=False), server_default=sa.text("now()"), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("search_event_history")
