"""Keep audit timestamps current for direct PostgreSQL updates.

Revision ID: 0002_updated_at_trigger
Revises: 0001_base_user_gender
"""

from alembic import op


revision = "0002_updated_at_trigger"
down_revision = "0001_base_user_gender"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$;
        """
    )
    for table_name in ("base_user", "gender"):
        op.execute(
            f"""
            CREATE TRIGGER {table_name}_updated_at_trigger
            BEFORE UPDATE ON {table_name}
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();
            """
        )


def downgrade() -> None:
    for table_name in ("base_user", "gender"):
        op.execute(
            f"DROP TRIGGER {table_name}_updated_at_trigger ON {table_name};"
        )
    op.execute("DROP FUNCTION set_updated_at();")