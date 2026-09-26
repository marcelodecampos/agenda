from typing import Any, Literal
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query
from opensearchpy.exceptions import OpenSearchException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from agenda.api.auth import require_authenticated_user
from agenda.api.database import get_session
from agenda.api.localities import normalize_search_name
from agenda.models.federative_unit import FederativeUnit
from agenda.models.municipality import Municipality
from agenda.search.municipality_search import search_municipalities
from agenda.search.opensearch_adapter import shared_client

router = APIRouter(prefix="/search", tags=["search"])
logger = structlog.get_logger("agenda.api.search")

MIN_SEARCH_LENGTH = 3


class FederativeUnitOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    abbreviation: str


class MunicipalitySearchItem(BaseModel):
    id: UUID
    ibge_code: str
    name: str
    federative_unit_id: UUID
    federative_unit_abbreviation: str
    federative_unit_name: str


class MunicipalitySearchResponse(BaseModel):
    source: Literal["opensearch", "postgresql"]
    items: list[MunicipalitySearchItem]


@router.get("/federative-units", response_model=list[FederativeUnitOption])
def list_federative_units(_: dict = Depends(require_authenticated_user), session: Session = Depends(get_session)) -> list[FederativeUnit]:
    return list(session.scalars(select(FederativeUnit).order_by(FederativeUnit.name)))


def search_municipalities_in_database(session: Session, text: str, federative_unit_id: UUID | None, limit: int) -> list[dict[str, Any]]:
    statement = (
        select(
            Municipality.id,
            Municipality.ibge_code,
            Municipality.name,
            FederativeUnit.id.label("federative_unit_id"),
            FederativeUnit.abbreviation.label("federative_unit_abbreviation"),
            FederativeUnit.name.label("federative_unit_name"),
        )
        .join(FederativeUnit, Municipality.federative_unit_id == FederativeUnit.id)
        .where(Municipality.search_name.like(f"{normalize_search_name(text)}%"))
        .order_by(Municipality.name)
        .limit(limit)
    )
    if federative_unit_id:
        statement = statement.where(Municipality.federative_unit_id == federative_unit_id)
    return [dict(row._mapping) for row in session.execute(statement)]


@router.get("/municipalities", response_model=MunicipalitySearchResponse)
def search_municipality(
    q: str = Query(max_length=150),
    federative_unit_id: UUID | None = None,
    limit: int = Query(default=10, ge=1, le=50),
    _: dict = Depends(require_authenticated_user),
    session: Session = Depends(get_session),
) -> MunicipalitySearchResponse:
    text = q.strip()
    if len(text) < MIN_SEARCH_LENGTH:
        return MunicipalitySearchResponse(source="opensearch", items=[])
    try:
        items = search_municipalities(shared_client(), text, federative_unit_id, limit)
        return MunicipalitySearchResponse(source="opensearch", items=items)
    except OpenSearchException as error:
        logger.warning("municipality_search_fallback", error=str(error))
    items = search_municipalities_in_database(session, text, federative_unit_id, limit)
    return MunicipalitySearchResponse(source="postgresql", items=items)
