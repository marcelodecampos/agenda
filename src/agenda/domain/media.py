import re
import uuid
from dataclasses import dataclass
from datetime import datetime

from agenda.domain.exceptions import ErroDominio

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class MediaInvalidaError(ErroDominio):
    pass


@dataclass(frozen=True)
class Media:
    """Metadados de um arquivo binario qualquer (foto, video, PDF, documento).

    O conteudo efetivo nunca fica nesta tabela: vive no backend configurado via
    ArmazenamentoBinarioPort (disco local hoje, Azure/S3/GCS no futuro), referenciado
    por storage_key. O sha256 garante deduplicacao por conteudo: o mesmo arquivo,
    enviado por qualquer entidade, nunca ocupa espaco duas vezes."""

    id: uuid.UUID
    sha256: str
    mime_type: str
    tamanho_bytes: int
    storage_provider: str
    storage_key: str
    criado_em: datetime
    nome_original: str | None = None

    def __post_init__(self) -> None:
        if not SHA256_PATTERN.fullmatch(self.sha256):
            raise MediaInvalidaError("sha256 deve ter 64 caracteres hexadecimais")
        if not self.mime_type.strip():
            raise MediaInvalidaError("mime_type e obrigatorio")
        if self.tamanho_bytes <= 0:
            raise MediaInvalidaError("tamanho_bytes deve ser positivo")
        if not self.storage_provider.strip():
            raise MediaInvalidaError("storage_provider e obrigatorio")
        if not self.storage_key.strip():
            raise MediaInvalidaError("storage_key e obrigatorio")


@dataclass(frozen=True)
class AnexoMedia:
    """Vincula uma Media a qualquer entidade do sistema (organizacao, servico,
    usuario, cliente, agendamento, etc.), com um papel (contexto) e ordem opcional.

    Generico de proposito: entidade_tipo/entidade_id evitam colunas de FK dedicadas
    em cada tabela que precisar de midia, mantendo o modelo flexivel para os varios
    casos de personalizacao (layout do salao, fotos de servico, avatar, documentos)."""

    id: uuid.UUID
    media_id: uuid.UUID
    entidade_tipo: str
    entidade_id: uuid.UUID
    papel: str
    criado_em: datetime
    ordem: int = 0

    def __post_init__(self) -> None:
        if not self.entidade_tipo.strip():
            raise MediaInvalidaError("entidade_tipo e obrigatorio")
        if not self.papel.strip():
            raise MediaInvalidaError("papel e obrigatorio")
        if self.ordem < 0:
            raise MediaInvalidaError("ordem nao pode ser negativa")
