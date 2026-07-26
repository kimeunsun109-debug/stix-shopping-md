# -*- coding: utf-8
"""Apply sale price on Coupang Wing via CDP UI (로켓그로스 옵션별 수정)."""
from __future__ import annotations

import time
from dataclasses import dataclass

from playwright.sync_api import Page

from item_winner.env_util import get_coupang_login

WING_LIST = "https://wing.coupang.com/tenants/seller-web/vendor-inventory/list"

# vendorItemId -> (vendorInventoryId, option_match_code)
ROCKET_OPTION_MAP: dict[str, tuple[str, str]] = {
    "94214344499": ("15897375629", "15mlx1"),
    "94705203391": ("16020715295", "15mlx3"),
    "94705203395": ("16020715295", "110mlx2"),
}


@dataclass
class ApplyResult:
    ok: bool
    message: str


def ensure_wing_login(page: Page, env: dict[str, str] | None = None) -> ApplyResult:
    page.goto(WING_LIST, wait_until="domcontentloaded", timeout=120000)
    time.sleep(2)
    if "wing.coupang.com" in page.url and "xauth" not in page.url and "auth" not in page.url:
        if "상품 조회" in (page.evaluate("() => document.body.innerText") or ""):
            return ApplyResult(True, "already logged in")

    user, pw = get_coupang_login(env)
    if not user or not pw:
        return ApplyResult(False, "COUPANG_ID/PASSWORD missing in .env.txt")

    try:
        page.fill("#username", user, timeout=8000)
        page.fill("#password", pw, timeout=8000)
        page.click("#kc-login", timeout=8000)
        page.wait_for_load_state("domcontentloaded", timeout=120000)
        time.sleep(4)
    except Exception as e:
        return ApplyResult(False, f"login form failed: {e}")

    if "wing.coupang.com" in page.url and "xauth" not in page.url:
        return ApplyResult(True, "login ok")
    return ApplyResult(False, f"login failed url={page.url[:120]}")


def _modal_present(page: Page) -> bool:
    return bool(
        page.evaluate(
            """() => {
          const m = document.querySelector('[data-layer="modalView"]');
          if (!m) return false;
          const r = m.getBoundingClientRect();
          return r.width > 20 && r.height > 20;
        }"""
        )
    )


def _modal_text(page: Page) -> str:
    return page.evaluate(
        """() => {
          const m = document.querySelector('[data-layer="modalView"]');
          return m ? (m.innerText || '') : '';
        }"""
    )


def _is_option_edit_modal(text: str) -> bool:
    return "옵션 수정" in text and ("노출상품ID" in text or "판매가 (원)" in text)


def _is_submit_confirm_modal(text: str) -> bool:
    return any(x in text for x in ("검수", "수정 하시겠", "저장하시겠", "변경하시겠"))


def _is_blocking_modal(text: str) -> bool:
    if _is_option_edit_modal(text) or _is_submit_confirm_modal(text):
        return False
    return any(x in text for x in ("수수료", "이미지", "앱 다운", "앱다운"))


def _dismiss_modals(page: Page) -> None:
    """Close Wing overlays (수수료조회 / 이미지가이드 / 앱다운로드 등) that block submit."""
    for _ in range(8):
        if not _modal_present(page):
            break
        text = _modal_text(page)
        if _is_option_edit_modal(text) or _is_submit_confirm_modal(text):
            break
        closed = False
        if _is_blocking_modal(text):
            for label in ("취소", "닫기", "나중에", "건너뛰기"):
                try:
                    ok = page.evaluate(
                        """(label) => {
                      const m = document.querySelector('[data-layer="modalView"]');
                      if (!m) return false;
                      for (const b of m.querySelectorAll('button')) {
                        const t = (b.innerText||'').trim();
                        if (t === label && b.offsetParent && !b.disabled) { b.click(); return true; }
                      }
                      return false;
                    }""",
                        label,
                    )
                    if ok:
                        closed = True
                        time.sleep(0.5)
                        break
                except Exception:
                    pass
        if not closed:
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            time.sleep(0.3)
        if not _modal_present(page):
            break


