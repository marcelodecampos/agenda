from __future__ import annotations

import uuid

from sqlalchemy import String, select
from sqlalchemy.orm import mapped_column, Mapped

from agenda.domain.usuario import Usuario
from agenda.infrastructure.db import Base, criar_session


class UsuarioModel(Base):
    __tablename__ = "usuarios"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[str] = mapped_column(String, nullable=False)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    cpf: Mapped[str | None] = mapped_column(String(11), unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    telefone: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)

    @classmethod
    def from_domain(cls, usuario: Usuario) -> "UsuarioModel":
        return cls(
            id=str(usuario.id),
            provider=usuario.provider,
            subject=usuario.subject,
            nome=usuario.nome,
            cpf=usuario.cpf,
            email=usuario.email,
            telefone=usuario.telefone,
        )

    def to_domain(self) -> Usuario:
        return Usuario(
            id=uuid.UUID(self.id),
            provider=self.provider,
            subject=self.subject,
            nome=self.nome,
            cpf=self.cpf,
            email=self.email,
            telefone=self.telefone,
        )


class UsuarioRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, usuario: Usuario) -> Usuario:
        with criar_session(self.engine) as session:
            session.add(UsuarioModel.from_domain(usuario))
            session.commit()
        return usuario

    def atualizar(self, usuario: Usuario) -> Usuario:
        with criar_session(self.engine) as session:
            session.merge(UsuarioModel.from_domain(usuario))
            session.commit()
        return usuario

    def remover(self, id_: uuid.UUID) -> None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(UsuarioModel).where(UsuarioModel.id == str(id_))
            ).scalar_one_or_none()
            if row is not None:
                session.delete(row)
                session.commit()

    def listar(self) -> list[Usuario]:
        with criar_session(self.engine) as session:
            rows = session.execute(select(UsuarioModel)).scalars().all()
            return [row.to_domain() for row in rows]

    def buscar_por_provider_subject(self, provider: str, subject: str) -> Usuario | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(UsuarioModel).where(
                    UsuarioModel.provider == provider,
                    UsuarioModel.subject == subject,
                )
            ).scalar_one_or_none()
            return row.to_domain() if row else None

    def buscar_por_cpf(self, cpf: str) -> Usuario | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(UsuarioModel).where(UsuarioModel.cpf == cpf)
            ).scalar_one_or_none()
            return row.to_domain() if row else None

    def buscar_por_email(self, email: str) -> Usuario | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(UsuarioModel).where(UsuarioModel.email == email)
            ).scalar_one_or_none()
            return row.to_domain() if row else None

    def buscar_por_telefone(self, telefone: str) -> Usuario | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(UsuarioModel).where(UsuarioModel.telefone == telefone)
            ).scalar_one_or_none()
            return row.to_domain() if row else None

    def buscar_por_id(self, id_: uuid.UUID) -> Usuario | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(UsuarioModel).where(UsuarioModel.id == str(id_))
            ).scalar_one_or_none()
            return row.to_domain() if row else None
