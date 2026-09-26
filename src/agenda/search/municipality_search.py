from typing import Any
from uuid import UUID

from opensearchpy import OpenSearch

from agenda.search.indexers.municipality import INDEXER

SEARCH_TIMEOUT_SECONDS = 2


def search_municipalities(client: OpenSearch, text: str, federative_unit_id: UUID | None, limit: int) -> list[dict[str, Any]]:
    filters = [{"term": {"federative_unit_id": str(federative_unit_id)}}] if federative_unit_id else []
    body = {
        "size": limit,
        "query": {
            "bool": {
                "should": [
                    {"match": {"name": {"query": text, "operator": "and", "boost": 2}}},
                    {"match": {"name": {"query": text, "operator": "and", "fuzziness": "AUTO"}}},
                ],
                "minimum_should_match": 1,
                "filter": filters,
            }
        },
        "sort": ["_score", {"name.keyword": "asc"}],
    }
    response = client.search(index=INDEXER.alias, body=body, request_timeout=SEARCH_TIMEOUT_SECONDS)
    return [hit["_source"] for hit in response["hits"]["hits"]]
