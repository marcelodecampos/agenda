from __future__ import annotations

from decimal import Decimal

import httpx

from agenda.ports import Coordenada, GeocodificacaoPort


class NominatimGeocodificacaoAdapter(GeocodificacaoPort):
    def __init__(
        self,
        *,
        base_url: str,
        client: httpx.Client | None = None,
        user_agent: str = "agenda-app",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client()
        self.user_agent = user_agent

    @property
    def search_url(self) -> str:
        return f"{self.base_url}/search"

    def geocodificar(self, endereco: str) -> Coordenada:
        response = self.client.get(
            self.search_url,
            params={"q": endereco, "format": "jsonv2"},
            headers={"User-Agent": self.user_agent},
            timeout=10.0,
        )
        response.raise_for_status()

        payload = response.json()
        if not payload:
            raise ValueError("endereco nao encontrado")

        item = payload[0]
        return Coordenada(
            latitude=Decimal(str(item["lat"])),
            longitude=Decimal(str(item["lon"])),
        )
