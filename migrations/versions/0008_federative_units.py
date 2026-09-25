"""Create and seed Brazilian federative units from IBGE.

Revision ID: 0008_federative_units
Revises: 0007_default_start_date
"""

from uuid6 import uuid7

import sqlalchemy as sa
from alembic import op


revision = "0008_federative_units"
down_revision = "0007_default_start_date"
branch_labels = None
depends_on = None


UNITS = (
    ("11", "Rondônia", "RO"),
    ("12", "Acre", "AC"),
    ("13", "Amazonas", "AM"),
    ("14", "Roraima", "RR"),
    ("15", "Pará", "PA"),
    ("16", "Amapá", "AP"),
    ("17", "Tocantins", "TO"),
    ("21", "Maranhão", "MA"),
    ("22", "Piauí", "PI"),
    ("23", "Ceará", "CE"),
    ("24", "Rio Grande do Norte", "RN"),
    ("25", "Paraíba", "PB"),
    ("26", "Pernambuco", "PE"),
    ("27", "Alagoas", "AL"),
    ("28", "Sergipe", "SE"),
    ("29", "Bahia", "BA"),
    ("31", "Minas Gerais", "MG"),
    ("32", "Espírito Santo", "ES"),
    ("33", "Rio de Janeiro", "RJ"),
    ("35", "São Paulo", "SP"),
    ("41", "Paraná", "PR"),
    ("42", "Santa Catarina", "SC"),
    ("43", "Rio Grande do Sul", "RS"),
    ("50", "Mato Grosso do Sul", "MS"),
    ("51", "Mato Grosso", "MT"),
    ("52", "Goiás", "GO"),
    ("53", "Distrito Federal", "DF"),
)


def upgrade() -> None:
    op.create_table(
        "federative_unit",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("ibge_code", sa.String(length=2), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("abbreviation", sa.String(length=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ibge_code"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("abbreviation"),
    )
    op.create_index("ix_federative_unit_ibge_code", "federative_unit", ["ibge_code"])
    op.execute(
        """
        CREATE TRIGGER federative_unit_updated_at_trigger
        BEFORE UPDATE ON federative_unit
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """
    )
    table = sa.table(
        "federative_unit",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("ibge_code", sa.String(length=2)),
        sa.column("name", sa.String(length=100)),
        sa.column("abbreviation", sa.String(length=2)),
    )
    op.bulk_insert(
        table,
        [
            {"id": uuid7(), "ibge_code": code, "name": name, "abbreviation": abbreviation}
            for code, name, abbreviation in UNITS
        ],
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER federative_unit_updated_at_trigger ON federative_unit;")
    op.drop_index("ix_federative_unit_ibge_code", table_name="federative_unit")
    op.drop_table("federative_unit")
