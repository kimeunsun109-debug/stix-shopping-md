# Coupang SEO Recovery Engine v3.0

자체 학습형 이커머스 SEO 운영 AI. Collector만 교체하면 동일 Analyzer가 동작합니다.

```
Collector (coupang|smartstore|gmarket|auction|11st|amazon)
        |  Mode A CDP / Mode B Manual / Mode Hybrid
        v
CollectionBundle
        v
Analyzer (Gap, Title+AB, Golden, Trend, Memory, Learning)
        v
Recovery Report 1-20  ->  seo_history / Dashboard
```

## CLI

```bash
python md_coupang_seo_recovery.py --mode manual --input seo_engine/samples/mode_b_jewel_crossstitch.json
python md_coupang_seo_recovery.py --mode auto --keyword 보석십자수 --input seo_engine/samples/...
python md_coupang_seo_recovery.py --marketplace smartstore --input ...
python md_seo_dashboard.py
python md_seo_rank_monitor.py --product-id demo-stix-001 --keyword 보석십자수 --rank 11
```

## v3 modules

| Module | Role |
|--------|------|
| collectors/marketplaces.py | Multi-marketplace adapters |
| engines/trend.py | Daily TOP5 + new keyword alerts |
| engines/memory.py | Change reason + CTR/CVR/rank effects |
| engines/dashboard.py | Risk / recovery priorities |
| Keyword/Golden | Volume, competition, effect learning |
