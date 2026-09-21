"""Add optional CNPJ to organizations."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0020_cnpj_organizacoes"
down_revision: Union[str, Sequence[str], None] = "0019_endereco_localidade"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "organizacoes" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("organizacoes")}
    if "cnpj" not in columns:
        with op.batch_alter_table("organizacoes") as batch_op:
            batch_op.add_column(sa.Column("cnpj", sa.String(length=14), nullable=True))
            batch_op.create_unique_constraint("uq_organizacoes_cnpj", ["cnpj"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "organizacoes" in inspector.get_table_names() and "cnpj" in {column["name"] for column in inspector.get_columns("organizacoes")}:
        with op.batch_alter_table("organizacoes") as batch_op:
            batch_op.drop_constraint("uq_organizacoes_cnpj", type_="unique")
            batch_op.drop_column("cnpj")