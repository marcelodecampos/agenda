"""Create medias and anexos_media tables for generic binary storage."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0013_medias"
down_revision: Union[str, Sequence[str], None] = "0012_membership_papeis"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tabelas = inspector.get_table_names()
    if "medias" not in tabelas:
        op.create_table(
            "medias",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("sha256", sa.String(length=64), nullable=False, unique=True),
            sa.Column("mime_type", sa.String(), nullable=False),
            sa.Column("tamanho_bytes", sa.Integer(), nullable=False),
            sa.Column("storage_provider", sa.String(), nullable=False),
            sa.Column("storage_key", sa.String(), nullable=False),
            sa.Column("criado_em", sa.String(), nullable=False),
            sa.Column("nome_original", sa.String(), nullable=True),
        )
    if "anexos_media" not in tabelas:
        op.create_table(
            "anexos_media",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("media_id", sa.String(), nullable=False),
            sa.Column("entidade_tipo", sa.String(), nullable=False),
            sa.Column("entidade_id", sa.String(), nullable=False),
            sa.Column("papel", sa.String(), nullable=False),
            sa.Column("ordem", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("criado_em", sa.String(), nullable=False),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tabelas = inspector.get_table_names()
    if "anexos_media" in tabelas:
        op.drop_table("anexos_media")
    if "medias" in tabelas:
        op.drop_table("medias")
