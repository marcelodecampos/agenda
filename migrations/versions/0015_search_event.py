"""Create the search indexing event table.

Revision ID: 0015_search_event
Revises: 0014_search_extensions
"""

import sqlalchemy as sa
from alembic import op


revision = "0015_search_event"
down_revision = "0014_search_extensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "search_event",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.text("now()"), nullable=False),
        sa.Column("processed", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("search_event")
