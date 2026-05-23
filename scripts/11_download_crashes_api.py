"""
Download 2023+ crash data from WisTransPortal Community Maps ArcGIS GP service.

WI State Patrol Box.com open data only covers through 2022. This script uses:
  https://transportal.cee.wisc.edu/arcgis/rest/services/crash/GP/GPServer

Two-phase fetch per year:
  1. GetCrashByCountyYear  → list of crash IDs for Dane County
  2. GetCrashProps (concurrent, 20 workers) → full DT4000 fields per crash

Already-loaded years are skipped automatically via DB check.
Run: .venv/bin/python3 scripts/11_download_crashes_api.py
"""

import json
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

COUNTY_YEAR_URL = (
    "https://transportal.cee.wisc.edu/arcgis/rest/services/crash"
    "/getcrashbycountyyear/GPServer/GetCrashByCountyYear/execute"
)
CRASH_PROPS_URL = (
    "https://transportal.cee.wisc.edu/arcgis/rest/services/crash"
    "/GetCrashProps/GPServer/GetCrashProps/execute"
)
DANE_COUNTY_STR = "Dane - 13"    # format expected by Counties parameter
DANE_COUNTY_CODE = 13
TARGET_YEARS = [2023, 2024, 2025]
DB_URL = "dbname=madison_analysis"
MAX_WORKERS = 20

