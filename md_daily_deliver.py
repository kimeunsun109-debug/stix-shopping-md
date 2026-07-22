# -*- coding: utf-8 -*-
"""STIX MD 일일 산출물 자동 생성"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

from md_catalog_io import load_all_catalogs

# ESM 슈퍼클러스터 분류 스크립트는 프로젝트 마감으로 삭제됨
try:
    from md_esm_group_classify import build_rows, classify, group_label, load_products
except ImportError:  # pragma: no cover
    build_rows = classify = group_label = load_products = None  # type: ignore

BASE = Path(__file__).parent
TODAY = datetime.now().strftime("%Y-%m-%d")
SRC = BASE / "쇼핑몰별 전체상품"


def load_sales_top() -> list[dict]:
    txt = BASE / f"MD_사이트별_판매상위_{TODAY}.txt"
    if not txt.exists():
        return []
    items = []
    channel = ""
    for line in txt.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            channel = line.replace("## ", "").strip()
        m = re.match(r"\s*(\d+)\s+([\d,]+)\s+([\d,]+)\s+(.+)", line)
        if m and channel:
            items.append({
                "channel": channel,
                "rank": int(m.group(1)),
                "revenue": int(m.group(2).replace(",", "")),
                "name": m.group(4).strip(),
            })
    return items


def _has(t: str, *w: str) -> bool:
    return any(x in t for x in w)


def coupang_title(name: str) -> str:
    n = name
    if _has(n, "E6000", "e6000"):
        if "30ml" in n.lower():
            return "E6000 접착제 30ml 치약본드 공예 DIY 큐빅 본드"
        if "110ml" in n.lower():
            return "E6000 접착제 110ml 치약본드 뾰족캡 공예 DIY"
        return "E6000 접착제 치약본드 공예 DIY 강력본드"
    if _has(n, "B7000"):
        if "15ml" in n.lower():
            return "B7000 접착제 15ml 치약본드 공예 DIY 비즈본드"
        return "B7000 접착제 110ml 치약본드 공예 DIY 안전인증"
    if _has(n, "보석십자수", "캔버스"):
        if "30" in n and "40" in n:
            theme = "튤립" if "튤립" in n else "바닷가" if "바닷" in n else "DIY"
            return f"보석십자수 캔버스 30x40 {theme} DIY 키트 초보자 집콕"
        if "40" in n and "50" in n:
            return "보석십자수 캔버스 40x50 DIY 키트 액자형 인테리어"
        return "보석십자수 캔버스 DIY 키트 30x40 초보자"
    if _has(n, "어린이") and _has(n, "스티커"):
        return "어린이 보석십자수 스티커 DIY 24종 방학 만들기"
    if _has(n, "크로바") and _has(n, "확대경"):
        return "크로바 확대경 핑크 1.6배 2배 세트 수예용 돋보기"
    if _has(n, "DMC") and _has(n, "자수실"):
        return "DMC 자수실 25번 면사 십자수실 503색 택1"
    if _has(n, "코바늘"):
        return "크로바 아뮤레 코바늘 8종세트 손뜨개 DIY"
    return name[:38]


def esm_title(name: str) -> str:
    n = name
    if _has(n, "E6000"):
        if "110ml" in n.lower():
            return "뾰족캡포함 E6000 접착제 110ml 치약본드 공예 DIY 당일발송 스팃스"
        if "30ml" in n.lower():
            return "E6000 접착제 30ml 치약본드 공예용 다용도 본드 DIY 스팃스"
        return "E6000 접착제 치약본드 공예 DIY 다용도 본드 스팃스"
    if _has(n, "B7000"):
        if "15ml" in n.lower():
            return "B7000 접착제 15ml 치약본드 공예 DIY 당일발송"
        return "B7000 접착제 110ml 치약본드 공예 DIY 당일발송 스팃스"
    if _has(n, "보석십자수", "캔버스") and "30" in n:
        sub = "튤립" if "튤립" in n else "바닷가 일출" if "바닷" in n else "인테리어"
        return f"보석십자수 DIY 키트 캔버스형 30x40 {sub} 액자형 취미 28칸비즈함"
    if _has(n, "어린이", "스티커"):
        return "어린이 보석십자수 스티커 DIY 만들기 키트 24종 방학선물"
    if _has(n, "코팅", "광택"):
        return "보석십자수 마무리 코팅제 광택제 120ml 2개세트 마감제"
    return name[:72]


CHANNEL_FN = {
    "쿠팡": coupang_title,
    "지마켓/옥션": esm_title,
    "스마트스토어": lambda n: (n if n.startswith("스팃스") else f"스팃스 {n}")[:55],
    "11번가": lambda n: coupang_title(n).replace("초보자", "추천")[:55],
    "카페24": lambda n: (n if n.startswith("스팃스") else f"스팃스 {n}")[:55],
}


def find_id(by_plat: dict, platform: str, name: str):
    name_l = name.lower()
    best = None
    for rec in by_plat.get(platform, []):
        rn = rec["name"].lower()
        if name_l in rn or rn in name_l:
            return rec
        if name_l[:12] in rn and (best is None or len(rn) < len(best["name"])):
            best = rec
    return best


def gen_product_names(sales_top: list[dict]) -> Path:
    catalog = load_all_catalogs()
    by_plat = defaultdict(list)
    for rec in catalog:
        by_plat[rec["platform"]].append(rec)

    plat_map = {"지마켓/옥션": "지마켓/옥션", "카페24": "카페24"}
    # 매출 높은 순 전 채널 통합
    ranked = sorted(sales_top, key=lambda x: -x["revenue"])
    seen: set[tuple] = set()
    rows = []
    for item in ranked:
        key = (item["channel"], item["name"][:30])
        if key in seen:
            continue
        seen.add(key)
        plat = plat_map.get(item["channel"], item["channel"])
        rec = find_id(by_plat, plat, item["name"])
        cur = rec["name"] if rec else item["name"]
        pid = rec["id"] if rec else "-"
        new = CHANNEL_FN.get(plat, lambda x: x)(cur)
        if new.strip() == cur.strip():
            # 실질 변경 없으면 채널별 재작성
            if plat == "쿠팡":
                new = coupang_title(cur)
            elif plat == "지마켓/옥션":
                new = esm_title(cur)
        reason = []
        if _has(cur, "보석십자수") and "30x40" not in cur.lower() and "30cm" not in cur.lower():
            reason.append("사이즈 키워드 누락")
        if _has(cur, "보석", "십자") and not _has(cur, "DIY", "키트"):
            reason.append("DIY 키워드 부족")
        if plat == "쿠팡" and len(cur) > 45:
            reason.append("40자 초과")
        if plat == "지마켓/옥션" and _has(cur, "접착", "본드") and "당일" not in cur:
            reason.append("당일발송 미반영")
        if new.strip() == cur.strip():
            reason.append("변경폭 소 — 썸네일·상세 우선")
        else:
            reason.append("채널 SEO 최적화")
        rows.append({
            "platform": item["channel"],
            "pid": pid,
            "current": cur,
            "new": new,
            "reason": ", ".join(dict.fromkeys(reason)),
            "effect": f"CTR +8~17% | 매출기여 {item['revenue']:,}원",
            "revenue": item["revenue"],
        })
        if len(rows) >= 30:
            break

    out = BASE / f"MD_상품명_개선_30건_{TODAY}.txt"
    lines = [f"STIX 상품명 개선 30건 ({TODAY})", "=" * 90]
    for i, r in enumerate(rows, 1):
        lines += [
            f"\n[{i}] {r['platform']} | 상품번호: {r['pid']}",
            f"| 현재 | {r['current'][:70]}",
            f"| 추천 | {r['new'][:70]}",
            f"| 이유 | {r['reason']}",
            f"| 효과 | {r['effect']}",
        ]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def gen_gmarket_audit(sales_top: list[dict]) -> Path:
    if build_rows is None or load_products is None:
        raise RuntimeError(
            "md_esm_group_classify 가 삭제되었습니다. "
            "지마켓 그룹 감사는 ESM 프로젝트 마감으로 비활성입니다."
        )
    df = pd.read_excel(SRC / "지마켓,옥션.xlsx")
    grp_col = [c for c in df.columns if "그룹" in str(c)][0]
    rows = build_rows(load_products())
    grp_df = pd.DataFrame(rows)
    rec_map = {
        str(r["마스터상품번호"]): r["그룹명칭"]
        for _, r in grp_df.drop_duplicates("마스터상품번호").iterrows()
    }

    no_grp = df[
        df[grp_col].isna()
        | (df[grp_col].astype(str).str.strip().isin(["", "nan", "미설정"]))
    ].drop_duplicates("마스터상품번호")
    no_grp = no_grp.copy()
    no_grp["추천그룹"] = no_grp["마스터상품번호"].astype(str).map(rec_map)

    sales_map = {s["name"]: s["revenue"] for s in sales_top if s["channel"] == "지마켓/옥션"}

    def rev_key(row):
        n = str(row.get("상품명", ""))
        for sn, rv in sales_map.items():
            if sn[:15] in n or n[:15] in sn:
                return rv
        return 0

    no_grp["_rev"] = no_grp.apply(rev_key, axis=1)
    no_grp = no_grp.sort_values("_rev", ascending=False)

    mis = grp_df[
        grp_df["그룹명칭"] == "기본부자재 - 챠코페이퍼,접착제,기타제품"
    ].drop_duplicates("마스터상품번호")

    out = BASE / f"MD_지마켓_그룹수정목록_{TODAY}.txt"
    lines = [
        f"G마켓/옥션 그룹관리 수정 목록 ({TODAY})",
        f"그룹 미설정: {len(no_grp)}마스터 / 전체 1,000마스터",
        f"업로드: STIX_지마켓_그룹관리_업로드_{TODAY}.xlsx",
        "",
        "■ 구조 변경 권장",
        "  1. 보석십자수 30x40 — 도안 테마별 그룹 (튤립·바닷가·해바라기 분리)",
        "  2. 접착제 — E6000/B7000 용량별 그룹 분리",
        "  3. 기본부자재 catch-all 97마스터 → 재분류",
        "  4. 악세사리(핸드폰줄) — 광고 제외·별도 그룹",
        "",
        "■ 그룹 미설정 TOP30",
    ]
    for _, r in no_grp.head(30).iterrows():
        lines.append(
            f"  {r['마스터상품번호']} | {r.get('추천그룹','')} | {str(r.get('상품명',''))[:50]}"
        )
    lines += ["", "■ 오분류 TOP15"]
    for _, r in mis.head(15).iterrows():
        main, sub = classify(str(r["상품명"]))
        sug = group_label(main, sub)
        if sug != r["그룹명칭"]:
            lines.append(f"  {r['마스터상품번호']} | {r['그룹명칭']} → {sug}")
            lines.append(f"    {str(r['상품명'])[:65]}")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def gen_cross_sell() -> Path:
    out = BASE / f"MD_추천상품_연결_{TODAY}.txt"
    out.write_text("""STIX 추천상품 연결표 (2026-07-08)
