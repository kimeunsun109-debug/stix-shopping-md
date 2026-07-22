# -*- coding: utf-8
"""Coupang Open API — vendor item price update."""
from __future__ import annotations

import gzip
import hashlib
import hmac
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

from item_winner.env_util import load_env

API_HOST = "https://api-gateway.coupang.com"


def _decode_body(raw: bytes, encoding: str) -> str:
    if encoding.lower() == "gzip" or raw[:2] == b"\x1f\x8b":
        try:
            raw = gzip.decompress(raw)
        except Exception:
            pass
    return raw.decode("utf-8", errors="replace")


@dataclass
class ApiResult:
    ok: bool
    message: str
    code: int | None = None


def _strip_quotes(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] == '"':
        return v[1:-1]
    return v


def _api_keys(env: dict[str, str] | None = None) -> tuple[str, str, str]:
    e = env or load_env()
    access = _strip_quotes(e.get("COUPANG_ACCESS_KEY", ""))
    secret = _strip_quotes(e.get("COUPANG_SECRET_KEY", ""))
    vendor = _strip_quotes(e.get("COUPANG_VENDOR_ID", ""))
    return access, secret, vendor


def _auth_header(method: str, path: str, query: str, access: str, secret: str) -> str:
    signed_date = datetime.now(timezone.utc).strftime("%y%m%dT%H%M%S") + "Z"
    message = signed_date + method + path + query
    signature = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return (
        f"CEA algorithm=HmacSHA256, access-key={access}, "
        f"signed-date={signed_date}, signature={signature}"
    )


def update_vendor_item_price(vendor_item_id: str, price: int, env: dict[str, str] | None = None) -> ApiResult:
    access, secret, _vendor = _api_keys(env)
    if not access or not secret:
        return ApiResult(False, "COUPANG_ACCESS_KEY/SECRET_KEY missing")

    path = f"/v2/providers/seller_api/apis/api/v1/marketplace/vendor-items/{vendor_item_id}/prices/{price}"
    query = "forceSalePriceUpdate=true"
    url = f"{API_HOST}{path}?{query}"
    auth = _auth_header("PUT", path, query, access, secret)

    req = urllib.request.Request(url, method="PUT")
    req.add_header("Content-Type", "application/json;charset=UTF-8")
    req.add_header("Authorization", auth)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            body = _decode_body(raw, resp.headers.get("Content-Encoding", ""))
            return ApiResult(True, body[:500], resp.status)
    except urllib.error.HTTPError as e:
        raw = e.read()
        body = _decode_body(raw, e.headers.get("Content-Encoding", "") if e.headers else "")
        return ApiResult(False, f"HTTP {e.code}: {body[:500]}", e.code)
    except Exception as e:
        return ApiResult(False, str(e))