def _click_btn_text(page: Page, *labels: str) -> bool:
    for label in labels:
        ok = page.evaluate(
            """(label) => {
          for (const b of document.querySelectorAll('button')) {
            const t = (b.innerText||'').trim();
            if (t === label && b.offsetParent && !b.disabled) { b.click(); return true; }
          }
          return false;
        }""",
            label,
        )
        if ok:
            time.sleep(2)
            return True
    return False


def _scroll_options(page: Page) -> None:
    page.evaluate(
        """() => {
      const el = [...document.querySelectorAll('*')].find(e =>
        (e.innerText||'').includes('옵션 목록') || (e.innerText||'').includes('판매가')
      );
      el?.scrollIntoView({block:'center'});
    }"""
    )
    time.sleep(1)


def _option_index(page: Page, match_code: str) -> int:
    """Return option row index for match_code, or -1."""
    return int(
        page.evaluate(
            """(code) => {
          const norm = (t) => (t||'').replace(/\\s/g,'').replace(/×/g,'x').toLowerCase();
          const match = (t) => {
            const s = norm(t);
            if (code === '15mlx3') return s.includes('15mlx3') || /15mlx?3/.test(s);
            if (code === '110mlx2') return s.includes('110mlx2') || /110mlx?2/.test(s);
            if (code === '15mlx1') {
              if (/15mlx?[235]/.test(s)) return false;
              return s.includes('15ml');
            }
            return s.includes(String(code).toLowerCase());
          };
          const names = [...document.querySelectorAll('.option-pane-table-cell')]
            .filter(c => /^\\d\\./.test((c.innerText||'').trim()));
          return names.findIndex(c => match(c.innerText));
        }""",
            match_code,
        )
    )


def _click_scored_sale_edit(page: Page) -> bool:
    """Playwright click on 판매가/아이템위너 인근 수정 (single-option p1)."""
    _scroll_options(page)
    idx = int(
        page.evaluate(
            """() => {
          const btns = [...document.querySelectorAll('button')]
            .filter(b => (b.innerText||'').trim()==='수정' && b.offsetParent);
          let best = -1, bestScore = -999;
          btns.forEach((b, i) => {
            const around = ((b.closest('tr,table,[class*=option],section') || b.parentElement || b).innerText || '');
            let score = 0;
            if (/아이템위너/.test(around)) score += 5;
            if (/1,500|1500|1,\\d{3}/.test(around)) score += 3;
            if (/판매가/.test(around)) score += 2;
            if (/상품 구성/.test(around)) score -= 10;
            if (score > bestScore) { bestScore = score; best = i; }
          });
          return best;
        }"""
        )
    )
    loc = page.locator("button", has_text="수정")
    visible = [i for i in range(loc.count()) if loc.nth(i).is_visible()]
    if not visible:
        return False
    pick = visible[idx] if 0 <= idx < len(visible) else visible[-1]
    loc.nth(pick).scroll_into_view_if_needed()
    loc.nth(pick).click(timeout=5000)
    time.sleep(2.5)
    for _ in range(10):
        if page.locator(".editable-cell input").count() > 0:
            return True
        time.sleep(0.5)
    return page.locator(".editable-cell input").count() > 0


def _click_option_edit(page: Page, match_code: str) -> bool:
    """Click 수정 for the option — this reveals `.editable-cell` price inputs."""
    if match_code == "15mlx1":
        return _click_scored_sale_edit(page)

    _scroll_options(page)
    idx = _option_index(page, match_code)
    btns = page.locator(".option-pane-table-cell button", has_text="수정")
    count = btns.count()
    if idx < 0 or idx >= count:
        # single-option: click the 수정 near 판매가
        clicked = page.evaluate(
            """() => {
          const btns = [...document.querySelectorAll('button')]
            .filter(b => (b.innerText||'').trim()==='수정' && b.offsetParent);
          for (const b of btns) {
            const around = (b.closest('tr,table,[class*=option],[class*=pane]')||b.parentElement||b).innerText||'';
            if (/판매가|아이템위너|\\d{1,3},\\d{3}/.test(around) && !/상품 구성/.test(around)) {
              b.click(); return true;
            }
          }
          if (btns.length) { btns[btns.length-1].click(); return true; }
          return false;
        }"""
        )
        time.sleep(2.5)
        return bool(clicked)

    btns.nth(idx).click(timeout=5000)
    time.sleep(2.5)
    # wait until editable cells appear
    for _ in range(10):
        if page.locator(".editable-cell input").count() > 0:
            return True
        time.sleep(0.5)
    return page.locator(".editable-cell input").count() > 0


