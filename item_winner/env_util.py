# -*- coding: utf-8
"""Load secrets from .env.txt without printing values."""
from __future__ import annotations

import os
from pathlib import Path


def load_env(path: Path | None = None) -> dict[str, str]:
    p = path or Path(__file__).resolve().parent.parent / ".env.txt"
    out: dict[str, str] = {}
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def get_coupang_login(env: dict[str, str] | None = None) -> tuple[str, str]:
    e = env or load_env()
    user = e.get("WING_USERNAME") or e.get("COUPANG_ID") or os.environ.get("COUPANG_ID", "")
    pw = e.get("WING_PASSWORD") or e.get("COUPANG_PASSWORD") or os.environ.get("COUPANG_PASSWORD", "")
    return user, pw


def cdp_port(env: dict[str, str] | None = None) -> int:
    e = env or load_env()
    raw = e.get("CDP_PORT", "9233")
    try:
        return int(raw)
    except ValueError:
        return 9233
