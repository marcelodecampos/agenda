from __future__ import annotations

import uvicorn

from agenda.config import settings


if __name__ == "__main__":
    uvicorn.run(
        "agenda.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
    )
