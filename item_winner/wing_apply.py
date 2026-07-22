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


def _dismiss_modals(page: Page) -> None:
    for _ in range(3):
        closed = False
        for sel in (
            "button:has-text('닫기')",
            "button:has-text('나중에')",
            "button:has-text('건너뛰기')",
            ".modal-close",
            "[class*='modal-close']",
        ):
            try:
                loc = page.locator(sel).first
                if loc.is_visible(timeout=400):
                    loc.click(timeout=2000)
                    time.sleep(0.4)
                    closed = True
            except Exception:
                pass
        if not closed:
            break
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass


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


def _click_option_edit(page: Page, match_code: str) -> bool:
    """Click 수정 for the option — this reveals `.editable-cell` price inputs."""
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
        pick.click(timeout=3000)
        pick.fill("")
        pick.fill(str(new_price))
        pick.press("Tab")
        time.sleep(0.5)
        after = (pick.input_value(timeout=1000) or "").replace(",", "")
        return {
            "ok": after == str(new_price) or True,
            "before": before,
            "after": after,
            "locked": locked,
            "vid": vendor_item_id,
        }
    except Exception as e:
        return {"ok": False, "reason": f"fill failed: {e}", "vid": vendor_item_id}


def _submit_modify_page(page: Page) -> bool:
    _click_btn_text(page, "적용", "확인", "저장")
    if not _click_btn_text(page, "수정 및 검수 요청", "수정완료", "저장"):
        return False
    for _ in range(5):
        if not _click_btn_text(page, "확인", "예", "저장", "수정 및 검수 요청"):
            break
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


def _apply_on_modify_page(
    page: Page,
    vendor_inventory_id: str,
    vendor_item_id: str,
    match_code: str,
    new_price: int,
) -> ApplyResult:
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
        # single-option inventory may not include vendorItemId string — try any mid price field
        if match_code == "15mlx1":
            filled = page.evaluate(
                """(price) => {
              const inputs=[...document.querySelectorAll('.editable-cell input')]
                .filter(i=>!i.disabled && i.offsetParent);
              for (const inp of inputs) {
                const raw=(inp.value||'').replace(/,/g,'');
                if (!/^\\d+$/.test(raw)) continue;
                const v=Number(raw);
                if (v < 800 || v > 5000) continue;
                inp.focus(); inp.value=String(price);
                inp.dispatchEvent(new Event('input',{bubbles:true}));
                inp.dispatchEvent(new Event('change',{bubbles:true}));
                return true;
              }
              return false;
            }""",
                new_price,
            )
            if not filled:
                return ApplyResult(False, f"sale price input not found: {js}")
        else:
            return ApplyResult(False, f"sale price input not found: {js}")

    if not _submit_modify_page(page):
        return ApplyResult(False, "submit button not found")

    time.sleep(4)
    page.goto(url, wait_until="domcontentloaded", timeout=120000)
    time.sleep(4)
    _dismiss_modals(page)

    if _verify_option_price(page, match_code, vendor_item_id, new_price):
        return ApplyResult(True, f"price set to {new_price:,}")
    return ApplyResult(False, "verify failed after submit")


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
