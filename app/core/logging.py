import logging
import sys

import structlog

from app.core.config import Settings


def _resolve_log_level(log_level: str) -> int:
    return getattr(logging, log_level.upper(), logging.INFO)


def configure_logging(settings: Settings) -> None:
    """Configure application logging with structured processors."""

    level = _resolve_log_level(settings.log_level)

    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stdout,
        force=True,
    )

    renderer = (
        structlog.processors.JSONRenderer()
        if settings.log_json
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
