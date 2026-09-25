"""Enable PostgreSQL text search extensions.

Revision ID: 0014_search_extensions
Revises: 0013_address_street_number
"""

from alembic import op


revision = "0014_search_extensions"
down_revision = "0013_address_street_number"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS fuzzystrmatch")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS fuzzystrmatch")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS unaccent")
