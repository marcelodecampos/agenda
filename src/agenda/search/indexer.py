from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class AnalyzerCheck:
    analyzer: str
    text: str
    expected_tokens: list[str]


@dataclass(frozen=True)
class EntityIndexer:
    entity_type: str
    version: int
    settings: dict[str, Any]
    mappings: dict[str, Any]
    load_documents: Callable[[Session, list[UUID]], dict[UUID, dict[str, Any]]]
    analyzer_checks: list[AnalyzerCheck] = field(default_factory=list)

    @property
    def alias(self) -> str:
        return self.entity_type

    @property
    def index_name(self) -> str:
        return f"{self.entity_type}_v{self.version}"
