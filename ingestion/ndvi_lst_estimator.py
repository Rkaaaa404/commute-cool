"""NDVI & LST Estimator - Proxy estimation without satellite imagery.

Instead of requiring Google Earth Engine or Copernicus downloads,
this module estimates NDVI and LST per street segment using:
- NDVI proxy: Tree density within buffer of each segment (from OSM data in PostGIS)
- LST proxy: Open-Meteo surface temperature + material correction factors

Rationale:
- Tree density correlates highly with NDVI (r > 0.7 in urban studies)
- Surface material (asphalt vs grass vs concrete) strongly affects surface temp
- This approach is validated in urban microclimate literature

For production deployment, this module would be replaced by actual
Sentinel-2 NDVI and Landsat-8 LST processing via GEE or Copernicus.
"""

import json
import os
from datetime import datetime

import psycopg2
import requests

from ingestion.config import (
    DATABASE_URL,
    OPEN_METEO_BASE_URL,
    SURABAYA_LAT,
    SURABAYA_LNG,
)


# Surface temperature correction factors (relative to air temperature)
# Based on urban microclimate studies in tropical cities
SURFACE_TEMP_CORRECTION = {
    "asphalt": +8.0,      # Asphalt absorbs much more heat
    "concrete": +6.0,
    "concrete:plates": +5.5,
    "paving_stones": +4.0,
    "sett": +4.0,
    "compacted": +3.0,
    "gravel": +2.0,
    "fine_gravel": +2.0,
    "ground": +1.0,
    "dirt": +1.0,
    "grass": -2.0,        # Grass is cooler than air temp via evapotranspiration
    "sand": +5.0,
    "unpaved": +2.0,
}

# NDVI estimation from tree density
# 0 trees nearby = NDVI ~0.1 (bare urban), 10+ trees = NDVI ~0.7 (dense canopy)
MAX_TREES_FOR_MAX_NDVI = 10
NDVI_MIN = 0.10  # Bare urban surface
NDVI_MAX = 0.72  # Dense urban canopy


def get_current_air_temperature() -> float:
    """Fetch current air temperature from Open-Meteo."""
    try:
        params = {
            "latitude": SURABAYA_LAT,
            "longitude": SURABAYA_LNG,
            "current": "temperature_2m",
            "timezone": "Asia/Jakarta",
        }
        response = requests.get(OPEN_METEO_BASE_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data["current"]["temperature_2m"]
    except Exception as e:
        print(f"  [Warning] Could not fetch temperature: {e}. Using default 32C.")
        return 32.0


def estimate_ndvi_per_segment():
    """Estimate NDVI for each segment based on nearby tree count.

    NDVI proxy formula:
        ndvi = NDVI_MIN + (tree_count / MAX_TREES) * (NDVI_MAX - NDVI_MIN)

    Trees are counted within a 30m buffer of each segment.
    """
    print("[NDVI Estimator] Computing tree-density NDVI proxy per segment...")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Count trees within ~30m of each segment
    # 0.0003 degrees ≈ 33m at Surabaya latitude
    cur.execute("""
        SELECT
            s.segment_id,
            COUNT(t.tree_id) as tree_count
        FROM segments s
        LEFT JOIN trees t ON ST_DWithin(s.geom, t.geom, 0.0003)
        GROUP BY s.segment_id
    """)

    results = cur.fetchall()
    print(f"  Processing {len(results)} segments...")

    # Insert/update NDVI estimates
    inserted = 0
    today = datetime.now().date()

    for segment_id, tree_count in results:
        # Calculate proxy NDVI
        tree_count = tree_count or 0
        ratio = min(tree_count / MAX_TREES_FOR_MAX_NDVI, 1.0)
        ndvi = NDVI_MIN + ratio * (NDVI_MAX - NDVI_MIN)

        cur.execute("""
            INSERT INTO segment_raster_scores (segment_id, avg_ndvi, avg_lst, computed_at)
            VALUES (%s, %s, NULL, %s)
            ON CONFLICT (segment_id, computed_at)
            DO UPDATE SET avg_ndvi = EXCLUDED.avg_ndvi
        """, (segment_id, round(ndvi, 4), today))
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"  Estimated NDVI for {inserted} segments")
    return inserted


def estimate_lst_per_segment():
    """Estimate Land Surface Temperature per segment.

    LST proxy formula:
        lst = air_temperature + surface_correction[material]

    Surface correction based on known urban material thermal properties.
    """
    print("[LST Estimator] Computing surface temperature proxy per segment...")

    air_temp = get_current_air_temperature()
    print(f"  Current air temperature: {air_temp}C")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Get all segments with surface type
    cur.execute("""
        SELECT segment_id, surface_type
        FROM segments
    """)

    results = cur.fetchall()
    print(f"  Processing {len(results)} segments...")

    today = datetime.now().date()
    updated = 0

    for segment_id, surface_type in results:
        # Calculate LST estimate
        correction = SURFACE_TEMP_CORRECTION.get(surface_type, +4.0)  # default: moderate heat
        lst = air_temp + correction

        # Also factor in shade (segments with trees are cooler)
        # This will be refined by shadow model, but gives initial estimate
        cur.execute("""
            UPDATE segment_raster_scores
            SET avg_lst = %s
            WHERE segment_id = %s AND computed_at = %s
        """, (round(lst, 2), segment_id, today))

        if cur.rowcount == 0:
            # Row doesn't exist yet (segment had no trees nearby)
            cur.execute("""
                INSERT INTO segment_raster_scores (segment_id, avg_ndvi, avg_lst, computed_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (segment_id, computed_at)
                DO UPDATE SET avg_lst = EXCLUDED.avg_lst
            """, (segment_id, NDVI_MIN, round(lst, 2), today))

        updated += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"  Estimated LST for {updated} segments")
    return updated


def estimate_all():
    """Run both NDVI and LST estimation."""
    print("=== NDVI/LST Estimation Started ===")
    print("  (Using OSM tree density + Open-Meteo temperature as proxy)")
    print()

    ndvi_count = estimate_ndvi_per_segment()
    lst_count = estimate_lst_per_segment()

    print()
    print("=== NDVI/LST Estimation Complete ===")
    print(f"  NDVI segments: {ndvi_count}")
    print(f"  LST segments: {lst_count}")


if __name__ == "__main__":
    estimate_all()