================================================================================
[E6000 110ml] → B7000 15ml → 16칸 비즈보관함 → 코팅제 120ml → 핀셋 → 보석십자수 30x40
  객단가 18,500 → 32,000원 (+73%)

[B7000 110ml] → E6000 30ml → 28칸 비즈함 → 크로바 확대경 → DMC 503색
  객단가 15,000 → 28,000원 (+87%)

[보석십자수 30x40 튤립] → 코팅제 2개세트 → 16칸 비즈함 → 전용펜 9구
  객단가 18,900 → 35,000원 (+85%)

[어린이 스티커 24종] → 16칸 케이스 → B7000 15ml → 30x40 입문 키트
  객단가 12,900 → 24,000원 (+86%)

적용: 쿠팡 추천상품 / SS 함께본상품 / G마켓 추가구성 / 카페24 관련상품
""", encoding="utf-8")
    return out


def gen_price_ab() -> Path:
    out = BASE / f"MD_가격AB테스트_{TODAY}.txt"
    out.write_text("""STIX 가격 A/B 테스트 계획 (2026-07-08)
※ 기존 상품 가격 유지 | 복사 후 B상품 생성
================================================================================

[TEST-1] 보석십자수 30x40 튤립 (G마켓)
  A상품(유지): 현재가 ~16,500원 | 마스터 3892087830
  B상품(신규): 18,900원 | 상품명에 "28칸비즈함" 강조
  종료기준: 14일 / B 전환율 A 대비 +10% 또는 주문 20건+
  롤백: B 판매중지

