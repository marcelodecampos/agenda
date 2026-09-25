"""Rename address.number to address.street_number.

Revision ID: 0013_address_street_number
Revises: 0012_municipality_search_name
"""

from alembic import op


revision = "0013_address_street_number"
down_revision = "0012_municipality_search_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("address", "number", new_column_name="street_number")


def downgrade() -> None:
    op.alter_column("address", "street_number", new_column_name="number")