"""Link client profiles to internal users."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008_cliente_usuario"
down_revision: Union[str, Sequence[str], None] = "0007_regras_comissao"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("clientes")}
    if "usuario_id" not in columns:
        with op.batch_alter_table("clientes") as batch_op:
            batch_op.add_column(sa.Column("usuario_id", sa.String(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "usuario_id" in {column["name"] for column in inspector.get_columns("clientes")}:
        with op.batch_alter_table("clientes") as batch_op:
            batch_op.drop_column("usuario_id")
