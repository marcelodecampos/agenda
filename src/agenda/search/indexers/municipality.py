from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from agenda.models.federative_unit import FederativeUnit
from agenda.models.municipality import Municipality
from agenda.search.indexer import AnalyzerCheck, EntityIndexer

SETTINGS: dict[str, Any] = {
    "analysis": {
        "filter": {
            "autocomplete_edge_ngram": {"type": "edge_ngram", "min_gram": 2, "max_gram": 20},
        },
        "analyzer": {
            "autocomplete_index": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": ["lowercase", "asciifolding", "autocomplete_edge_ngram"],
            },
            "autocomplete_search": {
                "type": "custom",
                "tokenizer": "standard",
                "filter": ["lowercase", "asciifolding"],
            },
        },
        "normalizer": {
            "sort_normalizer": {"type": "custom", "filter": ["lowercase", "asciifolding"]},
        },
    },
}

MAPPINGS: dict[str, Any] = {
    "dynamic": "strict",
    "properties": {
        "id": {"type": "keyword"},
        "ibge_code": {"type": "keyword"},
        "name": {
            "type": "text",
            "analyzer": "autocomplete_index",
            "search_analyzer": "autocomplete_search",
            "fields": {"keyword": {"type": "keyword", "normalizer": "sort_normalizer"}},
        },
        "federative_unit_id": {"type": "keyword"},
        "federative_unit_abbreviation": {"type": "keyword"},
        "federative_unit_name": {"type": "text", "analyzer": "autocomplete_search"},
    },
}


def load_documents(session: Session, ids: list[UUID]) -> dict[UUID, dict[str, Any]]:
    statement = (
        select(
            Municipality.id,
            Municipality.ibge_code,
            Municipality.name,
            FederativeUnit.id.label("federative_unit_id"),
            FederativeUnit.abbreviation.label("federative_unit_abbreviation"),
            FederativeUnit.name.label("federative_unit_name"),
        )
        .join(FederativeUnit, Municipality.federative_unit_id == FederativeUnit.id)
        .where(Municipality.id.in_(ids))
    )
    return {
        row.id: {
            "id": str(row.id),
            "ibge_code": row.ibge_code,
            "name": row.name,
            "federative_unit_id": str(row.federative_unit_id),
            "federative_unit_abbreviation": row.federative_unit_abbreviation,
            "federative_unit_name": row.federative_unit_name,
        }
        for row in session.execute(statement)
    }


INDEXER = EntityIndexer(
    entity_type="municipality",
    version=1,
    settings=SETTINGS,
    mappings=MAPPINGS,
    load_documents=load_documents,
    analyzer_checks=[
        AnalyzerCheck("autocomplete_search", "São Paulo", ["sao", "paulo"]),
        AnalyzerCheck("autocomplete_index", "São", ["sa", "sao"]),
    ],
)
