# 상세페이지 생성기 (제작_산출물 → 6섹션 상세페이지)

OneDrive `제작_산출물` 폴더의 상품 이미지(2x2 콜라주)를 읽어, 상품마다 스팃스 하우스 스타일 상세페이지를 만듭니다.
상품 87종 기준. 기존 `완성_상세페이지` 와 같은 구조(HERO · 대표 이미지 · 포인트 · WHY · 활용 컷 · 핵심기능/스펙)입니다.

## 실행

```bash
pip3 install --break-system-packages pillow numpy playwright
# 폴더를 로컬로 받아둔 뒤 (OneDrive 동기화 폴더도 가능)
python3 -m detail_page.build --src "/경로/제작_산출물" --out detail_page_out
python3 -m detail_page.build --src ... --out ... --only 01_ 13031829_     # 일부만
python3 -m detail_page.build --src ... --out ... --no-render               # HTML만(Chrome 불필요)
```

Chrome 은 `/usr/local/bin/google-chrome`, `/usr/bin/google-chrome`, `/usr/bin/chromium` 순으로 찾고, 없으면 Playwright 기본 브라우저를 씁니다.

## 출력

| 경로 | 내용 |
|---|---|
| `pages/<id>.html` | 편집 가능한 HTML (우측 하단 분할 저장 버튼 포함) |
| `slices/<id>/01~06_*.jpg` | 섹션별 분할 이미지 (스토어 업로드용, 폭 1720px) |
| `long/<id>.jpg` | 세로 한 장 합본 |
| `images/` | 콜라주에서 분리한 패널 이미지 |
| `index.html` | 전체 상품 미리보기 |
| `QA_REPORT.md` | 업로드 전 확인이 필요한 상품(이미지·상품명 불일치, 저해상도) |

## 카피 원칙

- 상품명에 적힌 사실(수량·규격·색상)만 단정합니다. 인증·효능·근거 없는 수치는 쓰지 않습니다.
- 활용 컷 캡션은 이미지와 어긋나지 않도록 중립 문구입니다.
- 카피는 `catalog.py` 한 곳에서 수정합니다. `qa` 값이 있는 상품은 `QA_REPORT.md` 에 올라갑니다.
- 상품 자동 수정은 하지 않습니다. 이 도구는 파일만 생성하며 쇼핑몰/OneDrive 는 건드리지 않습니다.

## 테스트

```bash
python3 -m unittest detail_page.tests.test_detail_page
```
