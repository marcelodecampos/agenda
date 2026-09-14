from __future__ import annotations

from decimal import Decimal

import httpx

from agenda.ports import Coordenada, DistanciaPort


class OSRMDistanciaAdapter(DistanciaPort):
    def __init__(
        self,
        *,
        base_url: str,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client()

    @property
    def route_url(self) -> str:
        return f"{self.base_url}/route/v1/driving"

    def estimar_km(self, origem: Coordenada, destino: Coordenada) -> Decimal:
        coords = (
            f"{origem.longitude},{origem.latitude};"
            f"{destino.longitude},{destino.latitude}"
        )
        response = self.client.get(
            f"{self.route_url}/{coords}",
            timeout=10.0,
        )
        response.raise_for_status()

        payload = response.json()
        routes = payload.get("routes") or []
        if not routes:
            raise ValueError("nenhuma rota encontrada")

        distancia_metros = Decimal(str(routes[0]["distance"]))
        return (distancia_metros / Decimal("1000")).quantize(Decimal("0.01"))
