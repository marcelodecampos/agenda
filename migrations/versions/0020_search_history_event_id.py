"""Reference the original event from the search event history.

Revision ID: 0020_search_history_event_id
Revises: 0019_search_event_retry_dlq
"""

import sqlalchemy as sa
from alembic import op


revision = "0020_search_history_event_id"
down_revision = "0019_search_event_retry_dlq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("search_event_history", sa.Column("event_id", sa.Uuid(as_uuid=True), nullable=False))
    op.create_index("ix_search_event_history_event_id", "search_event_history", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_search_event_history_event_id", table_name="search_event_history")
    op.drop_column("search_event_history", "event_id")
