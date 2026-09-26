import os
import signal
import socket
import sys
import threading
from collections import defaultdict
from datetime import timedelta
from uuid import UUID

import structlog
from opensearchpy.exceptions import OpenSearchException
from sqlalchemy import create_engine, delete, func, or_, select, update
from sqlalchemy.orm import Session

from agenda.config import settings
from agenda.logging import configure_logging
from agenda.models.search_event import SearchEvent
from agenda.models.search_event_dlq import SearchEventDlq
from agenda.models.search_event_history import SearchEventHistory
from agenda.search.opensearch_adapter import OpenSearchIndex, create_client
from agenda.search.ports import SearchIndexPort
from agenda.search.registry import INDEXERS

logger = structlog.get_logger("agenda.search.worker")

MAX_ERROR_LENGTH = 2000


def retry_delay_seconds(attempts: int) -> int:
    delay = settings.search_worker_retry_delay_seconds * 2 ** (attempts - 1)
    return min(delay, settings.search_worker_retry_max_delay_seconds)


def claim_batch(session: Session, worker_name: str) -> list[SearchEvent]:
    lock_expired_at = func.now() - timedelta(seconds=settings.search_worker_lock_timeout_seconds)
    statement = (
        select(SearchEvent)
        .where(
            SearchEvent.next_run_at <= func.now(),
            or_(SearchEvent.locked_at.is_(None), SearchEvent.locked_at < lock_expired_at),
        )
        .order_by(SearchEvent.created_at)
        .limit(settings.search_worker_batch_size)
        .with_for_update(skip_locked=True)
    )
    events = list(session.scalars(statement))
    if events:
        session.execute(
            update(SearchEvent)
            .where(SearchEvent.id.in_([event.id for event in events]))
            .values(locked_at=func.now(), locked_by=worker_name)
        )
    session.commit()
    return events


def sync_entities(session: Session, index: SearchIndexPort, entity_type: str, entity_ids: list[UUID]) -> dict[UUID, str]:
    indexer = INDEXERS[entity_type]
    try:
        documents = indexer.load_documents(session, entity_ids)
        upserts = {str(entity_id): documents[entity_id] for entity_id in entity_ids if entity_id in documents}
        deletes = [str(entity_id) for entity_id in entity_ids if entity_id not in documents]
        errors: dict[str, str] = {}
        if upserts:
            errors |= index.bulk_upsert(indexer.alias, upserts)
        if deletes:
            errors |= index.bulk_delete(indexer.alias, deletes)
    except Exception as exc:
        logger.exception("search_sync_failed", entity_type=entity_type, entities=len(entity_ids))
        return {entity_id: f"{type(exc).__name__}: {exc}" for entity_id in entity_ids}
    return {UUID(entity_id): error for entity_id, error in errors.items()}


def record_success(session: Session, event: SearchEvent, worker_name: str) -> None:
    session.add(history_entry(event, event.attempts + 1, True, None, worker_name))
    session.execute(delete(SearchEvent).where(SearchEvent.id == event.id))


def record_failure(session: Session, event: SearchEvent, error: str, worker_name: str, retryable: bool = True) -> None:
    attempts = event.attempts + 1
    error = error[:MAX_ERROR_LENGTH]
    if not retryable or attempts >= settings.search_worker_max_attempts:
        session.add(
            SearchEventDlq(
                id=event.id,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                operation=event.operation,
                created_at=event.created_at,
                attempts=attempts,
                last_error=error,
                locked_by=worker_name,
            )
        )
        session.execute(delete(SearchEvent).where(SearchEvent.id == event.id))
        logger.warning("search_event_dead_lettered", event_id=str(event.id), entity_type=event.entity_type, error=error)
        return
    session.add(history_entry(event, attempts, False, error, worker_name))
    session.execute(
        update(SearchEvent)
        .where(SearchEvent.id == event.id)
        .values(
            attempts=attempts,
            next_run_at=func.now() + timedelta(seconds=retry_delay_seconds(attempts)),
            locked_at=None,
            locked_by=None,
        )
    )


def history_entry(event: SearchEvent, attempts: int, success: bool, error: str | None, worker_name: str) -> SearchEventHistory:
    return SearchEventHistory(
        event_id=event.id,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        operation=event.operation,
        created_at=event.created_at,
        processed_at=func.now(),
        attempts=attempts,
        success=success,
        last_error=error,
        locked_by=worker_name,
    )


def process_batch(session: Session, index: SearchIndexPort, events: list[SearchEvent], worker_name: str) -> None:
    events_by_type: dict[str, list[SearchEvent]] = defaultdict(list)
    for event in events:
        events_by_type[event.entity_type].append(event)

    for entity_type, typed_events in events_by_type.items():
        if entity_type not in INDEXERS:
            for event in typed_events:
                record_failure(session, event, f"Nenhum indexador registrado para '{entity_type}'.", worker_name, retryable=False)
            continue
        # Varios eventos da mesma entidade viram uma unica sincronizacao com o estado atual do banco.
        entity_ids = list(dict.fromkeys(event.entity_id for event in typed_events))
        errors = sync_entities(session, index, entity_type, entity_ids)
        for event in typed_events:
            error = errors.get(event.entity_id)
            if error is None:
                record_success(session, event, worker_name)
            else:
                record_failure(session, event, error, worker_name)
    session.commit()
    logger.info("search_batch_processed", events=len(events), worker=worker_name)


def missing_aliases(index: OpenSearchIndex) -> list[str]:
    return [indexer.alias for indexer in INDEXERS.values() if not index.alias_exists(indexer.alias)]


def run() -> int:
    configure_logging(settings.log_level, settings.log_format)
    worker_name = settings.search_worker_name or f"{socket.gethostname()}-{os.getpid()}"
    index = OpenSearchIndex(create_client())

    try:
        missing = missing_aliases(index)
    except OpenSearchException as exc:
        logger.error("search_opensearch_unavailable", error=str(exc))
        return 1
    if missing:
        logger.error("search_indexes_not_prepared", aliases=missing, hint="Execute 'poetry run searchctl prepare'.")
        return 1

    stop = threading.Event()

    def request_stop(signum: int, _frame: object) -> None:
        logger.info("search_worker_stopping", signal=signum)
        stop.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    engine = create_engine(settings.database_url)
    logger.info("search_worker_started", worker=worker_name, batch_size=settings.search_worker_batch_size, indexers=sorted(INDEXERS))
    while not stop.is_set():
        try:
            with Session(engine, expire_on_commit=False) as session:
                events = claim_batch(session, worker_name)
                if events:
                    process_batch(session, index, events, worker_name)
        except Exception:
            logger.exception("search_worker_batch_error")
            events = []
        if not events:
            stop.wait(settings.search_worker_poll_interval_seconds)
    logger.info("search_worker_stopped", worker=worker_name)
    return 0


if __name__ == "__main__":
    sys.exit(run())
