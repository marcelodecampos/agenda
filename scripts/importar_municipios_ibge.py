from __future__ import annotations

import argparse
from uuid import UUID

import httpx
from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.orm import Session
from uuid6 import uuid7

from agenda.config import settings
from agenda.models import FederativeUnit, Municipality

IBGE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"


def import_municipalities(session: Session) -> int:
    units = dict(session.execute(select(FederativeUnit.ibge_code, FederativeUnit.id)).all())
    rows: list[dict[str, UUID | str]] = []
    with httpx.Client(timeout=60) as client:
        for ibge_code, unit_id in units.items():
            response = client.get(f"{IBGE_URL}/{int(ibge_code)}/municipios")
            response.raise_for_status()
            for municipality in response.json():
                rows.append(
                    {
                        "id": uuid7(),
                        "ibge_code": str(municipality["id"]),
                        "name": municipality["nome"],
                        "federative_unit_id": unit_id,
                    }
                )

    if rows:
        statement = postgres_insert(Municipality.__table__).values(rows)
        statement = statement.on_conflict_do_update(
            index_elements=[Municipality.__table__.c.ibge_code],
            set_={
                "name": statement.excluded.name,
                "federative_unit_id": statement.excluded.federative_unit_id,
                "updated_at": func.now(),
            },
        )
        session.execute(statement)
    session.commit()
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa municípios da API do IBGE.")
    parser.parse_args()
    engine = create_engine(settings.database_url)
    with Session(engine) as session:
        total = import_municipalities(session)
    engine.dispose()
    print(f"municipalities_processed={total}")


if __name__ == "__main__":
    main()
