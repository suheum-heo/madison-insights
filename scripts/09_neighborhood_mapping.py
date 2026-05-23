"""
Map each census tract to a Madison Neighborhood Association name.

Uses TIGER's INTPTLAT/INTPTLON (Census-provided interior points, guaranteed
on land — avoids lake-boundary centroid errors), then does point-in-polygon
against Madison Neighborhood Association polygons.

Adds a `neighborhood` column to the census_tracts table.
No external GIS libraries needed — pure-Python ray casting.

Run: .venv/bin/python3 scripts/09_neighborhood_mapping.py
"""

import json
import urllib.request
import psycopg2

DB_URL = "dbname=madison_analysis"

NEIGHBORHOOD_URL = (
    "https://maps.cityofmadison.com/arcgis/rest/services/Public/OPEN_DATA/MapServer/12"
    "/query?where=1%3D1&outFields=NEIGHB_NAME&f=geojson&outSR=4326&returnGeometry=true"
)
# Request INTPTLAT/INTPTLON — Census interior points, not geometry centroids
TIGER_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks"
    "/MapServer/0/query?where=STATE%3D%2755%27+AND+COUNTY%3D%27025%27"
    "&outFields=GEOID,NAME,INTPTLAT,INTPTLON&f=json&returnGeometry=false"
)


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


def find_neighborhood(lon: float, lat: float, neighborhoods: list[dict]) -> str | None:
    for nb in neighborhoods:
        for ring in polygon_rings(nb["geometry"]):
            if point_in_polygon(lon, lat, ring):
                return nb["properties"]["NEIGHB_NAME"].strip()
    return None


def main():
    print("Fetching Madison Neighborhood Association polygons...")
    nb_data = fetch_json(NEIGHBORHOOD_URL)
    neighborhoods = nb_data["features"]
    print(f"  {len(neighborhoods)} neighborhood polygons loaded")

    print("Fetching TIGER interior points for Dane County tracts...")
    tiger = fetch_json(TIGER_URL)
    tracts = tiger["features"]
    print(f"  {len(tracts)} tract interior points loaded")

    # Parse interior points from TIGER attributes
    tract_points: dict[str, tuple[float, float]] = {}
    for feat in tracts:
        attr = feat["attributes"]
        geoid = attr["GEOID"]
        try:
            lat = float(attr["INTPTLAT"])
            lon = float(attr["INTPTLON"])
            tract_points[geoid] = (lon, lat)
        except (TypeError, ValueError):
            pass

    print(f"  {len(tract_points)} interior points parsed")

    print("Running point-in-polygon mapping...")
    mapping: dict[str, str | None] = {}
    for geoid, (lon, lat) in tract_points.items():
        mapping[geoid] = find_neighborhood(lon, lat, neighborhoods)

    matched = sum(1 for v in mapping.values() if v is not None)
    print(f"  Matched: {matched}/{len(mapping)} tracts")
    print(f"  Unmatched (no association coverage): {len(mapping) - matched}")

    print("\nSample mappings:")
    for geoid, nb in sorted(mapping.items())[:10]:
        print(f"  {geoid} → {nb or '(no match)'}")

    # Reset all neighborhood values, then apply new mapping
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("ALTER TABLE census_tracts ADD COLUMN IF NOT EXISTS neighborhood TEXT;")
    cur.execute("UPDATE census_tracts SET neighborhood = NULL;")
    updated = 0
    for geoid, nb_name in mapping.items():
        cur.execute(
            "UPDATE census_tracts SET neighborhood = %s WHERE geoid = %s",
            (nb_name, geoid),
        )
        updated += cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    print(f"\nUpdated {updated} rows in census_tracts.neighborhood")
    print("Done.")


if __name__ == "__main__":
    main()
