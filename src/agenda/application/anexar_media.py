from __future__ import annotations

import uuid
from datetime import datetime

from agenda.domain.ids import novo_id
from agenda.domain.media import AnexoMedia


class AnexarMedia:
    def __init__(self, repositorio: object) -> None:
        self.repositorio = repositorio

    def executar(
        self,
        *,
        media_id: uuid.UUID,
        entidade_tipo: str,
        entidade_id: uuid.UUID,
        papel: str,
        ordem: int = 0,
    ) -> AnexoMedia:
        anexo = AnexoMedia(
            id=novo_id(),
            media_id=media_id,
            entidade_tipo=entidade_tipo,
            entidade_id=entidade_id,
            papel=papel,
            ordem=ordem,
            criado_em=datetime.now(),
        )
        return self.repositorio.salvar(anexo)
