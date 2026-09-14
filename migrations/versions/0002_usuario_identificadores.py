"""Add CPF, email, and phone identifiers to users."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_usuario_identificadores"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("cpf", sa.String(length=11), nullable=True))
    op.add_column("usuarios", sa.Column("email", sa.String(), nullable=True))
    op.add_column("usuarios", sa.Column("telefone", sa.String(), nullable=True))
    op.create_unique_constraint("uq_usuarios_cpf", "usuarios", ["cpf"])
    op.create_unique_constraint("uq_usuarios_email", "usuarios", ["email"])
    op.create_unique_constraint("uq_usuarios_telefone", "usuarios", ["telefone"])


def downgrade() -> None:
    op.drop_constraint("uq_usuarios_telefone", "usuarios", type_="unique")
    op.drop_constraint("uq_usuarios_email", "usuarios", type_="unique")
    op.drop_constraint("uq_usuarios_cpf", "usuarios", type_="unique")
    op.drop_column("usuarios", "telefone")
    op.drop_column("usuarios", "email")
    op.drop_column("usuarios", "cpf")