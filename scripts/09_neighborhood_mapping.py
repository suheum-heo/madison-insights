"""
Map each census tract to the best available human-readable label.

Cascade of three point-in-polygon passes (same pure-Python ray-casting):
  1. Madison Neighborhood Associations (141 polygons)
  2. Madison Aldermanic Districts (20 polygons — covers all of Madison city)
  3. TIGER Incorporated Places + CDPs (Wisconsin, bbox-filtered to Dane County)
  4. Final fallback: "Dane County"

Uses TIGER INTPTLAT/INTPTLON (Census interior points — guaranteed on land) so
lake-boundary tracts don't drift into the wrong polygon.

Run: .venv/bin/python3 scripts/09_neighborhood_mapping.py
"""

import json
import re
import urllib.request

import psycopg2

DB_URL = "dbname=madison_analysis"

NEIGHBORHOOD_URL = (
    "https://maps.cityofmadison.com/arcgis/rest/services/Public/OPEN_DATA/MapServer/12"
    "/query?where=1%3D1&outFields=NEIGHB_NAME&f=geojson&outSR=4326&returnGeometry=true"
)
ALDERMANIC_URL = (
    "https://maps.cityofmadison.com/arcgis/rest/services/Public/OPEN_DATA/MapServer/10"
    "/query?where=1%3D1&outFields=ALD_DIST&f=geojson&outSR=4326&returnGeometry=true"
)
# Layer 18 = Incorporated Places, Layer 19 = Census Designated Places
TIGER_PLACES_URL_TMPL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb"
    "/Places_CouSub_ConCity_SubMCD/MapServer/{layer}/query"
    "?where=STATE%3D%2755%27&outFields=NAME&f=geojson&outSR=4326&returnGeometry=true"
)
TIGER_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks"
    "/MapServer/0/query?where=STATE%3D%2755%27+AND+COUNTY%3D%27025%27"
    "&outFields=GEOID,NAME,INTPTLAT,INTPTLON&f=json&returnGeometry=false"
)

# Dane County approximate bounding box for TIGER places pre-filter
DANE_BBOX = (-89.9, 42.8, -88.8, 43.4)  # (min_lon, min_lat, max_lon, max_lat)


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())


def polygon_rings(geometry: dict) -> list[list[tuple]]:
    """Exterior rings as (lon, lat) tuples for Polygon and MultiPolygon."""
    if geometry["type"] == "Polygon":
        return [[(c[0], c[1]) for c in geometry["coordinates"][0]]]
    elif geometry["type"] == "MultiPolygon":
        return [[(c[0], c[1]) for c in part[0]] for part in geometry["coordinates"]]
    return []


def point_in_polygon(px: float, py: float, ring: list[tuple]) -> bool:
    """Ray-casting even-odd test."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def ring_centroid(ring: list[tuple]) -> tuple[float, float]:
    """Simple mean centroid of a ring — used for bbox pre-filtering only."""
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    return sum(lons) / len(lons), sum(lats) / len(lats)


def in_dane_bbox(geometry: dict) -> bool:
    """Quick bbox check: does the polygon's centroid fall within Dane County bbox?"""
    rings = polygon_rings(geometry)
    if not rings:
        return False
    cx, cy = ring_centroid(rings[0])
    min_lon, min_lat, max_lon, max_lat = DANE_BBOX
    return min_lon <= cx <= max_lon and min_lat <= cy <= max_lat


def pip_search(lon: float, lat: float, features: list[dict], label_fn) -> str | None:
    """Run PiP against a list of GeoJSON features; return label_fn(feature) or None."""
    for feat in features:
        for ring in polygon_rings(feat["geometry"]):
            if point_in_polygon(lon, lat, ring):
                return label_fn(feat)
    return None


def clean_place_name(name: str) -> str:
    """Strip trailing city/village/town/township/CDP from TIGER place names."""
    return re.sub(r"\s+(city|village|town|township|CDP)$", "", name, flags=re.I).strip()


