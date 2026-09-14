from __future__ import annotations

import json
import uuid

from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from agenda.domain.disponibilidade import (
    Disponibilidade,
    ExcecaoAgenda,
    IntervaloHorario,
    JanelaSemanal,
)
from agenda.infrastructure.db import Base, criar_session


def _intervalo_para_dict(intervalo: IntervaloHorario) -> dict[str, str]:
    return {
        "inicio": intervalo.inicio.isoformat(timespec="minutes"),
        "fim": intervalo.fim.isoformat(timespec="minutes"),
    }


def _intervalo_de_dict(dados: dict[str, str]) -> IntervaloHorario:
    return IntervaloHorario(
        inicio=__import__("datetime").datetime.strptime(dados["inicio"], "%H:%M").time(),
        fim=__import__("datetime").datetime.strptime(dados["fim"], "%H:%M").time(),
    )


def _janela_para_dict(janela: JanelaSemanal) -> dict[str, object]:
    return {
        "dia_semana": janela.dia_semana,
        "intervalo": _intervalo_para_dict(janela.intervalo),
    }


def _janela_de_dict(dados: dict[str, object]) -> JanelaSemanal:
    return JanelaSemanal(
        dia_semana=int(dados["dia_semana"]),
        intervalo=_intervalo_de_dict(dados["intervalo"]),
    )


def _excecao_para_dict(excecao: ExcecaoAgenda) -> dict[str, object]:
    return {
        "data": excecao.data.isoformat(),
        "intervalos": [_intervalo_para_dict(intervalo) for intervalo in excecao.intervalos],
    }


def _excecao_de_dict(dados: dict[str, object]) -> ExcecaoAgenda:
    return ExcecaoAgenda(
        data=__import__("datetime").date.fromisoformat(str(dados["data"])),
        intervalos=tuple(
            _intervalo_de_dict(intervalo)
            for intervalo in (dados.get("intervalos") or [])
        ),
    )


class DisponibilidadeModel(Base):
    __tablename__ = "disponibilidades"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    semanal: Mapped[str] = mapped_column(String, nullable=False)
    excecoes: Mapped[str] = mapped_column(String, nullable=False)
    profissional_id: Mapped[str | None] = mapped_column(String, nullable=True)
    organizacao_id: Mapped[str | None] = mapped_column(String, nullable=True)

    @classmethod
    def from_domain(cls, disponibilidade: Disponibilidade) -> "DisponibilidadeModel":
        return cls(
            id=str(disponibilidade.id),
            semanal=json.dumps(
                [_janela_para_dict(janela) for janela in disponibilidade.semanal],
                ensure_ascii=False,
            ),
            excecoes=json.dumps(
                [_excecao_para_dict(excecao) for excecao in disponibilidade.excecoes],
                ensure_ascii=False,
            ),
            profissional_id=str(disponibilidade.profissional_id) if disponibilidade.profissional_id else None,
            organizacao_id=str(disponibilidade.organizacao_id) if disponibilidade.organizacao_id else None,
        )

    def to_domain(self) -> Disponibilidade:
        semanal = tuple(
            _janela_de_dict(item) for item in json.loads(self.semanal or "[]")
        )
        excecoes = tuple(
            _excecao_de_dict(item) for item in json.loads(self.excecoes or "[]")
        )
        return Disponibilidade(
            id=uuid.UUID(self.id),
            semanal=semanal,
            excecoes=excecoes,
            profissional_id=uuid.UUID(self.profissional_id) if self.profissional_id else None,
            organizacao_id=uuid.UUID(self.organizacao_id) if self.organizacao_id else None,
        )


class DisponibilidadeRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, disponibilidade: Disponibilidade) -> Disponibilidade:
        with criar_session(self.engine) as session:
            session.merge(DisponibilidadeModel.from_domain(disponibilidade))
            session.commit()
        return disponibilidade

    def atualizar(self, disponibilidade: Disponibilidade) -> Disponibilidade:
        with criar_session(self.engine) as session:
            session.merge(DisponibilidadeModel.from_domain(disponibilidade))
            session.commit()
        return disponibilidade

    def remover(self, id_: uuid.UUID) -> None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(DisponibilidadeModel).where(DisponibilidadeModel.id == str(id_))
            ).scalar_one_or_none()
            if row is not None:
                session.delete(row)
                session.commit()

    def listar(self) -> list[Disponibilidade]:
        with criar_session(self.engine) as session:
            rows = session.execute(select(DisponibilidadeModel)).scalars().all()
            return [row.to_domain() for row in rows]

    def buscar_por_id(self, id_: uuid.UUID) -> Disponibilidade | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(DisponibilidadeModel).where(DisponibilidadeModel.id == str(id_))
            ).scalar_one_or_none()
            return row.to_domain() if row else None
