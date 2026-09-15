"""Persist commission rules."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_regras_comissao"
down_revision: Union[str, Sequence[str], None] = "0006_status_notificacoes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "regras_comissao" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "regras_comissao",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("tipo", sa.String(), nullable=False),
            sa.Column("valor", sa.String(), nullable=False),
            sa.Column("membership_id", sa.String(), nullable=True),
            sa.Column("servico_id", sa.String(), nullable=True),
        )


def downgrade() -> None:
    if "regras_comissao" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("regras_comissao")