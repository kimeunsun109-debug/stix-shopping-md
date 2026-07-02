# -*- coding: utf-8
"""
로켓그로스(B7000) 가격 자동 관리 — 메인 루프.

동작:
  1. .env 로드
  2. COMPETITOR_URL 에서 SET2/SET4 경쟁가·판매자 수집
  3. 내가 판매자가 아니면 (경쟁가 - PRICE_UNDERCUT), 최저가 MIN_PRICE_* 적용
  4. Wing 로그인 → 가격 수정 → 저장
  5. CHECK_INTERVAL 초 대기 후 반복

Wing 가격 수정 selector 는 wing_probe.py 로 1회 검증 필요.
"""
from __future__ import annotations

import json
import logging
import sys
import time
import traceback
from datetime import datetime

from browser import create_driver, wait_page_ready
from competitor import calc_target_price, load_selectors, scrape_competitor_option
from config import AppConfig, PriceSetConfig, load_config
from logger_util import setup_logger
from wing_auth import login_wing
from wing_price import WingPriceNotVerifiedError, update_wing_price

logger = setup_logger()


def _fmt_price(n: int) -> str:
    return f"{n:,}"


def _process_set(
    driver,
    cfg: AppConfig,
    selectors: dict,
    pset: PriceSetConfig,
) -> None:
    snap = scrape_competitor_option(
        driver,
        cfg.competitor_url,
        pset.competitor_option_label,
        cfg.my_seller_name,
        selectors,
        cfg.retry_count,
        cfg.retry_delay,
    )

    logger.info(
        "[%s] 경쟁 옵션=%s | 현재가격=%s | 판매자=%s",
        pset.name,
        snap.option_label,
        _fmt_price(snap.price),
        snap.seller_name,
    )

    if snap.is_my_listing:
        logger.info("[%s] 현재 판매자가 본인(%s) — 가격 변경 스킵", pset.name, cfg.my_seller_name)
        return

    target = calc_target_price(snap.price, cfg.price_undercut, pset.min_price)
    if target >= snap.price:
        logger.info("[%s] 변경 불필요 (목표가 >= 경쟁가)", pset.name)
        return

    old, new = update_wing_price(
        driver,
        cfg,
        selectors,
        pset,
        target,
        cfg.retry_count,
        cfg.retry_delay,
    )

    now = datetime.now().strftime("%H:%M")
    print(f"\n[{now}]")
    print(f"  [{pset.name}] 현재가격 : {_fmt_price(old) if old else '(미확인)'}")
    print(f"  [{pset.name}] 변경가격 : {_fmt_price(new)}")
    print("  업데이트 완료")
    print("-" * 19)


def run_once(cfg: AppConfig, selectors: dict, driver) -> None:
    login_wing(
        driver,
        cfg.wing_username,
        cfg.wing_password,
        cfg.my_product_url,
        selectors,
        cfg.retry_count,
        cfg.retry_delay,
    )
    for pset in cfg.price_sets:
        _process_set(driver, cfg, selectors, pset)


def main() -> int:
    cfg = load_config()
    selectors = load_selectors(cfg.selectors_path)

    if not selectors.get("wing", {}).get("verified"):
        logger.error("=" * 60)
        logger.error("Wing 가격 수정 selector 가 아직 검증되지 않았습니다.")
        logger.error("다음 순서로 진행하세요:")
        logger.error("  1) .env 에 WING_USERNAME / WING_PASSWORD 입력")
        logger.error("  2) python wing_probe.py  실행 (로그인 후 DOM 수집)")
        logger.error("  3) probe_results/*.json 과 스크린샷 육안 확인")
        logger.error("  4) python main.py 실행")
        logger.error("=" * 60)
        return 1

    driver = create_driver(cfg)
    logger.info("로켓그로스 가격 자동관리 시작 (interval=%ss)", cfg.check_interval)

    try:
        while True:
            try:
                run_once(cfg, selectors, driver)
            except WingPriceNotVerifiedError as exc:
                logger.error("%s", exc)
                return 1
            except Exception as exc:
                logger.error("루프 예외: %s", exc)
                logger.debug(traceback.format_exc())
                logger.info("%ss 후 재시도...", cfg.retry_delay)
                time.sleep(cfg.retry_delay)
                continue

            logger.info("%ss 대기...", cfg.check_interval)
            time.sleep(cfg.check_interval)
    except KeyboardInterrupt:
        logger.info("사용자 중단")
        return 0
    finally:
        if not cfg.use_cdp:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
