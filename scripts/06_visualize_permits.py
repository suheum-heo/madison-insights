"""
Permit visualizations — saves PNGs to charts/.

Charts produced:
  permits_annual_trend.png      — Total units authorized per year (bar)
  permits_sf_vs_mf.png          — Single-family vs multifamily % split (stacked area)
  permits_top_tracts.png        — Top 15 census tracts by % housing growth 2010→2022
  permits_shrinking_tracts.png  — Tracts with net housing unit loss

Run: .venv/bin/python3 scripts/06_visualize_permits.py
"""

import os
from pathlib import Path

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
        SELECT name,
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
    # Shorten labels: "Census Tract 4.01" → "Tract 4.01"
    df["label"] = df["name"].str.replace("Census Tract", "Tract", regex=False)
    df = df.sort_values("growth_pct")

    fig, ax = plt.subplots(figsize=(9, 7))
    bars = ax.barh(df["label"], df["growth_pct"], color=GREEN, zorder=2)
    ax.bar_label(bars, fmt="%.1f%%", padding=4, fontsize=8)
    ax.set_title("Top 15 Fastest-Growing Census Tracts (2010→2022)\n% Change in Housing Units",
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
        SELECT name,
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

    df["label"] = df["name"].str.replace("Census Tract", "Tract", regex=False)
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


if __name__ == "__main__":
    print("Generating permit charts...")
    chart_annual_trend()
    chart_sf_vs_mf()
    chart_top_tracts()
    chart_shrinking_tracts()
    print("Done.")
