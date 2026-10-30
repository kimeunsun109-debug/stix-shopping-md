# 11번가 셀러 Open API — 추가구성상품 조사 노트

조사일: 2026-10-29. 목적: 기존 상품의 추가구성상품(이름·가격·재고)만 바꾸고, 상품명·판매가·옵션·상세·배송·할인은 건드리지 않을 수 있는지 확인한다.

이 문서는 **공개된 페이지에서 읽은 것만** 적는다. 확인하지 못한 것은 확인하지 못했다고 적는다. 셀러 개발가이드 본문은 로그인 뒤에 있어서 이번 조사에서 열지 못했다.

## 1. 두 개의 API를 구분해야 한다

11번가 Open API 센터(`https://openapi.11st.co.kr/openapi/OpenApiFrontMain.tmall`)에는 성격이 다른 API가 있다.

### 1-1. 공개 쇼핑 조회 API (상품 수정 불가)

개발가이드(로그인 없이 열림):

- http://openapi.11st.co.kr/openapi/OpenApiGuide.tmall
- http://openapi.11st.co.kr/openapi/OpenApiGuide.tmall?commonGuideNo=3

여기 상품 API는 쇼핑몰에 붙이는 **검색·조회**다.

| 용도 | 호출 |
| --- | --- |
| 상품 검색 | `GET http://openapi.11st.co.kr/openapi/OpenApiService.tmall?key=[key]&apiCode=ProductSearch&keyword=[keyword]` |
| 상품 정보 | 같은 URL, `apiCode=ProductInfo`, `productCode=[productCode]` |
| 옵션 부가정보 | `option=PdOption` |

인증 키는 **쿼리스트링 `key`**. 가이드의 에러 표는 `doPut()`, `doDelete()`, `multipart/form-data`를 처리하지 않는다고 적는다 (`001 invalidRequestType`). 출력 필드 설명에 상품명·가격·이미지·배송비·옵션(`PdOption`)은 있고, **추가구성상품 필드는 없다.**

이 API로 추가구성을 넣거나 이름을 바꾸는 엔드포인트는 가이드에 없다. 이 도구는 이 URL을 쓰지 않는다.

### 1-2. 셀러 REST API (등록·수정)

센터 첫 화면은 상품 API를 카테고리 조회, 상품조회, 상품관리(등록·수정·판매기간), 재고, Q&A, 판매중지, 배송으로 나누어 소개한다.

- http://openapi.11st.co.kr/openapi/OpenApiServiceIntroduce.tmall?introduceType=PRODUCT

소개 문구만 있고, 경로·XML 스키마는 로그인 전 페이지에 없다. API 검색 버튼도 로그인으로 보낸다. 셀러 가이드 본문은 이번 조사에서 **미확인**이다.

공개된 연동 기록으로 확인한 한국 11번가 호출은 아래가 전부다.

| 동작 | 메서드·URL | 근거 | 확신 |
| --- | --- | --- | --- |
| 상품 등록 | `POST http://api.11st.co.kr/rest/prodservices/product` | 2016년 연동 정리. 헤더 `openapikey`, `Content-Type: text/xml; charset=utf-8`. 본문은 XML. 글쓴이는 매뉴얼의 euc-kr 예제가 틀리고 UTF-8로 보내야 했다고 적음. http://jaymz96.blogspot.com/2016/01/apache-commons-httpclient-44-11.html | 등록 URL·헤더·POST는 이 글이 매뉴얼을 보고 쓴 호출이다. XML 필드 목록은 글에 없음 |
| 상품 수정 | `PUT http://api.11st.co.kr/rest/prodservices/product/{prdNo}` | 2009년 PHP 질문의 실제 URL. 헤더 `openapikey`, `Content-type: text/xml;charset=EUC-KR`, 본문 XML. https://www.phpschool.com/gnuboard4/bbs/board.php?bo_table=qna_function&wr_id=268108 같은 블로그는 상품 수정·판매중지·판매재개에 PUT을 쓴다고만 하고 URL 리터럴은 변수로 둠 | 포럼에 적힌 URL이다. **현재 공식 가이드 페이지로 재확인하지 못함** |
| 판매가 변경 | `GET http://api.11st.co.kr/rest/prodservices/product/price/{prdNo}/{selPrc}` | https://zero-week.tistory.com/104 헤더 `openapikey` | 블로그 코드와 아래 자매 매뉴얼이 같은 경로 |

