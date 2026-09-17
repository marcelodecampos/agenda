from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class DestinatarioNotificacao:
    id: str
    canal: str
    destino: str


@dataclass(frozen=True)
class NotificacaoAgendamento:
    agendamento_id: str
    destinatario: DestinatarioNotificacao
    mensagem: str
    enviar_em: datetime
    status: str = "pendente"
    tentativas: int = 0
    erro: str | None = None
    enviado_em: datetime | None = None


class NotificacaoPort(Protocol):
    def enviar(self, notificacao: NotificacaoAgendamento) -> None:
        """Entrega uma notificacao por um canal suportado pelo adapter."""


@dataclass(frozen=True)
class Coordenada:
    latitude: Decimal
    longitude: Decimal


class GeocodificacaoPort(Protocol):
    def geocodificar(self, endereco: str) -> Coordenada:
        """Converte endereco em coordenada sem expor o provedor externo."""


class DistanciaPort(Protocol):
    def estimar_km(self, origem: Coordenada, destino: Coordenada) -> Decimal:
        """Estima distancia entre pontos para descoberta ou deslocamento."""


class ArmazenamentoBinarioPort(Protocol):
    """Capacidade de guardar/servir arquivos binarios, independente do provedor
    (disco local hoje; Azure Blob, S3 ou GCS no futuro). A chave e opaca para quem
    chama: cada adapter decide seu proprio esquema de armazenamento."""

    def salvar(self, *, chave: str, conteudo: bytes, mime_type: str) -> None:
        """Grava o conteudo sob a chave informada. Idempotente: gravar a mesma
        chave duas vezes com o mesmo conteudo nao deve falhar nem duplicar."""

    def obter_url(self, chave: str) -> str:
        """Retorna uma URL para obter o conteudo (local, assinada/temporaria, etc.)."""

    def remover(self, chave: str) -> None:
        """Remove o conteudo referenciado pela chave, se existir."""


@dataclass(frozen=True)
class IdentidadeExterna:
    provider: str
    subject: str
    nome: str
    username: str | None = None
    cpf: str | None = None
    email: str | None = None
    telefone: str | None = None


class IdentidadePort(Protocol):
    def obter_identidade(self, token: str) -> IdentidadeExterna:
        """Valida token OIDC e devolve identidade, sem expor o provedor ao dominio."""