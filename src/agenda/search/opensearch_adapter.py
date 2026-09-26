from functools import lru_cache
from typing import Any

from opensearchpy import OpenSearch, helpers

from agenda.config import settings


def create_client() -> OpenSearch:
    auth = (settings.opensearch_username, settings.opensearch_password) if settings.opensearch_password else None
    return OpenSearch(
        hosts=[settings.opensearch_url],
        http_auth=auth,
        http_compress=True,
        verify_certs=settings.opensearch_verify_certs,
        ssl_show_warn=settings.opensearch_verify_certs,
    )


@lru_cache(maxsize=1)
def shared_client() -> OpenSearch:
    return create_client()


class OpenSearchIndex:
    def __init__(self, client: OpenSearch) -> None:
        self._client = client

    def bulk_upsert(self, index: str, documents: dict[str, dict[str, Any]]) -> dict[str, str]:
        actions = [{"_op_type": "index", "_index": index, "_id": doc_id, "_source": doc} for doc_id, doc in documents.items()]
        return self._bulk(actions)

    def bulk_delete(self, index: str, ids: list[str]) -> dict[str, str]:
        actions = [{"_op_type": "delete", "_index": index, "_id": doc_id} for doc_id in ids]
        return self._bulk(actions)

    def _bulk(self, actions: list[dict[str, Any]]) -> dict[str, str]:
        _, failures = helpers.bulk(self._client, actions, raise_on_error=False, refresh=False)
        errors: dict[str, str] = {}
        for failure in failures:
            operation, item = next(iter(failure.items()))
            if operation == "delete" and item.get("status") == 404:
                continue
            errors[str(item.get("_id"))] = str(item.get("error") or item.get("result") or item.get("status"))
        return errors

    def cluster_health(self) -> str:
        return str(self._client.cluster.health()["status"])

    def ensure_index(self, name: str, body: dict[str, Any]) -> bool:
        if self._client.indices.exists(index=name):
            return False
        self._client.indices.create(index=name, body=body)
        return True

    def ensure_alias(self, alias: str, index: str) -> bool:
        if self._client.indices.exists_alias(name=alias):
            return False
        self._client.indices.put_alias(index=index, name=alias)
        return True

    def alias_exists(self, alias: str) -> bool:
        return bool(self._client.indices.exists_alias(name=alias))

    def analyze(self, index: str, analyzer: str, text: str) -> list[str]:
        response = self._client.indices.analyze(index=index, body={"analyzer": analyzer, "text": text})
        return [token["token"] for token in response["tokens"]]
