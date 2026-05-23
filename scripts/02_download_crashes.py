"""
Download WI State Patrol crash data (2018-2022) from Box.com and load to Postgres.

Box.com requires a browser login for the redirect, so this script attempts a
direct download first; if that fails it prints manual-download instructions.

Manual download steps (do once, then re-run this script):
  1. Open each URL below in your browser
  2. Click "Download" (no account needed)
  3. Save the ZIP file to data/raw/crashes/

  WI_Crash_Annual_2022.zip  → https://wisdot.box.com/s/d9t72ih7tko8w8nhx35t01aqdxppy5n5
  WI_Crash_Annual_2021.zip  → https://wisdot.box.com/s/nze1fgpp5uxe0go365u04zq2j3y9qrho
  WI_Crash_Annual_2020.zip  → https://wisdot.box.com/s/0ro1y4upd4bwp8xcmhfxxyyunh7xcxnf
  WI_Crash_Annual_2019.zip  → https://wisdot.box.com/s/hcc85hy4tzh768v9u4b4ov0nbsge3h7q
  WI_Crash_Annual_2018.zip  → https://wisdot.box.com/s/gu1o556fz24zlz8zp0huhhva4mo5nib9
  Documentation             → https://wisdot.box.com/s/57ojuczi71rffpehyjk39cfn8o6u44rd
"""

import os
import zipfile
import glob
import json
import re
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

RAW_DIR = Path(__file__).parent.parent / "data/raw/crashes"
DB_URL = "dbname=madison_analysis"

# Dane County FIPS = 13 (county_code in DT4000 data)
# City of Madison city_code varies by year; filter by city_name instead
DANE_COUNTY_CODE = 13


def find_zip_files(skip_years: set[int] = frozenset()):
    zips = sorted(RAW_DIR.glob("WI_Crash_Annual_*.zip")) + \
           sorted(RAW_DIR.glob("WI_Accident_Annual_*.zip"))
    return [z for z in zips if extract_year(z) not in skip_years]


def extract_year(path: Path) -> int:
    m = re.search(r"(\d{4})", path.name)
    return int(m.group(1)) if m else 0


def load_csv_from_zip(zip_path: Path) -> pd.DataFrame | None:
    """Return the dt4000 crash CSV from the ZIP (handles 2018 and 2019+ layouts)."""
    with zipfile.ZipFile(zip_path) as z:
        # Prefer dt4000 crash CSV; fall back to any crash CSV
        candidates = [n for n in z.namelist()
                      if "crash" in n.lower() and n.lower().endswith(".csv")
                      and "vehicle" not in n.lower() and "person" not in n.lower()
                      and "object" not in n.lower() and "legacy" not in n.lower()]
        if not candidates:
            candidates = [n for n in z.namelist()
                          if "crash" in n.lower() and n.lower().endswith(".csv")]
        if not candidates:
            print(f"  No CSV found in {zip_path.name}")
            return None
        print(f"  Reading {candidates[0]} from {zip_path.name}")
        with z.open(candidates[0]) as f:
            raw = f.read()
        df = None
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                import io
                df = pd.read_csv(io.BytesIO(raw), dtype=str,
                                 low_memory=False, encoding=enc)
                break
            except (UnicodeDecodeError, Exception):
                continue
        if df is None:
            print(f"  Could not decode {candidates[0]}")
            return None
    return df


