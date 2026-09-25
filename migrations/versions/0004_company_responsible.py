"""Create the company responsible relationship.

Revision ID: 0004_company_responsible
Revises: 0003_gender_audit_columns
"""

import sqlalchemy as sa
from alembic import op


revision = "0004_company_responsible"
down_revision = "0003_gender_audit_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_responsible",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("company_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("person_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["company_id"], ["company.id"]),
        sa.ForeignKeyConstraint(["person_id"], ["person.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "person_id"),
    )
    op.execute(
        """
        CREATE TRIGGER company_responsible_updated_at_trigger
        BEFORE UPDATE ON company_responsible
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER company_responsible_updated_at_trigger "
        "ON company_responsible;"
    )
    op.drop_table("company_responsible")