def _set_price_by_vendor_item(page: Page, vendor_item_id: str, new_price: int) -> dict:
    """
    After option 수정, Wing exposes `.editable-cell` inputs keyed by vendorItemId.
    Observed columns: td3 stock, td4 sale/list (editable, matches display), td6 secondary, td7 locked display.
    """
    # Prefer Playwright fill for React
    rows = page.locator("tr").filter(has_text=vendor_item_id)
    if rows.count() == 0:
        return {"ok": False, "reason": "row not found", "vid": vendor_item_id}

    target = None
    for i in range(rows.count()):
        row = rows.nth(i)
        if row.locator(".editable-cell input").count() > 0:
            target = row
            break
    if target is None:
        return {"ok": False, "reason": "no editable-cell in row", "vid": vendor_item_id}

    locked = None
    for inp in target.locator("input").all():
        try:
            if inp.is_disabled():
                raw = (inp.input_value(timeout=400) or "").replace(",", "")
                if raw.isdigit() and int(raw) >= 500:
                    locked = raw
                    break
        except Exception:
            pass

    candidates: list[tuple] = []
    for inp in target.locator(".editable-cell input").all():
        try:
            if not inp.is_enabled(timeout=300):
                continue
            raw = (inp.input_value(timeout=400) or "").replace(",", "")
            if not raw.isdigit():
                continue
            v = int(raw)
            if v < 500:
                continue
            candidates.append((inp, raw, v))
        except Exception:
            continue

    if not candidates:
        return {"ok": False, "reason": "no enabled price inputs", "vid": vendor_item_id, "locked": locked}

    pick = None
    before = None
    if locked:
        for inp, raw, v in candidates:
            if raw == locked:
                pick, before = inp, v
                break
    if pick is None:
        # Prefer the larger price field (sale/list), not secondary/min hints
        candidates.sort(key=lambda x: -x[2])
        pick, before = candidates[0][0], candidates[0][2]

    try:
        # Ctrl+A + type — fill("") then fill(price) can CONCATENATE on Wing React inputs
        # (root cause of 15001490 / 7500750 disasters on 2026-07-23).
        pick.click(timeout=3000)
        pick.press("Control+a")
        pick.press("Backspace")
        pick.type(str(new_price), delay=30)
        pick.press("Tab")
        time.sleep(0.5)
        after = (pick.input_value(timeout=1000) or "").replace(",", "")
        ok = after == str(new_price)
        return {
            "ok": ok,
            "before": before,
            "after": after,
            "locked": locked,
            "vid": vendor_item_id,
        }
    except Exception as e:
        return {"ok": False, "reason": f"fill failed: {e}", "vid": vendor_item_id}


def _save_option_edit_modal(page: Page) -> bool:
    """Commit inline price edit — Playwright click 저장 on option modal."""
    for _ in range(4):
        if not _modal_present(page):
            return True
        text = _modal_text(page)
        if not _is_option_edit_modal(text):
            return True
        try:
            modal = page.locator("[data-layer='modalView']")
            btn = modal.get_by_role("button", name="저장")
            if btn.count():
                btn.first.click(timeout=5000, force=True)
            else:
                page.locator("button", has_text="저장").first.click(timeout=5000, force=True)
        except Exception:
            return False
        time.sleep(2)
    return not _modal_present(page)


def _confirm_submit_dialogs(page: Page) -> None:
    for _ in range(8):
        if not _modal_present(page):
            break
        text = _modal_text(page)
        if _is_blocking_modal(text):
            _dismiss_modals(page)
            continue
        if not _is_submit_confirm_modal(text) and "확인" not in text and "예" not in text:
            break
        clicked = page.evaluate(
            """() => {
          const m = document.querySelector('[data-layer="modalView"]');
          if (!m) return null;
          for (const want of ['확인', '예', '수정 및 검수 요청']) {
            for (const b of m.querySelectorAll('button')) {
              if ((b.innerText||'').trim() === want && !b.disabled && b.offsetParent) {
                b.click(); return want;
              }
            }
          }
          return null;
        }"""
        )
        if not clicked:
            break
        time.sleep(1.5)


