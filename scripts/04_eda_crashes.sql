-- ─── Crash EDA: Hotspots & Seasonality ──────────────────────────────────────
-- Run in psql: \i scripts/04_eda_crashes.sql

\echo '=== Row count by year ==='
SELECT source_year, COUNT(*) AS crashes,
       SUM(num_injuries)   AS injuries,
       SUM(num_fatalities) AS fatalities
FROM   crashes
GROUP  BY source_year
ORDER  BY source_year;


\echo ''
\echo '=== Seasonality: crashes by month ==='
SELECT EXTRACT(MONTH FROM crash_date)::INT AS month,
       TO_CHAR(crash_date, 'Mon')           AS month_name,
       COUNT(*)                             AS total_crashes,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
FROM   crashes
WHERE  crash_date IS NOT NULL
GROUP  BY 1, 2
ORDER  BY 1;


\echo ''
\echo '=== Seasonality: crashes by day-of-week ==='
SELECT EXTRACT(DOW FROM crash_date)::INT AS dow,
       TO_CHAR(crash_date, 'Day')         AS day_name,
       COUNT(*)                           AS total_crashes
FROM   crashes
WHERE  crash_date IS NOT NULL
GROUP  BY 1, 2
ORDER  BY 1;


\echo ''
\echo '=== Severity breakdown ==='
SELECT severity,
       COUNT(*) AS crashes,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct
FROM   crashes
GROUP  BY severity
ORDER  BY crashes DESC;


\echo ''
\echo '=== Top 20 intersection hotspots (by crash count) ==='
SELECT on_road_name,
       at_road_name,
       COUNT(*)                              AS crashes,
       SUM(num_injuries)                     AS total_injuries,
       SUM(num_fatalities)                   AS total_fatalities,
       ROUND(AVG(latitude)::NUMERIC, 5)      AS avg_lat,
       ROUND(AVG(longitude)::NUMERIC, 5)     AS avg_lon
FROM   crashes
WHERE  on_road_name IS NOT NULL AND on_road_name NOT IN ('', 'NaN')
  AND  at_road_name IS NOT NULL AND at_road_name NOT IN ('', 'NaN')
GROUP  BY on_road_name, at_road_name
HAVING COUNT(*) >= 3
ORDER  BY crashes DESC
LIMIT  20;


\echo ''
\echo '=== Top 20 road-segment hotspots (on-road only) ==='
SELECT on_road_name,
       COUNT(*)             AS crashes,
       SUM(num_injuries)    AS total_injuries,
       SUM(num_fatalities)  AS total_fatalities
FROM   crashes
WHERE  on_road_name IS NOT NULL
  AND  on_road_name NOT IN ('', 'NaN', 'PARKING LOT', 'PRIVATE PROPERTY')
GROUP  BY on_road_name
ORDER  BY crashes DESC
LIMIT  20;


\echo ''
\echo '=== Seasonal pattern by severity ==='
SELECT EXTRACT(MONTH FROM crash_date)::INT AS month,
       severity,
       COUNT(*) AS crashes
FROM   crashes
WHERE  crash_date IS NOT NULL
  AND  severity IS NOT NULL
GROUP  BY 1, 2
ORDER  BY 1, crashes DESC;


\echo ''
\echo '=== Weather conditions in crashes ==='
-- DT4000 weather codes: 101=clear, 102=cloudy, 103=rain, 104=snow/sleet,
--   105=freezing rain, 106=fog, 107=severe crosswinds, 108=blowing sand/dirt
SELECT CASE weather
           WHEN '101' THEN 'Clear'
           WHEN '102' THEN 'Cloudy'
           WHEN '103' THEN 'Rain'
           WHEN '104' THEN 'Snow/Sleet'
           WHEN '105' THEN 'Freezing Rain'
           WHEN '106' THEN 'Fog'
           WHEN '107' THEN 'Severe Crosswinds'
           WHEN '108' THEN 'Blowing Sand/Dirt'
           ELSE weather
       END AS weather_desc,
       COUNT(*) AS crashes,
       SUM(num_injuries) AS injuries
FROM   crashes
WHERE  weather IS NOT NULL AND weather NOT IN ('NaN', '999', '998')
GROUP  BY weather, weather_desc
ORDER  BY crashes DESC;


\echo ''
\echo '=== Crash hour distribution ==='
SELECT EXTRACT(HOUR FROM crash_time)::INT AS hour,
       COUNT(*) AS crashes
FROM   crashes
WHERE  crash_time IS NOT NULL
GROUP  BY 1
ORDER  BY 1;