공통점: 키는 URL이 아니라 헤더 `openapikey`. 상품 등록·수정의 본문은 XML.

## 2. 같은 계열 매뉴얼(elevenia)에서 확인한 경로

elevenia(`api.elevenia.co.id`)는 11번가와 같은 SK플래닛 계열 상품 API다. 공개 PDF 텍스트에 경로와 XML 요소명이 남아 있다.

- https://adoc.pub/untuk-memulai-menggunakan-product-api-elevenia-ikuti-langkah.html

**이것은 한국 11번가 공식 문서가 아니다.** 경로 이름이 한국 연동 글과 같다는 보조 근거로만 쓴다.

그 매뉴얼에 나온 상품 관련 URL:

| 매뉴얼 제목 | 메서드 | 경로 |
| --- | --- | --- |
| 상품 등록 | POST | `/rest/prodservices/product` |
| 상품 상세 | GET | `/rest/prodservices/product/details/{prdNo}` |
| 상품 목록 | GET | `/rest/prodservices/product/listing?page={pageNumber}` |
| 옵션 수정 | POST | `/rest/prodservices/updateProductOption/{prdNo}` |
| 가격 변경 | GET | `/rest/prodservices/product/price/{prdNo}/{selPrc}` |
| 할인 변경 | POST | `/rest/prodservices/product/priceCoupon/{prdNo}` |
| 재고번호 조회 | GET | `/rest/prodmarketservice/prodmarket/stck/{prdNo}` |
| 재고 수정 | PUT | `/rest/prodservices/stockqty/{prdStckNo}` |
| 판매중지(비전시) | PUT | `/rest/prodstatservice/stat/stopdisplay/{prdNo}` |
| 판매재개 | PUT | `/rest/prodstatservice/stat/restartdisplay/{prdNo}` |

상세 조회의 설명은 "업로드 XML과 같은 형식으로 상품 상세 XML을 돌려준다"이다.

"Update Produk" 절은 PDF를 텍스트로 풀면서 깨져 있다. 제목 바로 뒤에 `Method Type : GET`과 등록 URL(`/rest/prodservices/product`, 상품번호 없음)이 붙고, 출력 설명은 상세 조회 문장과 같다. **이 절의 메서드와 URL은 신뢰하지 않는다.** 한국 쪽 PUT `.../product/{prdNo}`를 이 PDF가 증명하지 않는다.

인증 실패 코드(매뉴얼): `100` 키 없음, `200` 키 무효, `300` 셀러 미승인. 상품 처리 결과 코드: `200` 성공, `500` 업무 오류, `-1000` 점검. 키 오류의 200과 성공의 200은 **서로 다른 API**의 코드다. 상품 응답의 `resultCode`만 성공 판단에 쓴다.

## 3. 추가구성상품 XML

### 3-1. 화면에서 확인한 항목 (한국 11번가 셀러 매뉴얼)

셀러오피스 상품등록 안내:

- https://i.011st.com/ui_img/seller/pdf/prod.pdf
- 마트 안내에도 같은 설명: http://i.011st.com/ui_img/seller/pdf/mart.pdf

추가구성상품은 옵션과 별도다. 장바구니에 함께 담는 상품이고, 쿠폰 등 고객혜택이 적용되지 않는다고 적혀 있다. 입력 항목은 추가상품명(한글 기준 최대 25자), 추가상품값, 추가상품가격, 재고수량. 여러 개 등록(`+`/`-`)과 엑셀 일괄 등록이 **화면**에는 있다. 이 PDF는 API 스키마가 아니다.

