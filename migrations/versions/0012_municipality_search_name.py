"""Add normalized municipality search name and indexes.

Revision ID: 0012_municipality_search_name
Revises: 0011_postal_code_cache
"""

import sqlalchemy as sa
from alembic import op


revision = "0012_municipality_search_name"
down_revision = "0011_postal_code_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
    op.add_column(
        "municipality",
        sa.Column("search_name", sa.String(length=150), nullable=True),
    )
    op.execute(
        "UPDATE municipality SET search_name = upper(unaccent(name))"
    )
    op.alter_column("municipality", "search_name", nullable=False)
    op.create_index("ix_municipality_name", "municipality", ["name"])
    op.create_index("ix_municipality_search_name", "municipality", ["search_name"])
    op.execute(
        """
        CREATE OR REPLACE FUNCTION normalize_municipality_search_name()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.search_name = upper(unaccent(NEW.name));
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER municipality_search_name_trigger
        BEFORE INSERT OR UPDATE OF name ON municipality
        FOR EACH ROW
        EXECUTE FUNCTION normalize_municipality_search_name();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER municipality_search_name_trigger ON municipality;")
    op.execute("DROP FUNCTION normalize_municipality_search_name();")
    op.drop_index("ix_municipality_search_name", table_name="municipality")
    op.drop_index("ix_municipality_name", table_name="municipality")
    op.drop_column("municipality", "search_name")