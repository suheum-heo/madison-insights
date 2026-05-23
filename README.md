# Madison Insights

Exploratory analysis of Madison, WI public data — building permits and traffic crashes — surfaced as an interactive Streamlit dashboard.

---

## Questions Answered

1. 🏗️ **Building Permits** — Which neighborhoods are growing fastest?
2. 🚗 **Traffic Crashes** — Where are the hotspot intersections, and what are the seasonal patterns?

---

## Key Findings

### 🏗️ Building Permits
Madison MSA housing construction accelerated sharply after 2013, peaking at **7,334 units authorized in 2021** — a 5× increase from the 2010–2012 post-recession floor. The mix has shifted decisively toward density: by 2022, single-family homes made up only **28.7%** of permitted units, with multifamily (5+) driving the bulk of growth.

Neighborhood-level mapping (Census ACS + Madison Neighborhood Associations) identified **Madison West** as the fastest-growing area at **+148.8%** housing unit growth since 2010, followed by Capitol Neighborhoods tracts (+75%) and the Campus Area (+62%). Growth clusters on Madison's east and southwest edges along the E Washington Ave, Verona Rd, and Stoughton Rd corridors.

![Annual permit trend](charts/permits_annual_trend.png)
![Top growing areas](charts/permits_top_tracts.png)

### 🚗 Traffic Crashes
Hotspot intersections are ranked by **severity score** (fatal×5, injury×2, PDO×1) to surface genuinely dangerous locations rather than high-volume low-severity spots. The **#1 severity-weighted hotspot** is **S Gammon Rd @ Watts Rd** (score 144, 106 crashes), followed by S Stoughton Rd @ Pflaum Rd (140) and John Nolen Dr (134). E Washington Ave appears three times in the top 15.

**October is the peak crash month** (939 avg/year), with January and December nearly as high. The **5 PM hour** accounts for the most crashes (4,342 total), with the full 3–5 PM window making up ~24% of all timed crashes.

![Top crash hotspots](charts/crashes_top_intersections.png)
![Monthly seasonality](charts/crashes_monthly_seasonality.png)

---

## Dashboard Features

| Tab | Features |
|---|---|
| 🏗️ Building Permits | Annual trend with year-range slider · SF vs multifamily share · Top N fastest-growing areas with neighborhood names · **Geographic choropleth** of tract-level growth across Dane County |
| 🚗 Traffic Crashes | Monthly seasonality · Hourly distribution · Severity-weighted hotspot chart · Interactive folium heatmap · **Intersection drill-down** (year trend, hour-of-day, severity breakdown for any selected intersection) |

---

## How to Run

```bash
# 1. Create venv and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install pandas psycopg2-binary plotly streamlit folium matplotlib seaborn numpy

# 2. Set up PostgreSQL database
psql -c "CREATE DATABASE madison_analysis"
psql madison_analysis -f scripts/01_create_schema.sql

# 3. Load data (see scripts/02 and 03 for download instructions)
python3 scripts/02_download_crashes.py
python3 scripts/03_download_permits.py

# 4. Map census tracts to neighborhood names
python3 scripts/09_neighborhood_mapping.py

# 5. Generate static charts and maps
python3 scripts/06_visualize_permits.py
python3 scripts/07_visualize_crashes.py

# 6. Launch dashboard
streamlit run app.py
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

Python · PostgreSQL · pandas · psycopg2 · plotly · streamlit · folium · matplotlib · numpy
