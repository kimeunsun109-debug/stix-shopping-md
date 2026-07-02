# -*- coding: utf-8
"""Wing 상품 가격 수정 — modify / seller-price-management (검증된 selector)."""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from browser import wait_page_ready
from config import AppConfig, PriceSetConfig

logger = logging.getLogger("rocket_price")

FIND_PRICE_JS = """
const label = arguments[0];
const inputs = [...document.querySelectorAll('input.sc-common-input')];
for (const inp of inputs) {
  const raw = (inp.value || '').replace(/,/g, '');
  if (!/^[0-9]+$/.test(raw)) continue;
  if (parseInt(raw, 10) < 100) continue;
  let p = inp;
  for (let depth = 0; depth < 15; depth++) {
    p = p.parentElement;
    if (!p) break;
    if ((p.innerText || '').includes(label)) return inp;
  }
}
return null;
"""


class WingPriceNotVerifiedError(RuntimeError):
    pass


def _load_selectors(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_verified(selectors: dict) -> None:
    wing = selectors.get("wing", {})
    if not wing.get("verified"):
        raise WingPriceNotVerifiedError("wing_probe.py 먼저 실행하세요.")
    if wing.get("page_mode") == "modify" and not wing.get("save_button"):
        raise WingPriceNotVerifiedError("selectors.json wing.save_button 누락")


def _parse_price_value(raw: str) -> int | None:
    digits = re.sub(r"[^\d]", "", raw or "")
    return int(digits) if digits else None


def _build_modify_url(cfg: AppConfig, selectors: dict) -> str:
    if not cfg.vendor_inventory_id:
        raise ValueError("modify 모드: VENDOR_INVENTORY_ID 필요")
    return selectors["wing"]["modify_url_template"].format(
        vendor_inventory_id=cfg.vendor_inventory_id
    )


def _click_save(driver: webdriver.Chrome, selectors: dict) -> None:
    wing = selectors["wing"]
    save = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, wing["save_button"]))
    )
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", save)
    save.click()
    wait_page_ready(driver, 2)

    # 확인 모달
    confirm_sel = wing.get("save_confirm_button")
    if confirm_sel:
        confirms = driver.find_elements(By.CSS_SELECTOR, confirm_sel)
        visible = [c for c in confirms if c.is_displayed()]
        if visible:
            visible[0].click()
            wait_page_ready(driver, 3)
            logger.info("저장 확인 모달 클릭")


def update_wing_price(
    driver: webdriver.Chrome,
    cfg: AppConfig,
    selectors: dict,
    pset: PriceSetConfig,
    new_price: int,
    retry_count: int = 3,
    retry_delay: int = 10,
) -> tuple[int | None, int]:
    """Wing modify 페이지에서 옵션별 판매가 변경."""
    _ensure_verified(selectors)
    wing = selectors["wing"]
    url = _build_modify_url(cfg, selectors)
    last_err: Exception | None = None

    for attempt in range(1, retry_count + 1):
        try:
            driver.get(url)
            wait_page_ready(driver, 12)

            if wing.get("page_mode") == "modify":
                price_input = driver.execute_script(FIND_PRICE_JS, pset.wing_option_label)
                if not price_input:
                    raise ValueError(
                        f"옵션 '{pset.wing_option_label}' 판매가 input 미발견 — WING_*_OPTION_LABEL 확인"
                    )
                old_price = _parse_price_value(price_input.get_attribute("value") or "")
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", price_input
                )
                price_input.clear()
                price_input.send_keys(str(new_price))
            else:
                raise NotImplementedError(
                    "seller-price-management 모드는 wing_probe 후 추가 설정 필요"
                )

            _click_save(driver, selectors)
            logger.info("[%s] Wing 가격 저장 완료", pset.name)
            return old_price, new_price

        except (TimeoutException, WebDriverException, ValueError) as exc:
            last_err = exc
            logger.warning(
                "[%s] Wing 가격 변경 실패 (%s/%s): %s",
                pset.name,
                attempt,
                retry_count,
                exc,
            )
            time.sleep(retry_delay)

    raise RuntimeError(f"[{pset.name}] Wing 가격 변경 최종 실패: {last_err}")
