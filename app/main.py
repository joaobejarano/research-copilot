from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.schemas.health import HealthResponse

logger = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "app.startup",
            app_name=settings.app_name,
            environment=settings.environment,
        )
        yield
        logger.info("app.shutdown", app_name=settings.app_name)

    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

    @app.get("/health", tags=["system"], response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            app_name=settings.app_name,
            environment=settings.environment,
        )

    return app


app = create_app()
