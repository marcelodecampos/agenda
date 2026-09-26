import argparse
import sys

import structlog
from opensearchpy.exceptions import OpenSearchException

from agenda.config import settings
from agenda.logging import configure_logging
from agenda.search.opensearch_adapter import OpenSearchIndex, create_client
from agenda.search.registry import INDEXERS

logger = structlog.get_logger("agenda.search.cli")


def prepare(index: OpenSearchIndex) -> int:
    health = index.cluster_health()
    if health not in {"green", "yellow"}:
        logger.error("search_cluster_unhealthy", status=health)
        return 1
    logger.info("search_cluster_ok", status=health)

    failed = False
    for indexer in INDEXERS.values():
        created = index.ensure_index(indexer.index_name, {"settings": indexer.settings, "mappings": indexer.mappings})
        aliased = index.ensure_alias(indexer.alias, indexer.index_name)
        logger.info("search_index_ready", index=indexer.index_name, alias=indexer.alias, index_created=created, alias_created=aliased)
        for check in indexer.analyzer_checks:
            tokens = index.analyze(indexer.index_name, check.analyzer, check.text)
            if tokens != check.expected_tokens:
                failed = True
                logger.error("search_analyzer_invalid", index=indexer.index_name, analyzer=check.analyzer, text=check.text, expected=check.expected_tokens, actual=tokens)
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="searchctl", description="Administracao dos indices de busca.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("prepare", help="Cria indices, mappings e aliases e valida analyzers e cluster.")
    args = parser.parse_args()

    configure_logging(settings.log_level, settings.log_format)
    try:
        if args.command == "prepare":
            sys.exit(prepare(OpenSearchIndex(create_client())))
    except OpenSearchException as exc:
        logger.error("search_opensearch_error", error=str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
