"""Create one-to-one addresses attached to BaseUser.

Revision ID: 0010_address
Revises: 0009_municipalities
"""

import sqlalchemy as sa
from alembic import op


revision = "0010_address"
down_revision = "0009_municipalities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "address",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("postal_code", sa.String(length=8), nullable=True),
        sa.Column("street_type", sa.String(length=50), nullable=True),
        sa.Column("street_name", sa.String(length=255), nullable=True),
        sa.Column("number", sa.String(length=20), nullable=True),
        sa.Column("complement", sa.String(length=255), nullable=True),
        sa.Column("neighborhood", sa.String(length=100), nullable=True),
        sa.Column("municipality_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.ForeignKeyConstraint(["id"], ["base_user.id"]),
        sa.ForeignKeyConstraint(["municipality_id"], ["municipality.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_address_municipality_id", "address", ["municipality_id"])
    op.execute(
        """
        CREATE TRIGGER address_updated_at_trigger
        BEFORE UPDATE ON address
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER address_updated_at_trigger ON address;")
    op.drop_index("ix_address_municipality_id", table_name="address")
    op.drop_table("address")
