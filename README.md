# Madison Insights

End-to-end analysis of Madison, WI public data — 50K+ traffic crash records (WI State Patrol DT4000) and building permit trends (FRED + Census ACS) — surfaced as an interactive Streamlit dashboard. Analytical highlights include severity-weighted hotspot ranking, spatial join of Census tracts to neighborhood names via pure-Python ray casting, and a geographic choropleth with percentile-clipped color scaling.

![Dashboard preview](charts/dashboard_preview.png)

---

## Key Findings

### Building Permits
Madison MSA housing construction accelerated sharply after 2013, peaking at **7,334 units authorized in 2021** — a 5× increase from the 2010–2012 post-recession floor. The mix has shifted decisively toward density: by 2022, single-family homes made up only **28.7%** of permitted units, with multifamily (5+) driving the bulk of growth.

Neighborhood-level mapping (Census ACS + Madison Neighborhood Associations) identified **Madison West** as the fastest-growing area at **+148.8%** housing unit growth since 2010, followed by Capitol Neighborhoods (+75%) and the Campus Area (+62%). Growth clusters on Madison's east and southwest edges along the E Washington Ave, Verona Rd, and Stoughton Rd corridors.

![Annual permit trend](charts/permits_annual_trend.png)
![Top growing areas](charts/permits_top_tracts.png)

### Traffic Crashes
Hotspot intersections are ranked by **severity score** (fatal×5, injury×2, PDO×1) to surface genuinely dangerous locations rather than high-volume low-severity spots. The **#1 severity-weighted hotspot** is **S Gammon Rd @ Watts Rd** (score 144, 106 crashes), followed by S Stoughton Rd @ Pflaum Rd (140) and John Nolen Dr (134). E Washington Ave appears three times in the top 15.

**October is the peak crash month** (939 avg/year), with January and December nearly as high. The **5 PM hour** accounts for the most crashes (4,342 total), with the full 3–5 PM window making up ~24% of all timed crashes.

![Top crash hotspots](charts/crashes_top_intersections.png)
![Monthly seasonality](charts/crashes_monthly_seasonality.png)

---

## Dashboard Features

| Tab | Features |
|---|---|
| Building Permits | Annual trend with year-range slider · SF vs multifamily share · Top N fastest-growing areas with neighborhood names · Geographic choropleth of tract-level growth across Dane County |
| Traffic Crashes | Monthly seasonality · Hourly distribution · Severity-weighted hotspot chart · Interactive folium heatmap · Intersection drill-down (year trend, hour-of-day, severity breakdown for any selected intersection) |

---

## How to Run

```bash
# 1. Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Launch dashboard (uses pre-built Parquet files in data/)
streamlit run app.py
```

To rebuild data from scratch (requires PostgreSQL + raw source files):
```bash
psql -c "CREATE DATABASE madison_analysis"
psql madison_analysis -f scripts/01_create_schema.sql
python3 scripts/02_download_crashes.py
python3 scripts/03_download_permits.py
python3 scripts/09_neighborhood_mapping.py
python3 scripts/06_visualize_permits.py
python3 scripts/07_visualize_crashes.py
python3 scripts/10_export_parquet.py
```

---

## Data Sources

| Dataset | Source | Coverage |
|---|---|---|
| WI State Patrol Crash Records (DT4000) | [WisDOT Box](https://wisdot.box.com) | 2018–2022, Dane County |
| Building Permits (FRED) | [FRED MADI555BP1FH](https://fred.stlouisfed.org) | 1988–present, Madison MSA |
| Census Tract Housing Units (ACS 5-yr) | [Census API](https://api.census.gov) | 2010 + 2022 |
| Madison Neighborhood Associations | [City of Madison GIS](https://maps.cityofmadison.com) | 141 neighborhoods |
| Census Tract Boundaries (TIGER) | [Census TIGERweb](https://tigerweb.geo.census.gov) | Dane County |

---

## Tech Stack

Python · DuckDB · pandas · pyarrow · plotly · streamlit · folium · numpy
