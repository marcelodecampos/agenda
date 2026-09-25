import unicodedata
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agenda.api.auth import require_platform_admin
from agenda.api.database import get_session
from agenda.models.federative_unit import FederativeUnit
from agenda.models.municipality import Municipality

router = APIRouter(prefix="/admin", tags=["admin-localities"])


class FederativeUnitInput(BaseModel):
    ibge_code: str = Field(min_length=2, max_length=2)
    name: str = Field(min_length=1, max_length=100)
    abbreviation: str = Field(min_length=2, max_length=2)


class FederativeUnitOutput(FederativeUnitInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class MunicipalityInput(BaseModel):
    ibge_code: str = Field(min_length=7, max_length=7)
    name: str = Field(min_length=1, max_length=150)
    federative_unit_id: UUID


class MunicipalityOutput(MunicipalityInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    federative_unit_name: str
    federative_unit_abbreviation: str


def clean(value: str) -> str:
    return value.strip()


def normalize_search_name(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    return "".join(character for character in normalized if not unicodedata.combining(character)).upper()


def unique_error(error: IntegrityError, detail: str) -> None:
    raise HTTPException(status_code=409, detail=detail) from error


@router.get("/federative-units", response_model=list[FederativeUnitOutput])
def list_federative_units(search: str = Query(default="", max_length=100), _: dict = Depends(require_platform_admin), session: Session = Depends(get_session)) -> list[FederativeUnit]:
    statement = select(FederativeUnit).order_by(FederativeUnit.name)
    if search.strip():
        term = f"%{search.strip()}%"
        statement = statement.where(FederativeUnit.name.ilike(term) | FederativeUnit.abbreviation.ilike(term))
    return list(session.scalars(statement))


@router.post("/federative-units", response_model=FederativeUnitOutput, status_code=status.HTTP_201_CREATED)
def create_federative_unit(payload: FederativeUnitInput, _: dict = Depends(require_platform_admin), session: Session = Depends(get_session)) -> FederativeUnit:
    unit = FederativeUnit(ibge_code=clean(payload.ibge_code), name=clean(payload.name), abbreviation=clean(payload.abbreviation).upper())
    session.add(unit)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        unique_error(error, "Código, nome ou sigla já cadastrados.")
    session.refresh(unit)
    return unit


@router.patch("/federative-units/{unit_id}", response_model=FederativeUnitOutput)
def update_federative_unit(unit_id: UUID, payload: FederativeUnitInput, _: dict = Depends(require_platform_admin), session: Session = Depends(get_session)) -> FederativeUnit:
    unit = session.get(FederativeUnit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Unidade federativa não encontrada.")
    unit.ibge_code = clean(payload.ibge_code)
    unit.name = clean(payload.name)
    unit.abbreviation = clean(payload.abbreviation).upper()
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        unique_error(error, "Código, nome ou sigla já cadastrados.")
    session.refresh(unit)
    return unit


@router.delete("/federative-units/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_federative_unit(unit_id: UUID, _: dict = Depends(require_platform_admin), session: Session = Depends(get_session)) -> None:
    unit = session.get(FederativeUnit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Unidade federativa não encontrada.")
    session.delete(unit)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        unique_error(error, "A unidade possui municípios vinculados.")


def municipality_output(municipality: Municipality) -> MunicipalityOutput:
    return MunicipalityOutput(id=municipality.id, ibge_code=municipality.ibge_code, name=municipality.name, federative_unit_id=municipality.federative_unit_id, federative_unit_name=municipality.federative_unit.name, federative_unit_abbreviation=municipality.federative_unit.abbreviation)


@router.get("/municipalities", response_model=list[MunicipalityOutput])
def list_municipalities(search: str = Query(default="", max_length=150), federative_unit_id: UUID | None = None, _: dict = Depends(require_platform_admin), session: Session = Depends(get_session)) -> list[MunicipalityOutput]:
    statement = select(Municipality).order_by(Municipality.name).limit(10)
    if search.strip():
        normalized_search = normalize_search_name(search)
        if len(normalized_search) < 3:
            return []
        term = f"{normalized_search}%"
        statement = statement.where(Municipality.search_name.like(term))
    if federative_unit_id:
        statement = statement.where(Municipality.federative_unit_id == federative_unit_id)
    return [municipality_output(item) for item in session.scalars(statement)]


@router.post("/municipalities", response_model=MunicipalityOutput, status_code=status.HTTP_201_CREATED)
def create_municipality(payload: MunicipalityInput, _: dict = Depends(require_platform_admin), session: Session = Depends(get_session)) -> MunicipalityOutput:
    municipality = Municipality(ibge_code=clean(payload.ibge_code), name=clean(payload.name), federative_unit_id=payload.federative_unit_id)
    session.add(municipality)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        unique_error(error, "Código IBGE já cadastrado ou unidade federativa inválida.")
    session.refresh(municipality)
    return municipality_output(municipality)


@router.patch("/municipalities/{municipality_id}", response_model=MunicipalityOutput)
def update_municipality(municipality_id: UUID, payload: MunicipalityInput, _: dict = Depends(require_platform_admin), session: Session = Depends(get_session)) -> MunicipalityOutput:
    municipality = session.get(Municipality, municipality_id)
    if municipality is None:
        raise HTTPException(status_code=404, detail="Município não encontrado.")
    municipality.ibge_code = clean(payload.ibge_code)
    municipality.name = clean(payload.name)
    municipality.federative_unit_id = payload.federative_unit_id
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        unique_error(error, "Código IBGE já cadastrado ou unidade federativa inválida.")
    session.refresh(municipality)
    return municipality_output(municipality)


@router.delete("/municipalities/{municipality_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_municipality(municipality_id: UUID, _: dict = Depends(require_platform_admin), session: Session = Depends(get_session)) -> None:
    municipality = session.get(Municipality, municipality_id)
    if municipality is None:
        raise HTTPException(status_code=404, detail="Município não encontrado.")
    session.delete(municipality)
    session.commit()
