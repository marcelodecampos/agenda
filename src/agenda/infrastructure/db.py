from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def criar_engine(database_url: str, *, echo: bool = False) -> object:
    """Create the application engine from the configured database URL."""
    return create_engine(database_url, pool_pre_ping=True, echo=echo)


def criar_engine_sqlite_memoria() -> object:
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return engine


def criar_session(engine: object) -> Session:
    return Session(bind=engine)
