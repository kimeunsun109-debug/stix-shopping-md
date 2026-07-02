# -*- coding: utf-8
"""
Wing 가격관리 / 상품수정 화면 DOM 프로브.

실제 Wing 화면에서 selector 를 수집해 selectors.json 을 갱신합니다.

사용법:
  1) CDP Chrome(9233) Wing 로그인 상태  또는  .env WING_USERNAME/PASSWORD
  2) python wing_probe.py
  3) probe_results/ 결과 + selectors.json 확인
"""
from __future__ import annotations

import json
import logging
import sys
import urllib.request
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By

from browser import create_driver, wait_page_ready
from config import load_config
from logger_util import setup_logger
from wing_auth import is_logged_in, login_wing

BASE_DIR = Path(__file__).resolve().parent
PROBE_DIR = BASE_DIR / "probe_results"
SELECTORS_PATH = BASE_DIR / "selectors.json"

logger = setup_logger()

# modify 페이지: 옵션명 텍스트로 sc-common-input 판매가 찾기 (2026-06-29 검증)
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

DISCOVER_JS = """
return (function(){
  const out = { inputs: [], buttons: [], optionPrices: [] };
  document.querySelectorAll('input.sc-common-input').forEach((inp, idx) => {
    const val = inp.value || '';
    out.inputs.push({
      idx, val, ph: inp.placeholder || '', cls: (inp.className || '').toString().slice(0, 120),
    });
    const raw = val.replace(/,/g, '');
    if (!/^[0-9]+$/.test(raw) || parseInt(raw, 10) < 100) return;
    let p = inp, optionText = '';
    for (let i = 0; i < 15; i++) {
      p = p.parentElement;
      if (!p) break;
      const t = (p.innerText || '').replace(/\\s+/g, ' ');
      const m = t.match(/(\\d+ml × \\d+개[^,|]{0,40})/);
      if (m) { optionText = m[1]; break; }
    }
    out.optionPrices.push({ optionText, price: val, idx });
  });
  document.querySelectorAll('button').forEach(btn => {
    const text = (btn.innerText || '').trim();
    if (!text || text.length > 30) return;
    if (/저장|확인|적용|수정 및 검수/.test(text)) {
      out.buttons.push({
        text,
        cls: (btn.className || '').toString().slice(0, 160),
        css: btn.id ? ('#' + CSS.escape(btn.id)) : null,
      });
    }
  });
  return out;
})();
"""


def cdp_alive(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2):
            return True
    except Exception:
        return False


def probe_modify_page(driver: webdriver.Chrome, vendor_id: str, selectors: dict) -> dict:
    url = selectors["wing"]["modify_url_template"].format(vendor_inventory_id=vendor_id)
    logger.info("modify 페이지 프로브: %s", url)
    driver.get(url)
    wait_page_ready(driver, 15)

    discovered = driver.execute_script(DISCOVER_JS)
    save_buttons = driver.find_elements(By.CSS_SELECTOR, "button.fs-unmask")
    save_confirm = driver.find_elements(By.CSS_SELECTOR, "button.wing-modal-confirm-trigger")

    report = {
        "mode": "modify",
        "url": driver.current_url,
        "title": driver.title,
        "discovered": discovered,
        "save_fs_unmask_count": len(save_buttons),
        "save_fs_unmask_text": [b.text.strip() for b in save_buttons[:3]],
        "save_confirm_count": len(save_confirm),
    }

    # 옵션 라벨로 input 찾기 테스트
    for label in ("15ml × 5개", "110ml × 4개"):
        el = driver.execute_script(FIND_PRICE_JS, label)
        report[f"find_price_{label[:8]}"] = bool(el)
        if el:
            report[f"price_{label[:8]}"] = driver.execute_script(
                "return arguments[0].value;", el
            )

    PROBE_DIR.mkdir(exist_ok=True)
    out = PROBE_DIR / f"wing_probe_modify_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    driver.save_screenshot(str(PROBE_DIR / "wing_probe_modify.png"))
    logger.info("저장: %s", out)
    return report


def probe_price_management(driver: webdriver.Chrome, search: str, selectors: dict) -> dict:
    url = selectors["wing"]["price_page_url_template"].format(search=search)
    logger.info("가격관리 페이지 프로브: %s", url)
    driver.get(url)
    wait_page_ready(driver, 12)

    discovered = driver.execute_script(DISCOVER_JS)
    modify_links = driver.find_elements(By.CSS_SELECTOR, "a.ap-action-link")

    report = {
        "mode": "seller-price-management",
        "url": driver.current_url,
        "title": driver.title,
        "discovered": discovered,
        "modify_link_count": len(modify_links),
        "search_input_count": len(
            driver.find_elements(By.CSS_SELECTOR, selectors["wing"].get("search_input", ""))
        ),
    }
    out = PROBE_DIR / f"wing_probe_price_mgmt_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    driver.save_screenshot(str(PROBE_DIR / "wing_probe_price_mgmt.png"))
    logger.info("저장: %s", out)
    return report


