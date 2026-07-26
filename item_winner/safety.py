# -*- coding: utf-8
"""Pre-apply safety gates for item winner price changes.

2026-07-26 — after P1 disaster (Wing fill concatenated prices e.g. 15001490, 7500750).
Blocked changes are logged only; Coupang API / Wing apply are NOT called.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APPLY_COUNT_FILE = ROOT / "apply_counts.json"
BLOCK_LOG = ROOT / "safety_block.jsonl"

# Absolute ceilings (won) — per-SKU overrides via max_price on SkuTarget later
DEFAULT_MAX_PRICE = 50_000
DEFAULT_MIN_PRICE = 500
MAX_RELATIVE_DELTA = 0.20  # ±20%
MAX_APPLY_PER_SKU_PER_DAY = 5
# Hard reject obvious concatenation / garbage regardless of relative %
ABSURD_PRICE_FLOOR = 100
ABSURD_DIGIT_LEN = 6  # 6+ digits for a 15ml glue SKU is never sane; also catch any >= 100000


@dataclass
class SafetyResult:
    ok: bool
    reason: str


def _load_counts() -> dict:
    if not APPLY_COUNT_FILE.exists():
        return {}
    try:
        return json.loads(APPLY_COUNT_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_counts(data: dict) -> None:
    APPLY_COUNT_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _log_block(record: dict) -> None:
    BLOCK_LOG.parent.mkdir(parents=True, exist_ok=True)
    with BLOCK_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def today_apply_count(sku: str) -> int:
    data = _load_counts()
    day = date.today().isoformat()
    return int(data.get(day, {}).get(sku, 0))


def record_successful_apply(sku: str) -> None:
    data = _load_counts()
    day = date.today().isoformat()
    data.setdefault(day, {})
    data[day][sku] = int(data[day].get(sku, 0)) + 1
    # keep last 14 days
    for k in list(data.keys()):
        if k < date.fromordinal(date.today().toordinal() - 14).isoformat():
            del data[k]
    _save_counts(data)


def check_price_change(
    *,
    sku: str,
    current_price: int,
    new_price: int,
    min_price: int | None = None,
    max_price: int | None = None,
) -> SafetyResult:
    """Return ok=False to block API/Wing call."""
    lo = min_price if min_price is not None else DEFAULT_MIN_PRICE
    hi = max_price if max_price is not None else DEFAULT_MAX_PRICE

    if new_price <= 0:
        return SafetyResult(False, f"new_price={new_price} <= 0")

    if new_price < ABSURD_PRICE_FLOOR:
        return SafetyResult(False, f"new_price={new_price} < absurd floor {ABSURD_PRICE_FLOOR}")

    if new_price >= 10 ** (ABSURD_DIGIT_LEN - 1) and new_price > hi:
        return SafetyResult(
            False,
            f"absurd/concatenated price? new={new_price:,} (digits/ceiling)",
        )

    if new_price < lo:
        return SafetyResult(False, f"new={new_price:,} < min {lo:,}")

    if new_price > hi:
        return SafetyResult(False, f"new={new_price:,} > max {hi:,}")

    if current_price > 0:
        delta = abs(new_price - current_price) / current_price
        if delta > MAX_RELATIVE_DELTA:
            return SafetyResult(
                False,
                f"Δ{delta:.0%} > ±{MAX_RELATIVE_DELTA:.0%} "
                f"({current_price:,} → {new_price:,})",
            )

    # Detect classic concat: str(a)+str(b) where both look like prices
    s = str(new_price)
    if len(s) >= 6 and current_price > 0:
        cur = str(current_price)
        if s.startswith(cur) or s.endswith(cur):
            rest = s[len(cur) :] if s.startswith(cur) else s[: -len(cur)]
            if rest.isdigit() and 500 <= int(rest) <= 100_000:
                return SafetyResult(
                    False,
                    f"likely concatenated fill ({current_price} + {rest} → {new_price})",
                )

    if today_apply_count(sku) >= MAX_APPLY_PER_SKU_PER_DAY:
        return SafetyResult(
            False,
            f"daily apply cap {MAX_APPLY_PER_SKU_PER_DAY} reached for {sku}",
        )

    return SafetyResult(True, "ok")


def block_and_log(
    *,
    sku: str,
    current_price: int,
    new_price: int,
    reason: str,
    extra: dict | None = None,
) -> None:
    from datetime import datetime

    rec = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "sku": sku,
        "current": current_price,
        "new": new_price,
        "reason": reason,
    }
    if extra:
        rec.update(extra)
    _log_block(rec)
