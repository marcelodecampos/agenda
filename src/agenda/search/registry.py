from agenda.search.indexer import EntityIndexer
from agenda.search.indexers import municipality

INDEXERS: dict[str, EntityIndexer] = {
    indexer.entity_type: indexer
    for indexer in (
        municipality.INDEXER,
    )
}
