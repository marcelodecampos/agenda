"""Add a selectable description to cadastro address links."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0026_descricao_endereco"
down_revision: Union[str, Sequence[str], None] = "0025_bairro_enderecos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "cadastro_enderecos" in inspector.get_table_names() and "descricao" not in {column["name"] for column in inspector.get_columns("cadastro_enderecos")}:
        with op.batch_alter_table("cadastro_enderecos") as batch_op:
            batch_op.add_column(sa.Column("descricao", sa.String(40), nullable=False, server_default="Matriz"))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "cadastro_enderecos" in inspector.get_table_names() and "descricao" in {column["name"] for column in inspector.get_columns("cadastro_enderecos")}:
        with op.batch_alter_table("cadastro_enderecos") as batch_op:
            batch_op.drop_column("descricao")
