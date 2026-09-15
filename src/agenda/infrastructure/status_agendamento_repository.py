from __future__ import annotations

import uuid

from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from agenda.domain.agendamento import (
    CatalogoStatus,
    StatusAgendamento,
    TransicaoStatus,
)
from agenda.infrastructure.db import Base, criar_session


class StatusAgendamentoModel(Base):
    __tablename__ = "status_agendamento"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    chave: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    nome: Mapped[str] = mapped_column(String, nullable=False)


class TransicaoStatusModel(Base):
    __tablename__ = "transicoes_status_agendamento"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    de: Mapped[str] = mapped_column(String, nullable=False)
    para: Mapped[str] = mapped_column(String, nullable=False)
    atores: Mapped[str] = mapped_column(String, nullable=False)


class CatalogoStatusRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, catalogo: CatalogoStatus) -> CatalogoStatus:
        with criar_session(self.engine) as session:
            for status in catalogo.status:
                session.merge(
                    StatusAgendamentoModel(
                        id=str(uuid.uuid7()), chave=status.chave, nome=status.nome
                    )
                )
            for transicao in catalogo.transicoes:
                session.add(
                    TransicaoStatusModel(
                        id=str(uuid.uuid7()),
                        de=transicao.de,
                        para=transicao.para,
                        atores="|".join(sorted(transicao.atores)),
                    )
                )
            session.commit()
        return catalogo

    def obter(self) -> CatalogoStatus:
        with criar_session(self.engine) as session:
            statuses = session.execute(select(StatusAgendamentoModel)).scalars().all()
            transicoes = session.execute(
                select(TransicaoStatusModel)
            ).scalars().all()
            return CatalogoStatus(
                status=tuple(
                    StatusAgendamento(chave=item.chave, nome=item.nome)
                    for item in statuses
                ),
                transicoes=tuple(
                    TransicaoStatus(
                        de=item.de,
                        para=item.para,
                        atores=frozenset(filter(None, item.atores.split("|"))),
                    )
                    for item in transicoes
                ),
            )