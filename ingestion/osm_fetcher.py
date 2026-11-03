"""OSM Fetcher - Download pedestrian infrastructure from OpenStreetMap.

Uses Overpass API to fetch:
- Pedestrian ways (footway, pedestrian, path, steps)
- Buildings (with height/levels for shadow modeling)
- Trees (natural=tree for canopy shade)

Scope: Surabaya bounding box.
"""

import json
import os
import time
from datetime import datetime

import requests

from ingestion.config import OVERPASS_API_URLS, SURABAYA_BBOX, OSM_DIR


def _build_overpass_query(element_type: str) -> str:
    """Build Overpass QL query for Surabaya bbox."""
    bbox = f"{SURABAYA_BBOX['south']},{SURABAYA_BBOX['west']},{SURABAYA_BBOX['north']},{SURABAYA_BBOX['east']}"

    if element_type == "footways":
        # 2-category filter to capture all pedestrian-accessible roads:
        #
        # Category A — always included (dedicated pedestrian or safe local roads):
        #   footway, pedestrian, path, steps, living_street, residential,
        #   tertiary, secondary, unclassified, service
        #
        # Category B — included ONLY if tagged with a sidewalk:
        #   primary roads that have a physically mapped sidewalk in OSM
        #   (this catches Jl. Basuki Rahmat etc. where a trotoar exists)
        #
        # Explicitly EXCLUDED (high-speed / no pedestrian access):
        #   trunk, trunk_link  — bypass / arterial at speed (e.g. Ahmad Yani bypass)
        #   motorway, motorway_link — toll roads
        return f"""
        [out:json][timeout:180];
        (
          way["highway"~"footway|pedestrian|path|steps|living_street|residential|tertiary|secondary|unclassified|service"]({bbox});
          way["sidewalk"~"both|left|right|yes"]["highway"!~"motorway|motorway_link|trunk|trunk_link"]({bbox});
        );
        out body geom;
        """

    elif element_type == "buildings":
        return f"""
        [out:json][timeout:180];
        (
          way["building"]({bbox});
          relation["building"]({bbox});
        );
        out body geom;
        """
    elif element_type == "trees":
        return f"""
        [out:json][timeout:60];
        (
          node["natural"="tree"]({bbox});
        );
        out body;
        """
    else:
        raise ValueError(f"Unknown element type: {element_type}")


def _query_overpass(query: str) -> dict:
    """Execute Overpass API query, falling back across mirrors on failure.

    Tries every mirror, up to OVERPASS_RETRY_ROUNDS rounds (default 4), waiting
    longer between rounds since public mirrors are often briefly overloaded.
    """
    last_error = None
    rounds = int(os.getenv("OVERPASS_RETRY_ROUNDS", "4"))
    for attempt in range(rounds):
        if attempt:
            wait = 30 * attempt
            print(f"  All Overpass mirrors failed; retrying in {wait}s (round {attempt + 1}/{rounds})...")
            time.sleep(wait)
        result = _try_overpass_mirrors(query)
        if not isinstance(result, Exception):
            return result
        last_error = result
    raise RuntimeError(f"All Overpass mirrors failed; last error: {last_error}")


def _try_overpass_mirrors(query: str):
    """One pass over all mirrors. Returns parsed JSON, or the last exception."""
    last_error = None
    for url in OVERPASS_API_URLS:
        print(f"  Querying Overpass API ({url})...")
        try:
            response = requests.post(
                url,
                data={"data": query},
                headers={"User-Agent": "Teduh/1.0 (academic project)"},
                timeout=200,
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as e:
            print(f"    ✗ {url} failed: {e}")
            last_error = e
    return last_error


def _overpass_to_geojson_ways(data: dict, properties_extractor) -> dict:
    """Convert Overpass way elements to GeoJSON FeatureCollection."""
    features = []
    for element in data.get("elements", []):
        if element.get("type") != "way":
            continue
        geometry = element.get("geometry")
        if not geometry:
            continue

        coords = [[pt["lon"], pt["lat"]] for pt in geometry]
        if len(coords) < 2:
            continue

        feature = {
            "type": "Feature",
            "properties": properties_extractor(element),
            "geometry": {
                "type": "LineString",
                "coordinates": coords,
            },
        }
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}


