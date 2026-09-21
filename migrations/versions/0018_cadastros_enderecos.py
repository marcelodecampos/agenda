"""Centralize addresses behind the owning cadastro record."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0018_cadastros_enderecos"
down_revision: Union[str, Sequence[str], None] = "0017_municipios_localidades"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "cadastros" not in tables:
        op.create_table(
            "cadastros",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("tipo", sa.String(length=40), nullable=False),
        )
    if "enderecos" not in tables:
        op.create_table(
            "enderecos",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("cadastro_id", sa.String(), nullable=False, unique=True),
            sa.Column("logradouro", sa.String(), nullable=False),
            sa.Column("numero", sa.String(), nullable=False),
            sa.Column("complemento", sa.String(), nullable=True),
            sa.Column("bairro", sa.String(), nullable=True),
            sa.Column("cep", sa.String(), nullable=False),
            sa.Column("cidade", sa.String(), nullable=False, server_default=""),
            sa.Column("estado", sa.String(length=2), nullable=False, server_default=""),
            sa.Column("municipio_id", sa.String(), nullable=True),
            sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
            sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
            sa.ForeignKeyConstraint(["cadastro_id"], ["cadastros.id"], name="fk_enderecos_cadastro"),
            sa.ForeignKeyConstraint(["municipio_id"], ["municipios.id"], name="fk_enderecos_municipio"),
        )

    for table_name, tipo in (("clientes", "cliente"), ("organizacoes", "organizacao")):
        if table_name not in tables:
            continue
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "endereco_id" not in columns:
            with op.batch_alter_table(table_name) as batch_op:
                batch_op.add_column(sa.Column("endereco_id", sa.String(), nullable=True))
        bind.execute(
            sa.text(
                "INSERT INTO cadastros (id, tipo) "
                f"SELECT id, :tipo FROM {table_name} "
                "WHERE NOT EXISTS (SELECT 1 FROM cadastros c WHERE c.id = "
                f"{table_name}.id)"
            ),
            {"tipo": tipo},
        )
        op.execute(
            sa.text(
                f"INSERT INTO enderecos "
                "(id, cadastro_id, logradouro, numero, cep, cidade, estado, municipio_id, latitude, longitude) "
                f"SELECT id, id, endereco_logradouro, endereco_numero, endereco_cep, "
                "COALESCE(endereco_cidade, ''), COALESCE(endereco_estado, ''), NULL, NULL, NULL "
                f"FROM {table_name} t WHERE t.endereco_logradouro IS NOT NULL "
                "AND NOT EXISTS (SELECT 1 FROM enderecos e WHERE e.cadastro_id = t.id)"
            )
        )
        op.execute(
            sa.text(
                f"UPDATE {table_name} SET endereco_id = "
                "(SELECT e.id FROM enderecos e WHERE e.cadastro_id = "
                f"{table_name}.id) WHERE endereco_id IS NULL AND EXISTS "
                "(SELECT 1 FROM enderecos e WHERE e.cadastro_id = "
                f"{table_name}.id)"
            )
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table_name in ("clientes", "organizacoes"):
        if table_name in tables and "endereco_id" in {column["name"] for column in inspector.get_columns(table_name)}:
            with op.batch_alter_table(table_name) as batch_op:
                batch_op.drop_column("endereco_id")
    if "enderecos" in tables:
        op.drop_table("enderecos")
    if "cadastros" in tables:
        op.drop_table("cadastros")
