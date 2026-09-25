"""Add audit and optimistic concurrency columns to gender.

Revision ID: 0003_gender_audit_columns
Revises: 0002_updated_at_trigger
"""

import sqlalchemy as sa
from alembic import op


revision = "0003_gender_audit_columns"
down_revision = "0002_updated_at_trigger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "gender",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.add_column(
        "gender",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.add_column(
        "gender",
        sa.Column(
            "version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("gender", "version")
    op.drop_column("gender", "updated_at")
    op.drop_column("gender", "created_at")