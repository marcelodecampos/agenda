from decimal import Decimal

import httpx

from agenda.adapters.nominatim_geocodificacao_adapter import (
    NominatimGeocodificacaoAdapter,
)
from agenda.ports import Coordenada


def test_geocodifica_endereco_por_api_nominatim() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith("https://nominatim.example.com/search")
        assert request.url.params["format"] == "jsonv2"
        assert request.url.params["q"] == "Rua A, 10, Sao Paulo"
        assert request.headers["User-Agent"] == "agenda-app"
        return httpx.Response(
            200,
            json=[{"lat": "-23.5505", "lon": "-46.6333"}],
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = NominatimGeocodificacaoAdapter(
        base_url="https://nominatim.example.com",
        client=client,
    )

    coordenada = adapter.geocodificar("Rua A, 10, Sao Paulo")

    assert coordenada == Coordenada(
        latitude=Decimal("-23.5505"),
        longitude=Decimal("-46.6333"),
    )
