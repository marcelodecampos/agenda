"""Add CPF, email, and phone identifiers to users."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_usuario_identificadores"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    colunas = {coluna["name"] for coluna in inspector.get_columns("usuarios")}
    colunas_para_adicionar = []
    for nome, tipo in (
        ("cpf", sa.String(length=11)),
        ("email", sa.String()),
        ("telefone", sa.String()),
    ):
        if nome not in colunas:
            colunas_para_adicionar.append(sa.Column(nome, tipo, nullable=True))

    unicos = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("usuarios")
    }
    indices_unicos = {
        indice["name"]
        for indice in inspector.get_indexes("usuarios")
        if indice.get("unique")
    }
    existentes = unicos | indices_unicos
    constraints_para_adicionar = []
    for nome, coluna in (
        ("uq_usuarios_cpf", "cpf"),
        ("uq_usuarios_email", "email"),
        ("uq_usuarios_telefone", "telefone"),
    ):
        if nome not in existentes:
            constraints_para_adicionar.append((nome, coluna))

    if colunas_para_adicionar or constraints_para_adicionar:
        with op.batch_alter_table("usuarios") as batch_op:
            for coluna in colunas_para_adicionar:
                batch_op.add_column(coluna)
            for nome, coluna in constraints_para_adicionar:
                batch_op.create_unique_constraint(nome, [coluna])


def downgrade() -> None:
    op.drop_constraint("uq_usuarios_telefone", "usuarios", type_="unique")
    op.drop_constraint("uq_usuarios_email", "usuarios", type_="unique")
    op.drop_constraint("uq_usuarios_cpf", "usuarios", type_="unique")
    op.drop_column("usuarios", "telefone")
    op.drop_column("usuarios", "email")
    op.drop_column("usuarios", "cpf")