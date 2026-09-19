"""Add UUIDv7 defaults to UUID primary keys."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0015_defaults_uuidv7"
down_revision: Union[str, Sequence[str], None] = "0014_catalogo_servicos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID_PRIMARY_KEY_TABLES = (
    "usuarios",
    "organizacoes",
    "papeis",
    "memberships",
    "membership_papeis",
    "agendamentos",
    "disponibilidades",
    "clientes",
    "regras_comissao",
    "destinatarios_notificacao",
    "notificacoes_agendamento",
    "recompensas_fidelidade",
    "programas_fidelidade",
    "resgates_fidelidade",
    "pacotes",
    "medias",
    "anexos_media",
    "status_agendamento",
    "transicoes_status_agendamento",
    "tipos_procedimento",
    "nomes_servico",
    "categorias_servico",
    "servicos",
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table_name in UUID_PRIMARY_KEY_TABLES:
        if table_name in tables:
            op.alter_column(
                table_name,
                "id",
                existing_type=sa.String(),
                server_default=sa.text("uuidv7()::text"),
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table_name in UUID_PRIMARY_KEY_TABLES:
        if table_name in tables:
            op.alter_column(
                table_name,
                "id",
                existing_type=sa.String(),
                server_default=None,
            )
