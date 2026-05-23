-- Madison Insights — PostgreSQL schema

-- ─── Traffic Crashes ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crashes (
    crash_id        BIGSERIAL PRIMARY KEY,
    source_year     SMALLINT,
    crash_date      DATE,
    crash_time      TIME,
    county_code     SMALLINT,
    city_name       TEXT,
    on_road_name    TEXT,
    at_road_name    TEXT,
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    severity        TEXT,           -- O=PDO, C=possible, B=minor, A=severe, K=fatal
    num_vehicles    SMALLINT,
    num_injuries    SMALLINT,
    num_fatalities  SMALLINT,
    collision_type  TEXT,
    weather         TEXT,
    light_condition TEXT,
    road_surface    TEXT,
    alcohol_related BOOLEAN,
    drug_related    BOOLEAN,
    hit_run         BOOLEAN,
    bike_involved   BOOLEAN,
    ped_involved    BOOLEAN,
    raw             JSONB           -- full original row
);

CREATE INDEX IF NOT EXISTS crashes_date_idx   ON crashes (crash_date);
CREATE INDEX IF NOT EXISTS crashes_city_idx   ON crashes (city_name);
CREATE INDEX IF NOT EXISTS crashes_county_idx ON crashes (county_code);
CREATE INDEX IF NOT EXISTS crashes_latlon_idx ON crashes (latitude, longitude)
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL;


-- ─── Building Permits (Census BPS — place level) ─────────────────────────────
CREATE TABLE IF NOT EXISTS permits_bps_monthly (
    id              BIGSERIAL PRIMARY KEY,
    survey_date     DATE,           -- first day of the month
    place_fips      TEXT,           -- 5-digit state+place FIPS
    place_name      TEXT,
    units_1fam      INTEGER,
    units_2fam      INTEGER,
    units_3_4fam    INTEGER,
    units_5plus     INTEGER,
    units_total     INTEGER         -- derived
);

CREATE INDEX IF NOT EXISTS bps_date_idx  ON permits_bps_monthly (survey_date);
CREATE INDEX IF NOT EXISTS bps_place_idx ON permits_bps_monthly (place_fips);


-- ─── Reference: Dane County census tracts (for neighborhood join) ─────────────
CREATE TABLE IF NOT EXISTS census_tracts (
    geoid       TEXT PRIMARY KEY,   -- 11-digit FIPS
    name        TEXT,
    county_fips TEXT,
    housing_units_2010  INTEGER,
    housing_units_2020  INTEGER,
    housing_units_2023  INTEGER
);
