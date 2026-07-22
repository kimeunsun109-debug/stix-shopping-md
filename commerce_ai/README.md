# STIX Commerce AI — Decision Quality + Production Grade (v7)

새 Engine / Dashboard / Report를 추가하지 않습니다.
기존 계층을 개선해 **추천 정확도 · 매출 · 운영시간 · 신뢰도 · 유지보수성**을 올립니다.

## What improved (existing modules)

| Module | Improvement |
|--------|-------------|
| `recommendation_engine` | A/B pair + Memory 기반 Expected Impact + INFO logging |
| `memory` | 최근 성공 가중 · A/B 승자 · JSONL cache (`entries`) |
| `confidence` | Memory 단일 패스 (stats/similar/evidence 공유) |
| `verification` | `record_ab_result` + JSONL cache |
| `jsonl_util` / `cache` | mtime JSONL cache + TTL + `clear_runtime_caches` |
| `dashboard` / `web/md.html` | Evidence · 실패가능성 · A/B · ops payload TTL |
| `batch_ops` / `ops_catalog` | snapshot cache · catalog TTL |
| `report` | Evidence / Expected Impact / A/B 섹션 |

## Docs

- [ARCHITECTURE.md](ARCHITECTURE.md) — layers, data flow, logging
- [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) — ops readiness
- [CTO_REVIEW.md](CTO_REVIEW.md) — scores & backlog

## A/B cycle (approve → measure → Memory)

```
추천 A/B 제안 → 사용자 승인 → 실행 준비(dry-run)
  → Verification /verification/ab → 승자 Memory 저장
  → 다음 추천 Evidence에 반영
```

## KPI

① 추천 정확도 ② 성공률 ③ 매출 ④ CTR ⑤ CVR ⑥ 운영시간 ⑦ 신뢰도

승인 없이 상품을 수정하지 않습니다.

## Tests

```bash
python -m unittest discover -s commerce_ai/tests -v
```
