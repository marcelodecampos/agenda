"""Add plataforma.gerenciar_catalogos permission to the administrador_plataforma role."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_permissao_catalogos"
down_revision: Union[str, Sequence[str], None] = "0009_fidelidade_segmento_resgate"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NOVA_PERMISSAO = "plataforma.gerenciar_catalogos"


def upgrade() -> None:
    conexao = op.get_bind()
    papeis = sa.table(
        "papeis",
        sa.column("chave", sa.String()),
        sa.column("permissoes", sa.String()),
    )
    linha = conexao.execute(
        sa.select(papeis.c.permissoes).where(papeis.c.chave == "administrador_plataforma")
    ).first()
    if linha is None:
        return
    permissoes_atuais = set(filter(None, linha[0].split("|")))
    if NOVA_PERMISSAO in permissoes_atuais:
        return
    permissoes_atuais.add(NOVA_PERMISSAO)
    conexao.execute(
        papeis.update()
        .where(papeis.c.chave == "administrador_plataforma")
        .values(permissoes="|".join(sorted(permissoes_atuais)))
    )


def downgrade() -> None:
    conexao = op.get_bind()
    papeis = sa.table(
        "papeis",
        sa.column("chave", sa.String()),
        sa.column("permissoes", sa.String()),
    )
    linha = conexao.execute(
        sa.select(papeis.c.permissoes).where(papeis.c.chave == "administrador_plataforma")
    ).first()
    if linha is None:
        return
    permissoes_atuais = set(filter(None, linha[0].split("|")))
    permissoes_atuais.discard(NOVA_PERMISSAO)
    conexao.execute(
        papeis.update()
        .where(papeis.c.chave == "administrador_plataforma")
        .values(permissoes="|".join(sorted(permissoes_atuais)))
    )
