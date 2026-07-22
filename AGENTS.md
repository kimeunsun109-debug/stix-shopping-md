# STIX 쇼핑몰 MD — Agent 가이드

> **로컬 Agent · Cloud Agent 공통 필독** — 사용자 협업 방식은 아래 「사용자와의 협업」과 `.cursor/rules/user-working-style.mdc`를 따른다.

## 역할
멀티몰(쿠팡·ESM·스마트스토어·11번가·카페24) MD 분석. 브랜드: **스팃스(STIX)**.

## 사용자와의 협업 (2026-07-19)
사용자는 완벽한 프롬프트를 붙여넣지 않는다. **모르는 것 · 알고 싶은 것 · 하고 싶은 방향**을 솔직히 말한다.

- 개발 경험은 적을 수 있으나 **상급 퀄리티**를 원함 → 에이전트가 설계·검증·마감을 보완
- **결과물로 판단** → 설명보다 완성된 산출물 우선
- 강점: **끈기 · 오기 · 집요함** → 에이전트도 중도 포기·대충 마감 금지
- “프롬프트를 더 잘 써 달라”로 책임을 돌리지 말 것. 솔직한 말을 더 좋은 입력으로 쓸 것.
- 눈치껏 의도·품질·다음 행동을 추론하고, 실패 시 재시도·대안·검증까지 이어 갈 것.

원문·상세 행동 지침: `.cursor/rules/user-working-style.mdc` (alwaysApply)

## 작업 폴더
- 코드: 저장소 루트
- 데이터: `쇼핑몰별 전체상품/` (Git 제외, 실행 전 필수)
- 로켓그로스 정산: `쇼핑몰별 전체상품/로켓그로스/`

## 규칙
1. **상품 자동 수정 금지** — 분석·보고만, 실행은 사용자 승인 후
2. `.env.txt` 비밀번호 출력·커밋 금지
3. CDP 스크래핑은 로컬 Chrome 9233 전용 (Cloud에서는 엑셀 수동 export 가정)

## 최근 작업 (2026-07)
- **Decision Quality (post-v7)** — 새 Engine 없이 정확도 개선
  - 추천 A/B (상품명·이미지·가격·FAQ) → Verification → Memory 승자 학습
  - Confidence/Evidence가 **최근 성공 사례** 우선
  - Dashboard Action 카드에 Evidence · 실패가능성 · A/B
  - KPI: 추천 정확도·매출·운영시간·신뢰도 (기능 수 아님)
- **v7 AI MD Autonomous** Daily/Weekly/Monthly · Opportunity · Priority · /md
- **v6 Real Operation** 배치 100+ / 스케줄러 / Memory KB
- **SEO Recovery Engine** 유지·재사용
- ESM 슈퍼클러스터 그룹 적용 프로젝트는 **마감·삭제됨**

## 출력 파일
- `SEO_RECOVERY_*.txt`, `seo_history/*.json`
- `STIX_*.xlsx`, `MD_*.txt` — 스크립트 실행 시 루트에 생성
