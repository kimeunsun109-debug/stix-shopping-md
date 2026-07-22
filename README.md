# STIX 쇼핑몰 MD (Multi-mall)

스팃스(STIX) 멀티몰 MD용 Python 분석·자동화 스크립트입니다.

## 주요 스크립트

| 스크립트 | 설명 |
|----------|------|
| `md_commerce_ai.py` | Commerce AI v7 (Autonomous AI MD + Production Grade) |
| `md_coupang_seo_recovery.py` | SEO Recovery v3 (cdp/manual/auto + 멀티마켓) |
| `md_seo_rank_monitor.py` | 일일 순위 모니터 + 하락 시 자동 분석 |
| `md_seo_dashboard.py` | SEO 대시보드 (위험도·오늘 할 일) |
| `md_sales_top_products.py` | 사이트별 판매상위 TOP30 |
| `md_rocket_margin.py` | 로켓그로스 실마진 (원가·보관·배송·입출고) |
| `md_price_sales_analyze.py` | 전체 상품 가격·매출 분석 |
| `md_seller_fetch.py` | CDP(9233) 셀러센터 스크래핑 |
| `md_run_pipeline.py` | export + analyze 파이프라인 |

## STIX Commerce AI v7 — Autonomous AI MD

```bash
python md_commerce_ai.py --autonomous
python md_commerce_ai.py --autonomous --batch 100
python md_commerce_ai.py --daily-report
python md_commerce_ai.py --web          # http://localhost:3000/md
python md_commerce_ai.py --schedule --now
```

매일 출근하는 MD처럼 Opportunity·Priority·Daily Report·자가평가를 수행합니다.

품질·운영 문서:
- `commerce_ai/ARCHITECTURE.md` — 계층·데이터 흐름
- `commerce_ai/PRODUCTION_CHECKLIST.md` — 운영 체크리스트
- `commerce_ai/CTO_REVIEW.md` — Production Readiness Score

```bash
python -m unittest discover -s commerce_ai/tests -v
```

## STIX Commerce AI v5

OS 계층(추천·실행계획·검증·학습) — v6에 포함·강화됨.

## STIX Commerce AI v4

SEO + 매출/가격/경쟁/이미지/알림/MD 플래너 (v6에 포함).

## Coupang SEO Recovery Engine

공통 Analyzer + **Collector만 교체** (Mode A/B/auto, 멀티마켓).

```bash
python md_coupang_seo_recovery.py --mode manual --input seo_engine/samples/mode_b_jewel_crossstitch.json
python md_seo_dashboard.py
```

- 리포트 ①–⑳ / `seo_history/`
- 마켓: `--marketplace coupang|smartstore|gmarket|auction|11st|amazon`

## 로컬 설정

```bash
cd 쇼핑몰관리md
pip install -r requirements.txt
python -m playwright install chromium
copy .env.example .env.txt   # Windows — 비밀번호 입력
```

매출/상품 엑셀은 **`쇼핑몰별 전체상품/`** 에 Git으로 포함 (~6MB). Cloud Agent clone 후 바로 분석 가능.

Chrome CDP (로컬 스크래핑): `start_chrome_for_md.bat` → 포트 **9233**

## Cursor Cloud에서 이어하기

1. GitHub 저장소 연결 후 Cloud Agent 실행
2. `.cursor/environment.json` 이 Python + Playwright 설치
3. **데이터**: `쇼핑몰별 전체상품/` 에 엑셀 업로드 (또는 OneDrive에서 복사)
4. **비밀번호**: Cursor Dashboard → Cloud Agents → Secrets 에 `.env.txt` 내용 등록  
   (또는 클라우드 작업 후 로컬 CDP만 사용)

## 로켓그로스 원가 (md_rocket_margin.py)

- B7000 15ml×3: 1080 / ×5: 1800
- B7000 110ml×1: 2600 / ×2·×4: 5200
- 십자수 패키지: 7130 / 스티커: 1800 / 액자: 2900 / 패브릭: 5500

## 주의

- 상품 가격·재고 **자동 수정 금지** — 분석 후 사용자 승인 필요
- `.env.txt` / `.env` 는 Git에 올리지 않음
