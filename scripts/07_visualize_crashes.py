"""
Crash visualizations — saves PNGs and an interactive HTML map to charts/.

Charts produced:
  crashes_monthly_seasonality.png  — Average crashes by month
  crashes_hourly.png               — Crashes by hour of day
  crashes_dow.png                  — Crashes by day of week
  crashes_top_intersections.png    — Top 15 hotspot intersections
  crashes_map.html                 — Interactive folium heatmap + hotspot markers

Run: .venv/bin/python3 scripts/07_visualize_crashes.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import psycopg2
import folium
from folium.plugins import HeatMap

DB_URL = "dbname=madison_analysis"
CHARTS = Path(__file__).parent.parent / "charts"
CHARTS.mkdir(exist_ok=True)

BLUE   = "#2563EB"
RED    = "#DC2626"
AMBER  = "#D97706"
TEAL   = "#0D9488"

plt.rcParams.update({
    "figure.dpi": 150,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "font.size": 10,
})

MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]
DOW_NAMES   = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]


def query(sql: str) -> pd.DataFrame:
    conn = psycopg2.connect(DB_URL)
    df = pd.read_sql(sql, conn)
    conn.close()
    return df


# ── 1. Monthly seasonality ────────────────────────────────────────────────────
def chart_monthly():
    df = query("""
        SELECT EXTRACT(MONTH FROM crash_date)::INT AS month,
               COUNT(*) AS crashes
        FROM   crashes
        WHERE  crash_date IS NOT NULL
        GROUP  BY 1
        ORDER  BY 1
    """)
    df["month_name"] = df["month"].apply(lambda m: MONTH_NAMES[m - 1])

    num_years = query("SELECT COUNT(DISTINCT source_year) AS n FROM crashes")["n"][0]
    df["avg_crashes"] = (df["crashes"] / num_years).round(0).astype(int)

    colors = [RED if v == df["avg_crashes"].max() else BLUE for v in df["avg_crashes"]]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(df["month_name"], df["avg_crashes"], color=colors, zorder=2)
    ax.bar_label(bars, fmt="%d", padding=3, fontsize=8)
    ax.set_title("Madison Area Crashes — Average per Month (2018–2025)",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Month")
    ax.set_ylabel("Avg Crashes / Year")
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=1)
    fig.tight_layout()
    out = CHARTS / "crashes_monthly_seasonality.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  Saved {out}")


# ── 2. Hourly distribution ────────────────────────────────────────────────────
def chart_hourly():
    df = query("""
        SELECT EXTRACT(HOUR FROM crash_time)::INT AS hour,
               COUNT(*) AS crashes
        FROM   crashes
        WHERE  crash_time IS NOT NULL
        GROUP  BY 1
        ORDER  BY 1
    """)

    peak = df.loc[df["crashes"].idxmax(), "hour"]
    colors = [RED if h == peak else TEAL for h in df["hour"]]

    fig, ax = plt.subplots(figsize=(11, 5))
    bars = ax.bar(df["hour"], df["crashes"], color=colors, zorder=2)
    ax.set_title("Crashes by Hour of Day (2018–2022)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Hour (0 = midnight)")
    ax.set_ylabel("Total Crashes")
    ax.set_xticks(range(0, 24))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=1)
    fig.tight_layout()
    out = CHARTS / "crashes_hourly.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  Saved {out}")


# ── 3. Day-of-week ───────────────────────────────────────────────────────────
def chart_dow():
    df = query("""
        SELECT EXTRACT(DOW FROM crash_date)::INT AS dow,
               COUNT(*) AS crashes
        FROM   crashes
        WHERE  crash_date IS NOT NULL
        GROUP  BY 1
        ORDER  BY 1
    """)
    df["day_name"] = df["dow"].apply(lambda d: DOW_NAMES[d])

    peak = df.loc[df["crashes"].idxmax(), "dow"]
    colors = [RED if d == peak else AMBER for d in df["dow"]]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(df["day_name"], df["crashes"], color=colors, zorder=2)
    ax.bar_label(bars, fmt="%d", padding=3, fontsize=9)
    ax.set_title("Crashes by Day of Week (2018–2022)", fontsize=13, fontweight="bold")
    ax.set_ylabel("Total Crashes")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=1)
    fig.tight_layout()
    out = CHARTS / "crashes_dow.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  Saved {out}")


# ── 4. Top intersection hotspots ──────────────────────────────────────────────
def chart_top_intersections():
    df = query("""
        SELECT on_road_name || ' @ ' || at_road_name AS intersection,
               COUNT(*) AS crashes,
               SUM(num_injuries) AS injuries
        FROM   crashes
        WHERE  on_road_name IS NOT NULL AND on_road_name NOT IN ('', 'NaN', 'nan')
          AND  at_road_name IS NOT NULL AND at_road_name NOT IN ('', 'NaN', 'nan')
          AND  on_road_name != at_road_name
        GROUP  BY 1
        HAVING COUNT(*) >= 3
        ORDER  BY crashes DESC
        LIMIT  15
    """)
    df = df.sort_values("crashes")

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(df["intersection"], df["crashes"], color=RED, zorder=2)
    ax.bar_label(bars, fmt="%d", padding=4, fontsize=8)
    ax.set_title("Top 15 Crash Hotspot Intersections — Dane County (2018–2025)",
                 fontsize=11, fontweight="bold")
    ax.set_xlabel("Total Crashes")
    ax.grid(axis="x", linestyle="--", alpha=0.4, zorder=1)
    fig.tight_layout()
    out = CHARTS / "crashes_top_intersections.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  Saved {out}")


# ── 5. Interactive folium map ─────────────────────────────────────────────────
def chart_map():
    # Heatmap layer: all crashes with coords
    pts = query("""
        SELECT latitude, longitude
        FROM   crashes
        WHERE  latitude  BETWEEN 42.9 AND 43.3
          AND  longitude BETWEEN -89.7 AND -89.0
    """)

    # Top hotspot markers
    hotspots = query("""
        SELECT on_road_name || ' @ ' || at_road_name AS label,
               COUNT(*) AS crashes,
               ROUND(AVG(latitude)::NUMERIC, 5)  AS lat,
               ROUND(AVG(longitude)::NUMERIC, 5) AS lon
        FROM   crashes
        WHERE  on_road_name IS NOT NULL AND on_road_name NOT IN ('', 'NaN', 'nan')
          AND  at_road_name IS NOT NULL AND at_road_name NOT IN ('', 'NaN', 'nan')
          AND  latitude  BETWEEN 42.9 AND 43.3
          AND  longitude BETWEEN -89.7 AND -89.0
        GROUP  BY 1
        HAVING COUNT(*) >= 5
        ORDER  BY crashes DESC
        LIMIT  20
    """)

    m = folium.Map(location=[43.0731, -89.4012], zoom_start=12,
                   tiles="CartoDB positron")

    heat_data = pts[["latitude", "longitude"]].dropna().values.tolist()
    HeatMap(heat_data, radius=10, blur=15, min_opacity=0.3).add_to(m)

    for _, row in hotspots.iterrows():
        if pd.notna(row["lat"]) and pd.notna(row["lon"]):
            folium.CircleMarker(
                location=[float(row["lat"]), float(row["lon"])],
                radius=max(5, min(15, int(row["crashes"]) // 3)),
                color="darkred",
                fill=True,
                fill_color="red",
                fill_opacity=0.7,
                popup=folium.Popup(f"{row['label']}<br>{row['crashes']} crashes", max_width=250),
                tooltip=f"{row['label']}: {row['crashes']} crashes",
            ).add_to(m)

    out = CHARTS / "crashes_map.html"
    m.save(str(out))
    print(f"  Saved {out}")


if __name__ == "__main__":
    print("Generating crash charts...")
    chart_monthly()
    chart_hourly()
    chart_dow()
    chart_top_intersections()
    chart_map()
    print("Done.")
