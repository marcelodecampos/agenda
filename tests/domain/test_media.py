from datetime import datetime

import pytest

from agenda.domain.ids import novo_id
from agenda.domain.media import AnexoMedia, Media, MediaInvalidaError

SHA256_VALIDO = "a" * 64


def _nova_media(**overrides) -> Media:
    dados = {
        "id": novo_id(),
        "sha256": SHA256_VALIDO,
        "mime_type": "image/png",
        "tamanho_bytes": 100,
        "storage_provider": "filesystem",
        "storage_key": SHA256_VALIDO,
        "criado_em": datetime.now(),
    }
    dados.update(overrides)
    return Media(**dados)


def test_media_valida_e_criada_com_sucesso() -> None:
    media = _nova_media()
    assert media.sha256 == SHA256_VALIDO


@pytest.mark.parametrize(
    "sha256",
    ["curto", "A" * 64, "g" * 64, "a" * 63, "a" * 65],
)
def test_media_rejeita_sha256_invalido(sha256: str) -> None:
    with pytest.raises(MediaInvalidaError):
        _nova_media(sha256=sha256)


def test_media_rejeita_tamanho_nao_positivo() -> None:
    with pytest.raises(MediaInvalidaError):
        _nova_media(tamanho_bytes=0)


def test_media_rejeita_mime_type_vazio() -> None:
    with pytest.raises(MediaInvalidaError):
        _nova_media(mime_type="  ")


def test_anexo_media_valido() -> None:
    anexo = AnexoMedia(
        id=novo_id(),
        media_id=novo_id(),
        entidade_tipo="organizacao",
        entidade_id=novo_id(),
        papel="capa",
        criado_em=datetime.now(),
    )
    assert anexo.ordem == 0


def test_anexo_media_rejeita_ordem_negativa() -> None:
    with pytest.raises(MediaInvalidaError):
        AnexoMedia(
            id=novo_id(),
            media_id=novo_id(),
            entidade_tipo="organizacao",
            entidade_id=novo_id(),
            papel="capa",
            criado_em=datetime.now(),
            ordem=-1,
        )


def test_anexo_media_rejeita_papel_vazio() -> None:
    with pytest.raises(MediaInvalidaError):
        AnexoMedia(
            id=novo_id(),
            media_id=novo_id(),
            entidade_tipo="organizacao",
            entidade_id=novo_id(),
            papel=" ",
            criado_em=datetime.now(),
        )
