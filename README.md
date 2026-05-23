# Madison Insights

Exploratory analysis of Madison, WI public data — building permits and traffic crashes — surfaced as an interactive Streamlit dashboard.

---

## Questions Answered

| | Question | |
|---|---|---|
| 🏗️ | 건물 허가: **어느 동네가 빠르게 성장하고 있나?** | Which neighborhoods are growing fastest? |
| 🚗 | 교통사고: **사고 다발 구간은 어디인가? 계절성 패턴은?** | Where are crash hotspots? What are the seasonal patterns? |

---

## Key Findings

### Building Permits
Madison MSA housing construction accelerated sharply after 2013, peaking at **7,334 units authorized in 2021** — a 5× increase from the 2010–2012 post-recession floor. The mix has shifted decisively toward density: by 2022, single-family homes made up only **28.7%** of permitted units, down from a majority in earlier years, with multifamily (5+ units) driving the bulk of growth.

At the neighborhood level, **Census Tract 109.03** (far east Madison, near East Towne) saw the most explosive growth — a **+148.8%** increase in housing units over 2010 levels. Fast-growing tracts cluster on Madison's east and southwest edges, consistent with the city's outward expansion along E Washington Ave, Verona Rd, and Stoughton Rd corridors.

![Annual permit trend](charts/permits_annual_trend.png)

### Traffic Crashes
The **#1 crash hotspot** over 2018–2022 was **S Gammon Rd @ Watts Rd** (106 crashes), followed by S Stoughton Rd @ Pflaum Rd (103) and the John Nolen Dr corridor (97). These are high-volume arterial intersections on Madison's south and east sides. E Washington Ave appeared three times in the top 15, underscoring persistent safety challenges on that corridor.

**October is the peak crash month** (939 avg/year), with January and December nearly as high — fall/winter conditions drive the spike. Crashes dip to their lowest in spring (March–April). By time of day, the **5 PM hour** had the most crashes (4,342), with the 3–5 PM window accounting for ~24% of all timed crashes.

![Top crash hotspots](charts/crashes_top_intersections.png)
![Monthly seasonality](charts/crashes_monthly_seasonality.png)

---

## How to Run

```bash
# 1. Create venv and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install pandas psycopg2-binary plotly streamlit folium matplotlib seaborn

# 2. Set up PostgreSQL database
psql -c "CREATE DATABASE madison_analysis"
psql madison_analysis -f scripts/01_create_schema.sql

# 3. Load data (see scripts/02 and 03 for download instructions)
python3 scripts/02_download_crashes.py
python3 scripts/03_download_permits.py

# 4. Generate static charts
python3 scripts/06_visualize_permits.py
python3 scripts/07_visualize_crashes.py

# 5. Launch dashboard
streamlit run app.py
```

---

## Data Sources

| Dataset | Source | Coverage |
|---|---|---|
| WI State Patrol Crash Records (DT4000) | [WisDOT Box](https://wisdot.box.com) | 2018–2022, Dane County |
| Building Permits (FRED) | [FRED MADI555BP1FH](https://fred.stlouisfed.org) | 1988–present, Madison MSA |
| Census Tract Housing Units (ACS 5-yr) | [Census API](https://api.census.gov) | 2010 + 2022 |

---

## Tech Stack

Python · PostgreSQL · pandas · psycopg2 · plotly · streamlit · folium · matplotlib
