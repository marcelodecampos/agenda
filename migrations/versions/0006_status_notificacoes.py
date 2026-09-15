"""Add delivery state to scheduled notifications."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_status_notificacoes"
down_revision: Union[str, Sequence[str], None] = "0005_clientes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("notificacoes_agendamento")}
    with op.batch_alter_table("notificacoes_agendamento") as batch_op:
        if "status" not in columns:
            batch_op.add_column(sa.Column("status", sa.String(), nullable=True))
        if "tentativas" not in columns:
            batch_op.add_column(sa.Column("tentativas", sa.Integer(), nullable=True))
        if "erro" not in columns:
            batch_op.add_column(sa.Column("erro", sa.String(), nullable=True))
        if "enviado_em" not in columns:
            batch_op.add_column(sa.Column("enviado_em", sa.String(), nullable=True))
    op.execute(sa.text("UPDATE notificacoes_agendamento SET status = 'pendente' WHERE status IS NULL"))
    op.execute(sa.text("UPDATE notificacoes_agendamento SET tentativas = 0 WHERE tentativas IS NULL"))
    inspector = sa.inspect(op.get_bind())
    constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("notificacoes_agendamento")
    }
    if "uq_notificacao_agendamento" not in constraints:
        with op.batch_alter_table("notificacoes_agendamento") as batch_op:
            batch_op.create_unique_constraint(
                "uq_notificacao_agendamento", ["agendamento_id"]
            )


def downgrade() -> None:
    with op.batch_alter_table("notificacoes_agendamento") as batch_op:
        batch_op.drop_constraint("uq_notificacao_agendamento", type_="unique")
        batch_op.drop_column("enviado_em")
        batch_op.drop_column("erro")
        batch_op.drop_column("tentativas")
        batch_op.drop_column("status")