def main():
    # ── Pass 1: Madison Neighborhood Associations ─────────────────────────────
    print("Fetching Madison Neighborhood Association polygons...")
    nb_data = fetch_json(NEIGHBORHOOD_URL)
    nb_features = nb_data["features"]
    print(f"  {len(nb_features)} polygons")

    # ── Pass 2: Madison Aldermanic Districts ──────────────────────────────────
    print("Fetching Madison Aldermanic District polygons...")
    ald_data = fetch_json(ALDERMANIC_URL)
    ald_features = ald_data["features"]
    print(f"  {len(ald_features)} polygons")

    # ── Pass 3: TIGER Places (Incorporated + CDPs), bbox-filtered ────────────
    print("Fetching TIGER Incorporated Places for Wisconsin...")
    inc_data = fetch_json(TIGER_PLACES_URL_TMPL.format(layer=18))
    inc_features = [f for f in inc_data["features"] if in_dane_bbox(f["geometry"])]
    print(f"  {len(inc_features)} features within Dane County bbox")

    print("Fetching TIGER Census Designated Places for Wisconsin...")
    cdp_data = fetch_json(TIGER_PLACES_URL_TMPL.format(layer=19))
    cdp_features = [f for f in cdp_data["features"] if in_dane_bbox(f["geometry"])]
    print(f"  {len(cdp_features)} features within Dane County bbox")

    place_features = inc_features + cdp_features

    # ── TIGER interior points for all Dane County tracts ─────────────────────
    print("Fetching TIGER interior points for Dane County tracts...")
    tiger = fetch_json(TIGER_URL)
    tract_points: dict[str, tuple[float, float]] = {}
    for feat in tiger["features"]:
        attr = feat["attributes"]
        geoid = attr["GEOID"]
        try:
            lat = float(attr["INTPTLAT"])
            lon = float(attr["INTPTLON"])
            tract_points[geoid] = (lon, lat)
        except (TypeError, ValueError):
            pass
    print(f"  {len(tract_points)} interior points parsed")

    # ── PiP cascade ───────────────────────────────────────────────────────────
    print("\nRunning point-in-polygon cascade...")
    mapping: dict[str, str] = {}
    counts = {"association": 0, "aldermanic": 0, "place": 0, "county": 0}

    for geoid, (lon, lat) in tract_points.items():
        # Pass 1: Neighborhood Association
        label = pip_search(
            lon, lat, nb_features,
            lambda f: f["properties"]["NEIGHB_NAME"].strip()
        )
        if label:
            mapping[geoid] = label
            counts["association"] += 1
            continue

        # Pass 2: Aldermanic District
        label = pip_search(
            lon, lat, ald_features,
            lambda f: f"Ald. District {f['properties']['ALD_DIST']}"
        )
        if label:
            mapping[geoid] = label
            counts["aldermanic"] += 1
            continue

        # Pass 3: TIGER Places
        label = pip_search(
            lon, lat, place_features,
            lambda f: clean_place_name(f["properties"]["NAME"])
        )
        if label:
            mapping[geoid] = label
            counts["place"] += 1
            continue

        # Pass 4: Dane County fallback
        mapping[geoid] = "Dane County"
        counts["county"] += 1

    print(f"  Neighborhood Association : {counts['association']}")
    print(f"  Aldermanic District      : {counts['aldermanic']}")
    print(f"  TIGER Place              : {counts['place']}")
    print(f"  Dane County fallback     : {counts['county']}")
    print(f"  Total mapped             : {sum(counts.values())}/{len(tract_points)}")

    print("\nSample mappings (first 15):")
    for geoid, label in sorted(mapping.items())[:15]:
        print(f"  {geoid} → {label}")

    # ── DB update ─────────────────────────────────────────────────────────────
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("ALTER TABLE census_tracts ADD COLUMN IF NOT EXISTS neighborhood TEXT;")
    cur.execute("UPDATE census_tracts SET neighborhood = NULL;")
    updated = 0
    for geoid, label in mapping.items():
        cur.execute(
            "UPDATE census_tracts SET neighborhood = %s WHERE geoid = %s",
            (label, geoid),
        )
        updated += cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"\nUpdated {updated} rows in census_tracts.neighborhood")
    print("Done.")


if __name__ == "__main__":
    main()