def update_selectors(selectors: dict, report: dict, cfg) -> None:
    wing = selectors["wing"]
    wing["verified"] = True
    wing["page_mode"] = cfg.wing_page_mode
    wing["probed_url"] = report.get("url", "")
    wing["probed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    if cfg.wing_page_mode == "modify":
        wing["price_input_class"] = "input.sc-common-input"
        wing["save_button"] = "button.fs-unmask"
        wing["save_confirm_button"] = "button.wing-modal-confirm-trigger"
        wing["find_price_by_option_label_js"] = True
        if not cfg.vendor_inventory_id:
            logger.warning("VENDOR_INVENTORY_ID 없음 — modify URL 템플릿만 저장")
    else:
        wing["search_input"] = 'input[placeholder*="등록상품명"]'
        wing["row_modify_link"] = "a.ap-action-link"
        wing["save_button"] = "button.wing-modal-confirm-trigger"
        wing["price_management_apply_button"] = "button.wds2.w-btn-primary"

    selectors["meta"]["wing_price_verified_at"] = wing["probed_at"]
    SELECTORS_PATH.write_text(json.dumps(selectors, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("selectors.json 갱신 (wing.verified=true)")


def wait_for_manual_login(
    driver: webdriver.Chrome,
    cfg,
    selectors: dict,
    timeout_sec: int = 180,
) -> bool:
    """CDP Chrome 창에서 사용자가 수동 로그인할 때까지 대기."""
    logger.info(
        "Wing 로그인 필요 — CDP Chrome(포트 %s) 창에서 로그인하세요. 최대 %ss 대기...",
        cfg.cdp_port,
        timeout_sec,
    )
    import time

    for _ in range(timeout_sec // 5):
        driver.get(cfg.my_product_url)
        wait_page_ready(driver, 3)
        if is_logged_in(driver, selectors["wing"]):
            logger.info("Wing 수동 로그인 확인됨")
            return True
        time.sleep(5)
    return False


def main() -> int:
    cfg = load_config()
    selectors = json.loads(SELECTORS_PATH.read_text(encoding="utf-8"))

    # CDP 9233 자동 사용 (로그인 세션 재사용)
    if not cfg.use_cdp and cdp_alive(cfg.cdp_port):
        logger.info("CDP %s 감지 — 로그인 세션 재사용 (USE_CDP=true 권장)", cfg.cdp_port)
        cfg = replace(cfg, use_cdp=True)

    driver = create_driver(cfg)
    try:
        # CDP attach 직후 빈 탭일 수 있음 → Wing URL 먼저 열기
        driver.get(cfg.my_product_url)
        wait_page_ready(driver, 5)

        if cfg.wing_username and cfg.wing_password:
            login_wing(
                driver,
                cfg.wing_username,
                cfg.wing_password,
                cfg.my_product_url,
                selectors,
                cfg.retry_count,
                cfg.retry_delay,
            )
        elif not is_logged_in(driver, selectors["wing"]):
            if cfg.use_cdp and wait_for_manual_login(driver, cfg, selectors):
                pass
            else:
                logger.error(
                    "Wing 미로그인 — .env WING_USERNAME/PASSWORD 입력 "
                    "또는 CDP Chrome(%s)에서 Wing 로그인 후 재실행",
                    cfg.cdp_port,
                )
                return 1
        else:
            logger.info("CDP 세션 Wing 로그인 확인됨 — 로그인 스킵")

        if cfg.wing_page_mode == "modify":
            if not cfg.vendor_inventory_id:
                logger.error("modify 모드: .env VENDOR_INVENTORY_ID 필수 (예: 16020715295)")
                return 1
            report = probe_modify_page(driver, cfg.vendor_inventory_id, selectors)
            if not report.get("discovered", {}).get("optionPrices"):
                logger.error("옵션별 판매가 input 을 찾지 못했습니다. probe_results 스크린샷 확인")
                return 1
            if report.get("save_fs_unmask_count", 0) < 1:
                logger.error("저장 버튼 button.fs-unmask 미발견")
                return 1
        else:
            kw = cfg.price_sets[0].wing_search_keyword if cfg.price_sets else "B7000"
            report = probe_price_management(driver, kw, selectors)

        update_selectors(selectors, report, cfg)

        logger.info("--- 프로브 결과 요약 ---")
        if "optionPrices" in report.get("discovered", {}):
            for row in report["discovered"]["optionPrices"]:
                logger.info("  옵션: %-35s 판매가: %s", row.get("optionText", ""), row.get("price", ""))
        logger.info("  저장 버튼: button.fs-unmask → '%s'", report.get("save_fs_unmask_text", [""])[0])
        logger.info("probe 완료 — main.py 실행 가능")
        return 0
    finally:
        if not cfg.use_cdp:
            driver.quit()


if __name__ == "__main__":
    sys.exit(main())
