import structlog
from fastapi import FastAPI

from agenda.config import settings
from agenda.logging import configure_logging


configure_logging(settings.log_level, settings.log_format)
logger = structlog.get_logger(__name__)

app = FastAPI(title=settings.app_name)


@app.get("/health")
async def health() -> dict[str, str]:
    logger.info("health_check_completed")
    return {"status": "ok", "service": "agenda"}