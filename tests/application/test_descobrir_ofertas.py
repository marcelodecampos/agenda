from decimal import Decimal

from agenda.application.descobrir_ofertas import DescobrirOfertas
from agenda.domain.endereco import Endereco
from agenda.domain.ids import novo_id
from agenda.domain.organizacao import Organizacao
from agenda.domain.servico import Servico
from agenda.ports import Coordenada


class GeocodificadorFalso:
    def geocodificar(self, endereco: str) -> Coordenada:
        return Coordenada(Decimal("-23.5"), Decimal("-46.6"))


class DistanciaFalsa:
    def estimar_km(self, origem: Coordenada, destino: Coordenada) -> Decimal:
        return Decimal("4.20")


class Repositorio:
    def __init__(self, itens: list[object]) -> None:
        self.itens = itens

    def listar(self) -> list[object]:
        return self.itens


def test_descobre_servicos_por_categoria() -> None:
    organizacao_id = novo_id()
    servico = Servico(
        id=novo_id(),
        nome="Manicure",
        categoria="Unhas",
        duracao_base_minutos=60,
        preco_base=Decimal("80"),
        organizacao_id=organizacao_id,
    )
    organizacao = Organizacao(id=organizacao_id, nome="Studio", unipessoal=False)

    ofertas = DescobrirOfertas(
        Repositorio([servico]), Repositorio([organizacao])
    ).executar(categoria="unhas")

    assert len(ofertas) == 1
    assert ofertas[0].servico.id == servico.id


def test_descobre_por_proximidade_e_descarta_sem_endereco() -> None:
    organizacao_id = novo_id()
    servico = Servico(
        id=novo_id(),
        nome="Massagem",
        categoria="Bem-estar",
        duracao_base_minutos=60,
        preco_base=Decimal("150"),
        organizacao_id=organizacao_id,
    )
    organizacao = Organizacao(
        id=organizacao_id,
        nome="Clinica",
        endereco=Endereco("Rua A", "10", "Sao Paulo", "SP", "01000-000"),
    )

    ofertas = DescobrirOfertas(
        Repositorio([servico]),
        Repositorio([organizacao]),
        GeocodificadorFalso(),
        DistanciaFalsa(),
    ).executar(endereco="Rua B", raio_km=Decimal("5"))

    assert ofertas[0].distancia_km == Decimal("4.20")