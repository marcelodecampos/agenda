"""Create IBGE municipality and selected locality catalogs."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0017_municipios_localidades"
down_revision: Union[str, Sequence[str], None] = "0016_catalogo_unidades_federacao"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    uf_columns = {column["name"] for column in inspector.get_columns("unidades_federacao")}
    if "codigo_ibge" not in uf_columns:
        with op.batch_alter_table("unidades_federacao") as batch_op:
            batch_op.add_column(sa.Column("codigo_ibge", sa.String(length=2), nullable=True))
        op.execute(
            sa.text(
                "UPDATE unidades_federacao SET codigo_ibge = CASE sigla "
                "WHEN 'AC' THEN '12' WHEN 'AL' THEN '27' WHEN 'AP' THEN '16' "
                "WHEN 'AM' THEN '13' WHEN 'BA' THEN '29' WHEN 'CE' THEN '23' "
                "WHEN 'DF' THEN '53' WHEN 'ES' THEN '32' WHEN 'GO' THEN '52' "
                "WHEN 'MA' THEN '21' WHEN 'MT' THEN '51' WHEN 'MS' THEN '50' "
                "WHEN 'MG' THEN '31' WHEN 'PA' THEN '15' WHEN 'PB' THEN '25' "
                "WHEN 'PR' THEN '41' WHEN 'PE' THEN '26' WHEN 'PI' THEN '22' "
                "WHEN 'RJ' THEN '33' WHEN 'RN' THEN '24' WHEN 'RS' THEN '43' "
                "WHEN 'RO' THEN '11' WHEN 'RR' THEN '14' WHEN 'SC' THEN '42' "
                "WHEN 'SP' THEN '35' WHEN 'SE' THEN '28' WHEN 'TO' THEN '17' END"
            )
        )
        with op.batch_alter_table("unidades_federacao") as batch_op:
            batch_op.alter_column("codigo_ibge", existing_type=sa.String(length=2), nullable=False)
            batch_op.create_unique_constraint("uq_unidades_federacao_codigo_ibge", ["codigo_ibge"])
    if "municipios" not in tables:
        op.create_table(
            "municipios",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("codigo_ibge", sa.String(length=7), nullable=False, unique=True),
            sa.Column("nome", sa.String(), nullable=False),
            sa.Column("unidade_federacao_id", sa.String(), nullable=False),
            sa.ForeignKeyConstraint(
                ["unidade_federacao_id"], ["unidades_federacao.id"],
                name="fk_municipios_unidade_federacao",
            ),
        )
    if "localidades" not in tables:
        op.create_table(
            "localidades",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("codigo_setor", sa.String(length=15), nullable=True, unique=True),
            sa.Column("municipio_id", sa.String(), nullable=False),
            sa.Column("tipo", sa.String(length=10), nullable=True),
            sa.Column("bairro_codigo", sa.String(length=12), nullable=True),
            sa.Column("bairro_nome", sa.String(length=60), nullable=True),
            sa.Column("subdistrito_codigo", sa.String(length=11), nullable=True),
            sa.Column("subdistrito_nome", sa.String(length=60), nullable=True),
            sa.Column("distrito_codigo", sa.String(length=9), nullable=True),
            sa.Column("distrito_nome", sa.String(length=60), nullable=True),
            sa.Column("microregiao_nome", sa.String(length=100), nullable=True),
            sa.Column("mesoregiao_nome", sa.String(length=100), nullable=True),
            sa.Column("nivel_codigo", sa.String(length=1), nullable=True),
            sa.Column("categoria_codigo", sa.String(length=5), nullable=True),
            sa.Column("categoria_nome", sa.String(length=50), nullable=True),
            sa.Column("nome", sa.String(length=60), nullable=False),
            sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
            sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
            sa.Column("altitude_metros", sa.Numeric(8, 2), nullable=True),
            sa.Column("fonte", sa.String(length=100), nullable=False),
            sa.Column("ano_referencia", sa.SmallInteger(), nullable=False),
            sa.ForeignKeyConstraint(
                ["municipio_id"], ["municipios.id"],
                name="fk_localidades_municipio",
            ),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "localidades" in tables:
        op.drop_table("localidades")
    if "municipios" in tables:
        op.drop_table("municipios")