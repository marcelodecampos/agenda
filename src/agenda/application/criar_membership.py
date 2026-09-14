from __future__ import annotations

import uuid

from agenda.domain.membership import Membership
from agenda.domain.papel import Papel


class CriarMembership:
    def __init__(self, repositorio: object) -> None:
        self.repositorio = repositorio

    def executar(
        self,
        *,
        usuario_id: uuid.UUID,
        organizacao_id: uuid.UUID,
        papeis: tuple[Papel, ...] | list[Papel],
    ) -> Membership:
        membership = Membership(
            id=uuid.uuid7(),
            usuario_id=usuario_id,
            organizacao_id=organizacao_id,
            papeis=list(papeis),
        )
        return self.repositorio.salvar(membership)
