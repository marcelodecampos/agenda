"""Create the polymorphic user hierarchy and gender catalog.

Revision ID: 0001_base_user_gender
Revises:
"""

from uuid6 import uuid7

import sqlalchemy as sa
from alembic import op


revision = "0001_base_user_gender"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "base_user",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("person_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("nickname", sa.String(length=255), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_base_user_name", "base_user", ["name"])
    op.create_index("ix_base_user_nickname", "base_user", ["nickname"])

    op.create_table(
        "person",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("cpf", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["id"], ["base_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cpf"),
    )

    op.create_table(
        "company",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("cnpj", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["id"], ["base_user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cnpj"),
    )

    op.create_table(
        "gender",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("description"),
    )

    gender_table = sa.table(
        "gender",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("description", sa.String(length=255)),
    )
    op.bulk_insert(
        gender_table,
        [
            {"id": uuid7(), "description": "Masculino"},
            {"id": uuid7(), "description": "Feminino"},
        ],
    )


def downgrade() -> None:
    op.drop_table("gender")
    op.drop_table("company")
    op.drop_table("person")
    op.drop_index("ix_base_user_nickname", table_name="base_user")
    op.drop_index("ix_base_user_name", table_name="base_user")
    op.drop_table("base_user")