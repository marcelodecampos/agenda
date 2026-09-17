from agenda.application.anexar_media import AnexarMedia
from agenda.application.enviar_media import EnviarMedia
from agenda.domain.ids import novo_id
from agenda.infrastructure.db import criar_engine_sqlite_memoria
from agenda.infrastructure.media_repository import AnexoMediaRepository, MediaRepository


class ArmazenamentoFalso:
    def __init__(self) -> None:
        self.gravados: dict[str, bytes] = {}
        self.removidos: list[str] = []

    def salvar(self, *, chave: str, conteudo: bytes, mime_type: str) -> None:
        self.gravados[chave] = conteudo

    def obter_url(self, chave: str) -> str:
        return f"http://storage.local/{chave}"

    def remover(self, chave: str) -> None:
        self.removidos.append(chave)
        self.gravados.pop(chave, None)


def test_enviar_media_grava_e_persiste_metadados() -> None:
    engine = criar_engine_sqlite_memoria()
    repo = MediaRepository(engine)
    armazenamento = ArmazenamentoFalso()

    resultado = EnviarMedia(repo, armazenamento).executar(
        conteudo=b"conteudo-teste",
        mime_type="image/png",
        nome_original="foto.png",
    )

    assert resultado.reaproveitada is False
    assert len(armazenamento.gravados) == 1
    assert repo.buscar_por_sha256(resultado.media.sha256) == resultado.media


def test_enviar_media_deduplica_por_sha256() -> None:
    engine = criar_engine_sqlite_memoria()
    repo = MediaRepository(engine)
    armazenamento = ArmazenamentoFalso()
    use_case = EnviarMedia(repo, armazenamento)

    primeiro = use_case.executar(conteudo=b"mesmo-conteudo", mime_type="application/pdf")
    segundo = use_case.executar(conteudo=b"mesmo-conteudo", mime_type="application/pdf")

    assert segundo.reaproveitada is True
    assert segundo.media.id == primeiro.media.id
    assert len(armazenamento.gravados) == 1
    assert len(repo.listar()) == 1


def test_anexar_media_cria_vinculo_com_entidade() -> None:
    engine = criar_engine_sqlite_memoria()
    media_repo = MediaRepository(engine)
    anexo_repo = AnexoMediaRepository(engine)
    armazenamento = ArmazenamentoFalso()

    resultado = EnviarMedia(media_repo, armazenamento).executar(
        conteudo=b"foto-servico", mime_type="image/jpeg"
    )
    entidade_id = novo_id()

    anexo = AnexarMedia(anexo_repo).executar(
        media_id=resultado.media.id,
        entidade_tipo="servico",
        entidade_id=entidade_id,
        papel="galeria",
    )

    encontrados = anexo_repo.listar_por_entidade("servico", entidade_id)
    assert encontrados == [anexo]
    assert anexo_repo.contar_por_media_id(resultado.media.id) == 1
