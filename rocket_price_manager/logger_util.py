# -*- coding: utf-8 -*-
"""콘솔 + 파일 로그."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"


def setup_logger(name: str = "rocket_price") -> logging.Logger:
    LOG_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    file_handler = logging.FileHandler(
        LOG_DIR / f"rocket_price_{datetime.now():%Y%m%d}.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s %(message)s")
    )
    logger.addHandler(file_handler)
    return logger
