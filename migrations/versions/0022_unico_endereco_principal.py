"""Ensure each cadastro has at most one principal address."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0022_unico_endereco_principal"
down_revision: Union[str, Sequence[str], None] = "0021_multiplos_enderecos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_cadastro_enderecos_principal",
        "cadastro_enderecos",
        ["cadastro_id"],
        unique=True,
        postgresql_where=sa.text("principal = TRUE AND ativo = TRUE"),
        sqlite_where=sa.text("principal = 1 AND ativo = 1"),
    )


def downgrade() -> None:
    op.drop_index("uq_cadastro_enderecos_principal", table_name="cadastro_enderecos")
