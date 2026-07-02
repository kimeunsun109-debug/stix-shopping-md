# STIX 쇼핑몰 MD (Multi-mall)

스팃스(STIX) 멀티몰 MD용 Python 분석·자동화 스크립트입니다.

## 주요 스크립트

| 스크립트 | 설명 |
|----------|------|
| `md_sales_top_products.py` | 사이트별 판매상위 TOP30 |
| `md_rocket_margin.py` | 로켓그로스 실마진 (원가·보관·배송·입출고) |
| `md_esm_group_classify.py` | 지마켓/옥션 그룹관리 업로드 분류 |
| `md_price_sales_analyze.py` | 전체 상품 가격·매출 분석 |
| `md_seller_fetch.py` | CDP(9233) 셀러센터 스크래핑 |
| `md_run_pipeline.py` | export + analyze 파이프라인 |

## 로컬 설정

```bash
cd 쇼핑몰관리md
pip install -r requirements.txt
python -m playwright install chromium
copy .env.example .env.txt   # Windows — 비밀번호 입력
```

매출/상품 엑셀은 `쇼핑몰별 전체상품/` 에 배치 (Git 미포함, OneDrive 동기화).

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
