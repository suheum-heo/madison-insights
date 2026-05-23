# Todo

## Next Up

- [ ] Add dashboard screenshot (`charts/dashboard_preview.png`) and commit

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
- [x] `scripts/06_visualize_permits.py` — 4 static charts + choropleth map (permits)
- [x] `scripts/07_visualize_crashes.py` — 4 static charts + folium heatmap (crashes)
- [x] `scripts/08_insights.md` — key findings summary
- [x] `scripts/09_neighborhood_mapping.py` — spatial join: 48 tracts mapped to Madison neighborhood names via TIGER interior points + ray casting
- [x] `app.py` — Streamlit dashboard: Permits tab (annual trend, SF/MF split, top areas, choropleth) + Crashes tab (seasonality, hourly, severity-weighted hotspots, folium map, intersection drill-down)
- [x] `README.md` — initial project README (needs update for Week 3–4 additions)
- [x] Polish pass: removed Korean text, fixed @st.cache_data scope, severity-weighted chart ranking, choropleth 95th-pct color scale, TIGER interior points for neighborhood mapping
- [x] `README.md` final update — rewritten opening, removed "Questions Answered", added screenshot placeholder
- [x] `scripts/10_export_parquet.py` — export DB tables to Parquet for deployment
- [x] `app.py` — swapped psycopg2 → DuckDB (reads Parquet; no hosted DB required)
- [x] `requirements.txt` — created for Streamlit Cloud deployment
