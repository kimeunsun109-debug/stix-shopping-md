# -*- coding: utf-8 -*-
"""STIX Commerce AI v7 — Autonomous AI MD Operating System (Production Grade)."""
from __future__ import annotations

from typing import Any

__all__ = [
    "run_commerce",
    "CommerceAnalyzer",
    "CommerceDashboard",
    "CommerceContainer",
    "get_container",
]


def __getattr__(name: str) -> Any:
    """Lazy exports — avoid importing the full graph on `import commerce_ai`."""
    if name == "run_commerce":
        from commerce_ai.pipeline import run_commerce

        return run_commerce
    if name == "CommerceAnalyzer":
        from commerce_ai.analyzer import CommerceAnalyzer

        return CommerceAnalyzer
    if name == "CommerceDashboard":
        from commerce_ai.dashboard import CommerceDashboard

        return CommerceDashboard
    if name == "CommerceContainer":
        from commerce_ai.container import CommerceContainer

        return CommerceContainer
    if name == "get_container":
        from commerce_ai.container import get_container

        return get_container
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
