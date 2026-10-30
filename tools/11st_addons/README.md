# 11번가 추가구성상품 맞추기

스팃스 액자형(보석십자수 캔버스 판넬) 상품에 아래 4개를 넣거나, 예전 이름이면 이 이름으로 바꿉니다. 조회한 상품 XML을 거의 그대로 다시 보내며, 도구가 글자를 바꾸는 곳은 추가구성 블록뿐입니다. 상품명, 판매가, 옵션, 썸네일, 상세페이지, 배송, 할인이 바뀌는 계산이 나오면 그 상품은 저장하지 않습니다.

| 추가구성 | 추가금액 | 재고 |
| --- | ---: | ---: |
| 3구펜+고체풀+트레이세트 | 1,000원 | 999 |
| 보석십자수 코팅제 120ml | 5,500원 | 999 |
| B7000 보석십자수본드 110ml | 5,000원 | 999 |
| 보석십자수 보조눈금자 11.5cm | 5,000원 | 999 |

그룹 이름(`addPrdGrpNm`)은 모두 `추가구성`, 부가세 `01`(과세), 사용 `Y`입니다. 재고 999는 `--addon-stock`으로 바꿀 수 있습니다. `9999`는 셀러오피스에서 자주 들어가던 잘못된 값이라 도구가 거부합니다.

기본 실행은 **조회와 비교만** 합니다. 11번가에 저장하는 요청은 `--apply`를 적을 때만 나갑니다.

조회는 두 번 합니다. `GET prodmarketservice/prodmarket/{prdNo}`(상품 전체 XML)와 `GET prodmarketservice/prodmarket/stck/{prdNo}`(현재 추가구성). 응답은 EUC-KR이고, 저장 본문도 EUC-KR로 보냅니다. 예전 `prodservices/product/details`는 이 키로 HTTP 500(-997)이라 쓰지 않습니다.

API에서 확인한 내용과 아직 모르는 부분은 [docs/11st-api-notes.md](../../docs/11st-api-notes.md)에 있습니다. 추가구성만 고치는 주소는 공개 문서에서 찾지 못했습니다. 저장은 상품 XML 전체를 다시 보내는 방식이라, 아래 순서를 지킵니다.

## Windows PowerShell (은선 PC)

저장소는 `%USERPROFILE%\stix-11st` 에 있습니다. 키는 사용자 환경변수 `ELEVENST_API_KEY`에 저장돼 있고, 창마다 아래 첫 줄로 불러옵니다. 키를 화면에 출력하지 않습니다.

```powershell
cd $env:USERPROFILE\stix-11st
git pull
$env:ELEVENST_API_KEY=[Environment]::GetEnvironmentVariable('ELEVENST_API_KEY','User')
"prdNo`n8578012899`n8578007121`n8578001406" | Set-Content -Encoding utf8 $env:USERPROFILE\run1030\check3.csv
# 1) 드라이런 (저장 안 함)
py tools\11st_addons\run.py --input $env:USERPROFILE\run1030\check3.csv --output $env:USERPROFILE\run1030\check3_result.csv --limit 0
# 2) 한 개만 저장 (드라이런 결과가 셀러오피스 화면과 같을 때만)
py tools\11st_addons\run.py --input $env:USERPROFILE\run1030\one.csv --output $env:USERPROFILE\run1030\one_result.csv --apply --limit 1
# 테스트
py -m unittest discover -s tools\11st_addons\tests
```

## 준비

1. 11번가 셀러 계정으로 [Open API 센터](https://openapi.11st.co.kr/openapi/OpenApiFrontMain.tmall)에 로그인합니다.
2. API 관리에서 키를 확인합니다. 키에 IP 제한이 있으면 이 프로그램을 실행하는 컴퓨터 IP가 들어가 있어야 합니다. 키 유효기간 안내는 센터 공지를 봅니다.
3. 키는 환경변수로만 넣습니다. 파일이나 명령 기록에 붙이지 않습니다.

```bash
export ELEVENST_API_KEY='센터에서 복사한 키'
```

4. 상품번호 CSV를 만듭니다. 첫 줄은 `prdNo` 입니다. 번호는 숫자만, 6~15자리입니다. 엑셀에서 저장할 때 상품번호 열을 텍스트로 두면 `1.23E+9`처럼 깨지지 않습니다.

```csv
prdNo
1234567890
```

예시는 `fixtures/prd_nos.sample.csv` 입니다. 번호는 가짜입니다.

저장소 루트에서 실행합니다.

```bash
python3 tools/11st_addons/run.py --help
```

## 순서

### 1. 드라이런

서버에 저장하지 않습니다. 상품을 조회해서, 추가구성이 어떻게 바뀌는지 화면에 보여주고 결과 CSV만 만듭니다.

```bash
python3 tools/11st_addons/run.py \
  --input 상품번호.csv \
  --output 결과.csv \
  --limit 0
