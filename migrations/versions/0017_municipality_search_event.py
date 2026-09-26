"""Sync the municipality table with OpenSearch.

Revision ID: 0017_municipality_search_event
Revises: 0016_search_event_capture
"""

from alembic import op


revision = "0017_municipality_search_event"
down_revision = "0016_search_event_capture"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS municipality_search_event_trigger ON municipality")
    op.execute(
        """
        CREATE TRIGGER municipality_search_event_trigger
        AFTER INSERT OR UPDATE OR DELETE ON municipality
        FOR EACH ROW EXECUTE FUNCTION search_event_capture();
        """
    )
    op.execute(
        """
        INSERT INTO search_event (id, entity_type, entity_id, operation)
        SELECT uuidv7(), 'municipality', id, 'INSERT' FROM municipality;
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS municipality_search_event_trigger ON municipality")