def normalize(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Map DT4000 columns to our schema. Filter to Dane County (CNTYCODE=13)."""

    # Filter: Dane County code 13 OR CNTYFIPS 55025 OR MUNINAME contains Madison
    mask = (
        (df["CNTYCODE"].astype(str).str.strip() == str(DANE_COUNTY_CODE)) |
        (df.get("CNTYFIPS", pd.Series(dtype=str)).astype(str).str.strip() == "55025") |
        (df["MUNINAME"].astype(str).str.upper().str.contains("MADISON", na=False))
    )
    df = df[mask].copy()
    print(f"    {len(df):,} Dane Co / Madison rows")

    def to_date(s):
        try:
            d = pd.to_datetime(s, format="%m/%d/%Y", errors="coerce")
            if d.isna().all():
                d = pd.to_datetime(s, errors="coerce")
            return d.dt.date
        except Exception:
            return pd.Series([None] * len(s))

    def to_time(s):
        try:
            val = str(int(float(s))).zfill(4)
            hh, mm = int(val[:2]), int(val[2:])
            if hh > 23 or mm > 59:
                return None
            return f"{hh:02d}:{mm:02d}"
        except Exception:
            return None

    def yn(col_name):
        return df[col_name].astype(str).str.strip().str.upper().eq("Y") \
            if col_name in df.columns else pd.Series([False] * len(df))

    out = pd.DataFrame({
        "source_year":    year,
        "crash_date":     to_date(df["CRSHDATE"]),
        "crash_time":     df["CRSHTIME"].apply(to_time),
        "county_code":    pd.to_numeric(df["CNTYCODE"], errors="coerce"),
        "city_name":      df["MUNINAME"].astype(str).str.strip().str.title(),
        "on_road_name":   df["ONSTR"].astype(str).str.strip(),
        "at_road_name":   df["ATSTR"].astype(str).str.strip(),
        "latitude":       pd.to_numeric(df["LATDECDG"], errors="coerce"),
        "longitude":      pd.to_numeric(df["LONDECDG"], errors="coerce"),
        "severity":       df["CRSHSVR"].astype(str).str.strip(),
        "num_vehicles":   pd.to_numeric(df["TOTVEH"], errors="coerce"),
        "num_injuries":   pd.to_numeric(df["TOTINJ"], errors="coerce"),
        "num_fatalities": pd.to_numeric(df["TOTFATL"], errors="coerce"),
        "collision_type": df["CRSHTYPE"].astype(str).str.strip(),
        "weather":        df["WTCOND01"].astype(str).str.strip(),
        "light_condition":df["LGTCOND"].astype(str).str.strip(),
        "road_surface":   df["RDCOND01"].astype(str).str.strip(),
        "alcohol_related":yn("ALCFLAG"),
        "drug_related":   yn("DRUGFLAG"),
        "hit_run":        yn("HITRUN"),
        "bike_involved":  yn("BIKEFLAG"),
        "ped_involved":   yn("PEDFLAG"),
        "raw":            df.apply(lambda r: {k: (None if (isinstance(v, float) and v != v) else v) for k, v in r.items()}, axis=1),
    })
    # Replace NaT / NaN dates with None so psycopg2 accepts them
    out["crash_date"] = out["crash_date"].where(out["crash_date"].notna(), None)
    return out


def upsert(conn, df: pd.DataFrame):
    cur = conn.cursor()
    def _none(v):
        """Convert NaN / pandas NA to None for psycopg2."""
        try:
            if v is None or (isinstance(v, float) and v != v):
                return None
        except Exception:
            pass
        return v

    rows = [
        (
            r.source_year, r.crash_date, _none(r.crash_time),
            None if pd.isna(r.county_code) else int(r.county_code),
            r.city_name, r.on_road_name, r.at_road_name,
            None if pd.isna(r.latitude) else r.latitude,
            None if pd.isna(r.longitude) else r.longitude,
            r.severity,
            None if pd.isna(r.num_vehicles) else int(r.num_vehicles),
            None if pd.isna(r.num_injuries) else int(r.num_injuries),
            None if pd.isna(r.num_fatalities) else int(r.num_fatalities),
            r.collision_type, r.weather, r.light_condition, r.road_surface,
            bool(r.alcohol_related), bool(r.drug_related), bool(r.hit_run),
            bool(r.bike_involved), bool(r.ped_involved),
            json.dumps(r.raw, allow_nan=False, default=str),
        )
        for _, r in df.iterrows()
    ]
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
    print(f"    Inserted {cur.rowcount} rows")
    cur.close()


def main():
    zips = find_zip_files(skip_years={2018})  # 2018 already loaded
    if not zips:
        print("No ZIP files found in data/raw/crashes/")
        print(__doc__)
        return

    conn = psycopg2.connect(DB_URL)
    for z in zips:
        year = extract_year(z)
        print(f"\nProcessing {z.name} (year={year})...")
        df_raw = load_csv_from_zip(z)
        if df_raw is None:
            continue
        df = normalize(df_raw, year)
        upsert(conn, df)
    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
