# -*- coding: utf-8
"""
B7000 아이템위너 30분 간격 자동 모니터 + 가격 반영.

사용:
  python md_item_winner_monitor.py          # 30분 루프
  python md_item_winner_monitor.py --once   # 1회만

전제: Chrome CDP 9233 (쿠팡 가격 관찰) + .env.txt Open API 키 (가격 반영)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from item_winner.config import B7000_TARGETS, GLOBAL_APPLY_ENABLED, INTERVAL_SEC, SKU_MAX_PRICE
from item_winner.coupang_api import update_vendor_item_price
from item_winner.decision import PriceInput, decide
from item_winner.env_util import cdp_port, load_env
from item_winner.notify import send_telegram
from item_winner.safety import (
    block_and_log,
    check_price_change,
    record_successful_apply,
)
from item_winner.scraper import observe_sku
from item_winner.wing_apply import ApplyResult, ensure_wing_login, set_vendor_item_price

ROOT = Path(__file__).resolve().parent
HISTORY = ROOT / "item_winner" / "monitor_history.jsonl"
LOG = ROOT / "item_winner" / "monitor.log"


def log(msg: str) -> None:
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    try:
        print(line.encode("cp949", errors="replace").decode("cp949"))
    except Exception:
        pass


def cdp_alive(port: int) -> bool:
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=3)
        return True
    except Exception:
        return False


def append_history(record: dict) -> None:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def apply_price(
    wing_page,
    vendor_item_id: str,
    new_price: int,
    env: dict,
    wing_ready: ApplyResult | None,
) -> tuple[bool, str]:
    """Open API 우선, 실패 시 Wing CDP."""
    api = update_vendor_item_price(vendor_item_id, new_price, env)
    if api.ok:
        return True, f"API OK"
    msg = f"API: {api.message[:180]}"
    if wing_ready and wing_ready.ok and wing_page is not None:
        res = set_vendor_item_price(wing_page, vendor_item_id, new_price)
        if res.ok:
            return True, f"Wing: {res.message}"
        msg += f" | Wing: {res.message}"
    return False, msg


def run_cycle(port: int, apply_prices: bool = True) -> None:
    env = load_env()
    ts = datetime.now().isoformat(timespec="seconds")
    log(f"=== cycle start (CDP:{port}) ===")

    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        shop = ctx.new_page()
        wing = ctx.new_page()

        wing_ready: ApplyResult | None = None
        if apply_prices:
            wing_ready = ensure_wing_login(wing, env)
            if wing_ready.ok:
                log(f"Wing CDP: {wing_ready.message}")
            else:
                log(f"Wing CDP skip ({wing_ready.message[:80]}), using Open API")

        for sku in B7000_TARGETS:
            try:
                obs = observe_sku(shop, sku)
            except Exception as e:
                log(f"{sku.key} scrape ERROR: {e}")
                continue

            if obs.my_price is None or obs.competitor_price is None:
                log(
                    f"{sku.key} incomplete my={obs.my_price} comp={obs.competitor_price} "
                    f"({obs.raw_note})"
                )
                continue

            # scrape sanity: bundled 15ml single should not exceed 3,000
            if sku.key == "p1_15mlx1" and obs.competitor_price > 3000:
                log(f"{sku.key} skip bad comp={obs.competitor_price} (scrape error)")
                continue

            inp = PriceInput(
                label=sku.label,
                my_price=obs.my_price,
                competitor_price=obs.competitor_price,
                min_price=sku.min_price,
                is_winner=obs.is_winner,
                step=sku.step,
                target_price=sku.target_price,
                hold_price=sku.hold_price,
                reactive_lower_only=sku.reactive_lower_only,
                defend_winner_only=sku.defend_winner_only,
            )
            dec = decide(inp)
            log(
                f"{sku.key} my={obs.my_price:,} comp={obs.competitor_price:,} "
                f"winner={obs.is_winner} -> {dec.action} {dec.recommended_price:,} | {dec.reason}"
            )

            applied = False
            apply_msg = ""
            want = dec.recommended_price
            would_apply = (
                GLOBAL_APPLY_ENABLED
                and sku.apply_enabled
                and apply_prices
                and dec.action != "HOLD"
                and want != obs.my_price
            )

            if not GLOBAL_APPLY_ENABLED:
                apply_msg = "GLOBAL_APPLY_ENABLED=False (paused 2026-07-26)"
                if dec.action != "HOLD" and want != obs.my_price:
                    log(f"{sku.key} apply=SKIP: {apply_msg} (would {dec.action} {want:,})")
            elif not sku.apply_enabled:
                apply_msg = "apply paused (apply_enabled=False)"
                if dec.action != "HOLD" and want != obs.my_price:
                    log(f"{sku.key} apply=SKIP: {apply_msg} (would {dec.action} {want:,})")
            elif would_apply:
                gate = check_price_change(
                    sku=sku.key,
                    current_price=obs.my_price,
                    new_price=want,
                    min_price=sku.min_price,
                    max_price=SKU_MAX_PRICE.get(sku.key),
                )
                if not gate.ok:
                    apply_msg = f"SAFETY BLOCK: {gate.reason}"
                    block_and_log(
                        sku=sku.key,
                        current_price=obs.my_price,
                        new_price=want,
                        reason=gate.reason,
                        extra={"action": dec.action},
                    )
                    log(f"{sku.key} apply=BLOCKED: {gate.reason}")
                    send_telegram(
                        f"⛔ STIX 가격변경 차단\n{sku.label}\n"
                        f"{obs.my_price:,} → {want:,}\n{gate.reason}",
                        env,
                    )
                else:
                    applied, apply_msg = apply_price(
                        wing, sku.vendor_item_id, want, env, wing_ready
                    )
                    log(f"{sku.key} apply={'OK' if applied else 'FAIL'}: {apply_msg}")
                    if applied:
                        record_successful_apply(sku.key)
                    send_telegram(
                        f"{'✅' if applied else '❌'} STIX 가격변경\n{sku.label}\n"
                        f"{obs.my_price:,} → {want:,}\n{apply_msg}",
                        env,
                    )

            append_history(
                {
                    "ts": ts,
                    "sku": sku.key,
                    "my_price": obs.my_price,
                    "competitor_price": obs.competitor_price,
                    "is_winner": obs.is_winner,
                    "action": dec.action,
                    "recommended": dec.recommended_price,
                    "applied": applied,
                    "apply_msg": apply_msg,
                    "reason": dec.reason,
                }
            )

        shop.close()
        wing.close()

    log("=== cycle end ===")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run single cycle")
    parser.add_argument("--interval", type=int, default=INTERVAL_SEC, help="Seconds between cycles")
    parser.add_argument("--no-apply", action="store_true", help="Observe only")
    args = parser.parse_args()

    env = load_env()
    port = cdp_port(env)

    if not cdp_alive(port):
        log(f"CDP port {port} unavailable. Run start_chrome_for_md.bat first.")
        return 1

    apply = not args.no_apply

    if args.once:
        run_cycle(port, apply_prices=apply)
        return 0

    log(f"Monitor started interval={args.interval}s apply={apply} mode=continuous")
    while True:
        try:
            if not cdp_alive(port):
                log(f"CDP {port} down - waiting 60s")
                time.sleep(60)
                continue
            run_cycle(port, apply_prices=apply)
        except Exception as e:
            log(f"cycle exception: {e}")
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
