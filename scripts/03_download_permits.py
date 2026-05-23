"""
Fetch building permit data for Madison, WI from two sources:

1. FRED (St. Louis Fed) — Madison MSA monthly permit counts, no auth needed
   Series used:
     MADI555BP1FH    1-unit structures (monthly, not seasonally adjusted)
     MADI555BPPRIVSA Total private units (seasonally adjusted annual rate)

2. Census ACS 5-year — housing unit counts by census tract in Dane County
   Requires a free Census API key from: https://api.census.gov/data/key_signup.html
   Set env var CENSUS_API_KEY or pass --census-key on command line

Run:
  python scripts/03_download_permits.py
  python scripts/03_download_permits.py --census-key YOUR_KEY_HERE
"""

import sys
import argparse
import urllib.request
import json
import csv
import io
from datetime import date, datetime

import psycopg2
from psycopg2.extras import execute_values

DB_URL = "dbname=madison_analysis"

FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"

FRED_SERIES = {
    "MADI555BP1FH":    "1-family units (monthly, not SA)",
    "MADI555BPPRIVSA": "All private units (SAAR)",
}

PLACE_FIPS = "55048000"  # Wisconsin(55) + Madison(48000)
DANE_COUNTY = "025"      # Dane County FIPS within Wisconsin


# ─── FRED ────────────────────────────────────────────────────────────────────

def fetch_fred(series_id: str) -> list[tuple]:
    """Return [(date, value), ...] from FRED CSV."""
    url = FRED_BASE.format(series=series_id)
    print(f"  Fetching FRED {series_id} ...")
    with urllib.request.urlopen(url, timeout=30) as r:
        lines = r.read().decode("utf-8").splitlines()
    rows = []
    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) < 2:
            continue
        try:
            d = date.fromisoformat(parts[0].strip())
            v = float(parts[1].strip()) if parts[1].strip() not in (".", "") else None
            rows.append((d, v))
        except (ValueError, TypeError):
            continue
    return rows


def load_fred_to_db(conn, series_id: str, label: str, rows: list[tuple]):
    cur = conn.cursor()
    # Store FRED series in permits_bps_monthly — map series to unit type columns
    data = []
    for d, v in rows:
        if v is None:
            continue
        units = round(v)
        # MADI555BP1FH → 1-family; others → total
        if "1FH" in series_id or "1FHSA" in series_id:
            row = (d, PLACE_FIPS, "Madison MSA (FRED)", units, None, None, None, units)
        else:
            row = (d, PLACE_FIPS, "Madison MSA (FRED)", None, None, None, None, units)
        data.append(row)

    execute_values(cur, """
        INSERT INTO permits_bps_monthly
            (survey_date, place_fips, place_name,
             units_1fam, units_2fam, units_3_4fam, units_5plus, units_total)
        VALUES %s
        ON CONFLICT (survey_date, place_fips) DO UPDATE
            SET units_total = EXCLUDED.units_total,
                units_1fam  = COALESCE(EXCLUDED.units_1fam, permits_bps_monthly.units_1fam)
    """, data, page_size=200)
    conn.commit()
    print(f"    → {cur.rowcount} rows upserted ({label})")
    cur.close()


# ─── Census ACS ──────────────────────────────────────────────────────────────

def fetch_acs_tracts(api_key: str, year: int = 2022) -> list[dict]:
    """
    Fetch housing unit counts (B25001_001E) by census tract for Dane County, WI.
    Requires a free Census API key from api.census.gov/data/key_signup.html
    """
    url = (
        f"https://api.census.gov/data/{year}/acs/acs5"
        f"?get=NAME,B25001_001E"
        f"&for=tract:*"
        f"&in=state:55%20county:{DANE_COUNTY}"
        f"&key={api_key}"
    )
    print(f"  Fetching Census ACS {year} housing units by tract (Dane County)...")
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)

    header = data[0]
    rows = []
    for row in data[1:]:
        d = dict(zip(header, row))
        geoid = f"55{DANE_COUNTY}{d.get('tract','').zfill(6)}"
        rows.append({
            "geoid":  geoid,
            "name":   d.get("NAME", ""),
            "county": DANE_COUNTY,
            "units":  int(d["B25001_001E"]) if d.get("B25001_001E") else None,
            "year":   year,
        })
    return rows


def load_acs_tracts(conn, rows_2010: list[dict], rows_2022: list[dict]):
    cur = conn.cursor()
    units_2010 = {r["geoid"]: r["units"] for r in rows_2010}
    units_2022 = {r["geoid"]: r["units"] for r in rows_2022}

    all_geoids = set(units_2010) | set(units_2022)
    data = [
        (geoid, units_2010.get(geoid), units_2022.get(geoid))
        for geoid in all_geoids
    ]
    execute_values(cur, """
        INSERT INTO census_tracts (geoid, housing_units_2010, housing_units_2023)
        VALUES %s
        ON CONFLICT (geoid) DO UPDATE
            SET housing_units_2010 = COALESCE(EXCLUDED.housing_units_2010, census_tracts.housing_units_2010),
                housing_units_2023 = COALESCE(EXCLUDED.housing_units_2023, census_tracts.housing_units_2023)
    """, data, page_size=200)
    conn.commit()
    print(f"    → {cur.rowcount} census tracts upserted")
    cur.close()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--census-key", default=None,
                        help="Free Census API key (api.census.gov/data/key_signup.html)")
    args = parser.parse_args()

    # Add unique constraint on permits table for upserts
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    try:
        cur.execute("""
            ALTER TABLE permits_bps_monthly
            ADD CONSTRAINT permits_bps_monthly_date_place
            UNIQUE (survey_date, place_fips)
        """)
        conn.commit()
    except psycopg2.errors.DuplicateTable:
        conn.rollback()
    except Exception:
        conn.rollback()
    cur.close()

    # 1. FRED data — no auth needed
    print("\n── FRED Building Permits ──")
    for series_id, label in FRED_SERIES.items():
        try:
            rows = fetch_fred(series_id)
            print(f"    Got {len(rows)} monthly observations")
            load_fred_to_db(conn, series_id, label, rows)
        except Exception as e:
            print(f"  FRED {series_id} failed: {e}")

    # 2. Census ACS tract-level — requires API key
    import os
    census_key = args.census_key or os.environ.get("CENSUS_API_KEY")
    if census_key:
        print("\n── Census ACS Tract-Level Housing Units ──")
        try:
            rows_2010 = fetch_acs_tracts(census_key, year=2010)
            rows_2022 = fetch_acs_tracts(census_key, year=2022)
            print(f"  2010: {len(rows_2010)} tracts | 2022: {len(rows_2022)} tracts")
            load_acs_tracts(conn, rows_2010, rows_2022)
        except Exception as e:
            print(f"  Census ACS failed: {e}")
    else:
        print("\n── Census tract-level analysis (optional) ──")
        print("  Skipped — no Census API key provided.")
        print("  Get a free key at: https://api.census.gov/data/key_signup.html")
        print("  Then run:  python scripts/03_download_permits.py --census-key YOUR_KEY")

    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
