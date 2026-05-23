# Todo

## Current

- [ ] Download crash ZIPs manually from Box.com (see instructions in `scripts/02_download_crashes.py`)
      Then run: `python scripts/02_download_crashes.py`
- [ ] Get free Census API key → https://api.census.gov/data/key_signup.html
      Then run: `python scripts/03_download_permits.py --census-key YOUR_KEY`
      (adds housing unit counts by census tract for neighborhood-level growth analysis)

## Completed

- [x] Project setup: `.venv`, PostgreSQL `madison_analysis` DB, schema created
- [x] `scripts/01_create_schema.sql` — crashes + permits_bps_monthly + census_tracts tables
- [x] `scripts/02_download_crashes.py` — WI State Patrol crash data loader (Dane County filter)
- [x] `scripts/03_download_permits.py` — FRED MSA permits + Census ACS tract housing units
- [x] `scripts/04_eda_crashes.sql` — hotspot + seasonality queries (ready to run after data loads)
- [x] `scripts/05_eda_permits.sql` — annual trend + YoY growth + seasonal queries
- [x] FRED data loaded: 459 months (1988–2026) of Madison MSA building permits
