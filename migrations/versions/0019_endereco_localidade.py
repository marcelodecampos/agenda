"""Add optional IBGE locality ownership to centralized addresses."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0019_endereco_localidade"
down_revision: Union[str, Sequence[str], None] = "0018_cadastros_enderecos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "enderecos" in inspector.get_table_names() and "localidade_id" not in {column["name"] for column in inspector.get_columns("enderecos")}:
        with op.batch_alter_table("enderecos") as batch_op:
            batch_op.add_column(sa.Column("localidade_id", sa.String(), nullable=True))
            batch_op.create_foreign_key("fk_enderecos_localidade", "localidades", ["localidade_id"], ["id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "enderecos" in inspector.get_table_names() and "localidade_id" in {column["name"] for column in inspector.get_columns("enderecos")}:
        with op.batch_alter_table("enderecos") as batch_op:
            batch_op.drop_constraint("fk_enderecos_localidade", type_="foreignkey")
            batch_op.drop_column("localidade_id")
