"""
Export PostgreSQL tables to Parquet for Streamlit Cloud deployment.
Writes data/permits.parquet, data/tracts.parquet, data/crashes.parquet.
"""

from pathlib import Path

import pandas as pd
import psycopg2

DATA = Path(__file__).parent.parent / "data"
DATA.mkdir(exist_ok=True)

conn = psycopg2.connect("dbname=madison_analysis")

print("Exporting permits_bps_monthly...")
df = pd.read_sql("SELECT * FROM permits_bps_monthly", conn)
df.to_parquet(DATA / "permits.parquet", index=False)
print(f"  {len(df):,} rows → data/permits.parquet")

print("Exporting census_tracts...")
df = pd.read_sql("SELECT * FROM census_tracts", conn)
df.to_parquet(DATA / "tracts.parquet", index=False)
print(f"  {len(df):,} rows → data/tracts.parquet")

print("Exporting crashes (excluding raw JSONB)...")
df = pd.read_sql("""
    SELECT crash_id, source_year, crash_date,
           CAST(crash_time AS TEXT) AS crash_time,
           county_code, city_name,
           on_road_name, at_road_name,
           latitude, longitude,
           severity, num_vehicles, num_injuries, num_fatalities,
           collision_type, weather, light_condition, road_surface,
           alcohol_related, drug_related, hit_run, bike_involved, ped_involved
    FROM crashes
""", conn)
df.to_parquet(DATA / "crashes.parquet", index=False)
print(f"  {len(df):,} rows → data/crashes.parquet")

conn.close()
print("Done.")