def _overpass_to_geojson_polygons(data: dict, properties_extractor) -> dict:
    """Convert Overpass way/relation elements to GeoJSON Polygon FeatureCollection."""
    features = []
    for element in data.get("elements", []):
        geometry = element.get("geometry")
        if not geometry:
            continue

        coords = [[pt["lon"], pt["lat"]] for pt in geometry]
        if len(coords) < 4:
            continue

        # Close polygon if needed
        if coords[0] != coords[-1]:
            coords.append(coords[0])

        feature = {
            "type": "Feature",
            "properties": properties_extractor(element),
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords],
            },
        }
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}


def _overpass_to_geojson_points(data: dict, properties_extractor) -> dict:
    """Convert Overpass node elements to GeoJSON Point FeatureCollection."""
    features = []
    for element in data.get("elements", []):
        if element.get("type") != "node":
            continue

        feature = {
            "type": "Feature",
            "properties": properties_extractor(element),
            "geometry": {
                "type": "Point",
                "coordinates": [element["lon"], element["lat"]],
            },
        }
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}


def fetch_footways() -> str:
    """Fetch pedestrian ways and save as GeoJSON."""
    print("[OSM] Fetching pedestrian footways...")
    query = _build_overpass_query("footways")
    data = _query_overpass(query)

    def extract_props(el):
        tags = el.get("tags", {})
        return {
            "osm_id": el.get("id"),
            "highway": tags.get("highway", ""),
            "name": tags.get("name", ""),
            "surface": tags.get("surface", ""),
            "smoothness": tags.get("smoothness", ""),
            "sidewalk": tags.get("sidewalk", ""),
            "width": tags.get("width", ""),
        }

    geojson = _overpass_to_geojson_ways(data, extract_props)
    print(f"  Found {len(geojson['features'])} footway segments")

    os.makedirs(OSM_DIR, exist_ok=True)
    output_path = os.path.join(OSM_DIR, "footways.geojson")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f)

    return output_path


def fetch_buildings() -> str:
    """Fetch buildings and save as GeoJSON."""
    print("[OSM] Fetching buildings...")
    query = _build_overpass_query("buildings")
    data = _query_overpass(query)

    def extract_props(el):
        tags = el.get("tags", {})
        height = tags.get("height", "")
        levels = tags.get("building:levels", "")
        # Estimate height: 3.5m per level if no explicit height
        height_m = None
        if height:
            try:
                height_m = float(height.replace("m", "").strip())
            except ValueError:
                pass
        if height_m is None and levels:
            try:
                height_m = int(levels) * 3.5
            except ValueError:
                height_m = 10.0  # default assumption
        if height_m is None:
            height_m = 10.0

        return {
            "osm_id": el.get("id"),
            "height_m": height_m,
            "levels": int(levels) if levels.isdigit() else None,
            "building_type": tags.get("building", "yes"),
        }

    geojson = _overpass_to_geojson_polygons(data, extract_props)
    print(f"  Found {len(geojson['features'])} buildings")

    os.makedirs(OSM_DIR, exist_ok=True)
    output_path = os.path.join(OSM_DIR, "buildings.geojson")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f)

    return output_path


def fetch_trees() -> str:
    """Fetch tree nodes and save as GeoJSON."""
    print("[OSM] Fetching trees...")
    query = _build_overpass_query("trees")
    data = _query_overpass(query)

    def extract_props(el):
        tags = el.get("tags", {})
        return {
            "osm_id": el.get("id"),
            "height_m": float(tags.get("height", 8.0)),
            "crown_diameter": tags.get("diameter_crown", ""),
            "species": tags.get("species", tags.get("genus", "")),
        }

    geojson = _overpass_to_geojson_points(data, extract_props)
    print(f"  Found {len(geojson['features'])} trees")

    os.makedirs(OSM_DIR, exist_ok=True)
    output_path = os.path.join(OSM_DIR, "trees.geojson")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f)

    return output_path


def fetch_all():
    """Fetch all OSM data for Surabaya."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"=== OSM Fetch Started: {timestamp} ===")

    footways_path = fetch_footways()
    buildings_path = fetch_buildings()
    trees_path = fetch_trees()

    print(f"\n=== OSM Fetch Complete ===")
    print(f"  Footways: {footways_path}")
    print(f"  Buildings: {buildings_path}")
    print(f"  Trees: {trees_path}")

    return {
        "footways": footways_path,
        "buildings": buildings_path,
        "trees": trees_path,
    }


if __name__ == "__main__":
    fetch_all()
