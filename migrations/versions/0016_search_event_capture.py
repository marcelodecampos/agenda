"""Create the generic search event capture function.

Revision ID: 0016_search_event_capture
Revises: 0015_search_event
"""

from alembic import op


revision = "0016_search_event_capture"
down_revision = "0015_search_event"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION search_event_capture()
        RETURNS trigger AS $$
        BEGIN
            INSERT INTO search_event (id, entity_type, entity_id, operation)
            VALUES (
                uuidv7(),
                TG_TABLE_NAME,
                CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END,
                TG_OP
            );
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS search_event_capture()")
