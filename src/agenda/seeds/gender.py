from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from agenda.models.gender import Gender


INITIAL_GENDERS: tuple[str, ...] = ("Masculino", "Feminino")


def seed_genders(session: Session, records: Sequence[str] = INITIAL_GENDERS) -> None:
    existing_descriptions = set(
        session.scalars(
            select(Gender.description).where(Gender.description.in_(records))
        )
    )
    session.add_all(
        Gender(description=description)
        for description in records
        if description not in existing_descriptions
    )
    session.flush()
