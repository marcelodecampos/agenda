"""Create the postal code lookup cache.

Revision ID: 0011_postal_code_cache
Revises: 0010_address
"""

import sqlalchemy as sa
from alembic import op


revision = "0011_postal_code_cache"
down_revision = "0010_address"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "postal_code_cache",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("postal_code", sa.String(length=8), nullable=False),
        sa.Column("street_name", sa.String(length=255), nullable=True),
        sa.Column("complement", sa.String(length=255), nullable=True),
        sa.Column("neighborhood", sa.String(length=100), nullable=True),
        sa.Column("municipality", sa.String(length=150), nullable=True),
        sa.Column("federative_unit", sa.String(length=2), nullable=True),
        sa.Column("ibge_code", sa.String(length=7), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("postal_code"),
    )
    op.create_index("ix_postal_code_cache_expires_at", "postal_code_cache", ["expires_at"])
    op.execute(
        """
        CREATE TRIGGER postal_code_cache_updated_at_trigger
        BEFORE UPDATE ON postal_code_cache
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER postal_code_cache_updated_at_trigger ON postal_code_cache;")
    op.drop_index("ix_postal_code_cache_expires_at", table_name="postal_code_cache")
    op.drop_table("postal_code_cache")