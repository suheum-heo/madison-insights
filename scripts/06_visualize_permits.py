"""
Permit visualizations — saves PNGs to charts/.

Charts produced:
  permits_annual_trend.png      — Total units authorized per year (bar)
  permits_sf_vs_mf.png          — Single-family vs multifamily % split (stacked area)
  permits_top_tracts.png        — Top 15 census tracts by % housing growth 2010→2022
  permits_shrinking_tracts.png  — Tracts with net housing unit loss

Run: .venv/bin/python3 scripts/06_visualize_permits.py
"""

import json
import urllib.request
from pathlib import Path

import folium
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import psycopg2

DB_URL = "dbname=madison_analysis"
CHARTS = Path(__file__).parent.parent / "charts"
CHARTS.mkdir(exist_ok=True)

BLUE   = "#2563EB"
ORANGE = "#F97316"
GREEN  = "#16A34A"
RED    = "#DC2626"
GRAY   = "#6B7280"

plt.rcParams.update({
    "figure.dpi": 150,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "font.size": 10,
})


def query(sql: str) -> pd.DataFrame:
    conn = psycopg2.connect(DB_URL)
    df = pd.read_sql(sql, conn)
    conn.close()
    return df


# ── 1. Annual permit trend ────────────────────────────────────────────────────
def chart_annual_trend():
    df = query("""
        SELECT EXTRACT(YEAR FROM survey_date)::INT AS year,
               SUM(units_total) AS total_units
        FROM   permits_bps_monthly
        GROUP  BY 1
        ORDER  BY 1
    """)
    df = df[df["year"] >= 2010]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(df["year"], df["total_units"], color=BLUE, width=0.7, zorder=2)
    ax.bar_label(bars, fmt="%d", padding=3, fontsize=8)
    ax.set_title("Madison MSA — Housing Units Authorized per Year", fontsize=13, fontweight="bold")
    ax.set_xlabel("Year")
    ax.set_ylabel("Units Authorized")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    ax.set_xticks(df["year"])
    ax.set_xticklabels(df["year"], rotation=45, ha="right")
    ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=1)
    fig.tight_layout()
    out = CHARTS / "permits_annual_trend.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  Saved {out}")


# ── 2. Single-family vs multifamily split ────────────────────────────────────
def chart_sf_vs_mf():
    df = query("""
        WITH annual AS (
            SELECT EXTRACT(YEAR FROM survey_date)::INT AS year,
                   SUM(units_1fam)  AS sf,
                   SUM(units_5plus) AS mf,
                   SUM(units_total) AS total
            FROM   permits_bps_monthly
            GROUP  BY 1
        )
        SELECT year,
               ROUND(sf * 100.0 / NULLIF(total, 0), 1) AS sf_pct,
               ROUND(mf * 100.0 / NULLIF(total, 0), 1) AS mf_pct
        FROM   annual
        ORDER  BY year
    """)
    df = df[df["year"] >= 2010].dropna()
    df["sf_pct"] = df["sf_pct"].astype(float)
    df["mf_pct"] = df["mf_pct"].astype(float)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.stackplot(df["year"], df["sf_pct"], df["mf_pct"],
                 labels=["Single-family", "Multifamily (5+)"],
                 colors=[BLUE, ORANGE], alpha=0.85)
    ax.set_title("Madison — Single-Family vs Multifamily Share", fontsize=13, fontweight="bold")
    ax.set_xlabel("Year")
    ax.set_ylabel("% of Total Units Authorized")
    ax.set_ylim(0, 100)
    ax.set_xticks(df["year"])
    ax.set_xticklabels(df["year"], rotation=45, ha="right")
    ax.legend(loc="upper right", framealpha=0.8)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    out = CHARTS / "permits_sf_vs_mf.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  Saved {out}")


# ── 3. Top 15 tracts by % growth ─────────────────────────────────────────────
def chart_top_tracts():
    df = query("""
        SELECT COALESCE(neighborhood, name) AS label,
               housing_units_2010                   AS units_2010,
               housing_units_2023                   AS units_2022,
               housing_units_2023 - housing_units_2010 AS units_added,
               ROUND((housing_units_2023 - housing_units_2010) * 100.0
                     / NULLIF(housing_units_2010, 0), 1) AS growth_pct
        FROM   census_tracts
        WHERE  housing_units_2010 > 100
          AND  housing_units_2023 IS NOT NULL
        ORDER  BY growth_pct DESC
        LIMIT  15
    """)
    df["label"] = df["label"].str.replace("Census Tract", "Tract", regex=False)
    # Disambiguate duplicate neighborhood labels
    dup_mask = df["label"].duplicated(keep=False)
    df.loc[dup_mask, "label"] = df.loc[dup_mask, "label"]
    # Re-query to get original tract name for disambiguation suffix
    df2 = query("""
        SELECT COALESCE(neighborhood, name) AS nb,
               REPLACE(name, 'Census Tract ', '') AS tract_num,
               ROUND((housing_units_2023 - housing_units_2010) * 100.0
                     / NULLIF(housing_units_2010, 0), 1) AS growth_pct
        FROM   census_tracts
        WHERE  housing_units_2010 > 100 AND housing_units_2023 IS NOT NULL
        ORDER  BY growth_pct DESC LIMIT 15
    """)
    df2["nb"] = df2["nb"].str.replace("Census Tract", "Tract", regex=False)
    dup = df2["nb"].duplicated(keep=False)
    df2.loc[dup, "nb"] = df2.loc[dup, "nb"] + " (Tract " + df2.loc[dup, "tract_num"] + ")"
    df2 = df2.sort_values("growth_pct")
    df2["growth_pct"] = df2["growth_pct"].astype(float)

    fig, ax = plt.subplots(figsize=(9, 7))
    bars = ax.barh(df2["nb"], df2["growth_pct"], color=GREEN, zorder=2)
    ax.bar_label(bars, fmt="%.1f%%", padding=4, fontsize=8)
    ax.set_title("Top 15 Fastest-Growing Areas (2010→2022)\n% Change in Housing Units",
                 fontsize=12, fontweight="bold")
    ax.set_xlabel("Growth (%)")
    ax.grid(axis="x", linestyle="--", alpha=0.4, zorder=1)
    fig.tight_layout()
    out = CHARTS / "permits_top_tracts.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  Saved {out}")


