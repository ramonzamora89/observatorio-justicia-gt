"""Logging estructurado (JSON) — un evento por peticion."""

from __future__ import annotations

import logging
import sys

import structlog


def configure(level: str = "INFO", pretty: bool = False) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stderr, level=level)
    renderer = (
        structlog.dev.ConsoleRenderer() if pretty else structlog.processors.JSONRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        cache_logger_on_first_use=True,
    )
