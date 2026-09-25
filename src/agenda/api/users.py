from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_serializer
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from agenda.api.auth import require_platform_admin
from agenda.api.database import get_session
from agenda.models.user import Company, CompanyResponsible, Person

router = APIRouter(prefix="/admin", tags=["admin-users"])


class UserInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    nickname: str | None = Field(default=None, max_length=255)
    birth_date: date | None = None


class PersonInput(UserInput):
    cpf: str | None = Field(default=None, max_length=32)


class CompanyInput(UserInput):
    cnpj: str | None = Field(default=None, max_length=32)


class PersonOutput(PersonInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    @field_serializer("cpf")
    def serialize_cpf(self, value: str | None) -> str | None:
        if not value:
            return value
        digits = "".join(character for character in value if character.isdigit())
        if len(digits) != 11:
            return value
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


class CompanyOutput(CompanyInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    @field_serializer("cnpj")
    def serialize_cnpj(self, value: str | None) -> str | None:
        if not value:
            return value
        digits = "".join(character for character in value if character.isdigit())
        if len(digits) != 14:
            return value
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


class ResponsibleOutput(PersonOutput):
    start_date: date


class ResponsibleInput(BaseModel):
    cpf: str = Field(min_length=1, max_length=32)
    name: str | None = Field(default=None, max_length=255)
    nickname: str | None = Field(default=None, max_length=255)
    birth_date: date | None = None


def clean(value: str | None) -> str | None:
    value = value.strip() if value else None
    return value or None


def clean_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise HTTPException(status_code=422, detail="Nome é obrigatório.")
    return value


def clean_document(value: str | None) -> str | None:
    value = clean(value)
    return "".join(character for character in value if character.isdigit()) if value else None


def handle_unique_error(error: IntegrityError, detail: str) -> None:
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from error


def get_company_or_404(company_id: UUID, session: Session) -> Company:
    company = session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Pessoa jurídica não encontrada.")
    return company


def responsible_output(person: Person, start_date: date) -> ResponsibleOutput:
    return ResponsibleOutput(
        id=person.id,
        name=person.name,
        nickname=person.nickname,
        birth_date=person.birth_date,
        cpf=person.cpf,
        start_date=start_date,
    )


@router.get("/persons", response_model=list[PersonOutput])
def list_persons(
    search: str = Query(default="", max_length=255),
    _: dict = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> list[Person]:
    statement = select(Person).order_by(Person.name)
    if search.strip():
        term = f"%{search.strip()}%"
        statement = statement.where(Person.name.ilike(term))
    return list(session.scalars(statement))


@router.post("/persons", response_model=PersonOutput, status_code=status.HTTP_201_CREATED)
def create_person(
    payload: PersonInput,
    _: dict = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> Person:
    person = Person(
        name=clean_name(payload.name),
        nickname=clean(payload.nickname),
        birth_date=payload.birth_date,
        cpf=clean_document(payload.cpf),
    )
    session.add(person)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        handle_unique_error(error, "Já existe uma pessoa com esse CPF.")
    session.refresh(person)
    return person


@router.patch("/persons/{person_id}", response_model=PersonOutput)
def update_person(
    person_id: UUID,
    payload: PersonInput,
    _: dict = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> Person:
    person = session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Pessoa física não encontrada.")
    person.name = clean_name(payload.name)
    person.nickname = clean(payload.nickname)
    person.birth_date = payload.birth_date
    person.cpf = clean_document(payload.cpf)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        handle_unique_error(error, "Já existe uma pessoa com esse CPF.")
    session.refresh(person)
    return person


@router.delete("/persons/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(
    person_id: UUID,
    _: dict = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> None:
    person = session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Pessoa física não encontrada.")
    session.delete(person)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        handle_unique_error(error, "Esta pessoa está vinculada a outros dados.")


@router.get("/companies", response_model=list[CompanyOutput])
def list_companies(
    search: str = Query(default="", max_length=255),
    _: dict = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> list[Company]:
    statement = select(Company).order_by(Company.name)
    if search.strip():
        term = f"%{search.strip()}%"
        statement = statement.where(Company.name.ilike(term))
    return list(session.scalars(statement))


@router.post("/companies", response_model=CompanyOutput, status_code=status.HTTP_201_CREATED)
def create_company(
    payload: CompanyInput,
    _: dict = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> Company:
    company = Company(
        name=clean_name(payload.name),
        nickname=clean(payload.nickname),
        birth_date=payload.birth_date,
        cnpj=clean_document(payload.cnpj),
    )
    session.add(company)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        handle_unique_error(error, "Já existe uma pessoa jurídica com esse CNPJ.")
    session.refresh(company)
    return company


@router.patch("/companies/{company_id}", response_model=CompanyOutput)
def update_company(
    company_id: UUID,
    payload: CompanyInput,
    _: dict = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> Company:
    company = session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Pessoa jurídica não encontrada.")
    company.name = clean_name(payload.name)
    company.nickname = clean(payload.nickname)
    company.birth_date = payload.birth_date
    company.cnpj = clean_document(payload.cnpj)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        handle_unique_error(error, "Já existe uma pessoa jurídica com esse CNPJ.")
    session.refresh(company)
    return company


@router.delete("/companies/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(
    company_id: UUID,
    _: dict = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> None:
    company = session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Pessoa jurídica não encontrada.")
    session.delete(company)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        handle_unique_error(error, "Esta pessoa jurídica está vinculada a outros dados.")


@router.get("/companies/{company_id}/responsibles", response_model=list[ResponsibleOutput])
def list_company_responsibles(
    company_id: UUID,
    _: dict = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> list[ResponsibleOutput]:
    get_company_or_404(company_id, session)
    rows = session.execute(
        select(Person, CompanyResponsible.start_date)
        .join(CompanyResponsible, CompanyResponsible.person_id == Person.id)
        .where(
            and_(
                CompanyResponsible.company_id == company_id,
                CompanyResponsible.end_date.is_(None),
            )
        )
        .order_by(Person.name)
    ).all()
    return [responsible_output(person, start_date) for person, start_date in rows]


@router.get("/companies/{company_id}/responsibles/lookup", response_model=PersonOutput)
def lookup_company_responsible(
    company_id: UUID,
    cpf: str = Query(min_length=1, max_length=32),
    _: dict = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> Person:
    get_company_or_404(company_id, session)
    person = session.scalar(
        select(Person).where(Person.cpf == clean_document(cpf))
    )
    if person is None:
        raise HTTPException(status_code=404, detail="Pessoa não encontrada.")
    return person


@router.post(
    "/companies/{company_id}/responsibles",
    response_model=ResponsibleOutput,
    status_code=status.HTTP_201_CREATED,
)
def add_company_responsible(
    company_id: UUID,
    payload: ResponsibleInput,
    _: dict = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> ResponsibleOutput:
    get_company_or_404(company_id, session)
    cpf = clean_document(payload.cpf)
    if not cpf:
        raise HTTPException(status_code=422, detail="CPF é obrigatório.")
    person = session.scalar(select(Person).where(Person.cpf == cpf))
    if person is None:
        if not payload.name:
            raise HTTPException(
                status_code=404,
                detail="Pessoa não encontrada. Informe o nome para criar o responsável.",
            )
        person = Person(
            name=clean_name(payload.name),
            nickname=clean(payload.nickname),
            birth_date=payload.birth_date,
            cpf=cpf,
        )
        session.add(person)
        session.flush()
    active_link = session.scalar(
        select(CompanyResponsible).where(
            CompanyResponsible.company_id == company_id,
            CompanyResponsible.person_id == person.id,
            CompanyResponsible.end_date.is_(None),
        )
    )
    if active_link is not None:
        raise HTTPException(status_code=409, detail="Esta pessoa já é responsável pela empresa.")
    link = CompanyResponsible(company_id=company_id, person_id=person.id)
    session.add(link)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        handle_unique_error(error, "Não foi possível incluir o responsável.")
    session.refresh(person)
    return responsible_output(person, link.start_date)


@router.delete(
    "/companies/{company_id}/responsibles/{person_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_company_responsible(
    company_id: UUID,
    person_id: UUID,
    _: dict = Depends(require_platform_admin),
    session: Session = Depends(get_session),
) -> None:
    get_company_or_404(company_id, session)
    link = session.scalar(
        select(CompanyResponsible).where(
            CompanyResponsible.company_id == company_id,
            CompanyResponsible.person_id == person_id,
            CompanyResponsible.end_date.is_(None),
        )
    )
    if link is None:
        raise HTTPException(status_code=404, detail="Responsável ativo não encontrado.")
    link.end_date = date.today()
    session.commit()
