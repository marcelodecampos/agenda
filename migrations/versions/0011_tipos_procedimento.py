"""Add controlled catalog of procedure types and link Servico to it."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_tipos_procedimento"
down_revision: Union[str, Sequence[str], None] = "0010_permissao_catalogos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "tipos_procedimento" not in inspector.get_table_names():
        op.create_table(
            "tipos_procedimento",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("chave", sa.String(), nullable=False, unique=True),
            sa.Column("nome", sa.String(), nullable=False),
        )
    colunas = {column["name"] for column in inspector.get_columns("servicos")}
    if "tipo_procedimento_id" not in colunas:
        with op.batch_alter_table("servicos") as batch_op:
            batch_op.add_column(sa.Column("tipo_procedimento_id", sa.String(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "tipo_procedimento_id" in {column["name"] for column in inspector.get_columns("servicos")}:
        with op.batch_alter_table("servicos") as batch_op:
            batch_op.drop_column("tipo_procedimento_id")
    if "tipos_procedimento" in inspector.get_table_names():
        op.drop_table("tipos_procedimento")
