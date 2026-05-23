# Todo

## Completed

- [x] Load 2023–2025 crash data via WisTransPortal ArcGIS API (`scripts/11_download_crashes_api.py`) — 73,691 total crashes
- [x] Backfill blank `on_road_name` for highway crashes (2023–2025) from ONHWYSYS+ONHWY fields (I-39, US-12, WI-19, CTH N, etc.)
- [x] Update dashboard to use all years (2018–2025): hotspot chart title, metric label, source caption, key findings blurb
- [x] Census housing data updated to ACS 2024 (125 tracts, 261,061 units)
- [x] Filter self-intersections from hotspot chart and drill-down (e.g. "JOHN NOLEN DR @ JOHN NOLEN DR")
- [x] Fix monthly crash chart — dynamic year count instead of hardcoded ÷5
- [x] Align `crashes_top_intersections.png` to severity-score ranking (matches dashboard)
- [x] Add dashboard screenshot (`charts/dashboard.png`) — uploaded by user, referenced in README
- [x] Deprecated API cleanup: `use_container_width` → `width="stretch"`, `st.components.v1.html` → `st.iframe`
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
- [x] Polish pass: removed Korean text, fixed @st.cache_data scope, severity-weighted chart ranking, choropleth 95th-pct color scale, TIGER interior points for neighborhood mapping
- [x] `README.md` — portfolio rewrite with live demo URL, key findings, screenshots, stack, how to run
- [x] `scripts/10_export_parquet.py` — export DB tables to Parquet for deployment
- [x] `app.py` — swapped psycopg2 → DuckDB (reads Parquet; no hosted DB required)
- [x] `requirements.txt` — created for Streamlit Cloud deployment
