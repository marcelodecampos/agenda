"""Make company responsible relationships temporal.

Revision ID: 0005_temporal_responsible
Revises: 0004_company_responsible
"""

from uuid6 import uuid7

import sqlalchemy as sa
from alembic import op


revision = "0005_temporal_responsible"
down_revision = "0004_company_responsible"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "company_responsible_pkey",
        "company_responsible",
        type_="primary",
    )
    op.add_column(
        "company_responsible",
        sa.Column("start_date", sa.Date(), nullable=True),
    )
    op.execute(
        "UPDATE company_responsible SET start_date = CURRENT_DATE "
        "WHERE start_date IS NULL"
    )
    op.alter_column("company_responsible", "start_date", nullable=False)
    op.add_column(
        "company_responsible",
        sa.Column("end_date", sa.Date(), nullable=True),
    )
    op.drop_column("company_responsible", "id")
    op.create_primary_key(
        "company_responsible_pkey",
        "company_responsible",
        ["company_id", "person_id", "start_date"],
    )
    op.create_check_constraint(
        "company_responsible_end_date_check",
        "company_responsible",
        "end_date IS NULL OR end_date >= start_date",
    )
    op.execute(
        """
        CREATE UNIQUE INDEX company_responsible_active_uq
        ON company_responsible (company_id, person_id)
        WHERE end_date IS NULL;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX company_responsible_active_uq")
    op.drop_constraint(
        "company_responsible_end_date_check",
        "company_responsible",
        type_="check",
    )
    op.drop_constraint(
        "company_responsible_pkey",
        "company_responsible",
        type_="primary",
    )
    op.add_column(
        "company_responsible",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=True),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT company_id, person_id, start_date "
            "FROM company_responsible"
        )
    )
    for company_id, person_id, start_date in rows:
        connection.execute(
            sa.text(
                "UPDATE company_responsible SET id = :id "
                "WHERE company_id = :company_id "
                "AND person_id = :person_id AND start_date = :start_date"
            ),
            {
                "id": uuid7(),
                "company_id": company_id,
                "person_id": person_id,
                "start_date": start_date,
            },
        )
    op.alter_column("company_responsible", "id", nullable=False)
    op.drop_column("company_responsible", "start_date")
    op.drop_column("company_responsible", "end_date")
    op.create_primary_key("company_responsible_pkey", "company_responsible", ["id"])