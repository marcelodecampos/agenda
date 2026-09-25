"""Create municipalities linked to federative units.

Revision ID: 0009_municipalities
Revises: 0008_federative_units
"""

import sqlalchemy as sa
from alembic import op


revision = "0009_municipalities"
down_revision = "0008_federative_units"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "municipality",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("ibge_code", sa.String(length=7), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("federative_unit_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.ForeignKeyConstraint(["federative_unit_id"], ["federative_unit.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ibge_code"),
    )
    op.create_index("ix_municipality_ibge_code", "municipality", ["ibge_code"])
    op.create_index("ix_municipality_federative_unit_id", "municipality", ["federative_unit_id"])
    op.execute(
        """
        CREATE TRIGGER municipality_updated_at_trigger
        BEFORE UPDATE ON municipality
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER municipality_updated_at_trigger ON municipality;")
    op.drop_index("ix_municipality_federative_unit_id", table_name="municipality")
    op.drop_index("ix_municipality_ibge_code", table_name="municipality")
    op.drop_table("municipality")