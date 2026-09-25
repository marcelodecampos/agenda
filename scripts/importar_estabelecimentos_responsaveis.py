from __future__ import annotations

import argparse
import csv
import re
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.orm import Session
from uuid6 import uuid7

from agenda.config import settings
from agenda.models import BaseUser, Company, CompanyResponsible, Person

DOCUMENT_DIGITS = re.compile(r"\D+")


def normalize_document(value: str | None) -> str:
    return DOCUMENT_DIGITS.sub("", value or "")


def read_csv(path: Path) -> Iterator[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        yield from csv.DictReader(file)


def chunks(items: Iterable[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    chunk: list[dict[str, Any]] = []
    for item in items:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def insert_ignore(session: Session, table: Any, rows: list[dict[str, Any]]) -> None:
    if rows:
        session.execute(postgres_insert(table).values(rows).on_conflict_do_nothing())


def load_responsibles(path: Path) -> dict[str, str]:
    responsibles: dict[str, str] = {}
    for row in read_csv(path):
        cpf = normalize_document(row.get("cpf"))
        name = (row.get("nome") or "").strip()
        if cpf and name:
            responsibles.setdefault(cpf, name)
    return responsibles


def import_data(
    session: Session,
    establishments_path: Path,
    responsibles_path: Path,
    batch_size: int,
) -> dict[str, int]:
    responsibles = load_responsibles(responsibles_path)
    establishments = list(read_csv(establishments_path))
    base_user_rows = []
    company_rows = []
    person_rows = []
    company_ids = dict(session.execute(select(Company.cnpj, Company.id)).all())
    person_ids_to_import = dict(
        session.execute(select(Person.cpf, Person.id)).all()
    )
    skipped_establishments = 0
    skipped_relationships = 0

    for row in establishments:
        cnpj = normalize_document(row.get("cnpj"))
        company_name = (row.get("nome") or "").strip()
        responsible_cpf = normalize_document(row.get("responsavel"))
        if not cnpj or not company_name:
            skipped_establishments += 1
            continue
        company_id = company_ids.get(cnpj)
        if company_id is None:
            company_id = uuid7()
            company_ids[cnpj] = company_id
            base_user_rows.append(
                {"id": company_id, "person_type": "company", "name": company_name}
            )
            company_rows.append({"id": company_id, "cnpj": cnpj})
        responsible_name = responsibles.get(responsible_cpf)
        if responsible_name:
            person_id = person_ids_to_import.get(responsible_cpf)
            if person_id is None:
                person_id = uuid7()
                person_ids_to_import[responsible_cpf] = person_id
                base_user_rows.append(
                    {
                        "id": person_id,
                        "person_type": "person",
                        "name": responsible_name,
                    }
                )
                person_rows.append({"id": person_id, "cpf": responsible_cpf})
        else:
            skipped_relationships += 1

    for batch in chunks(base_user_rows, batch_size):
        insert_ignore(session, BaseUser.__table__, batch)
    for batch in chunks(company_rows, batch_size):
        insert_ignore(session, Company.__table__, batch)
    for batch in chunks(person_rows, batch_size):
        insert_ignore(session, Person.__table__, batch)
    session.flush()

    company_ids = dict(
        session.execute(select(Company.cnpj, Company.id)).all()
    )
    person_ids = dict(
        session.execute(select(Person.cpf, Person.id)).all()
    )

    relationship_rows = []
    for row in establishments:
        cnpj = normalize_document(row.get("cnpj"))
        cpf = normalize_document(row.get("responsavel"))
        company_id = company_ids.get(cnpj)
        person_id = person_ids.get(cpf)
        if company_id is not None and person_id is not None:
            relationship_rows.append(
                {
                    "company_id": company_id,
                    "person_id": person_id,
                }
            )

    for batch in chunks(relationship_rows, batch_size):
        insert_ignore(session, CompanyResponsible.__table__, batch)

    return {
        "establishments_read": len(establishments),
        "companies_submitted": len(company_rows),
        "people_submitted": len(person_rows),
        "relationships_submitted": len(relationship_rows),
        "establishments_skipped": skipped_establishments,
        "relationships_skipped": skipped_relationships,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Importa estabelecimentos e seus responsáveis no PostgreSQL."
    )
    parser.add_argument(
        "--establishments",
        type=Path,
        default=Path("estabelecimentos.csv"),
    )
    parser.add_argument(
        "--responsibles",
        type=Path,
        default=Path("responsavel.csv"),
    )
    parser.add_argument("--batch-size", type=int, default=1000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = create_engine(settings.database_url)
    with Session(engine) as session:
        summary = import_data(
            session,
            args.establishments,
            args.responsibles,
            args.batch_size,
        )
        session.commit()
    engine.dispose()
    for key, value in summary.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
