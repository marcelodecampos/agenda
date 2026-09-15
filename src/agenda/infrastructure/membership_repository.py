from __future__ import annotations

import uuid

from sqlalchemy import String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column

from agenda.domain.membership import Membership
from agenda.domain.papel import Papel
from agenda.infrastructure.db import Base, criar_session


class PapelModel(Base):
    __tablename__ = "papeis"
    __table_args__ = (UniqueConstraint("chave", name="uq_papeis_chave"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    chave: Mapped[str] = mapped_column(String, nullable=False)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    permissoes: Mapped[str] = mapped_column(String, nullable=False)

    @classmethod
    def from_domain(cls, papel: Papel) -> "PapelModel":
        return cls(
            id=str(papel.id),
            chave=papel.chave,
            nome=papel.nome,
            permissoes="|".join(sorted(papel.permissoes)),
        )

    def to_domain(self) -> Papel:
        return Papel(
            id=uuid.UUID(self.id),
            chave=self.chave,
            nome=self.nome,
            permissoes=frozenset(filter(None, self.permissoes.split("|"))),
        )


class PapelRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, papel: Papel) -> Papel:
        with criar_session(self.engine) as session:
            session.add(PapelModel.from_domain(papel))
            session.commit()
        return papel

    def listar(self) -> list[Papel]:
        with criar_session(self.engine) as session:
            rows = session.execute(select(PapelModel)).scalars().all()
            return [row.to_domain() for row in rows]

    def buscar_por_chave(self, chave: str) -> Papel | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(PapelModel).where(PapelModel.chave == chave)
            ).scalar_one_or_none()
            return row.to_domain() if row else None


class MembershipModel(Base):
    __tablename__ = "memberships"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    usuario_id: Mapped[str] = mapped_column(String, nullable=False)
    organizacao_id: Mapped[str | None] = mapped_column(String, nullable=True)
    ativo: Mapped[bool] = mapped_column(default=True)

    @classmethod
    def from_domain(cls, membership: Membership) -> "MembershipModel":
        return cls(
            id=str(membership.id),
            usuario_id=str(membership.usuario_id),
            organizacao_id=str(membership.organizacao_id) if membership.organizacao_id else None,
            ativo=membership.ativo,
        )

    def to_domain(self, papeis: list[Papel]) -> Membership:
        return Membership(
            id=uuid.UUID(self.id),
            usuario_id=uuid.UUID(self.usuario_id),
            organizacao_id=uuid.UUID(self.organizacao_id) if self.organizacao_id else None,
            papeis=papeis,
            ativo=self.ativo,
        )


class MembershipRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, membership: Membership) -> Membership:
        with criar_session(self.engine) as session:
            for papel in membership.papeis:
                session.merge(PapelModel.from_domain(papel))

            session.add(MembershipModel.from_domain(membership))
            session.commit()
        return membership

    def atualizar(self, membership: Membership) -> Membership:
        with criar_session(self.engine) as session:
            for papel in membership.papeis:
                session.merge(PapelModel.from_domain(papel))
            session.merge(MembershipModel.from_domain(membership))
            session.commit()
        return membership

    def remover(self, id_: uuid.UUID) -> None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(MembershipModel).where(MembershipModel.id == str(id_))
            ).scalar_one_or_none()
            if row is not None:
                session.delete(row)
                session.commit()

    def listar(self) -> list[Membership]:
        with criar_session(self.engine) as session:
            rows = session.execute(select(MembershipModel)).scalars().all()
            papel_rows = session.execute(select(PapelModel)).scalars().all()
            papeis = [p.to_domain() for p in papel_rows]
            return [row.to_domain(papeis) for row in rows]

    def buscar_por_id(self, id_: uuid.UUID) -> Membership | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(MembershipModel).where(MembershipModel.id == str(id_))
            ).scalar_one_or_none()
            if row is None:
                return None

            papel_rows = session.execute(
                select(PapelModel)
            ).scalars().all()
            papeis = [p.to_domain() for p in papel_rows]
            return row.to_domain(papeis)

    def listar_por_usuario_id(self, usuario_id: uuid.UUID) -> list[Membership]:
        with criar_session(self.engine) as session:
            rows = session.execute(
                select(MembershipModel).where(
                    MembershipModel.usuario_id == str(usuario_id)
                )
            ).scalars().all()
            papel_rows = session.execute(select(PapelModel)).scalars().all()
            papeis = [papel.to_domain() for papel in papel_rows]
            return [row.to_domain(papeis) for row in rows]
