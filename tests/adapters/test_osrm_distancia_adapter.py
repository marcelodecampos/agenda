from decimal import Decimal

import httpx

from agenda.adapters.osrm_distancia_adapter import OSRMDistanciaAdapter
from agenda.ports import Coordenada


def test_estima_distancia_entre_pontos_com_osrm() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://router.project-osrm.org/route/v1/driving/-46.6333,-23.5505;-46.7000,-23.6000"
        return httpx.Response(
            200,
            json={
                "routes": [{"distance": 12000.0}],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    adapter = OSRMDistanciaAdapter(
        base_url="https://router.project-osrm.org",
        client=client,
    )

    origem = Coordenada(latitude=Decimal("-23.5505"), longitude=Decimal("-46.6333"))
    destino = Coordenada(latitude=Decimal("-23.6000"), longitude=Decimal("-46.7000"))

    distancia_km = adapter.estimar_km(origem, destino)

    assert distancia_km == Decimal("12")
