# Todo

## Week 3: Insight Extraction & Visualization

- [ ] `scripts/06_visualize_permits.py` — permits_annual_trend.png, permits_sf_vs_mf.png, permits_top_tracts.png, permits_shrinking_tracts.png
- [ ] `scripts/07_visualize_crashes.py` — crashes_monthly_seasonality.png, crashes_hourly.png, crashes_dow.png, crashes_top_intersections.png, crashes_map.html
- [ ] `scripts/08_insights.md` — key findings paragraph per question

## Completed

- [x] Project setup: `.venv`, PostgreSQL `madison_analysis` DB, schema created
- [x] `scripts/01_create_schema.sql` — crashes + permits_bps_monthly + census_tracts tables
- [x] `scripts/02_download_crashes.py` — WI State Patrol crash data loader (Dane County filter)
- [x] `scripts/03_download_permits.py` — FRED MSA permits + Census ACS tract housing units
- [x] `scripts/04_eda_crashes.sql` — hotspot + seasonality queries
- [x] `scripts/05_eda_permits.sql` — annual trend + YoY growth + seasonal queries
- [x] Crash data loaded: 50,055 Dane County rows (2018–2022)
- [x] FRED data loaded: 459 months (1988–2026) of Madison MSA building permits
- [x] Census ACS loaded: 142 census tracts (2010 + 2022 housing units)
