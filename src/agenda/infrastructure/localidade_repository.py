from __future__ import annotations

import uuid
from dataclasses import dataclass
from sqlalchemy import String, func, or_, select
from sqlalchemy.orm import Mapped, mapped_column

from agenda.infrastructure.db import Base, criar_session


class UnidadeFederacaoModel(Base):
    __tablename__ = "unidades_federacao"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    codigo_ibge: Mapped[str] = mapped_column(String(2), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    sigla: Mapped[str] = mapped_column(String(2), nullable=False, unique=True)


class MunicipioModel(Base):
    __tablename__ = "municipios"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    codigo_ibge: Mapped[str] = mapped_column(String(7), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    unidade_federacao_id: Mapped[str] = mapped_column(String, nullable=False)


@dataclass(frozen=True)
class Pagina:
    items: list[object]
    page: int
    page_size: int
    total: int

    @property
    def pages(self) -> int:
        return max(1, (self.total + self.page_size - 1) // self.page_size)


class LocalidadeRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    @staticmethod
    def _offset(page: int, page_size: int) -> int:
        return (max(1, page) - 1) * min(max(1, page_size), 100)

    def listar_ufs(self, busca: str, page: int, page_size: int) -> Pagina:
        return self._listar(UnidadeFederacaoModel, busca, page, page_size, [UnidadeFederacaoModel.nome, UnidadeFederacaoModel.sigla, UnidadeFederacaoModel.codigo_ibge])

    def listar_municipios(self, busca: str, uf_id: str | None, page: int, page_size: int) -> Pagina:
        filtros = []
        if busca.strip():
            termo = f"%{busca.strip()}%"
            filtros.append(or_(MunicipioModel.nome.ilike(termo), MunicipioModel.codigo_ibge.ilike(termo)))
        if uf_id:
            filtros.append(MunicipioModel.unidade_federacao_id == uf_id)
        return self._listar(MunicipioModel, "", page, page_size, [MunicipioModel.nome, MunicipioModel.codigo_ibge], filtros)

    def _listar(self, model, busca: str, page: int, page_size: int, order_by: list, filtros: list | None = None) -> Pagina:
        filtros = list(filtros or [])
        if busca.strip():
            termo = f"%{busca.strip()}%"
            filtros.append(or_(*[col.ilike(termo) for col in order_by]))
        with criar_session(self.engine) as session:
            total = session.scalar(select(func.count()).select_from(model).where(*filtros)) or 0
            items = session.scalars(
                select(model).where(*filtros).order_by(*order_by).offset(self._offset(page, page_size)).limit(min(max(1, page_size), 100))
            ).all()
            normalized_page = max(1, page)
            return Pagina(list(items), normalized_page, min(max(1, page_size), 100), total)

    def buscar_uf(self, id_: str) -> UnidadeFederacaoModel | None:
        return self._buscar(UnidadeFederacaoModel, id_)

    def buscar_uf_por_sigla(self, sigla: str) -> UnidadeFederacaoModel | None:
        with criar_session(self.engine) as session:
            return session.scalar(select(UnidadeFederacaoModel).where(UnidadeFederacaoModel.sigla == sigla.upper()))

    def buscar_municipio(self, id_: str) -> MunicipioModel | None:
        return self._buscar(MunicipioModel, id_)

    def _buscar(self, model, id_: str):
        with criar_session(self.engine) as session:
            return session.get(model, id_)

    def salvar(self, model) -> object:
        with criar_session(self.engine) as session:
            session.add(model)
            session.commit()
            session.refresh(model)
            return model

    def atualizar(self, model) -> object:
        with criar_session(self.engine) as session:
            salvo = session.merge(model)
            session.commit()
            session.refresh(salvo)
            return salvo

    def remover(self, model) -> bool:
        with criar_session(self.engine) as session:
            salvo = session.get(type(model), model.id)
            if salvo is None:
                return False
            session.delete(salvo)
            session.commit()
            return True


def novo_catalogo_id() -> str:
    return str(uuid.uuid7())
