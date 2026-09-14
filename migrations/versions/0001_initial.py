"""Create the initial application schema."""

from typing import Sequence, Union

from alembic import op

from agenda.infrastructure.db import Base
from agenda.infrastructure import (  # noqa: F401
    agendamento_repository,
    disponibilidade_repository,
    fidelidade_repository,
    membership_repository,
    notificacao_repository,
    organizacao_repository,
    pacote_repository,
    servico_repository,
    usuario_repository,
)

revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())