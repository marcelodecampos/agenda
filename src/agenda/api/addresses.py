import re
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from agenda.api.database import get_session
from agenda.models.postal_code_cache import PostalCodeCache

router = APIRouter(prefix="/public/addresses", tags=["public-addresses"])


class PostalCodeAddress(BaseModel):
    postal_code: str
    street_name: str | None = None
    complement: str | None = None
    neighborhood: str | None = None
    municipality: str | None = None
    federative_unit: str | None = None
    ibge_code: str | None = None


def cache_output(cache: PostalCodeCache) -> PostalCodeAddress:
    return PostalCodeAddress(
        postal_code=cache.postal_code,
        street_name=cache.street_name,
        complement=cache.complement,
        neighborhood=cache.neighborhood,
        municipality=cache.municipality,
        federative_unit=cache.federative_unit,
        ibge_code=cache.ibge_code,
    )


@router.get("/cep/{postal_code}", response_model=PostalCodeAddress)
def lookup_postal_code(
    postal_code: str,
    session: Session = Depends(get_session),
) -> PostalCodeAddress:
    digits = re.sub(r"\D", "", postal_code)
    if len(digits) != 8:
        raise HTTPException(status_code=422, detail="CEP deve conter 8 dígitos.")
    now = datetime.now(timezone.utc)
    cached = session.scalar(
        select(PostalCodeCache).where(
            PostalCodeCache.postal_code == digits,
            PostalCodeCache.expires_at > now,
        )
    )
    if cached is not None:
        return cache_output(cached)
    try:
        response = httpx.get(
            f"https://viacep.com.br/ws/{digits}/json/",
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail="Serviço de CEP indisponível.") from error
    if data.get("erro"):
        raise HTTPException(status_code=404, detail="CEP não encontrado.")
    if cached is None:
        cached = PostalCodeCache(postal_code=digits, source="viacep")
        session.add(cached)
    cached.street_name = data.get("logradouro") or None
    cached.complement = data.get("complemento") or None
    cached.neighborhood = data.get("bairro") or None
    cached.municipality = data.get("localidade") or None
    cached.federative_unit = data.get("uf") or None
    cached.ibge_code = data.get("ibge") or None
    cached.fetched_at = now
    cached.expires_at = now + timedelta(days=30)
    session.commit()
    session.refresh(cached)
    return cache_output(cached)