SEVERITY_MAP = {"FAT": "1", "INJ": "2", "PDO": "3", "PD": "3"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def clean(v):
    """Convert 'MISSING', '', None to None; otherwise return as-is."""
    if v is None or v == "" or (isinstance(v, str) and v.strip().upper() == "MISSING"):
        return None
    return v


def to_date(s) -> date | None:
    s = clean(s)
    if s is None:
        return None
    try:
        return pd.to_datetime(s, format="%m/%d/%Y", errors="coerce").date()
    except Exception:
        return None


def to_time(s) -> str | None:
    s = clean(s)
    if s is None:
        return None
    try:
        val = str(int(float(s))).zfill(4)
        hh, mm = int(val[:2]), int(val[2:])
        if hh > 23 or mm > 59:
            return None
        return f"{hh:02d}:{mm:02d}"
    except Exception:
        return None


def to_int(v) -> int | None:
    v = clean(v)
    if v is None:
        return None
    try:
        return int(float(v))
    except Exception:
        return None


def to_float(v) -> float | None:
    v = clean(v)
    if v is None:
        return None
    try:
        f = float(v)
        return None if f != f else f  # NaN guard
    except Exception:
        return None


def yn(v) -> bool:
    return isinstance(v, str) and v.strip().upper() == "Y"


# ── API calls ─────────────────────────────────────────────────────────────────

def get_crash_ids(year: int) -> list[str]:
    """Phase 1: return all crash ID strings for Dane County in the given year."""
    # Counties parameter expects a JSON array string: '["Dane - 13"]'
    params = urllib.parse.urlencode({
        "f": "json",
        "Counties": f'["{DANE_COUNTY_STR}"]',
        "Start_Year": str(year),
        "End_Year": str(year),
    })
    url = f"{COUNTY_YEAR_URL}?{params}"
    with urllib.request.urlopen(url, timeout=120) as r:
        data = json.loads(r.read())
    ids = []
    for result in data.get("results", []):
        if not isinstance(result, dict):
            continue
        val = result.get("value", {})
        if not isinstance(val, dict):
            continue
        for feat in val.get("features", []):
            cid = feat.get("attributes", {}).get("id")
            if cid:
                ids.append(str(cid))
    return ids


def get_crash_props(crash_id: str) -> dict | None:
    """Phase 2: return raw attributes dict for one crash ID, or None on error.

    GetCrashProps returns value as a flat dict (not GeoJSON features), e.g.:
      {"results": [{"paramName": "props", "dataType": "GPString", "value": {...}}]}
    """
    params = urllib.parse.urlencode({"f": "json", "docNumber": crash_id})
    url = f"{CRASH_PROPS_URL}?{params}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read())
        for result in data.get("results", []):
            if isinstance(result, dict) and result.get("paramName") == "props":
                val = result.get("value")
                if isinstance(val, dict):
                    return val
        return None
    except Exception:
        return None


# ── Normalization ─────────────────────────────────────────────────────────────

def normalize_row(attrs: dict, year: int) -> tuple:
    """Map API attributes to the upsert tuple column order.

    Coordinates: LATDECDG/LONDECDG (same as CSV DT4000 naming).
    Weather/road: API uses WTCOND_A/RDCOND_A vs WTCOND01/RDCOND01 in CSV.
    Severity: API uses FAT/INJ/PDO; DB stores '1'/'2'/'3'.
    """
    raw_for_db = {k: (None if (isinstance(v, float) and v != v) else v)
                  for k, v in attrs.items()}
    svr_raw = str(attrs.get("CRSHSVR", "") or "").strip().upper()
    return (
        year,
        to_date(attrs.get("CRSHDATE")),
        to_time(attrs.get("CRSHTIME")),
        to_int(attrs.get("CNTYCODE")) or DANE_COUNTY_CODE,
        (clean(attrs.get("MUNINAME")) or "").strip().title(),
        (clean(attrs.get("ONSTR")) or "").strip(),
        (clean(attrs.get("ATSTR")) or "").strip(),
        to_float(attrs.get("LATDECDG")),
        to_float(attrs.get("LONDECDG")),
        SEVERITY_MAP.get(svr_raw, clean(attrs.get("CRSHSVR"))),
        to_int(attrs.get("TOTVEH")),
        to_int(attrs.get("TOTINJ")),
        to_int(attrs.get("TOTFATL")),
        clean(attrs.get("CRSHTYPE")),
        clean(attrs.get("WTCOND_A")),
        clean(attrs.get("LGTCOND")),
        clean(attrs.get("RDCOND_A")),
        yn(attrs.get("ALCFLAG")),
        yn(attrs.get("DRUGFLAG")),
        yn(attrs.get("HITRUN")),
        yn(attrs.get("BIKEFLAG")),
        yn(attrs.get("PEDFLAG")),
        json.dumps(raw_for_db, default=str),
    )


# ── DB helpers (same contract as script 02) ───────────────────────────────────

def get_loaded_years(conn) -> set[int]:
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT source_year FROM crashes")
    years = {row[0] for row in cur.fetchall()}
    cur.close()
    return years


def upsert(conn, rows: list[tuple]):
    cur = conn.cursor()
    execute_values(cur, """
        INSERT INTO crashes (
            source_year, crash_date, crash_time,
            county_code, city_name, on_road_name, at_road_name,
            latitude, longitude,
            severity, num_vehicles, num_injuries, num_fatalities,
            collision_type, weather, light_condition, road_surface,
            alcohol_related, drug_related, hit_run,
            bike_involved, ped_involved, raw
        ) VALUES %s
        ON CONFLICT DO NOTHING
    """, rows, page_size=500)
    conn.commit()
    inserted = cur.rowcount
    cur.close()
    return inserted


# ── Fetch a full year ─────────────────────────────────────────────────────────

def fetch_year(year: int) -> list[tuple]:
    print(f"  Phase 1: fetching crash IDs for {year}...")
    ids = get_crash_ids(year)
    print(f"  {len(ids):,} crash IDs retrieved")
    if not ids:
        return []

    print(f"  Phase 2: fetching full properties (20 concurrent workers)...")
    rows = []
    errors = 0
    done = 0
    total = len(ids)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(get_crash_props, cid): cid for cid in ids}
        for future in as_completed(futures):
            done += 1
            if done % 500 == 0 or done == total:
                print(f"    {done}/{total} ({100*done//total}%)", end="\r", flush=True)
            attrs = future.result()
            if attrs is None:
                errors += 1
                continue
            # Skip non-Dane-County records (API occasionally returns strays)
            if to_int(attrs.get("CNTYCODE")) != DANE_COUNTY_CODE:
                continue
            rows.append(normalize_row(attrs, year))

    print()  # newline after \r progress
    if errors:
        print(f"  Warning: {errors} crashes failed to fetch (skipped)")
    return rows


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    conn = psycopg2.connect(DB_URL)
    loaded = get_loaded_years(conn)
    if loaded:
        print(f"Years already in DB: {sorted(loaded)}")

    years_to_load = [y for y in TARGET_YEARS if y not in loaded]
    if not years_to_load:
        print("All target years already loaded. Nothing to do.")
        conn.close()
        return

    for year in years_to_load:
        print(f"\nProcessing year {year}...")
        rows = fetch_year(year)
        if not rows:
            print(f"  No data returned for {year} — skipping")
            continue
        inserted = upsert(conn, rows)
        print(f"  Inserted {inserted} rows for {year}")

    conn.close()
    print("\nDone. Re-run scripts/10_export_parquet.py to update data/crashes.parquet")


if __name__ == "__main__":
    main()
