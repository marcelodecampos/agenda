from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Column, ForeignKey, String, Table, select
from sqlalchemy.orm import Mapped, mapped_column

from agenda.domain.catalogo_servico import CategoriaServico, NomeServico
from agenda.domain.servico import ModalidadeAtendimento, Servico
from agenda.infrastructure.db import Base, criar_session


class ModalidadeAtendimentoModel(Base):
    __tablename__ = "modalidades_atendimento"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    chave: Mapped[str] = mapped_column(String, nullable=False)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    ajuste_preco_fixo: Mapped[str | None] = mapped_column(String, nullable=True)
    ajuste_preco_percentual: Mapped[str | None] = mapped_column(String, nullable=True)
    ajuste_duracao_minutos: Mapped[int] = mapped_column(default=0)

    @classmethod
    def from_domain(cls, modalidade: ModalidadeAtendimento) -> "ModalidadeAtendimentoModel":
        return cls(
            id=f"{modalidade.chave}-{uuid.uuid4()}",
            chave=modalidade.chave,
            nome=modalidade.nome,
            ajuste_preco_fixo=str(modalidade.ajuste_preco_fixo) if modalidade.ajuste_preco_fixo is not None else None,
            ajuste_preco_percentual=str(modalidade.ajuste_preco_percentual) if modalidade.ajuste_preco_percentual is not None else None,
            ajuste_duracao_minutos=modalidade.ajuste_duracao_minutos,
        )

    def to_domain(self) -> ModalidadeAtendimento:
        return ModalidadeAtendimento(
            chave=self.chave,
            nome=self.nome,
            ajuste_preco_fixo=Decimal(self.ajuste_preco_fixo) if self.ajuste_preco_fixo is not None else None,
            ajuste_preco_percentual=Decimal(self.ajuste_preco_percentual) if self.ajuste_preco_percentual is not None else None,
            ajuste_duracao_minutos=self.ajuste_duracao_minutos,
        )


categoria_nome_servico = Table(
    "categoria_nome_servico",
    Base.metadata,
    Column("categoria_id", String, ForeignKey("categorias_servico.id"), primary_key=True),
    Column("nome_servico_id", String, ForeignKey("nomes_servico.id"), primary_key=True),
)


class CategoriaServicoModel(Base):
    __tablename__ = "categorias_servico"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    nome: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    def to_domain(self) -> CategoriaServico:
        return CategoriaServico(id=uuid.UUID(self.id), nome=self.nome)


class NomeServicoModel(Base):
    __tablename__ = "nomes_servico"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    nome: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    def to_domain(self) -> NomeServico:
        return NomeServico(id=uuid.UUID(self.id), nome=self.nome)


class ServicoModel(Base):
    __tablename__ = "servicos"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    nome_servico_id: Mapped[str] = mapped_column(
        String, ForeignKey("nomes_servico.id"), nullable=False
    )
    duracao_base_minutos: Mapped[int] = mapped_column(nullable=False)
    preco_base: Mapped[str] = mapped_column(String, nullable=False)
    profissional_id: Mapped[str | None] = mapped_column(String, nullable=True)
    organizacao_id: Mapped[str | None] = mapped_column(String, nullable=True)
    tipo_procedimento_id: Mapped[str | None] = mapped_column(String, nullable=True)

    @classmethod
    def from_domain(cls, servico: Servico) -> "ServicoModel":
        return cls(
            id=str(servico.id),
            nome_servico_id=str(servico.nome_servico_id),
            duracao_base_minutos=servico.duracao_base_minutos,
            preco_base=str(servico.preco_base),
            profissional_id=str(servico.profissional_id) if servico.profissional_id else None,
            organizacao_id=str(servico.organizacao_id) if servico.organizacao_id else None,
            tipo_procedimento_id=(
                str(servico.tipo_procedimento_id) if servico.tipo_procedimento_id else None
            ),
        )

    def to_domain(
        self,
        nome: str,
        categorias: tuple[str, ...],
        modalidades: tuple[ModalidadeAtendimento, ...],
    ) -> Servico:
        return Servico(
            id=uuid.UUID(self.id),
            nome=nome,
            categoria=categorias[0],
            duracao_base_minutos=self.duracao_base_minutos,
            preco_base=Decimal(self.preco_base),
            nome_servico_id=uuid.UUID(self.nome_servico_id),
            categorias=categorias,
            profissional_id=uuid.UUID(self.profissional_id) if self.profissional_id else None,
            organizacao_id=uuid.UUID(self.organizacao_id) if self.organizacao_id else None,
            tipo_procedimento_id=(
                uuid.UUID(self.tipo_procedimento_id) if self.tipo_procedimento_id else None
            ),
            modalidades=modalidades,
        )



class ServicoRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, servico: Servico) -> Servico:
        with criar_session(self.engine) as session:
            nome_servico = self._obter_ou_criar_nome(session, servico)
            self._obter_ou_criar_categorias(session, servico, nome_servico.id)
            servico = Servico(
                **{
                    **servico.__dict__,
                    "nome_servico_id": uuid.UUID(nome_servico.id),
                }
            )
            for modalidade in servico.modalidades:
                session.merge(ModalidadeAtendimentoModel.from_domain(modalidade))

            session.add(ServicoModel.from_domain(servico))
            session.commit()
        return servico

    def atualizar(self, servico: Servico) -> Servico:
        with criar_session(self.engine) as session:
            nome_servico = self._obter_ou_criar_nome(session, servico)
            self._obter_ou_criar_categorias(session, servico, nome_servico.id)
            servico = Servico(
                **{
                    **servico.__dict__,
                    "nome_servico_id": uuid.UUID(nome_servico.id),
                }
            )
            for modalidade in servico.modalidades:
                session.merge(ModalidadeAtendimentoModel.from_domain(modalidade))
            session.merge(ServicoModel.from_domain(servico))
            session.commit()
        return servico

    def remover(self, id_: uuid.UUID) -> None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(ServicoModel).where(ServicoModel.id == str(id_))
            ).scalar_one_or_none()
            if row is not None:
                session.delete(row)
                session.commit()

    def listar(self) -> list[Servico]:
        with criar_session(self.engine) as session:
            rows = session.execute(select(ServicoModel)).scalars().all()
            nomes = {
                row.id: row.nome for row in session.execute(select(NomeServicoModel)).scalars()
            }
            categorias_por_nome: dict[str, tuple[str, ...]] = {}
            for categoria_id, nome_id in session.execute(
                select(categoria_nome_servico.c.categoria_id, categoria_nome_servico.c.nome_servico_id)
            ):
                categoria = session.get(CategoriaServicoModel, categoria_id)
                if categoria is not None:
                    categorias_por_nome[nome_id] = (
                        *categorias_por_nome.get(nome_id, ()),
                        categoria.nome,
                    )
            modalidades = tuple(
                m.to_domain()
                for m in session.execute(select(ModalidadeAtendimentoModel)).scalars().all()
            )
            return [
                row.to_domain(
                    nomes[row.nome_servico_id],
                    categorias_por_nome[row.nome_servico_id],
                    modalidades,
                )
                for row in rows
            ]

    def buscar_por_id(self, id_: uuid.UUID) -> Servico | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(ServicoModel).where(ServicoModel.id == str(id_))
            ).scalar_one_or_none()
            if row is None:
                return None
            nome = session.get(NomeServicoModel, row.nome_servico_id)
            categorias = self._listar_categorias(session, row.nome_servico_id)
            modalidades = tuple(
                m.to_domain()
                for m in session.execute(select(ModalidadeAtendimentoModel)).scalars().all()
            )
            return row.to_domain(nome.nome, categorias, modalidades)

    @staticmethod
    def _obter_ou_criar_nome(session: object, servico: Servico) -> NomeServicoModel:
        if servico.nome_servico_id is not None:
            nome = session.get(NomeServicoModel, str(servico.nome_servico_id))
            if nome is not None:
                return nome
        nome = session.execute(
            select(NomeServicoModel).where(NomeServicoModel.nome == servico.nome)
        ).scalar_one_or_none()
        if nome is None:
            nome = NomeServicoModel(id=str(uuid.uuid7()), nome=servico.nome)
            session.add(nome)
            session.flush()
        return nome

    @staticmethod
    def _obter_ou_criar_categorias(session: object, servico: Servico, nome_id: str) -> None:
        for categoria_nome in servico.categorias:
            categoria = session.execute(
                select(CategoriaServicoModel).where(CategoriaServicoModel.nome == categoria_nome)
            ).scalar_one_or_none()
            if categoria is None:
                categoria = CategoriaServicoModel(id=str(uuid.uuid7()), nome=categoria_nome)
                session.add(categoria)
                session.flush()
            existente = session.execute(
                select(categoria_nome_servico).where(
                    categoria_nome_servico.c.categoria_id == categoria.id,
                    categoria_nome_servico.c.nome_servico_id == nome_id,
                )
            ).first()
            if existente is None:
                session.execute(
                    categoria_nome_servico.insert().values(
                        categoria_id=categoria.id,
                        nome_servico_id=nome_id,
                    )
                )

    @staticmethod
    def _listar_categorias(session: object, nome_id: str) -> tuple[str, ...]:
        return tuple(
            categoria.nome
            for categoria_id in session.execute(
                select(categoria_nome_servico.c.categoria_id).where(
                    categoria_nome_servico.c.nome_servico_id == nome_id
                )
            ).scalars()
            if (categoria := session.get(CategoriaServicoModel, categoria_id)) is not None
        )


class NomeServicoRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, nome_servico: NomeServico) -> NomeServico:
        with criar_session(self.engine) as session:
            session.add(NomeServicoModel(id=str(nome_servico.id), nome=nome_servico.nome))
            session.commit()
        return nome_servico

    def atualizar(self, nome_servico: NomeServico) -> NomeServico:
        with criar_session(self.engine) as session:
            session.merge(NomeServicoModel(id=str(nome_servico.id), nome=nome_servico.nome))
            session.commit()
        return nome_servico

    def remover(self, id_: uuid.UUID) -> bool:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(NomeServicoModel).where(NomeServicoModel.id == str(id_))
            ).scalar_one_or_none()
            if row is None:
                return False
            usado = session.execute(
                select(ServicoModel.id).where(ServicoModel.nome_servico_id == str(id_)).limit(1)
            ).scalar_one_or_none()
            if usado is not None:
                raise ValueError("nome de servico esta sendo usado por um servico")
            session.delete(row)
            session.commit()
        return True

    def listar(self) -> list[NomeServico]:
        with criar_session(self.engine) as session:
            rows = session.execute(
                select(NomeServicoModel).order_by(NomeServicoModel.nome)
            ).scalars().all()
            return [row.to_domain() for row in rows]

    def buscar_por_id(self, id_: uuid.UUID) -> NomeServico | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(NomeServicoModel).where(NomeServicoModel.id == str(id_))
            ).scalar_one_or_none()
            return row.to_domain() if row else None

    def buscar_por_nome(self, nome: str) -> NomeServico | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(NomeServicoModel).where(NomeServicoModel.nome == nome)
            ).scalar_one_or_none()
            return row.to_domain() if row else None


class CategoriaServicoRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, categoria: CategoriaServico) -> CategoriaServico:
        with criar_session(self.engine) as session:
            session.add(CategoriaServicoModel(id=str(categoria.id), nome=categoria.nome))
            session.commit()
        return categoria

    def atualizar(self, categoria: CategoriaServico) -> CategoriaServico:
        with criar_session(self.engine) as session:
            session.merge(CategoriaServicoModel(id=str(categoria.id), nome=categoria.nome))
            session.commit()
        return categoria

    def remover(self, id_: uuid.UUID) -> bool:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(CategoriaServicoModel).where(CategoriaServicoModel.id == str(id_))
            ).scalar_one_or_none()
            if row is None:
                return False
            usado = session.execute(
                select(categoria_nome_servico.c.nome_servico_id)
                .where(categoria_nome_servico.c.categoria_id == str(id_))
                .limit(1)
            ).scalar_one_or_none()
            if usado is not None:
                raise ValueError("categoria de servico esta sendo usada por um nome de servico")
            session.delete(row)
            session.commit()
        return True

    def listar(self) -> list[CategoriaServico]:
        with criar_session(self.engine) as session:
            rows = session.execute(
                select(CategoriaServicoModel).order_by(CategoriaServicoModel.nome)
            ).scalars().all()
            return [row.to_domain() for row in rows]

    def buscar_por_id(self, id_: uuid.UUID) -> CategoriaServico | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(CategoriaServicoModel).where(CategoriaServicoModel.id == str(id_))
            ).scalar_one_or_none()
            return row.to_domain() if row else None

    def buscar_por_nome(self, nome: str) -> CategoriaServico | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(CategoriaServicoModel).where(CategoriaServicoModel.nome == nome)
            ).scalar_one_or_none()
            return row.to_domain() if row else None
