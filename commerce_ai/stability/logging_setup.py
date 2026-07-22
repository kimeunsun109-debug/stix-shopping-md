# -*- coding: utf-8 -*-
"""Structured logging for Commerce AI."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

_CONFIGURED = False
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "commerce_history" / "logs"


def setup_logging(
    *,
    level: int = logging.INFO,
    to_file: bool = True,
    name: str = "commerce_ai",
) -> logging.Logger:
    global _CONFIGURED
    logger = logging.getLogger(name)
    if _CONFIGURED and logger.handlers:
        return logger

    logger.setLevel(level)
    logger.handlers.clear()
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    sh.setLevel(level)
    logger.addHandler(sh)

    if to_file:
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(
                LOG_DIR / "commerce_ai.log", encoding="utf-8"
            )
            fh.setFormatter(fmt)
            fh.setLevel(level)
            logger.addHandler(fh)
        except OSError:
            pass

    logger.propagate = False
    _CONFIGURED = True
    return logger


def get_logger(name: str = "commerce_ai") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logging(name=name.split(".")[0])
    return logger
