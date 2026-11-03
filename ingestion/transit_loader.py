"""Transit Loader - Load transit stop data into PostGIS.

Sources:
- database/seed_transit.sql (manual curated data)
- OSM Overpass query for public_transport stops
"""
from __future__ import annotations

import json
import os

import psycopg2

from ingestion.config import DATABASE_URL, SURABAYA_BBOX, TRANSIT_DIR
from ingestion.osm_fetcher import _query_overpass


def load_from_seed_sql():
    """Execute the seed SQL file directly."""
    seed_file = os.path.join(os.path.dirname(__file__), "..", "database", "seed_transit.sql")
    seed_file = os.path.abspath(seed_file)

    if not os.path.exists(seed_file):
        print(f"[Transit] Seed file not found: {seed_file}")
        return 0

    print(f"[Transit] Loading from seed SQL: {seed_file}")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    with open(seed_file, "r", encoding="utf-8") as f:
        sql = f.read()

    cur.execute(sql)
    conn.commit()

    cur.execute("SELECT count(*) FROM transit_stops")
    count = cur.fetchone()[0]

    cur.close()
    conn.close()
    print(f"  Total transit stops in DB: {count}")
    return count


def fetch_osm_transit_stops() -> list[dict]:
    """Fetch transit stops from OSM via Overpass API."""
    bbox = f"{SURABAYA_BBOX['south']},{SURABAYA_BBOX['west']},{SURABAYA_BBOX['north']},{SURABAYA_BBOX['east']}"

    query = f"""
    [out:json][timeout:60];
    (
      node["highway"="bus_stop"]({bbox});
      node["public_transport"="stop_position"]({bbox});
      node["public_transport"="platform"]({bbox});
      node["railway"="station"]({bbox});
      node["railway"="halt"]({bbox});
    );
    out body;
    """

    print("[Transit] Fetching transit stops from OSM...")
    data = _query_overpass(query)

    stops = []
    for el in data.get("elements", []):
        if el.get("type") != "node":
            continue
        tags = el.get("tags", {})
        stops.append({
            "osm_id": el["id"],
            "name": tags.get("name", "Unknown"),
            "lat": el["lat"],
            "lng": el["lon"],
            "stop_type": _classify_stop(tags),
            "operator": tags.get("operator", ""),
            "route": tags.get("route_ref", tags.get("ref", "")),
        })

    print(f"  Found {len(stops)} transit stops from OSM")

    # Save raw
    os.makedirs(TRANSIT_DIR, exist_ok=True)
    output_path = os.path.join(TRANSIT_DIR, "osm_transit_stops.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(stops, f, indent=2, ensure_ascii=False)

    return stops


def _classify_stop(tags: dict) -> str:
    """Classify stop type from OSM tags."""
    if tags.get("railway") in ("station", "halt"):
        return "train_station"
    if tags.get("highway") == "bus_stop":
        return "bus_stop"
    if tags.get("public_transport") in ("stop_position", "platform"):
        return "bus_stop"
    return "bus_stop"


def load_osm_transit_to_db(stops: list[dict]) -> int:
    """Insert OSM transit stops into PostGIS."""
    if not stops:
        return 0

    print(f"[Transit] Loading {len(stops)} OSM stops to PostGIS...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    inserted = 0
    for stop in stops:
        wkt = f"SRID=4326;POINT({stop['lng']} {stop['lat']})"
        cur.execute(
            """
            INSERT INTO transit_stops (name, geom, stop_type, operator, route_name)
            VALUES (%s, ST_GeomFromEWKT(%s), %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (
                stop["name"],
                wkt,
                stop["stop_type"],
                stop.get("operator") or None,
                stop.get("route") or None,
            ),
        )
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"  Inserted {inserted} stops")
    return inserted


def load_all():
    """Load transit data from both seed SQL and OSM."""
    print("=== Transit Load Started ===")
    seed_count = load_from_seed_sql()
    osm_stops = fetch_osm_transit_stops()
    osm_count = load_osm_transit_to_db(osm_stops)
    print(f"\n=== Transit Load Complete (seed: {seed_count}, OSM: {osm_count}) ===")


if __name__ == "__main__":
    load_all()
