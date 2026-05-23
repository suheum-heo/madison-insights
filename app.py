"""
Madison Insights Dashboard
Run: streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import streamlit as st

st.set_page_config(
    page_title="Madison Insights",
    page_icon="🏙️",
    layout="wide",
)

DB_URL = "dbname=madison_analysis"
CHARTS = Path(__file__).parent / "charts"

MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]
DOW_NAMES   = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]


@st.cache_data
def run_query(sql: str) -> pd.DataFrame:
    conn = psycopg2.connect(DB_URL)
    df = pd.read_sql(sql, conn)
    conn.close()
    return df


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏙️ Madison Insights")
    st.caption("Madison, WI — public data analysis")
    st.markdown("---")
    st.markdown("**Key Findings**")
    st.markdown(
        "- Housing permits peaked at **7,334 units** in 2021\n"
        "- Multifamily now >70% of all new units\n"
        "- Census Tract 109.03 grew **+148.8%** since 2010\n"
        "- Top crash hotspot: **S Gammon Rd @ Watts Rd** (106 crashes)\n"
        "- Peak crash hour: **5 PM**; peak month: **October**"
    )
    st.markdown("---")
    st.caption("Sources: WI State Patrol (2018–2022) · FRED · Census ACS")


# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_permits, tab_crashes = st.tabs(["🏗️ Building Permits", "🚗 Traffic Crashes"])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1: BUILDING PERMITS
# ════════════════════════════════════════════════════════════════════════════
with tab_permits:
    st.header("Building Permits — 어느 동네가 빠르게 성장하고 있나?")
    st.caption("Which neighborhoods are growing fast?")

    # ── Annual trend ─────────────────────────────────────────────────────────
    df_annual = run_query("""
        SELECT EXTRACT(YEAR FROM survey_date)::INT AS year,
               SUM(units_1fam)   AS single_family,
               SUM(units_5plus)  AS multifamily_5plus,
               SUM(units_total)  AS total_units
        FROM   permits_bps_monthly
        WHERE  EXTRACT(YEAR FROM survey_date) >= 2010
        GROUP  BY 1
        ORDER  BY 1
    """)

    year_min, year_max = int(df_annual["year"].min()), int(df_annual["year"].max())
    col1, col2 = st.columns([3, 1])
    with col2:
        year_range = st.slider("Year range", year_min, year_max,
                               (year_min, year_max), key="permit_year")
    with col1:
        df_filtered = df_annual[df_annual["year"].between(*year_range)]
        fig = px.bar(
            df_filtered, x="year", y="total_units",
            title="Housing Units Authorized per Year (Madison MSA)",
            labels={"year": "Year", "total_units": "Units Authorized"},
            color_discrete_sequence=["#2563EB"],
            text="total_units",
        )
        fig.update_traces(texttemplate="%{text:,}", textposition="outside")
        fig.update_layout(showlegend=False, plot_bgcolor="white",
                          yaxis=dict(gridcolor="#e5e7eb"),
                          margin=dict(t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)

    # ── SF vs MF split ───────────────────────────────────────────────────────
    df_mix = run_query("""
        WITH annual AS (
            SELECT EXTRACT(YEAR FROM survey_date)::INT AS year,
                   SUM(units_1fam)  AS sf,
                   SUM(units_5plus) AS mf,
                   SUM(units_total) AS total
            FROM   permits_bps_monthly
            WHERE  EXTRACT(YEAR FROM survey_date) >= 2010
            GROUP  BY 1
        )
        SELECT year,
               ROUND(sf * 100.0 / NULLIF(total, 0), 1)::FLOAT AS sf_pct,
               ROUND(mf * 100.0 / NULLIF(total, 0), 1)::FLOAT AS mf_pct
        FROM   annual
        ORDER  BY year
    """)
    df_mix = df_mix[df_mix["year"].between(*year_range)].dropna()

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=df_mix["year"], y=df_mix["sf_pct"],
        name="Single-family", fill="tozeroy",
        line=dict(color="#2563EB"), fillcolor="rgba(37,99,235,0.25)",
    ))
    fig2.add_trace(go.Scatter(
        x=df_mix["year"], y=df_mix["mf_pct"],
        name="Multifamily (5+)", fill="tozeroy",
        line=dict(color="#F97316"), fillcolor="rgba(249,115,22,0.25)",
    ))
    fig2.update_layout(
        title="Single-Family vs Multifamily Share of Permits",
        xaxis_title="Year", yaxis_title="% of Total Units",
        yaxis=dict(range=[0, 100], gridcolor="#e5e7eb"),
        plot_bgcolor="white", legend=dict(orientation="h"),
        margin=dict(t=50, b=20),
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ── Top tracts ───────────────────────────────────────────────────────────
    st.subheader("Fastest-Growing Census Tracts (2010 → 2022)")
    col_n, _ = st.columns([1, 3])
    with col_n:
        n_tracts = st.slider("Number of tracts", 5, 30, 15, key="n_tracts")

    df_tracts = run_query(f"""
        SELECT name,
               housing_units_2010                   AS units_2010,
               housing_units_2023                   AS units_2022,
               housing_units_2023 - housing_units_2010 AS units_added,
               ROUND((housing_units_2023 - housing_units_2010) * 100.0
                     / NULLIF(housing_units_2010, 0), 1)::FLOAT AS growth_pct
        FROM   census_tracts
        WHERE  housing_units_2010 > 100 AND housing_units_2023 IS NOT NULL
        ORDER  BY growth_pct DESC
        LIMIT  {n_tracts}
    """)
    df_tracts["label"] = df_tracts["name"].str.replace("Census Tract", "Tract", regex=False)
    df_tracts = df_tracts.sort_values("growth_pct")

    fig3 = px.bar(
        df_tracts, x="growth_pct", y="label", orientation="h",
        title=f"Top {n_tracts} Census Tracts by % Housing Unit Growth",
        labels={"growth_pct": "Growth (%)", "label": ""},
        color="growth_pct",
        color_continuous_scale="Greens",
        text="growth_pct",
    )
    fig3.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig3.update_layout(coloraxis_showscale=False, plot_bgcolor="white",
                       xaxis=dict(gridcolor="#e5e7eb"),
                       margin=dict(t=50, b=20), height=max(400, n_tracts * 28))
    st.plotly_chart(fig3, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 2: TRAFFIC CRASHES
# ════════════════════════════════════════════════════════════════════════════
with tab_crashes:
    st.header("Traffic Crashes — 사고 다발 구간 & 계절성")
    st.caption("Hotspot intersections and seasonality patterns")

    col_a, col_b, col_c = st.columns(3)
    crash_totals = run_query("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN severity = '2' THEN 1 ELSE 0 END) AS injury,
               SUM(CASE WHEN severity = '1' THEN 1 ELSE 0 END) AS fatal
        FROM crashes
    """)
    col_a.metric("Total Crashes (2018–2022)", f"{int(crash_totals['total'][0]):,}")
    col_b.metric("Injury Crashes", f"{int(crash_totals['injury'][0]):,}")
    col_c.metric("Fatal Crashes", f"{int(crash_totals['fatal'][0]):,}")

    st.markdown("---")

    # ── Monthly seasonality ──────────────────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        df_monthly = run_query("""
            SELECT EXTRACT(MONTH FROM crash_date)::INT AS month,
                   COUNT(*) AS crashes
            FROM   crashes
            WHERE  crash_date IS NOT NULL
            GROUP  BY 1
            ORDER  BY 1
        """)
        df_monthly["month_name"] = df_monthly["month"].apply(lambda m: MONTH_NAMES[m - 1])
        df_monthly["avg_per_year"] = (df_monthly["crashes"] / 5).round(0)

        fig4 = px.bar(
            df_monthly, x="month_name", y="avg_per_year",
            title="Average Crashes by Month",
            labels={"month_name": "Month", "avg_per_year": "Avg Crashes / Year"},
            color="avg_per_year",
            color_continuous_scale=[[0, "#93C5FD"], [0.5, "#2563EB"], [1, "#DC2626"]],
        )
        fig4.update_layout(coloraxis_showscale=False, plot_bgcolor="white",
                           yaxis=dict(gridcolor="#e5e7eb"), margin=dict(t=50, b=20))
        st.plotly_chart(fig4, use_container_width=True)

    # ── Hourly distribution ───────────────────────────────────────────────────
    with col_right:
        df_hourly = run_query("""
            SELECT EXTRACT(HOUR FROM crash_time)::INT AS hour,
                   COUNT(*) AS crashes
            FROM   crashes
            WHERE  crash_time IS NOT NULL
            GROUP  BY 1
            ORDER  BY 1
        """)
        fig5 = px.bar(
            df_hourly, x="hour", y="crashes",
            title="Crashes by Hour of Day",
            labels={"hour": "Hour (0 = midnight)", "crashes": "Total Crashes"},
            color="crashes",
            color_continuous_scale=[[0, "#93C5FD"], [0.5, "#2563EB"], [1, "#DC2626"]],
        )
        fig5.update_layout(coloraxis_showscale=False, plot_bgcolor="white",
                           yaxis=dict(gridcolor="#e5e7eb"), margin=dict(t=50, b=20))
        st.plotly_chart(fig5, use_container_width=True)

    # ── Top intersections ────────────────────────────────────────────────────
    st.subheader("Top Crash Hotspot Intersections")
    col_thresh, _ = st.columns([1, 3])
    with col_thresh:
        min_crashes = st.slider("Min crashes to show", 3, 30, 5, key="min_crashes")

    df_hot = run_query(f"""
        SELECT on_road_name || ' @ ' || at_road_name AS intersection,
               COUNT(*) AS crashes,
               SUM(num_injuries) AS injuries
        FROM   crashes
        WHERE  on_road_name NOT IN ('', 'NaN', 'nan')
          AND  at_road_name NOT IN ('', 'NaN', 'nan')
        GROUP  BY 1
        HAVING COUNT(*) >= {min_crashes}
        ORDER  BY crashes DESC
        LIMIT  20
    """)
    df_hot = df_hot.sort_values("crashes")

    fig6 = px.bar(
        df_hot, x="crashes", y="intersection", orientation="h",
        title=f"Top Crash Hotspots (≥{min_crashes} crashes, 2018–2022)",
        labels={"crashes": "Total Crashes", "intersection": ""},
        color="crashes",
        color_continuous_scale=[[0, "#FCA5A5"], [1, "#DC2626"]],
        text="crashes",
    )
    fig6.update_traces(textposition="outside")
    fig6.update_layout(coloraxis_showscale=False, plot_bgcolor="white",
                       xaxis=dict(gridcolor="#e5e7eb"),
                       margin=dict(t=50, b=20), height=max(400, len(df_hot) * 28))
    st.plotly_chart(fig6, use_container_width=True)

    # ── Folium map ────────────────────────────────────────────────────────────
    st.subheader("Interactive Crash Map")
    map_html = (CHARTS / "crashes_map.html").read_text()
    st.components.v1.html(map_html, height=520, scrolling=False)
