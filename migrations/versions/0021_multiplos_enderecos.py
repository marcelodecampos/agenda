"""Allow multiple addresses per cadastro through an association table."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0021_multiplos_enderecos"
down_revision: Union[str, Sequence[str], None] = "0020_cnpj_organizacoes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "cadastro_enderecos" not in tables:
        op.create_table(
            "cadastro_enderecos",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("cadastro_id", sa.String(), nullable=False),
            sa.Column("endereco_id", sa.String(), nullable=False),
            sa.Column("tipo", sa.String(length=40), nullable=False, server_default="principal"),
            sa.Column("principal", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.ForeignKeyConstraint(["cadastro_id"], ["cadastros.id"], name="fk_cadastro_enderecos_cadastro"),
            sa.ForeignKeyConstraint(["endereco_id"], ["enderecos.id"], name="fk_cadastro_enderecos_endereco"),
            sa.UniqueConstraint("cadastro_id", "endereco_id", name="uq_cadastro_enderecos_pair"),
        )
    uniques = inspector.get_unique_constraints("enderecos")
    for constraint in uniques:
        if constraint.get("column_names") == ["cadastro_id"]:
            with op.batch_alter_table("enderecos") as batch_op:
                batch_op.drop_constraint(constraint["name"], type_="unique")
    op.execute(
        sa.text(
            "INSERT INTO cadastro_enderecos "
            "(id, cadastro_id, endereco_id, tipo, principal, ativo) "
            "SELECT e.id, e.cadastro_id, e.id, 'principal', TRUE, TRUE FROM enderecos e "
            "WHERE NOT EXISTS (SELECT 1 FROM cadastro_enderecos ce "
            "WHERE ce.cadastro_id = e.cadastro_id AND ce.endereco_id = e.id)"
        )
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "cadastro_enderecos" in inspector.get_table_names():
        op.drop_table("cadastro_enderecos")
