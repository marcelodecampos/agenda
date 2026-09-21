"""Add optional trade name to organizations."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0023_nome_fantasia_org"
down_revision: Union[str, Sequence[str], None] = "0022_unico_endereco_principal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "organizacoes" in inspector.get_table_names() and "nome_fantasia" not in {column["name"] for column in inspector.get_columns("organizacoes")}:
        with op.batch_alter_table("organizacoes") as batch_op:
            batch_op.add_column(sa.Column("nome_fantasia", sa.String(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "organizacoes" in inspector.get_table_names() and "nome_fantasia" in {column["name"] for column in inspector.get_columns("organizacoes")}:
        with op.batch_alter_table("organizacoes") as batch_op:
            batch_op.drop_column("nome_fantasia")