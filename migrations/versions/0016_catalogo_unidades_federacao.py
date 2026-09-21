"""Create and seed the Brazilian federation unit catalog."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0016_catalogo_unidades_federacao"
down_revision: Union[str, Sequence[str], None] = "0015_defaults_uuidv7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UNIDADES_FEDERACAO = (
    ("01990000-0000-7000-8000-000000000201", "12", "Acre", "AC"),
    ("01990000-0000-7000-8000-000000000202", "27", "Alagoas", "AL"),
    ("01990000-0000-7000-8000-000000000203", "16", "Amapá", "AP"),
    ("01990000-0000-7000-8000-000000000204", "13", "Amazonas", "AM"),
    ("01990000-0000-7000-8000-000000000205", "29", "Bahia", "BA"),
    ("01990000-0000-7000-8000-000000000206", "23", "Ceará", "CE"),
    ("01990000-0000-7000-8000-000000000207", "53", "Distrito Federal", "DF"),
    ("01990000-0000-7000-8000-000000000208", "32", "Espírito Santo", "ES"),
    ("01990000-0000-7000-8000-000000000209", "52", "Goiás", "GO"),
    ("01990000-0000-7000-8000-000000000210", "21", "Maranhão", "MA"),
    ("01990000-0000-7000-8000-000000000211", "51", "Mato Grosso", "MT"),
    ("01990000-0000-7000-8000-000000000212", "50", "Mato Grosso do Sul", "MS"),
    ("01990000-0000-7000-8000-000000000213", "31", "Minas Gerais", "MG"),
    ("01990000-0000-7000-8000-000000000214", "15", "Pará", "PA"),
    ("01990000-0000-7000-8000-000000000215", "25", "Paraíba", "PB"),
    ("01990000-0000-7000-8000-000000000216", "41", "Paraná", "PR"),
    ("01990000-0000-7000-8000-000000000217", "26", "Pernambuco", "PE"),
    ("01990000-0000-7000-8000-000000000218", "22", "Piauí", "PI"),
    ("01990000-0000-7000-8000-000000000219", "33", "Rio de Janeiro", "RJ"),
    ("01990000-0000-7000-8000-000000000220", "24", "Rio Grande do Norte", "RN"),
    ("01990000-0000-7000-8000-000000000221", "43", "Rio Grande do Sul", "RS"),
    ("01990000-0000-7000-8000-000000000222", "11", "Rondônia", "RO"),
    ("01990000-0000-7000-8000-000000000223", "14", "Roraima", "RR"),
    ("01990000-0000-7000-8000-000000000224", "42", "Santa Catarina", "SC"),
    ("01990000-0000-7000-8000-000000000225", "35", "São Paulo", "SP"),
    ("01990000-0000-7000-8000-000000000226", "28", "Sergipe", "SE"),
    ("01990000-0000-7000-8000-000000000227", "17", "Tocantins", "TO"),
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "unidades_federacao" not in inspector.get_table_names():
        op.create_table(
            "unidades_federacao",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("codigo_ibge", sa.String(length=2), nullable=False, unique=True),
            sa.Column("nome", sa.String(), nullable=False, unique=True),
            sa.Column("sigla", sa.String(length=2), nullable=False, unique=True),
        )

    unidades = sa.table(
        "unidades_federacao",
        sa.column("id", sa.String()),
        sa.column("codigo_ibge", sa.String()),
        sa.column("nome", sa.String()),
        sa.column("sigla", sa.String()),
    )
    conexao = op.get_bind()
    existentes = {
        sigla
        for (sigla,) in conexao.execute(
            sa.select(unidades.c.sigla)
        ).all()
    }
    op.bulk_insert(
        unidades,
        [
            {"id": id_, "codigo_ibge": codigo_ibge, "nome": nome, "sigla": sigla}
            for id_, codigo_ibge, nome, sigla in UNIDADES_FEDERACAO
            if sigla not in existentes
        ],
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "unidades_federacao" in inspector.get_table_names():
        op.drop_table("unidades_federacao")