def _submit_modify_page(page: Page) -> bool:
    _dismiss_modals(page)
    clicked = False
    for label in ("수정 및 검수 요청", "수정완료", "저장"):
        try:
            btn = page.get_by_role("button", name=label)
            if btn.count():
                btn.first.click(timeout=5000, force=True)
                clicked = True
                time.sleep(2)
                break
        except Exception:
            pass
    if not clicked and not _click_btn_text(page, "수정 및 검수 요청", "수정완료", "저장"):
        return False
    _confirm_submit_dialogs(page)
    return True


def _verify_option_price(page: Page, match_code: str, vendor_item_id: str, new_price: int) -> bool:
    price_str = f"{new_price:,}"
    # option pane row near name
    ok = page.evaluate(
        """(args) => {
      const norm = (t) => (t||'').replace(/\\s/g,'').replace(/×/g,'x').toLowerCase();
      const match = (t) => {
        const s = norm(t); const code = args.code;
        if (code === '15mlx3') return s.includes('15mlx3') || /15mlx?3/.test(s);
        if (code === '110mlx2') return s.includes('110mlx2') || /110mlx?2/.test(s);
        if (code === '15mlx1') return s.includes('15ml') && !/15mlx?[235]/.test(s);
        return s.includes(code);
      };
      const names = [...document.querySelectorAll('.option-pane-table-cell')]
        .filter(c => /^\\d\\./.test((c.innerText||'').trim()));
      const idx = names.findIndex(c => match(c.innerText));
      const edits = [...document.querySelectorAll('.option-pane-table-cell button')]
        .filter(b => (b.innerText||'').trim()==='수정');
      if (idx >= 0 && edits[idx]) {
        const around = (edits[idx].closest('tr,[class*=option-pane-table-row]') || edits[idx].parentElement || names[idx]).innerText || '';
        if (around.includes(args.priceStr) || around.includes(String(args.price))) return true;
      }
      const body = document.body.innerText || '';
      // vendor item present with price nearby is weaker signal
      return body.includes(args.vid) && (body.includes(args.priceStr) || body.includes(String(args.price)));
    }""",
        {
            "code": match_code,
            "vid": vendor_item_id,
            "price": new_price,
            "priceStr": price_str,
        },
    )
    return bool(ok)


def _read_single_option_display_price(page: Page) -> int | None:
    val = page.evaluate(
        """() => {
      const parse = (t) => {
        const prices = [...(t||'').matchAll(/(\\d{1,3}(?:,\\d{3})*)\\s*원/g)]
          .map(m => Number(m[1].replace(/,/g, '')))
          .filter(v => v >= 800 && v <= 5000);
        if (prices.length) return prices[0];
        const nums = [...(t||'').matchAll(/(\\d{1,3}(?:,\\d{3})*)/g)]
          .map(m => Number(m[1].replace(/,/g, '')))
          .filter(v => v >= 800 && v <= 5000);
        return nums.length ? nums[0] : null;
      };
      const cells = [...document.querySelectorAll('.option-pane-table-cell, tr, [class*=option-pane]')];
      for (const el of cells) {
        const t = el.innerText || '';
        if (!/15ml/.test(t) || !/아이템위너|판매/.test(t)) continue;
        if (/추천가/.test(t)) continue;
        const v = parse(t);
        if (v) return v;
      }
      const body = document.body.innerText || '';
      const idx = body.indexOf('15ml');
      if (idx >= 0) {
        const slice = body.slice(idx, idx + 220);
        if (!/추천가/.test(slice)) {
          const v = parse(slice);
          if (v) return v;
        }
      }
      return null;
    }"""
    )
    return int(val) if val else None


