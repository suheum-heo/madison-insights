-- ─── Permits EDA: Growth Trends ──────────────────────────────────────────────
-- NOTE on tract → neighborhood mapping:
--   Census tracts 1–99    = core Madison (Downtown, Isthmus, Near East/West)
--   Tracts 100–119        = far east side / newer east Madison
--   Tracts 4.xx, 16.xx–18.xx = west / southwest / UW area
--   Tracts 125–137        = north Madison / outlying areas
--   For exact neighborhood names: cross-reference with Madison Neighborhood
--   Associations layer at maps.cityofmadison.com (layer 12 in OPEN_DATA service)
-- Run in psql: \i scripts/05_eda_permits.sql

\echo '=== Row count ==='
SELECT COUNT(*), MIN(survey_date), MAX(survey_date) FROM permits_bps_monthly;


\echo ''
\echo '=== Annual permit totals for Madison ==='
SELECT EXTRACT(YEAR FROM survey_date)::INT AS year,
       SUM(units_1fam)    AS single_family,
       SUM(units_2fam)    AS two_family,
       SUM(units_3_4fam)  AS three_four_family,
       SUM(units_5plus)   AS multifamily_5plus,
       SUM(units_total)   AS total_units
FROM   permits_bps_monthly
GROUP  BY 1
ORDER  BY 1;


\echo ''
\echo '=== Year-over-year growth rate ==='
WITH annual AS (
    SELECT EXTRACT(YEAR FROM survey_date)::INT AS year,
           SUM(units_total) AS total
    FROM   permits_bps_monthly
    GROUP  BY 1
)
SELECT year,
       total,
       LAG(total) OVER (ORDER BY year) AS prev_year,
       ROUND(
           (total - LAG(total) OVER (ORDER BY year)) * 100.0
           / NULLIF(LAG(total) OVER (ORDER BY year), 0),
           1
       ) AS yoy_pct
FROM   annual
ORDER  BY year;


\echo ''
\echo '=== Seasonal pattern: permits by month (all years) ==='
SELECT EXTRACT(MONTH FROM survey_date)::INT AS month,
       TO_CHAR(survey_date, 'Mon')           AS month_name,
       ROUND(AVG(units_total))               AS avg_units,
       SUM(units_total)                      AS total_units
FROM   permits_bps_monthly
GROUP  BY 1, 2
ORDER  BY 1;


\echo ''
\echo '=== Mix shift: single-family vs multifamily over time ==='
WITH annual AS (
    SELECT EXTRACT(YEAR FROM survey_date)::INT AS year,
           SUM(units_1fam)   AS sf,
           SUM(units_5plus)  AS mf,
           SUM(units_total)  AS total
    FROM   permits_bps_monthly
    GROUP  BY 1
)
SELECT year, sf, mf, total,
       ROUND(sf * 100.0 / NULLIF(total, 0), 1) AS sf_pct,
       ROUND(mf * 100.0 / NULLIF(total, 0), 1) AS mf_pct
FROM   annual
ORDER  BY year;


\echo ''
\echo '=== 3-year rolling average (smoothed trend) ==='
WITH monthly AS (
    SELECT survey_date, units_total
    FROM   permits_bps_monthly
    ORDER  BY survey_date
)
SELECT survey_date,
       units_total,
       ROUND(AVG(units_total) OVER (
           ORDER BY survey_date
           ROWS BETWEEN 35 PRECEDING AND CURRENT ROW
       )) AS rolling_36mo_avg
FROM   monthly
ORDER  BY survey_date;


\echo ''
\echo '=== Top 15 fastest-growing census tracts (2010 → 2022) ==='
SELECT
    name,
    housing_units_2010                   AS units_2010,
    housing_units_2023                   AS units_2022,
    housing_units_2023 - housing_units_2010 AS units_added,
    ROUND((housing_units_2023 - housing_units_2010) * 100.0
          / NULLIF(housing_units_2010, 0), 1) AS growth_pct
FROM census_tracts
WHERE housing_units_2010 > 100
  AND housing_units_2023 IS NOT NULL
ORDER BY growth_pct DESC
LIMIT 15;


\echo ''
\echo '=== Top 15 by absolute units added ==='
SELECT
    name,
    housing_units_2010                   AS units_2010,
    housing_units_2023                   AS units_2022,
    housing_units_2023 - housing_units_2010 AS units_added,
    ROUND((housing_units_2023 - housing_units_2010) * 100.0
          / NULLIF(housing_units_2010, 0), 1) AS growth_pct
FROM census_tracts
WHERE housing_units_2010 IS NOT NULL
  AND housing_units_2023 IS NOT NULL
ORDER BY units_added DESC
LIMIT 15;


\echo ''
\echo '=== Tracts that shrank (net housing unit loss) ==='
SELECT
    name,
    housing_units_2010,
    housing_units_2023,
    housing_units_2023 - housing_units_2010 AS units_change
FROM census_tracts
WHERE housing_units_2010 IS NOT NULL
  AND housing_units_2023 IS NOT NULL
  AND housing_units_2023 < housing_units_2010
ORDER BY units_change ASC;
