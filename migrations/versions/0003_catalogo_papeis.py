"""Create the initial role catalog."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_catalogo_papeis"
down_revision: Union[str, Sequence[str], None] = "0002_usuario_identificadores"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PAPEIS = (
    {
        "id": "01990000-0000-7000-8000-000000000001",
        "chave": "dono",
        "nome": "Dono",
        "permissoes": "agenda.configurar|agenda.visualizar|servico.gerenciar|pacote.gerenciar|agendamento.transicionar_status|agendamento.visualizar_estabelecimento|agendamento.visualizar_proprio|fidelidade.configurar_programa|cliente.ver_ficha|estabelecimento.gerenciar_equipe|estabelecimento.configurar_dados|comissao.configurar_regra|comissao.visualizar_relatorio",
    },
    {
        "id": "01990000-0000-7000-8000-000000000002",
        "chave": "autonomo_puro",
        "nome": "Autonomo Puro",
        "permissoes": "agenda.configurar|agenda.visualizar|servico.gerenciar|pacote.gerenciar|agendamento.transicionar_status|agendamento.visualizar_proprio|fidelidade.configurar_programa|cliente.ver_ficha|estabelecimento.configurar_dados",
    },
    {
        "id": "01990000-0000-7000-8000-000000000003",
        "chave": "funcionario",
        "nome": "Funcionario",
        "permissoes": "agenda.configurar|agenda.visualizar|agendamento.transicionar_status|agendamento.visualizar_proprio|cliente.ver_ficha|comissao.visualizar_relatorio",
    },
    {
        "id": "01990000-0000-7000-8000-000000000004",
        "chave": "autonomo_associado",
        "nome": "Autonomo Associado",
        "permissoes": "agenda.configurar|agenda.visualizar|servico.gerenciar|pacote.gerenciar|agendamento.transicionar_status|agendamento.visualizar_proprio|fidelidade.configurar_programa|cliente.ver_ficha|comissao.visualizar_relatorio",
    },
    {
        "id": "01990000-0000-7000-8000-000000000005",
        "chave": "cliente",
        "nome": "Cliente",
        "permissoes": "agenda.visualizar|agendamento.solicitar|agendamento.transicionar_status|agendamento.visualizar_proprio|fidelidade.visualizar_proprio_progresso",
    },
    {
        "id": "01990000-0000-7000-8000-000000000006",
        "chave": "administrador_plataforma",
        "nome": "Administrador da Plataforma",
        "permissoes": "plataforma.aprovar_cadastro|plataforma.suspender_conta|plataforma.visualizar_metricas_globais",
    },
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    unicos = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("papeis")
    }
    indices_unicos = {
        indice["name"]
        for indice in inspector.get_indexes("papeis")
        if indice.get("unique")
    }
    if "uq_papeis_chave" not in unicos | indices_unicos:
        with op.batch_alter_table("papeis") as batch_op:
            batch_op.create_unique_constraint("uq_papeis_chave", ["chave"])
    papeis = sa.table(
        "papeis",
        sa.column("id", sa.String()),
        sa.column("chave", sa.String()),
        sa.column("nome", sa.String()),
        sa.column("permissoes", sa.String()),
    )
    op.bulk_insert(papeis, list(PAPEIS))


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM papeis WHERE chave IN "
            "('dono', 'autonomo_puro', 'funcionario', "
            "'autonomo_associado', 'cliente', 'administrador_plataforma')"
        )
    )
    inspector = sa.inspect(op.get_bind())
    if any(
        constraint["name"] == "uq_papeis_chave"
        for constraint in inspector.get_unique_constraints("papeis")
    ):
        with op.batch_alter_table("papeis") as batch_op:
            batch_op.drop_constraint("uq_papeis_chave", type_="unique")