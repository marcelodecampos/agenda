"""Add optional neighborhood to centralized addresses."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0025_bairro_enderecos"
down_revision: Union[str, Sequence[str], None] = "0024_remover_localidades"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "enderecos" in inspector.get_table_names() and "bairro" not in {column["name"] for column in inspector.get_columns("enderecos")}:
        with op.batch_alter_table("enderecos") as batch_op:
            batch_op.add_column(sa.Column("bairro", sa.String(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "enderecos" in inspector.get_table_names() and "bairro" in {column["name"] for column in inspector.get_columns("enderecos")}:
        with op.batch_alter_table("enderecos") as batch_op:
            batch_op.drop_column("bairro")
