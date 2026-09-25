from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agenda.api.auth import require_platform_admin
from agenda.api.database import get_session
from agenda.models.gender import Gender

router = APIRouter(prefix="/admin/genders", tags=["admin-genders"])


class GenderInput(BaseModel):
    description: str = Field(min_length=1, max_length=255)


class GenderOutput(GenderInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


@router.get("", response_model=list[GenderOutput])
def list_genders(
    search: str = Query(default="", max_length=255),
    _: dict = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> list[Gender]:
    statement = select(Gender).order_by(Gender.description)
    if search.strip():
        statement = statement.where(Gender.description.ilike(f"%{search.strip()}%"))
    return list(session.scalars(statement))


@router.post("", response_model=GenderOutput, status_code=status.HTTP_201_CREATED)
def create_gender(
    payload: GenderInput,
    _: dict = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> Gender:
    gender = Gender(description=payload.description.strip())
    session.add(gender)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um gênero com essa descrição.",
        ) from error
    session.refresh(gender)
    return gender


@router.patch("/{gender_id}", response_model=GenderOutput)
def update_gender(
    gender_id: UUID,
    payload: GenderInput,
    _: dict = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> Gender:
    gender = session.get(Gender, gender_id)
    if gender is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gênero não encontrado.")
    gender.description = payload.description.strip()
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um gênero com essa descrição.",
        ) from error
    session.refresh(gender)
    return gender


@router.delete("/{gender_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gender(
    gender_id: UUID,
    _: dict = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> None:
    gender = session.get(Gender, gender_id)
    if gender is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gênero não encontrado.")
    session.delete(gender)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este gênero está sendo utilizado e não pode ser excluído.",
        ) from error
