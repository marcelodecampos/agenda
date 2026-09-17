from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from agenda.domain.ids import novo_id
from agenda.domain.media import Media
from agenda.ports import ArmazenamentoBinarioPort


@dataclass(frozen=True)
class ResultadoEnvioMedia:
    media: Media
    reaproveitada: bool


class EnviarMedia:
    """Faz upload de um binario com deduplicacao por sha256: se o conteudo ja existe,
    reaproveita a Media existente em vez de gravar/duplicar no storage."""

    def __init__(self, repositorio: object, armazenamento: ArmazenamentoBinarioPort) -> None:
        self.repositorio = repositorio
        self.armazenamento = armazenamento

    def executar(
        self,
        *,
        conteudo: bytes,
        mime_type: str,
        nome_original: str | None = None,
        storage_provider: str = "filesystem",
    ) -> ResultadoEnvioMedia:
        sha256 = hashlib.sha256(conteudo).hexdigest()
        existente = self.repositorio.buscar_por_sha256(sha256)
        if existente is not None:
            return ResultadoEnvioMedia(media=existente, reaproveitada=True)

        self.armazenamento.salvar(chave=sha256, conteudo=conteudo, mime_type=mime_type)
        media = Media(
            id=novo_id(),
            sha256=sha256,
            mime_type=mime_type,
            tamanho_bytes=len(conteudo),
            storage_provider=storage_provider,
            storage_key=sha256,
            criado_em=datetime.now(),
            nome_original=nome_original,
        )
        salvo = self.repositorio.salvar(media)
        return ResultadoEnvioMedia(media=salvo, reaproveitada=False)
