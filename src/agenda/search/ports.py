from typing import Any, Protocol


class SearchIndexPort(Protocol):
    """Retornam os erros por id de documento; ids ausentes foram processados com sucesso."""

    def bulk_upsert(self, index: str, documents: dict[str, dict[str, Any]]) -> dict[str, str]: ...

    def bulk_delete(self, index: str, ids: list[str]) -> dict[str, str]: ...
