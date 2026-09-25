"""Default responsibility start date to the current date.

Revision ID: 0007_default_start_date
Revises: 0006_allow_responsible_history
"""

import sqlalchemy as sa
from alembic import op


revision = "0007_default_start_date"
down_revision = "0006_allow_responsible_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "company_responsible",
        "start_date",
        server_default=sa.text("CURRENT_DATE"),
    )


def downgrade() -> None:
    op.alter_column(
        "company_responsible",
        "start_date",
        server_default=None,
    )