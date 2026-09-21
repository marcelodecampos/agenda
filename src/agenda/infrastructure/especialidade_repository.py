from __future__ import annotations

import uuid

from sqlalchemy import String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column

from agenda.domain.especialidade import Especialidade
from agenda.infrastructure.db import Base, criar_session


class EspecialidadeModel(Base):
    __tablename__ = "especialidades"
    __table_args__ = (UniqueConstraint("nome", name="uq_especialidades_nome"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    nome: Mapped[str] = mapped_column(String, nullable=False)

    @classmethod
    def from_domain(cls, especialidade: Especialidade) -> "EspecialidadeModel":
        return cls(id=str(especialidade.id), nome=especialidade.nome)

    def to_domain(self) -> Especialidade:
        return Especialidade(id=uuid.UUID(self.id), nome=self.nome)


class EspecialidadeRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, especialidade: Especialidade) -> Especialidade:
        with criar_session(self.engine) as session:
            session.add(EspecialidadeModel.from_domain(especialidade))
            session.commit()
        return especialidade

    def atualizar(self, especialidade: Especialidade) -> Especialidade:
        with criar_session(self.engine) as session:
            session.merge(EspecialidadeModel.from_domain(especialidade))
            session.commit()
        return especialidade

    def remover(self, id_: uuid.UUID) -> bool:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(EspecialidadeModel).where(EspecialidadeModel.id == str(id_))
            ).scalar_one_or_none()
            if row is None:
                return False
            session.delete(row)
            session.commit()
        return True

    def listar(self) -> list[Especialidade]:
        with criar_session(self.engine) as session:
            rows = session.execute(select(EspecialidadeModel).order_by(EspecialidadeModel.nome)).scalars().all()
            return [row.to_domain() for row in rows]

    def buscar_por_id(self, id_: uuid.UUID) -> Especialidade | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(EspecialidadeModel).where(EspecialidadeModel.id == str(id_))
            ).scalar_one_or_none()
            return row.to_domain() if row else None

    def buscar_por_nome(self, nome: str) -> Especialidade | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(EspecialidadeModel).where(EspecialidadeModel.nome == nome)
            ).scalar_one_or_none()
            return row.to_domain() if row else None
