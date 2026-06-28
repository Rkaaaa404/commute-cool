"""OSM Loader - Parse fetched GeoJSON and insert into PostGIS.

Loads footways → segments table, buildings → buildings table, trees → trees table.
"""
from __future__ import annotations

import json
import os

from shapely.geometry import shape, mapping
from shapely.ops import linemerge
import psycopg2
from psycopg2.extras import execute_values

from ingestion.config import DATABASE_URL, OSM_DIR


def _get_connection():
    """Create psycopg2 connection."""
    return psycopg2.connect(DATABASE_URL)


def _parse_width(width_str: str) -> float | None:
    """Parse width string like '2.5' or '2.5 m' to float."""
    if not width_str:
        return None
    try:
        return float(width_str.replace("m", "").strip())
    except (ValueError, TypeError):
        return None


def load_footways(filepath: str = None):
    """Load footway GeoJSON into segments table."""
    if filepath is None:
        filepath = os.path.join(OSM_DIR, "footways.geojson")

    print(f"[Loader] Loading footways from {filepath}...")

    with open(filepath, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    conn = _get_connection()
    cur = conn.cursor()

    inserted = 0
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry")

        if not geom or geom["type"] != "LineString":
            continue

        coords = geom["coordinates"]
        if len(coords) < 2:
            continue

        # Calculate length using Shapely
        line = shape(geom)
        # Approximate length in meters (using haversine would be better, but
        # for Surabaya-scale this is acceptable with a degree-to-meter factor)
        length_m = line.length * 111320  # rough conversion at equator

        wkt = f"SRID=4326;LINESTRING({','.join(f'{c[0]} {c[1]}' for c in coords)})"

        cur.execute(
            """
            INSERT INTO segments (osm_way_id, name, geom, length_m, highway_type,
                                  surface_type, smoothness, sidewalk_width)
            VALUES (%s, %s, ST_GeomFromEWKT(%s), %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (
                props.get("osm_id"),
                props.get("name") or None,
                wkt,
                round(length_m, 2),
                props.get("highway") or None,
                props.get("surface") or None,
                props.get("smoothness") or None,
                _parse_width(props.get("width", "")),
            ),
        )
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"  Inserted {inserted} footway segments")
    return inserted


def load_buildings(filepath: str = None):
    """Load building GeoJSON into buildings table."""
    if filepath is None:
        filepath = os.path.join(OSM_DIR, "buildings.geojson")

    print(f"[Loader] Loading buildings from {filepath}...")

    with open(filepath, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    conn = _get_connection()
    cur = conn.cursor()

    inserted = 0
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry")

        if not geom or geom["type"] != "Polygon":
            continue

        coords = geom["coordinates"][0]  # outer ring
        if len(coords) < 4:
            continue

        ring_str = ",".join(f"{c[0]} {c[1]}" for c in coords)
        wkt = f"SRID=4326;POLYGON(({ring_str}))"

        cur.execute(
            """
            INSERT INTO buildings (osm_id, geom, height_m, levels)
            VALUES (%s, ST_GeomFromEWKT(%s), %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (
                props.get("osm_id"),
                wkt,
                props.get("height_m"),
                props.get("levels"),
            ),
        )
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"  Inserted {inserted} buildings")
    return inserted


def load_trees(filepath: str = None):
    """Load tree GeoJSON into trees table."""
    if filepath is None:
        filepath = os.path.join(OSM_DIR, "trees.geojson")

    print(f"[Loader] Loading trees from {filepath}...")

    with open(filepath, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    conn = _get_connection()
    cur = conn.cursor()

    inserted = 0
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry")

        if not geom or geom["type"] != "Point":
            continue

        lon, lat = geom["coordinates"][0], geom["coordinates"][1]
        wkt = f"SRID=4326;POINT({lon} {lat})"

        # Parse crown radius from diameter
        crown_radius = 4.0  # default
        crown_diam = props.get("crown_diameter", "")
        if crown_diam:
            try:
                crown_radius = float(crown_diam.replace("m", "").strip()) / 2.0
            except (ValueError, TypeError):
                pass

        height_m = props.get("height_m", 8.0)
        if isinstance(height_m, str):
            try:
                height_m = float(height_m)
            except (ValueError, TypeError):
                height_m = 8.0

        cur.execute(
            """
            INSERT INTO trees (osm_id, geom, height_m, crown_radius_m)
            VALUES (%s, ST_GeomFromEWKT(%s), %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (
                props.get("osm_id"),
                wkt,
                height_m,
                crown_radius,
            ),
        )
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"  Inserted {inserted} trees")
    return inserted


def load_all():
    """Load all OSM data into PostGIS.
    
    Clears existing tables first to prevent duplicate entries if the pipeline is re-run.
    """
    print("=== OSM Load to PostGIS Started ===")
    
    # Clean up existing data to prevent duplication
    conn = _get_connection()
    cur = conn.cursor()
    try:
        print("  Clearing existing computed tables and segments to prevent duplication...")
        cur.execute("UPDATE cctv_cameras SET nearest_segment = NULL;")
        cur.execute("DELETE FROM tcs_simulations;")
        cur.execute("DELETE FROM edge_weights;")
        cur.execute("DELETE FROM thermal_comfort_scores;")
        cur.execute("DELETE FROM segment_shadows;")
        cur.execute("DELETE FROM segment_raster_scores;")
        cur.execute("DELETE FROM segments;")
        cur.execute("DELETE FROM buildings;")
        cur.execute("DELETE FROM trees;")
        conn.commit()
        print("    ✓ Successfully cleared existing database tables.")
    except Exception as e:
        conn.rollback()
        print(f"    ✗ Failed to clear database: {e}")
    finally:
        cur.close()
        conn.close()

    segments = load_footways()
    buildings = load_buildings()
    trees = load_trees()
    print(f"\n=== OSM Load Complete ===")
    print(f"  Segments: {segments}, Buildings: {buildings}, Trees: {trees}")


if __name__ == "__main__":
    load_all()