def _apply_single_option_modify(
    page: Page,
    vendor_inventory_id: str,
    vendor_item_id: str,
    new_price: int,
) -> ApplyResult:
    url = (
        "https://wing.coupang.com/tenants/seller-web/vendor-inventory/modify"
        f"?vendorInventoryId={vendor_inventory_id}"
    )
    page.goto(url, wait_until="domcontentloaded", timeout=120000)
    time.sleep(5)
    _dismiss_modals(page)

    if not _click_scored_sale_edit(page):
        return ApplyResult(False, "single-option edit button not found")

    if not _fill_locked_sale_price(page, new_price, lo=800, hi=5000):
        return ApplyResult(False, "single-option sale price input not found")

    if not _save_option_edit_modal(page):
        return ApplyResult(False, "option edit modal save failed")

    rejected = _price_change_rejected(page, new_price)
    if rejected:
        return ApplyResult(False, rejected)

    if not _submit_modify_page(page):
        return ApplyResult(False, "submit button not found")

    rejected = _price_change_rejected(page, new_price)
    if rejected:
        return ApplyResult(False, rejected)

    time.sleep(4)
    page.goto(url, wait_until="domcontentloaded", timeout=120000)
    time.sleep(4)
    _dismiss_modals(page)

    shown = _read_single_option_display_price(page)
    if shown == new_price:
        return ApplyResult(True, f"price set to {new_price:,}")

    body = page.evaluate("() => document.body.innerText || ''")
    price_str = f"{new_price:,}"
    if price_str in body or str(new_price) in body:
        return ApplyResult(True, f"price set to {new_price:,}")
    return ApplyResult(False, f"verify failed after submit (shown={shown})")


def _apply_on_modify_page(
    page: Page,
    vendor_inventory_id: str,
    vendor_item_id: str,
    match_code: str,
    new_price: int,
) -> ApplyResult:
    if match_code == "15mlx1":
        return _apply_single_option_modify(
            page, vendor_inventory_id, vendor_item_id, new_price
        )

    url = (
        "https://wing.coupang.com/tenants/seller-web/vendor-inventory/modify"
        f"?vendorInventoryId={vendor_inventory_id}"
    )
    page.goto(url, wait_until="domcontentloaded", timeout=120000)
    time.sleep(5)
    _dismiss_modals(page)

    if not _click_option_edit(page, match_code):
        return ApplyResult(False, f"option edit button not found: {match_code}")

    js = _set_price_by_vendor_item(page, vendor_item_id, new_price)
    if not js.get("ok"):
        filled = _fill_locked_sale_price(page, new_price, lo=800, hi=5000)
        if not filled:
            return ApplyResult(False, f"sale price input not found: {js}")

    if not _submit_modify_page(page):
        return ApplyResult(False, "submit button not found")

    time.sleep(4)
    page.goto(url, wait_until="domcontentloaded", timeout=120000)
    time.sleep(4)
    _dismiss_modals(page)

    if _verify_option_price(page, match_code, vendor_item_id, new_price):
        return ApplyResult(True, f"price set to {new_price:,}")
    # single-option verify: body near product block
    body = page.evaluate("() => document.body.innerText || ''")
    price_str = f"{new_price:,}"
    if price_str in body or str(new_price) in body:
        return ApplyResult(True, f"price set to {new_price:,}")
    return ApplyResult(False, "verify failed after submit")


