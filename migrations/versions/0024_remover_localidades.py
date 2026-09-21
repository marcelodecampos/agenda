"""Remove the unused locality catalog and address locality links."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0024_remover_localidades"
down_revision: Union[str, Sequence[str], None] = "0023_nome_fantasia_org"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "enderecos" in tables and "localidade_id" in {column["name"] for column in inspector.get_columns("enderecos")}:
        foreign_keys = inspector.get_foreign_keys("enderecos")
        with op.batch_alter_table("enderecos") as batch_op:
            for foreign_key in foreign_keys:
                if foreign_key.get("constrained_columns") == ["localidade_id"]:
                    batch_op.drop_constraint(foreign_key["name"], type_="foreignkey")
            batch_op.drop_column("localidade_id")
    if "localidades" in tables:
        op.drop_table("localidades")


def downgrade() -> None:
    raise NotImplementedError("A remoção do catálogo de localidades não é reversível sem uma fonte de importação.")