2012년 셀러존 공지 `[기능개선] 추가구성상품 등록 시, 과세/면세/영세 상품 등록 가능`은 메뉴 설명에 `(*API 포함)`이라고 적는다.

- https://www.11st.co.kr/tpost/FrontTPostAction.tmall?NtceNo=551439&method=getNoticeView&type=so

즉 그때 API로 추가구성의 과세 구분을 다뤘다는 공식 문장은 있다. **경로와 태그 이름은 이 공지에 없다.**

### 3-2. 등록 XML 안의 노드 (elevenia 매뉴얼)

상품 등록 XML의 선택 노드로 다음이 한 번 나온다. 필수 여부는 모두 N(선택)이다.

| 요소 | 매뉴얼 타입 | 매뉴얼 영어 설명 (기계번역, 어긋나 있을 수 있음) | 태그 이름으로 읽는 뜻 |
| --- | --- | --- | --- |
| `ProductComponent` | 노드 | Additional setting for Item | 추가구성 1개 |
| `addPrdGrpNm` | String | Additional Item Name | 추가상품 그룹명 |
| `compPrdNm` | String | Additional Item Data Type | 추가구성 상품명·값 |
| `sellerAddPrdCd` | String | Additional Item Number of Sellers | 판매자 추가상품코드 |
| `addCompPrc` | Number | Additional setting for Price | 추가 가격 |
| `compPrdQty` | Number | Amount of Sales | 수량(재고) |
| `compPrdVatCd` | String/Number | VAT Status | 부가세 코드 |
| `addUseYn` | String | (영어 설명이 목록에서 빠짐) | 사용 여부 |
| `addPrdWght` | Number | Additional Weight setting | 추가 무게 |

영어 설명은 열 순서가 한 칸씩 어긋난 흔적이 있다. **한국 공식 필드 사전으로 확인한 것이 아니다.** 태그 이름만 한국 약어로 분명하다. 이 도구는 조회 XML에 이 태그가 있을 때만 그 태그의 문자를 바꾼다. 없는 태그를 추측해서 다른 이름으로 만들지 않는다.

새 줄을 만들 때만 `compPrdVatCd`를 `01`로 넣는다. elevenia 매뉴얼의 상품 부가세 `01`은 과세이고, 2012년 공지는 추가구성을 기본 과세로 전환했다고 한다. 기존 줄의 부가세 값은 유지한다.

화면의 25자 제한은 API 최대 길이로 확인되지 않았다. 도구는 화면 제한에 맞춰 25자를 넘으면 그 상품을 쓰지 않는다.

## 4. 추가구성만 따로 수정할 수 있는가

**공개 자료 안에서는 아니다.**

- 공개 쇼핑 `ProductInfo`에는 추가구성 필드가 없다.
- elevenia 상품 API 목록에 추가구성 전용 URL은 없다.
- 부분 수정으로 문서화된 것은 옵션(`updateProductOption`), 가격(`product/price`), 할인(`priceCoupon`), 재고(`stockqty`), 전시 중지·재개뿐이다.
- 추가구성은 상품 **등록 XML의 `ProductComponent`** 로만 나온다.
- 한국 상품 수정으로 확인된 호출은 상품 전체 XML을 `PUT /rest/prodservices/product/{prdNo}`에 보내는 방식이다. 이 URL은 포럼 근거이고, 오늘 연 공식 가이드 페이지는 아니다.

그래서 이 도구의 실제 쓰기는 **상세 XML을 받아, `ProductComponent` 블록만 바꾼 뒤, 같은 문서를 상품 수정 PUT으로 다시 보내는 것**이다. 추가구성 전용 API가 나중에 가이드에 있으면 그 경로로 바꿔야 한다. 지금은 그 API가 있다고 가정하지 않는다.