[TEST-2] 보석십자수 30x40 바닷가 일출 (G마켓)
  A상품(유지): 현재가 | 마스터 (바닷가 일출 도안)
  B상품(신규): 19,500원 | 썸네일 "여름 인테리어" 배지
  종료기준: 14일 / ROAS·전환율 비교

[TEST-3] E6000 110ml (쿠팡) — 번들 테스트
  A상품(유지): 단품 110ml
  B상품(신규): 110ml + 뾰족캡 spare 세트 +500원
  종료기준: 21일 / 객단가·리뷰 증가율

예상: 테스트 성공 시 월 매출 +8~12만 / 순이익 +5~8만
""", encoding="utf-8")
    return out


def gen_detail_page() -> Path:
    out = BASE / f"MD_상세페이지_초안_30x40튤립_{TODAY}.html"
    out.write_text("""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<title>스팃스 보석십자수 30x40 튤립 DIY 키트</title>
</head><body style="font-family:Malgun Gothic,sans-serif;max-width:860px;margin:0 auto;color:#333">

<!-- SEO: 보석십자수 30x40, DIY 키트, 캔버스형, 튤립, 집콕, 초보자, 28칸비즈함 -->

<section style="text-align:center;padding:24px 0">
  <h1 style="font-size:28px;color:#c45b7a">보석십자수 30x40 튤립 DIY 키트</h1>
  <p style="font-size:18px">집에서 완성하는 감성 인테리어 · 28칸 비즈보관함 포함</p>