def _fill_locked_sale_price(page: Page, new_price: int, lo: int = 500, hi: int = 100000) -> bool:
    """Fill sale price editable-cell (column 2). Skip auto-price(1420) and vendor codes."""
    locked: str | None = None
    for loc in page.locator(".editable-cell input").all():
        try:
            if not loc.is_disabled(timeout=200):
                continue
            raw = (loc.input_value(timeout=400) or "").replace(",", "")
            if raw.isdigit() and lo <= int(raw) <= hi:
                locked = raw
                break
        except Exception:
            continue

    if locked:
        for loc in page.locator(".editable-cell input").all():
            try:
                if not loc.is_enabled(timeout=200):
                    continue
                raw = (loc.input_value(timeout=400) or "").replace(",", "")
                if raw == locked:
                    loc.click(timeout=3000)
                    loc.press("Control+a")
                    loc.press("Backspace")
                    loc.type(str(new_price), delay=30)
                    loc.press("Tab")
                    time.sleep(0.3)
                    got = (loc.input_value(timeout=800) or "").replace(",", "")
                    return got == str(new_price)
            except Exception:
                continue

    # Observed layout: [stock, sale, auto-price, locked-display, ...]
    cells = page.locator(".editable-cell input")
    try:
        if cells.count() >= 2 and cells.nth(1).is_enabled(timeout=300):
            loc = cells.nth(1)
            raw = (loc.input_value(timeout=400) or "").replace(",", "")
            if raw.isdigit() and lo <= int(raw) <= hi:
                loc.click(timeout=3000)
                loc.press("Control+a")
                loc.press("Backspace")
                loc.type(str(new_price), delay=30)
                loc.press("Tab")
                time.sleep(0.3)
                got = (loc.input_value(timeout=800) or "").replace(",", "")
                return got == str(new_price)
    except Exception:
        pass

    candidates: list[tuple] = []
    for loc in page.locator(".editable-cell input").all():
        try:
            if not loc.is_enabled(timeout=200):
                continue
            raw = (loc.input_value(timeout=400) or "").replace(",", "")
            if not raw.isdigit():
                continue
            v = int(raw)
            if v < lo or v > hi:
                continue
            candidates.append((loc, v))
        except Exception:
            continue
    if not candidates:
        return False
    # Prefer likely sale price over auto-adjust (~1420) when multiple mid-range values exist.
    candidates.sort(key=lambda x: (-x[1], x[1] == 1420))
    loc = candidates[0][0]
    try:
        loc.click(timeout=3000)
        loc.press("Control+a")
        loc.press("Backspace")
        loc.type(str(new_price), delay=30)
        loc.press("Tab")
        time.sleep(0.3)
        got = (loc.input_value(timeout=800) or "").replace(",", "")
        return got == str(new_price)
    except Exception:
        return False


def _promotion_blocks_price(page: Page) -> str | None:
    text = page.evaluate("() => document.body.innerText || ''")
    if "프로모션" in text and any(
        x in text for x in ("불가", "가격변경", "가격변경이", "종료후", "종료 후")
    ):
        return "프로모션 기간 중 가격변경 불가"
    if "프로모션 진행" in text:
        return "프로모션 기간 중 가격변경 불가"
    return None


def _price_change_rejected(page: Page, new_price: int) -> str | None:
    promo = _promotion_blocks_price(page)
    if promo:
        return promo
    shown = _read_single_option_display_price(page)
    if shown is not None and shown != new_price:
        if _promotion_blocks_price(page):
            return "프로모션 기간 중 가격변경 불가"
        return f"price not saved (shown={shown:,}, wanted={new_price:,})"
    return None


def set_vendor_item_price(page: Page, vendor_item_id: str, new_price: int) -> ApplyResult:
    mapping = ROCKET_OPTION_MAP.get(vendor_item_id)
    if mapping:
        inv_id, match_code = mapping
        return _apply_on_modify_page(page, inv_id, vendor_item_id, match_code, new_price)

    page.goto(
        f"{WING_LIST}?searchKeywordType=ALL&searchKeywords={vendor_item_id}&exposureStatus=ALL",
        wait_until="domcontentloaded",
        timeout=120000,
    )
    time.sleep(4)
    body = page.evaluate("() => document.body.innerText || ''")
    if "총 0개" in body and "총 1개" not in body:
        return ApplyResult(False, f"vendor item not found in list: {vendor_item_id}")

    try:
        page.evaluate("""() => {
          const el = [...document.querySelectorAll('a,button,span')].find(e => (e.innerText||'').trim()==='상품수정');
          el?.click();
        }""")
        time.sleep(5)
    except Exception as e:
        return ApplyResult(False, f"상품수정 click failed: {e}")

    _dismiss_modals(page)
    if not _click_option_edit(page, ""):
        return ApplyResult(False, "option edit not found")
    js = _set_price_by_vendor_item(page, vendor_item_id, new_price)
    if not js.get("ok"):
        return ApplyResult(False, "fallback modify flow failed")
    if not _submit_modify_page(page):
        return ApplyResult(False, "submit button not found")
    return ApplyResult(True, f"price set to {new_price:,}")