# ── 4. Shrinking tracts ───────────────────────────────────────────────────────
def chart_shrinking_tracts():
    df = query("""
        SELECT COALESCE(neighborhood, name) AS label,
               housing_units_2023 - housing_units_2010 AS units_change
        FROM   census_tracts
        WHERE  housing_units_2010 IS NOT NULL
          AND  housing_units_2023 IS NOT NULL
          AND  housing_units_2023 < housing_units_2010
        ORDER  BY units_change ASC
    """)
    if df.empty:
        print("  No shrinking tracts found — skipping chart")
        return

    df["label"] = df["label"].str.replace("Census Tract", "Tract", regex=False)
    df = df.sort_values("units_change", ascending=False)

    fig, ax = plt.subplots(figsize=(8, max(4, len(df) * 0.5)))
    bars = ax.barh(df["label"], df["units_change"], color=RED, zorder=2)
    ax.bar_label(bars, fmt="%d", padding=4, fontsize=8)
    ax.set_title("Census Tracts with Net Housing Unit Loss (2010→2022)",
                 fontsize=12, fontweight="bold")
    ax.set_xlabel("Change in Housing Units")
    ax.axvline(0, color="black", linewidth=0.8)
    ax.grid(axis="x", linestyle="--", alpha=0.4, zorder=1)
    fig.tight_layout()
    out = CHARTS / "permits_shrinking_tracts.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  Saved {out}")


# ── 5. Choropleth map ─────────────────────────────────────────────────────────
def chart_choropleth():
    # Fetch TIGER tract GeoJSON for Dane County
    url = (
        "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks"
        "/MapServer/0/query?where=STATE%3D%2755%27+AND+COUNTY%3D%27025%27"
        "&outFields=GEOID,NAME&f=geojson&returnGeometry=true"
    )
    with urllib.request.urlopen(url, timeout=30) as r:
        tiger = json.loads(r.read())

    # Pull growth data from DB
    df = query("""
        SELECT geoid,
               COALESCE(neighborhood, name) AS label,
               ROUND((housing_units_2023 - housing_units_2010) * 100.0
                     / NULLIF(housing_units_2010, 0), 1)::FLOAT AS growth_pct
        FROM   census_tracts
        WHERE  housing_units_2010 IS NOT NULL
          AND  housing_units_2023 IS NOT NULL
    """)
    df["growth_pct"] = df["growth_pct"].astype(float)
    growth_map = dict(zip(df["geoid"], df["growth_pct"]))
    label_map  = dict(zip(df["geoid"], df["label"]))

    # Cap color scale at 95th percentile so one outlier doesn't compress the palette.
    # Clip data values to [p05, p95] so folium doesn't reject out-of-range rows;
    # outliers still get the darkest/lightest color, they just don't skew the scale.
    import numpy as np
    valid = df["growth_pct"].dropna()
    p05 = float(valid.quantile(0.05))
    p95 = float(valid.quantile(0.95))
    # Keep exact endpoints to avoid off-by-rounding out-of-range errors in folium
    inner = [round(v, 1) for v in np.linspace(p05, p95, 6)[1:-1].tolist()]
    thresholds = [p05] + inner + [p95]
    df_plot = df.copy()
    df_plot["growth_pct"] = df_plot["growth_pct"].clip(lower=p05, upper=p95)

    # Attach label + raw (unclipped) growth_pct to TIGER features for tooltip
    for feat in tiger["features"]:
        gid = feat["properties"]["GEOID"]
        feat["properties"]["growth_pct"] = growth_map.get(gid)
        feat["properties"]["label"] = label_map.get(gid, feat["properties"]["NAME"])

    m = folium.Map(location=[43.07, -89.40], zoom_start=11, tiles="CartoDB positron")

    folium.Choropleth(
        geo_data=tiger,
        data=df_plot,
        columns=["geoid", "growth_pct"],
        key_on="feature.properties.GEOID",
        fill_color="YlOrRd",
        fill_opacity=0.75,
        line_opacity=0.3,
        nan_fill_color="#cccccc",
        threshold_scale=thresholds,
        legend_name=f"Housing Unit Growth % (2010→2022) — color capped at {p95:.0f}% (95th pct)",
        name="Growth %",
    ).add_to(m)

    # Tooltip overlay
    folium.GeoJson(
        tiger,
        style_function=lambda _: {"fillOpacity": 0, "weight": 0},
        tooltip=folium.GeoJsonTooltip(
            fields=["label", "growth_pct"],
            aliases=["Neighborhood", "Growth %"],
            localize=True,
        ),
    ).add_to(m)

    out = CHARTS / "permits_choropleth.html"
    m.save(str(out))
    print(f"  Saved {out}")


if __name__ == "__main__":
    print("Generating permit charts...")
    chart_annual_trend()
    chart_sf_vs_mf()
    chart_top_tracts()
    chart_shrinking_tracts()
    chart_choropleth()
    print("Done.")
