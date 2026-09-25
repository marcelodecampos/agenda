from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from agenda.config import settings

engine = create_engine(settings.database_url)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
