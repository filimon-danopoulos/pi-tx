from __future__ import annotations
import logging
import os
from typing import Optional

_LOG_INITIALIZED = False

LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def init_logging(level: str | int = None) -> None:
    global _LOG_INITIALIZED
    if _LOG_INITIALIZED:
        return
    if level is None:
        level_env = os.getenv("PI_TX_LOG_LEVEL", "INFO").upper()
        level = LEVEL_MAP.get(level_env, logging.INFO)
    elif isinstance(level, str):
        level = LEVEL_MAP.get(level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    _LOG_INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    if not _LOG_INITIALIZED:
        init_logging()
    return logging.getLogger(name)
