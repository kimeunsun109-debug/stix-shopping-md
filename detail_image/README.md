# 상세페이지 4분할 이미지 (Gemini) — 다시제작

Notion 할 일(2026-10-04) 기준 워크플로.

## 프롬프트

- 사용자 메모: `감성있는 4분할 이미지 만들어줘. 상품은 절대 변경하지마`
- 자동화용 전체 문구: `detail_image/prompts.py` → `GEMINI_4SPLIT_PROMPT_FULL`

## OneDrive 위치

`Desktop/상세페이지사진/짧은_구식_상세페이지/제작_산출물/다시제작` (67개 SKU)

상품 폴더 구조:

- `썸네일.jpg` — Gemini에 넣는 원본 상품 이미지
- `상세페이지_4분할_합성.jpg` — 2×2 합성 결과
- `4분할/` — 패널 4장 (또는 루트의 `01.jpg`~`04.jpg`)

## OneDrive 검수 (Graph 목록 스냅샷)

`detail_image/data/daesijejak_root_listing.json` 은 67 SKU 폴더의 `childCount`·용량 스냅샷입니다.

```bash
python3 detail_image/audit_manifest.py detail_image/data/daesijejak_root_listing.json \
  -o detail_image/MD_다시제작_검수.csv --json detail_image/MD_다시제작_검수.json
```

**2026-10-04 결과:** 67개 중 **18개** `flat_01_04`(01~04+thumb, 합성·`4분할/` 없음) → Gemini 재생성 1순위. 나머지 49개는 표준 구조(합성+`4분할/`).

## 로컬 검수 (패널 해상도·용량)

```bash
python3 detail_image/audit_local.py "C:/Users/.../다시제작"
```

## 합성 → 4패널 분할

```bash
python3 detail_image/split_composite.py "상품폴더/상세페이지_4분할_합성.jpg" -o "상품폴더/4분할"
```

## Gemini 자동 생성 (로컬 Chrome CDP)

Cloud Agent에서는 Gemini API/Chrome CDP가 없어 **실제 이미지 생성은 로컬**에서 진행합니다.

```bash
# Chrome: --remote-debugging-port=9222
node detail_image/scripts/gemini_4split_cdp.mjs \
  "ws://127.0.0.1:9222/devtools/page/<id>" \
  "/path/썸네일.jpg" \
  "/path/상세페이지_4분할_합성.jpg"
```

프롬프트는 `detail_image/prompts.py`의 `GEMINI_4SPLIT_PROMPT_FULL`과 동일합니다.

## 검수 루프

1. Gemini로 합성 생성 → `상세페이지_4분할_합성.jpg` 저장
2. `split_composite.py`로 `4분할/` 갱신
3. 상품 왜곡·저해상도면 프롬프트 동일하게 재생성
