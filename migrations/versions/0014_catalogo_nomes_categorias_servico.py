"""Normalize service names and categories into catalogs."""

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "0014_catalogo_servicos"
down_revision: Union[str, Sequence[str], None] = "0013_medias"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "nomes_servico" not in tables:
        op.create_table(
            "nomes_servico",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("nome", sa.String(), nullable=False, unique=True),
        )
    if "categorias_servico" not in tables:
        op.create_table(
            "categorias_servico",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("nome", sa.String(), nullable=False, unique=True),
        )
    if "categoria_nome_servico" not in tables:
        op.create_table(
            "categoria_nome_servico",
            sa.Column("categoria_id", sa.String(), nullable=False),
            sa.Column("nome_servico_id", sa.String(), nullable=False),
            sa.PrimaryKeyConstraint("categoria_id", "nome_servico_id"),
            sa.ForeignKeyConstraint(["categoria_id"], ["categorias_servico.id"]),
            sa.ForeignKeyConstraint(["nome_servico_id"], ["nomes_servico.id"]),
        )

    service_columns = {column["name"] for column in inspector.get_columns("servicos")}
    if "nome_servico_id" not in service_columns:
        with op.batch_alter_table("servicos") as batch_op:
            batch_op.add_column(sa.Column("nome_servico_id", sa.String(), nullable=True))

    if {"nome", "categoria"}.issubset(service_columns):
        rows = bind.execute(
            sa.text(
                "SELECT id, nome, categoria FROM servicos "
                "WHERE nome_servico_id IS NULL"
            )
        ).mappings().all()
        for row in rows:
            nome_id = str(uuid.uuid7())
            categoria_id = str(uuid.uuid7())
            existing_name = bind.execute(
                sa.text("SELECT id FROM nomes_servico WHERE nome = :nome"),
                {"nome": row["nome"]},
            ).scalar_one_or_none()
            if existing_name is None:
                existing_name = nome_id
                bind.execute(
                    sa.text("INSERT INTO nomes_servico (id, nome) VALUES (:id, :nome)"),
                    {"id": existing_name, "nome": row["nome"]},
                )
            existing_category = bind.execute(
                sa.text("SELECT id FROM categorias_servico WHERE nome = :nome"),
                {"nome": row["categoria"]},
            ).scalar_one_or_none()
            if existing_category is None:
                existing_category = categoria_id
                bind.execute(
                    sa.text("INSERT INTO categorias_servico (id, nome) VALUES (:id, :nome)"),
                    {"id": existing_category, "nome": row["categoria"]},
                )
            relation_exists = bind.execute(
                sa.text(
                    "SELECT 1 FROM categoria_nome_servico "
                    "WHERE categoria_id = :categoria_id AND nome_servico_id = :nome_servico_id"
                ),
                {"categoria_id": existing_category, "nome_servico_id": existing_name},
            ).scalar_one_or_none()
            if relation_exists is None:
                bind.execute(
                    sa.text(
                        "INSERT INTO categoria_nome_servico (categoria_id, nome_servico_id) "
                        "VALUES (:categoria_id, :nome_servico_id)"
                    ),
                    {"categoria_id": existing_category, "nome_servico_id": existing_name},
                )
            bind.execute(
                sa.text("UPDATE servicos SET nome_servico_id = :nome_servico_id WHERE id = :id"),
                {"nome_servico_id": existing_name, "id": row["id"]},
            )

    foreign_keys = inspector.get_foreign_keys("servicos")
    has_name_fk = any(
        "nome_servico_id" in constraint.get("constrained_columns", [])
        and constraint.get("referred_table") == "nomes_servico"
        for constraint in foreign_keys
    )
    if not has_name_fk:
        with op.batch_alter_table("servicos") as batch_op:
            batch_op.create_foreign_key(
                "fk_servicos_nome_servico_id",
                "nomes_servico",
                ["nome_servico_id"],
                ["id"],
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "servicos" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("servicos")}
        if "nome_servico_id" in columns:
            with op.batch_alter_table("servicos") as batch_op:
                batch_op.drop_column("nome_servico_id")
    for table in ("categoria_nome_servico", "categorias_servico", "nomes_servico"):
        if table in inspector.get_table_names():
            op.drop_table(table)
