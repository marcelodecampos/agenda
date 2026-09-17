"""Add client segments and loyalty redemptions."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009_fidelidade_segmento_resgate"
down_revision: Union[str, Sequence[str], None] = "0008_cliente_usuario"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("clientes")}
    if "segmento" not in columns:
        with op.batch_alter_table("clientes") as batch_op:
            batch_op.add_column(sa.Column("segmento", sa.String(), nullable=True))
    if "resgates_fidelidade" not in inspector.get_table_names():
        op.create_table(
            "resgates_fidelidade",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("programa_id", sa.String(), nullable=False),
            sa.Column("cliente_id", sa.String(), nullable=False),
            sa.Column("agendamento_id", sa.String(), nullable=True),
            sa.Column("preco_original", sa.String(), nullable=False),
            sa.Column("desconto", sa.String(), nullable=False),
            sa.Column("preco_final", sa.String(), nullable=False),
            sa.Column("gratuito", sa.Boolean(), nullable=False, default=False),
        )


def downgrade() -> None:
    if "resgates_fidelidade" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("resgates_fidelidade")
    if "segmento" in {column["name"] for column in sa.inspect(op.get_bind()).get_columns("clientes")}:
        with op.batch_alter_table("clientes") as batch_op:
            batch_op.drop_column("segmento")