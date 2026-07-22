# STIX Commerce AI — Production Checklist

운영 전 체크리스트. 모든 항목이 충족되어야 Production Grade로 간주합니다.

## 1. Environment

- [ ] Python 3.10+ (`python --version`)
- [ ] `pip install -r requirements.txt`
- [ ] Catalog path `쇼핑몰별 전체상품/` present and readable
- [ ] Write access to `commerce_history/`
- [ ] Optional: `STIX_LOG_LEVEL=INFO` (default INFO)

## 2. Logging

- [ ] `commerce_history/logs/commerce_ai.log` created after first run
- [ ] Batch / Autonomous / Scheduler emit INFO milestones
- [ ] Errors land in `commerce_history/error_reports.jsonl` without crashing the process

## 3. Backup

- [ ] Backup `commerce_history/*.jsonl` daily (copy or zip)
- [ ] Backup `commerce_history/daily/` reports
- [ ] Keep at least 14 days of JSONL history
- [ ] Test restore: copy JSONL into empty dir → dashboard still loads

## 4. Configuration

- [ ] Executors remain dry-run / NoOp unless explicitly enabling live API
- [ ] Scheduler hour confirmed (default 08:00 local)
- [ ] Batch default limit documented (100)
- [ ] Web port: `--web` → `http://localhost:3000/md`

## 5. Recovery

- [ ] Corrupt JSONL line skipped (not fatal)
- [ ] Missing catalog / empty memory → empty board, HTTP 200
- [ ] Batch continues on per-product failure (`errors` count in summary)
- [ ] `clear_runtime_caches()` after batch/autonomous so UI sees fresh data

## 6. Tests

```bash
cd <project-root>
python -m unittest discover -s commerce_ai/tests -v
```

- [ ] All suites green (`test_v5_os`, `test_v6_os`, `test_v7_autonomous`, `test_ops_phase`, `test_accuracy_ab`, `test_final_phase`)
- [ ] Target: meaningful coverage on Memory / Verification / Confidence / API / Batch helpers ≥ 80% of critical paths

## 7. Documentation

- [ ] Root `README.md` CLI flags match `md_commerce_ai.py`
- [ ] `commerce_ai/ARCHITECTURE.md` matches v7 modules
- [ ] `commerce_ai/README.md` decision-quality notes current
- [ ] This checklist reviewed after any ops change

## 8. Performance

- [ ] Dashboard `/md` responds with TTL cache (≤60s stale OK)
- [ ] JSONL reads use mtime cache (`jsonl_util`)
- [ ] Confidence scores Memory once per card (shared rows)
- [ ] Catalog `load_ops_products` TTL-cached (5 min)

## 9. Security

- [ ] No live marketplace credentials in repo
- [ ] `.env` / secrets gitignored
- [ ] Approve-only: no auto product mutation
- [ ] API bound to localhost for internal use unless reverse-proxied with auth

## 10. Smoke run (pre-prod)

```bash
python md_commerce_ai.py --autonomous --skip-batch
python md_commerce_ai.py --web
# open http://localhost:3000/md
python -m unittest discover -s commerce_ai/tests -v
```

- [ ] Board shows urgent/high/normal/verify lanes
- [ ] Health OK or DEGRADED with clear findings (not crash)
- [ ] No unhandled exceptions in log for the smoke path

## Sign-off

| Role | Name | Date | OK |
|------|------|------|----|
| Operator | | | |
| Maintainer | | | |