상세 조회 경로는 한국 블로그에서 리터럴로 확인하지 못했다. elevenia 매뉴얼의 `GET /rest/prodservices/product/details/{prdNo}`를 한국 호스트 `http://api.11st.co.kr`에 붙여 쓴다. 상세 응답이 등록 XML과 같은 모양이라는 문장도 elevenia 매뉴얼에만 있다. **한국 응답이 `ProductComponent`를 빼먹고 돌려주면, 도구는 추가구성이 없다고 보고 4개를 새로 넣어 중복을 만든다.** 적용 전에 드라이런의 "바꾸기 전" 목록이 셀러오피스 화면과 같은지 사람이 봐야 한다.

## 5. 상품 XML 전체를 다시 보낼 때의 위험

서버가 PUT을 전체 치환으로 처리하면, 요청에 없는 항목이 지워지거나 기본값으로 돌아간다. 조회 XML을 그대로 다시 보내는 방식이라 아래는 여전히 남는다.

1. 상세 응답과 수정 요청의 스키마가 다르면, 조회에만 있는 필드가 거절되거나 요청에 없는 저장 필드가 사라진다. 스키마 차이는 **미확인**.
2. 서버가 같은 값을 받아도 상세 HTML, 옵션 순서, 할인, 배송비를 다시 계산할 수 있다. 우리가 바이트를 안 바꿔도 저장 결과가 달라질 수 있다.
3. 상세 응답이 추가구성을 누락하면 중복 등록된다.
4. `addPrdGrpNm`(그룹)과 `compPrdNm`(값) 중 구매자 화면에 뭐가 보이는지는 **미확인**. 그룹명이 여러 줄에서 같으면 그룹명은 두고 값만 바꾼다. 한 줄만 쓰는 그룹명이면 둘 다 목표 이름으로 바꾼다. 구매자 페이지에서 문구를 확인해야 한다.
5. 인코딩. 매뉴얼·오래된 글은 euc-kr, 2016년 연동기는 UTF-8만 성공했다고 한다. 도구는 UTF-8로 보내고, 응답은 헤더 charset → UTF-8 → EUC-KR → CP949 순으로 읽는다. 어떤 인코딩이 현재 공식인지는 **미확인**.
6. 가격 변경 API가 GET이다. 조회처럼 보이는 주소가 판매가를 바꾼다. 이 도구는 그 URL을 호출하지 않는다.
7. 인증키. 센터 첫 화면 공지 제목은 `[중요] 11번가 OpenAPI 인증키 유효기간(180일) 정책 적용 안내 (6/30 시행)` (게시글 204447033). 이번 조회에서 공지 본문 HTML은 비어 있었다. 온채널 안내(https://onchannelnotice.oopy.io/9c49efec-ce7c-4ffe-8d42-32ec8b24b377)는 180일, 호출이 있으면 자동 연장, 만료 시 재발급, 키 등록 후 약 1시간 뒤 전송, IP 제한을 걸 수 있다고 적는다. 우리 키의 만료·IP 제한은 센터에 로그인해서 확인해야 한다.
8. 공식 가이드의 일 호출 한도(`004 overedTraffic`)는 쇼핑 조회 API 기준이다. 셀러 REST의 한도는 **미확인**.

## 6. 이 도구가 막는 것과 못 막는 것

막는 것:

- 기본 실행은 원격 쓰기를 하지 않는다. `--apply`가 있을 때만 PUT.
- `--limit` 기본값 1. 첫 적용은 목록의 첫 상품 한 개.
- PUT 직전에, `ProductComponent`를 지운 나머지 토큰이 조회본과 같은지 검사한다. 판매가·상품명·상세·옵션·배송·할인 글자가 바뀌면 그 상품은 중단한다.
- 적용 후 다시 조회해서 판매가, 상품명, 상세 HTML, 대표이미지, 카테고리, 판매자 상품코드, 본상품 재고, 옵션 블록, `dlv*`/`cupon*`/`cupn*`/`dsc*`/`mileage*`/`point*`/`pnt*` 값이 같은지 본다.
- 추가구성 재고 기본값 100. `9999`와 `99999`는 거부. 1~1000 밖도 거부.
- 연속 실패 2번이면 남은 상품은 쓰지 않는다.
- API 키는 환경변수 `ELEVENST_API_KEY`만 읽고, URL·로그·예외 문자열에 남기지 않는다. 리다이렉트는 따라가지 않는다.

못 막는 것:

- 서버가 우리가 검사하지 않는 필드를 바꾸는 경우. 검사 목록은 위 항목까지다.
- 구매자 화면의 실제 노출 문구. API 응답과 화면이 다를 수 있다.
- 이미 저장된 뒤의 자동 롤백. 백업 XML은 로컬에만 남긴다. 되돌리기도 같은 전체 PUT이라, 도구가 자동으로 다시 넣지 않는다.
- 키가 생기 전에는 실서버를 호출해 보지 못했다. 테스트는 기록해 둔 XML 픽스처다.

## 7. 목표 추가구성 (스팃스 액자형)

도구가 맞추는 4개. 가격은 추가금액(원)이다.

| 이름 | 추가금액 | 재고 |
| --- | ---: | ---: |
| 3구펜+고체풀+트레이세트 | 1000 | 기본 100 |
| 코팅제 120ml | 5500 | 기본 100 |
| B7000 110ml | 5000 | 기본 100 |
| 보조눈금자 11.5cm | 5000 | 기본 100 |

기존 줄은 키워드(3구펜·고체풀·트레이세트, 코팅제·코팅액, B7000, 보조눈금자·눈금자)로 찾아 이름을 바꾼다. 키워드가 없는 추가구성은 그대로 둔다. 한 줄이 두 종류에 걸리거나, 같은 종류가 두 줄이면 그 상품은 쓰지 않는다.

## 8. 아직 공식 가이드에서 열어야 할 것

키가 생긴 뒤, 로그인한 개발가이드에서 다음을 원문과 대조하기 전에는 `--limit`를 올리지 않는다.

1. 상품 상세 조회의 한국 경로와, 응답에 `ProductComponent`가 실제로 있는지.
2. 상품 수정의 한국 경로가 아직도 `PUT /rest/prodservices/product/{prdNo}`인지, 부분 수정인지.
3. 추가구성 전용 API가 새로 생겼는지.
4. `addPrdGrpNm`과 `compPrdNm` 중 구매자 노출 필드.
5. 수정 요청에서 비우면 지워지는 필드 목록.
6. 성공 `resultCode`의 정확한 값과 인코딩.

## 2026-10-30 실측 (은선 PC, 고정 IP)

- `GET /rest/prodservices/product/details/{prdNo}` → HTTP 500, resultCode -997 `등록된 API 정보가 존재하지 않습니다`. 이 키로는 쓸 수 없어 도구에서 뺐다.
- `GET /rest/prodmarketservice/prodmarket/{prdNo}` → 200, `<Product>` 전체 XML(EUC-KR). 추가구성은 들어 있지 않다.
- `GET /rest/prodmarketservice/prodmarket/stck/{prdNo}` → 200, `<ns2:ProductStocks>` 안 `ns2:productComponents/productComponent`에 현재 추가구성(`addCompPrc`, `addPrdGrpNm`, `addUseYn`, `compPrdNm`, `compPrdQty`, `compPrdVatCd`)이 있다.
- 도구는 두 응답을 합쳐(상품 XML 끝에 `ProductComponent` 블록) 비교하고, `--apply` 때 그 XML을 EUC-KR로 `PUT /rest/prodservices/product/{prdNo}` 한다. **prodmarket 조회 XML이 저장(PUT)에 필요한 필드를 모두 담는지는 아직 확인하지 않았다.** 첫 `--apply --limit 1` 뒤 셀러오피스·구매 화면에서 배송·옵션·상세가 그대로인지 반드시 본다.
- 실제 응답 샘플: `tools/11st_addons/fixtures/*_8578012899.euckr.xml` (셀러오피스에서 4종·재고 999로 손으로 맞춘 상품).