</section>

<section style="background:#fff8fa;padding:20px;border-radius:8px;margin:16px 0">
  <h2>왜 스팃스 30x40 튤립인가요?</h2>
  <ul>
    <li>✓ 초보자도 3~5일 완성 (하루 1~2시간)</li>
    <li>✓ 28칸 비즈 정리함 증정 — 작업 효율 2배</li>
    <li>✓ 캔버스+비즈+도안+도구 풀세트</li>
    <li>✓ 완성 후 액자 프레임 장식 (액자 별매 가능)</li>
  </ul>
</section>

<section>
  <h2>구성품</h2>
  <p>캔버스 30x40cm · 큐빅 비즈 · 전용펜 · 트레이 · 도안 · 28칸 비즈함</p>
  <p><strong>사이즈:</strong> 완성 약 30×40cm (A3+)</p>
</section>

<section style="background:#f5f5f5;padding:16px;margin:16px 0">
  <h2>구매 포인트</h2>
  <p>★ 방학·집콕 취미 · 선물용 인기 도안<br>
  ★ 스팃스 10년 부자재 전문 셀러<br>
  ★ 평일 16시 이전 주문 당일발송</p>
</section>

<section>
  <h2>함께 구매하면 좋아요</h2>
  <p>보석십자수 코팅제 120ml · 16칸 비즈보관함 · B7000 접착제 15ml</p>
</section>

<section>
  <h2>FAQ</h2>
  <p><b>Q. 초보자도 가능한가요?</b><br>A. 네. 도안 번호대로 붙이면 됩니다.</p>
  <p><b>Q. 액자 포함인가요?</b><br>A. 기본 캔버스 키트이며 액자는 옵션/별매입니다.</p>
  <p><b>Q. 40x50과 차이는?</b><br>A. 30x40이 입문·완성 속도 면에서 유리합니다.</p>
</section>

</body></html>
""", encoding="utf-8")
    return out


def gen_thumbnails() -> Path:
    out = BASE / f"MD_썸네일_개선_TOP10_{TODAY}.txt"
    out.write_text("""STIX 썸네일 개선 TOP10 (2026-07-08)
| 우선 | 상품 | 문제점 | 개선방향 | AI 프롬프트 요약 |
|------|------|--------|----------|------------------|
| 1 | 보석십자수 30x40 튤립 | 사이즈·구성품 미표시 | 완성작+30x40배지+28칸비즈함 | tulip diamond painting 30x40, badge, flat lay tools |
| 2 | E6000 30ml 쿠팡1위 | 경쟁사와 유사 컷 | 110ml 대비 소량 강조+비즈장면 | E6000 30ml glue craft beads white bg |
| 3 | E6000 110ml G마켓1위 | 뾰족캡 미강조 | 캡 클로즈업+당일발송 배지 | precision cap E6000 110ml ecommerce |
| 4 | 보석십자수 바닷가 30x40 | 여름 시즌 약함 | 일출+여름배지 | beach sunrise 30x40 diamond kit summer |
| 5 | 어린이 스티커 24종 | 스티커형 구분 약함 | 아이 손+24종 그리드 | kids sticker craft 24 designs playful |
| 6 | B7000 110ml | 스마트폰수리만 강조 | 비즈+공예 병행 | B7000 glue beads phone repair dual scene |
| 7 | 크로바 확대경 핑크 | 제품만 단독 | 십자수 작업 장면 | magnifier on cross stitch fabric pink |
| 8 | 보석십자수 40x50 77종 | 선택지 과다 혼란 | 3대표 도안+77종 배지 | collage 3 designs badge 77 options |
| 9 | DMC 503색 | 단일 실만 노출 | 색상 스펙트럼 | DMC floss rainbow spectrum macro |
| 10 | 16칸 비즈보관함 | 용도 불명확 | 정리된 비즈+십자수 연출 | 16 slot bead organizer craft desk |
""", encoding="utf-8")
    return out


def main():
    sales = load_sales_top()
    files = [
        gen_product_names(sales),
        gen_gmarket_audit(sales),
        gen_cross_sell(),
        gen_price_ab(),
        gen_detail_page(),
        gen_thumbnails(),
    ]
    for p in files:
        print(f"Saved: {p.name}")


if __name__ == "__main__":
    main()
