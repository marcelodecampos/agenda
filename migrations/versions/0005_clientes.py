"""Create client profiles."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_clientes"
down_revision: Union[str, Sequence[str], None] = "0004_catalogo_status_agendamento"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "clientes" in inspector.get_table_names():
        return
    op.create_table(
        "clientes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("nome", sa.String(), nullable=False),
        sa.Column("usuario_id", sa.String(), nullable=True),
        sa.Column("telefone", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("cpf", sa.String(length=11), nullable=True),
        sa.Column("endereco_logradouro", sa.String(), nullable=True),
        sa.Column("endereco_numero", sa.String(), nullable=True),
        sa.Column("endereco_cidade", sa.String(), nullable=True),
        sa.Column("endereco_estado", sa.String(), nullable=True),
        sa.Column("endereco_cep", sa.String(), nullable=True),
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "clientes" in inspector.get_table_names():
        op.drop_table("clientes")