```

`--limit` 기본값은 1입니다. 목록 전체를 보려면 `--limit 0` 입니다.

결과 CSV 열: `prdNo`, `before add-ons`, `after add-ons`, `status`, `error`.

드라이런에서 볼 것:

- `before add-ons`가 셀러오피스 추가구성 화면과 같은지. **화면에 추가구성이 있는데 여기가 비어 있으면 적용하지 않습니다.** 조회가 추가구성을 빼먹으면 같은 상품이 한 번 더 붙습니다.
- 화면의 `변경` 줄만 이름·가격·재고인지. `유지`는 이번 4종과 무관한 추가구성입니다. 그대로 둡니다.
- `추가구성 바깥 XML 토큰은 동일합니다`가 각 상품에 있는지.

상태가 `ambiguous` 또는 `error`인 상품은 이름이 두 종류와 겹치거나, 같은 종류가 두 줄인 경우입니다. 그 상품은 저장하지 않습니다. 셀러오피스에서 줄을 정리한 뒤 다시 돌립니다.

### 2. 상품 하나에만 적용

```bash
python3 tools/11st_addons/run.py \
  --input 상품번호.csv \
  --output 결과.csv \
  --apply \
  --limit 1
```

`--limit`를 생략해도 1개입니다. 수정 전 XML은 결과 CSV 옆 `11st_addon_backups/상품번호.before.xml`에 남습니다. 이 폴더는 git에 올리지 않습니다.

상태가 `verified`이면, 저장 뒤 다시 조회했을 때 판매가·상품명·상세 HTML·이미지·카테고리·판매자 상품코드·본상품 재고·옵션 블록·배송(`dlv`)·할인(`cupon`/`cupn`/`dsc`) 값이 조회 때와 같고, 목표 추가구성의 재고가 999입니다.

### 3. 구매자 페이지 확인

그 상품의 11번가 구매 화면에서 확인합니다.

- 상품명과 판매가가 그대로인지
- 옵션과 상세페이지가 그대로인지
- 추가구성 4개의 이름과 추가금액이 위 표와 같은지
- 재고가 999인지
- 원래 있던 다른 추가구성이 남아 있는지

구매 화면 문구가 다르면 목록을 더 돌리지 않습니다. 그룹 이름은 항상 `추가구성`, 값(`compPrdNm`)은 위 표 이름으로 맞춥니다(8578012899 셀러오피스 수동 설정과 같음).

### 4. 나머지

구매 화면이 맞으면 `--limit 0`으로 나머지를 적용합니다. 실패가 두 번 연속이면 그 뒤 상품은 `stopped`로 남고 요청을 멈춥니다.

```bash
python3 tools/11st_addons/run.py \
  --input 상품번호.csv \
  --output 결과.csv \
  --apply \
  --limit 0
```

재고를 999가 아닌 값으로 보려면 `--addon-stock`을 붙입니다. 아래는 저장하지 않는 드라이런입니다. 저장까지 하려면 `--apply`를 같이 적습니다.

```bash
python3 tools/11st_addons/run.py --input 상품번호.csv --output 결과.csv --addon-stock 80
```

허용 범위는 1~1000입니다. `9999`와 `99999`는 거부합니다.

## 결과 상태

| status | 의미 |
| --- | --- |
| `dry_run` | 비교만 했습니다. 저장 요청 없음 |
| `unchanged` | 이미 목표와 같습니다. 저장 요청 없음 |
| `verified` | 저장 후 재조회까지 확인했습니다 |
| `aborted_unsafe_diff` | 추가구성 바깥 글자가 달라 저장하지 않았습니다 |
| `ambiguous` | 어떤 줄에 이름을 맞춰야 하는지 겹칩니다 |
| `verify_failed` | 저장 뒤 재조회에서 판매가나 주요 항목 또는 추가구성이 기대와 다릅니다 |
| `error` | 조회·저장·응답 오류 |
| `stopped` | 앞의 실패가 두 번 연속이라 이 상품부터 멈추었습니다 |
| `skipped_limit` | `--limit` 밖입니다 |
| `skipped_duplicate` | 같은 상품번호가 앞에 있습니다 |

`verify_failed`이면 그 상품은 이미 저장 요청이 나간 상태입니다. 백업 XML을 보고 셀러오피스에서 판매가와 상세를 확인합니다. 도구는 자동으로 되돌리지 않습니다. 되돌리기도 상품 전체를 다시 보내는 요청이라, 사람이 화면에서 확인한 뒤에만 합니다.

## 예전 이름을 찾는 기준

| 목표 | 기존 이름에 포함되면 같은 줄로 봅니다 |
| --- | --- |
| 3구펜+고체풀+트레이세트 | 3구펜, 고체풀, 트레이세트 |
| 보석십자수 코팅제 120ml | 코팅제, 코팅액 |
| B7000 보석십자수본드 110ml | B7000, B-7000 |
| 보석십자수 보조눈금자 11.5cm | 보조눈금자, 눈금자 |

이 단어가 없는 추가구성은 유지합니다.

## 테스트

키 없이, 저장소에 넣어 둔 XML로 확인합니다.

```bash
cd tools/11st_addons
python3 -m unittest discover -s tests -v
```

저장소 루트에서는 아래도 같습니다.

```bash
python3 tools/11st_addons/tests/test_tool.py -v
```

## 파일

| 파일 | 역할 |
| --- | --- |
| `run.py` | 실행 진입점 |
| `cli.py` | 인자. 기본 드라이런, `--apply`, `--limit` |
| `client.py` | 조회 GET(prodmarket + stck 합침), 수정 PUT(EUC-KR). 키는 헤더에만 |
| `xml_edit.py` | 추가구성 블록만 교체하고 바깥 토큰을 검사 |
| `spec.py` | 4종 이름·가격·재고 정책 |
| `runner.py` | CSV, 연속 실패 2회 중단, 재조회 확인 |
