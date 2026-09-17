"""Create and seed the appointment status catalog."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_catalogo_status_agendamento"
down_revision: Union[str, Sequence[str], None] = "0003_catalogo_papeis"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tabelas = inspector.get_table_names()
    if "status_agendamento" not in tabelas:
        op.create_table(
            "status_agendamento",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("chave", sa.String(), nullable=False, unique=True),
            sa.Column("nome", sa.String(), nullable=False),
        )
    if "transicoes_status_agendamento" not in tabelas:
        op.create_table(
            "transicoes_status_agendamento",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("de", sa.String(), nullable=False),
            sa.Column("para", sa.String(), nullable=False),
            sa.Column("atores", sa.String(), nullable=False),
        )

    conexao = op.get_bind()
    status = sa.table(
        "status_agendamento",
        sa.column("id", sa.String()),
        sa.column("chave", sa.String()),
        sa.column("nome", sa.String()),
    )
    if conexao.execute(sa.select(sa.func.count()).select_from(status)).scalar() == 0:
        op.bulk_insert(
            status,
            [
                {"id": "01990000-0000-7000-8000-000000000101", "chave": "solicitado", "nome": "Solicitado"},
                {"id": "01990000-0000-7000-8000-000000000102", "chave": "confirmado", "nome": "Confirmado"},
                {"id": "01990000-0000-7000-8000-000000000103", "chave": "em_andamento", "nome": "Em andamento"},
                {"id": "01990000-0000-7000-8000-000000000104", "chave": "concluido", "nome": "Concluido"},
                {"id": "01990000-0000-7000-8000-000000000105", "chave": "cancelado", "nome": "Cancelado"},
                {"id": "01990000-0000-7000-8000-000000000106", "chave": "nao_compareceu", "nome": "Nao compareceu"},
            ],
        )
    transicoes = sa.table(
        "transicoes_status_agendamento",
        sa.column("id", sa.String()), sa.column("de", sa.String()),
        sa.column("para", sa.String()), sa.column("atores", sa.String()),
    )
    if conexao.execute(sa.select(sa.func.count()).select_from(transicoes)).scalar() == 0:
        op.bulk_insert(
            transicoes,
            [
                {"id": "01990000-0000-7000-8000-000000000111", "de": "solicitado", "para": "confirmado", "atores": "profissional|sistema"},
                {"id": "01990000-0000-7000-8000-000000000112", "de": "solicitado", "para": "cancelado", "atores": "cliente|profissional|sistema"},
                {"id": "01990000-0000-7000-8000-000000000113", "de": "confirmado", "para": "em_andamento", "atores": "profissional|sistema"},
                {"id": "01990000-0000-7000-8000-000000000114", "de": "confirmado", "para": "cancelado", "atores": "cliente|profissional|sistema"},
                {"id": "01990000-0000-7000-8000-000000000115", "de": "em_andamento", "para": "concluido", "atores": "profissional|sistema"},
                {"id": "01990000-0000-7000-8000-000000000116", "de": "confirmado", "para": "nao_compareceu", "atores": "profissional|sistema"},
            ],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tabelas = inspector.get_table_names()
    if "transicoes_status_agendamento" in tabelas:
        op.drop_table("transicoes_status_agendamento")
    if "status_agendamento" in tabelas:
        op.drop_table("status_agendamento")