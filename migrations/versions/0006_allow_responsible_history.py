"""Allow multiple historical responsibility periods.

Revision ID: 0006_allow_responsible_history
Revises: 0005_temporal_responsible
"""

from alembic import op


revision = "0006_allow_responsible_history"
down_revision = "0005_temporal_responsible"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "company_responsible_company_id_person_id_key",
        "company_responsible",
        type_="unique",
    )


def downgrade() -> None:
    op.create_unique_constraint(
        "company_responsible_company_id_person_id_key",
        "company_responsible",
        ["company_id", "person_id"],
    )