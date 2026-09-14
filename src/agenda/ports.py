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


@dataclass(frozen=True)
class IdentidadeExterna:
    provider: str
    subject: str
    nome: str


class IdentidadePort(Protocol):
    def obter_identidade(self, token: str) -> IdentidadeExterna:
        """Valida token OIDC e devolve identidade, sem expor o provedor ao dominio."""