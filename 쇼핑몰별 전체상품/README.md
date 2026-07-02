# 쇼핑몰별 전체상품 / 매출 데이터

Git에는 **용량 문제로 엑셀·CSV 원본은 포함하지 않습니다.**  
로컬 OneDrive 또는 Cloud Agent 작업 시 이 폴더에 아래 파일을 두세요.

## 필수 파일 예시

| 파일 | 용도 |
|------|------|
| `지마켓,옥션.xlsx` | ESM 그룹관리 분류 (`md_esm_group_classify.py`) |
| `지마켓 그룹관리 예시 템플릿.xls` | 업로드 양식 참고 |
| `스마트스토어 *매출*.xlsx` | 사이트별 판매상위 |
| `쿠팡*매출*.xlsx` | 사이트별 판매상위 |
| `로켓그로스/` | 6월 정산·배송·보관 (`md_rocket_margin.py`) |

## 스크립트

```bash
python md_sales_top_products.py
python md_rocket_margin.py
python md_esm_group_classify.py
```
