"""
Map each census tract centroid to a Madison Neighborhood Association name.

Adds a `neighborhood` column to the census_tracts table.
No external GIS libraries needed — uses pure-Python ray casting.

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
TIGER_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks"
    "/MapServer/0/query?where=STATE%3D%2755%27+AND+COUNTY%3D%27025%27"
    "&outFields=GEOID,NAME&f=geojson&returnGeometry=true"
)


def fetch_geojson(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())


def polygon_rings(geometry: dict) -> list[list[tuple]]:
    """Return exterior rings as list of (lon, lat) tuples, handling Polygon and MultiPolygon."""
    if geometry["type"] == "Polygon":
        return [[(c[0], c[1]) for c in geometry["coordinates"][0]]]
    elif geometry["type"] == "MultiPolygon":
        return [[(c[0], c[1]) for c in part[0]] for part in geometry["coordinates"]]
    return []


def centroid(ring: list[tuple]) -> tuple[float, float]:
    """Geometric centroid of a polygon ring via the shoelace formula."""
    n = len(ring)
    area = 0.0
    cx = 0.0
    cy = 0.0
    for i in range(n):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    area *= 0.5
    if abs(area) < 1e-12:
        # Degenerate — fall back to vertex mean
        return (sum(p[0] for p in ring) / n, sum(p[1] for p in ring) / n)
    cx /= (6 * area)
    cy /= (6 * area)
    return cx, cy


def point_in_polygon(px: float, py: float, ring: list[tuple]) -> bool:
    """Ray-casting point-in-polygon test."""
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
    """Return the first neighborhood whose polygon contains (lon, lat)."""
    for nb in neighborhoods:
        for ring in polygon_rings(nb["geometry"]):
            if point_in_polygon(lon, lat, ring):
                return nb["properties"]["NEIGHB_NAME"].strip()
    return None


def main():
    print("Fetching Madison Neighborhood Association polygons...")
    nb_data = fetch_geojson(NEIGHBORHOOD_URL)
    neighborhoods = nb_data["features"]
    print(f"  {len(neighborhoods)} neighborhood polygons loaded")

    print("Fetching TIGER census tract polygons for Dane County...")
    tract_data = fetch_geojson(TIGER_URL)
    tracts = tract_data["features"]
    print(f"  {len(tracts)} tract polygons loaded")

    # Build centroid for each TIGER tract
    tract_centroids: dict[str, tuple[float, float]] = {}
    for feat in tracts:
        geoid = feat["properties"]["GEOID"]
        rings = polygon_rings(feat["geometry"])
        if rings:
            lon, lat = centroid(rings[0])
            tract_centroids[geoid] = (lon, lat)

    print("Running point-in-polygon mapping...")
    mapping: dict[str, str | None] = {}
    for geoid, (lon, lat) in tract_centroids.items():
        mapping[geoid] = find_neighborhood(lon, lat, neighborhoods)

    matched = sum(1 for v in mapping.values() if v is not None)
    print(f"  Matched: {matched}/{len(mapping)} tracts")
    print(f"  Unmatched (suburban fringe): {len(mapping) - matched}")

    # Sample output
    print("\nSample mappings:")
    for geoid, nb in sorted(mapping.items())[:10]:
        print(f"  {geoid} → {nb or '(no match)'}")

    # Apply to DB
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("ALTER TABLE census_tracts ADD COLUMN IF NOT EXISTS neighborhood TEXT;")
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
