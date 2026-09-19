from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from agenda.domain.organizacao import Organizacao
from agenda.domain.servico import Servico
from agenda.ports import Coordenada, DistanciaPort, GeocodificacaoPort
from agenda.application.busca_textual import corresponde_busca


@dataclass(frozen=True)
class OfertaDescoberta:
    servico: Servico
    organizacao: Organizacao | None
    distancia_km: Decimal | None = None


class DescobrirOfertas:
    def __init__(
        self,
        servicos: object,
        organizacoes: object,
        geocodificacao: GeocodificacaoPort | None = None,
        distancia: DistanciaPort | None = None,
    ) -> None:
        self.servicos = servicos
        self.organizacoes = organizacoes
        self.geocodificacao = geocodificacao
        self.distancia = distancia

    def executar(
        self,
        *,
        termo: str | None = None,
        categoria: str | None = None,
        endereco: str | None = None,
        raio_km: Decimal | None = None,
    ) -> list[OfertaDescoberta]:
        if raio_km is not None and raio_km <= 0:
            raise ValueError("raio_km deve ser positivo")
        if endereco and (self.geocodificacao is None or self.distancia is None):
            raise ValueError("geolocalizacao nao configurada")

        origem: Coordenada | None = None
        if endereco:
            origem = self.geocodificacao.geocodificar(endereco)

        organizacoes = {
            organizacao.id: organizacao for organizacao in self.organizacoes.listar()
        }
        resultados: list[OfertaDescoberta] = []
        for servico in self.servicos.listar():
            termo_busca = termo or categoria
            if termo_busca and not corresponde_busca(
                termo_busca, servico.nome, *servico.categorias
            ):
                continue
            organizacao = (
                organizacoes.get(servico.organizacao_id)
                if servico.organizacao_id is not None
                else None
            )
            distancia_km = None
            if origem is not None:
                if organizacao is None or organizacao.endereco is None:
                    continue
                destino = self.geocodificacao.geocodificar(
                    self._endereco_texto(organizacao)
                )
                distancia_km = self.distancia.estimar_km(origem, destino)
                if raio_km is not None and distancia_km > raio_km:
                    continue
            resultados.append(
                OfertaDescoberta(
                    servico=servico,
                    organizacao=organizacao,
                    distancia_km=distancia_km,
                )
            )
        return sorted(
            resultados,
            key=lambda oferta: oferta.distancia_km
            if oferta.distancia_km is not None
            else Decimal("0"),
        )

    @staticmethod
    def _endereco_texto(organizacao: Organizacao) -> str:
        if organizacao.endereco is None:
            return ""
        endereco = organizacao.endereco
        return f"{endereco.logradouro}, {endereco.numero}, {endereco.cidade}, {endereco.estado}, {endereco.cep}"