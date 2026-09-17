from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column

from agenda.domain.media import AnexoMedia, Media
from agenda.infrastructure.db import Base, criar_session


class MediaModel(Base):
    __tablename__ = "medias"
    __table_args__ = (UniqueConstraint("sha256", name="uq_medias_sha256"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(nullable=False)
    storage_provider: Mapped[str] = mapped_column(String, nullable=False)
    storage_key: Mapped[str] = mapped_column(String, nullable=False)
    criado_em: Mapped[str] = mapped_column(String, nullable=False)
    nome_original: Mapped[str | None] = mapped_column(String, nullable=True)

    @classmethod
    def from_domain(cls, media: Media) -> "MediaModel":
        return cls(
            id=str(media.id),
            sha256=media.sha256,
            mime_type=media.mime_type,
            tamanho_bytes=media.tamanho_bytes,
            storage_provider=media.storage_provider,
            storage_key=media.storage_key,
            criado_em=media.criado_em.isoformat(),
            nome_original=media.nome_original,
        )

    def to_domain(self) -> Media:
        return Media(
            id=uuid.UUID(self.id),
            sha256=self.sha256,
            mime_type=self.mime_type,
            tamanho_bytes=self.tamanho_bytes,
            storage_provider=self.storage_provider,
            storage_key=self.storage_key,
            criado_em=datetime.fromisoformat(self.criado_em),
            nome_original=self.nome_original,
        )


class MediaRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, media: Media) -> Media:
        with criar_session(self.engine) as session:
            session.add(MediaModel.from_domain(media))
            session.commit()
        return media

    def remover(self, id_: uuid.UUID) -> None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(MediaModel).where(MediaModel.id == str(id_))
            ).scalar_one_or_none()
            if row is not None:
                session.delete(row)
                session.commit()

    def listar(self) -> list[Media]:
        with criar_session(self.engine) as session:
            rows = session.execute(select(MediaModel)).scalars().all()
            return [row.to_domain() for row in rows]

    def buscar_por_id(self, id_: uuid.UUID) -> Media | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(MediaModel).where(MediaModel.id == str(id_))
            ).scalar_one_or_none()
            return row.to_domain() if row else None

    def buscar_por_sha256(self, sha256: str) -> Media | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(MediaModel).where(MediaModel.sha256 == sha256)
            ).scalar_one_or_none()
            return row.to_domain() if row else None


class AnexoMediaModel(Base):
    __tablename__ = "anexos_media"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    media_id: Mapped[str] = mapped_column(String, nullable=False)
    entidade_tipo: Mapped[str] = mapped_column(String, nullable=False)
    entidade_id: Mapped[str] = mapped_column(String, nullable=False)
    papel: Mapped[str] = mapped_column(String, nullable=False)
    ordem: Mapped[int] = mapped_column(default=0, nullable=False)
    criado_em: Mapped[str] = mapped_column(String, nullable=False)

    @classmethod
    def from_domain(cls, anexo: AnexoMedia) -> "AnexoMediaModel":
        return cls(
            id=str(anexo.id),
            media_id=str(anexo.media_id),
            entidade_tipo=anexo.entidade_tipo,
            entidade_id=str(anexo.entidade_id),
            papel=anexo.papel,
            ordem=anexo.ordem,
            criado_em=anexo.criado_em.isoformat(),
        )

    def to_domain(self) -> AnexoMedia:
        return AnexoMedia(
            id=uuid.UUID(self.id),
            media_id=uuid.UUID(self.media_id),
            entidade_tipo=self.entidade_tipo,
            entidade_id=uuid.UUID(self.entidade_id),
            papel=self.papel,
            ordem=self.ordem,
            criado_em=datetime.fromisoformat(self.criado_em),
        )


class AnexoMediaRepository:
    def __init__(self, engine: object) -> None:
        self.engine = engine
        Base.metadata.create_all(bind=engine)

    def salvar(self, anexo: AnexoMedia) -> AnexoMedia:
        with criar_session(self.engine) as session:
            session.add(AnexoMediaModel.from_domain(anexo))
            session.commit()
        return anexo

    def remover(self, id_: uuid.UUID) -> None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(AnexoMediaModel).where(AnexoMediaModel.id == str(id_))
            ).scalar_one_or_none()
            if row is not None:
                session.delete(row)
                session.commit()

    def buscar_por_id(self, id_: uuid.UUID) -> AnexoMedia | None:
        with criar_session(self.engine) as session:
            row = session.execute(
                select(AnexoMediaModel).where(AnexoMediaModel.id == str(id_))
            ).scalar_one_or_none()
            return row.to_domain() if row else None

    def listar_por_entidade(self, entidade_tipo: str, entidade_id: uuid.UUID) -> list[AnexoMedia]:
        with criar_session(self.engine) as session:
            rows = session.execute(
                select(AnexoMediaModel)
                .where(
                    AnexoMediaModel.entidade_tipo == entidade_tipo,
                    AnexoMediaModel.entidade_id == str(entidade_id),
                )
                .order_by(AnexoMediaModel.ordem)
            ).scalars().all()
            return [row.to_domain() for row in rows]

    def contar_por_media_id(self, media_id: uuid.UUID) -> int:
        with criar_session(self.engine) as session:
            rows = session.execute(
                select(AnexoMediaModel).where(AnexoMediaModel.media_id == str(media_id))
            ).scalars().all()
            return len(rows)
