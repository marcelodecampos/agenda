import uuid
from dataclasses import dataclass
from decimal import Decimal

from agenda.domain.exceptions import ClienteInvalidoError, ErroDominio


class EnderecoInvalidoError(ErroDominio):
    pass


@dataclass(frozen=True)
class Endereco:
    logradouro: str
    numero: str
    cidade: str
    estado: str
    cep: str
    latitude: Decimal | None = None
    longitude: Decimal | None = None

    def __post_init__(self) -> None:
        if any(
            not valor.strip()
            for valor in (self.logradouro, self.numero, self.cidade, self.estado, self.cep)
        ):
            raise EnderecoInvalidoError("campos obrigatorios do endereco nao podem ser vazios")
        if (self.latitude is None) != (self.longitude is None):
            raise EnderecoInvalidoError(
                "latitude e longitude devem ser informadas juntas"
            )


@dataclass(frozen=True)
class Cliente:
    id: uuid.UUID
    nome: str
    usuario_id: uuid.UUID | None = None
    segmento: str | None = None
    telefone: str | None = None
    email: str | None = None
    cpf: str | None = None
    endereco: Endereco | None = None

    def __post_init__(self) -> None:
        if not self.nome.strip():
            raise ClienteInvalidoError("nome do cliente e obrigatorio")