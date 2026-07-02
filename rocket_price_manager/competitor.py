# -*- coding: utf-8 -*-
"""쿠팡 공개 상품페이지 — 가격·판매자 크롤링 (검증된 selector 사용)."""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from browser import wait_page_ready

logger = logging.getLogger("rocket_price")

PRICE_RE = re.compile(r"([0-9,]+)\s*원")


@dataclass
class CompetitorSnapshot:
    option_label: str
    price: int
    seller_name: str
    is_my_listing: bool


def load_selectors(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_price(text: str) -> int:
    m = PRICE_RE.search(text or "")
    if not m:
        raise ValueError(f"가격 파싱 실패: {text!r}")
    return int(m.group(1).replace(",", ""))


def _parse_seller(raw: str) -> str:
    """
    예: '판매자: 온라인 마켓 판매자 상품 보러가기' → '온라인 마켓'
    """
    text = re.sub(r"\s+", " ", (raw or "").strip())
    m = re.search(r"판매자:\s*([^판매]+?)(?:\s*판매자|\s*상품|\s*$)", text)
    if m:
        return m.group(1).strip()
    if "판매자:" in text:
        return text.split("판매자:", 1)[1].strip().split()[0]
    return text.strip()


def scrape_competitor_option(
    driver: webdriver.Chrome,
    url: str,
    option_label: str,
    my_seller_name: str,
    selectors: dict,
    retry_count: int = 3,
    retry_delay: int = 10,
) -> CompetitorSnapshot:
    """
    COMPETITOR_URL 접속 후 특정 수량 옵션(예: '2개') 가격과 판매자명 수집.

    selector 출처: probe_results/competitor.json (2026-06-29 검증)
    """
    comp = selectors["competitor"]
    last_err: Exception | None = None

    for attempt in range(1, retry_count + 1):
        try:
            driver.get(url)
            wait_page_ready(driver, 4)

            if "denied" in driver.title.lower() or "access" in driver.title.lower():
                raise WebDriverException("쿠팡 Access Denied — IP/봇 차단 가능")

            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, comp["price_container"])
                )
            )

            # 수량 옵션 클릭 (2개 / 4개 등)
            option_items = driver.find_elements(By.CSS_SELECTOR, comp["option_items"])
            clicked = False
            for item in option_items:
                label_text = item.text.replace("\n", " ")
                if option_label in label_text:
                    driver.execute_script("arguments[0].click();", item)
                    clicked = True
                    wait_page_ready(driver, 1.5)
                    break

            if not clicked and option_items:
                logger.warning(
                    "옵션 '%s' 미발견 — 현재 선택된 옵션 가격 사용", option_label
                )

            # 선택 옵션 가격 우선
            price_text = ""
            selected = driver.find_elements(
                By.CSS_SELECTOR, comp["price_selected_option"]
            )
            if selected:
                price_text = selected[0].text
            else:
                container = driver.find_element(By.CSS_SELECTOR, comp["price_container"])
                price_text = container.text.split("\n")[0]

            price = _parse_price(price_text)

            # 판매자
            seller_name = ""
            seller_nodes = driver.find_elements(By.XPATH, comp["seller_xpath"])
            for node in seller_nodes:
                t = node.text.strip()
                if "판매자:" in t:
                    seller_name = _parse_seller(t)
                    break

            is_mine = my_seller_name.lower() in seller_name.lower() if seller_name else False

            return CompetitorSnapshot(
                option_label=option_label,
                price=price,
                seller_name=seller_name or "(판매자 미확인)",
                is_my_listing=is_mine,
            )
        except (TimeoutException, WebDriverException, ValueError) as exc:
            last_err = exc
            logger.warning(
                "경쟁가 수집 실패 (%s/%s): %s", attempt, retry_count, exc
            )
            time.sleep(retry_delay)

    raise RuntimeError(f"경쟁가 수집 최종 실패: {last_err}")


def calc_target_price(
    competitor_price: int,
    undercut: int,
    min_price: int,
) -> int:
    """현재가 - undercut, 단 최저마진 미만이면 최저마진."""
    candidate = competitor_price - undercut
    return max(candidate, min_price)
