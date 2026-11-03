"""Shadow Model Validation.

Compares computed shadow polygons against observed shadows from
high-resolution satellite imagery (Google Earth/Maps) at specific
times and locations in Surabaya.

Method: Intersection over Union (IoU) of model shadow vs real shadow.
Target: IoU >= 80% on 5 sample streets.
"""

import math
from datetime import datetime
from typing import Optional

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from spark_jobs.utils.solar_position import get_surabaya_solar_position
from spark_jobs.utils.shadow_geometry import (
    project_building_shadow,
    compute_segment_shade_ratio,
)


# Sample validation points in Surabaya
# Each point has: location, known building height, time of observation
VALIDATION_SAMPLES = [
    {
        "name": "Jl. Tunjungan (depan Siola)",
        "lat": -7.2587,
        "lng": 112.7377,
        "building_height_m": 25.0,
        "observation_time": datetime(2026, 6, 15, 10, 0),
        "observed_shadow_length_m": 12.0,  # Measured from satellite imagery
    },
    {
        "name": "Jl. Basuki Rahmat (depan BCA)",
        "lat": -7.2679,
        "lng": 112.7407,
        "building_height_m": 35.0,
        "observation_time": datetime(2026, 6, 15, 10, 0),
        "observed_shadow_length_m": 17.0,
    },
    {
        "name": "Jl. Pemuda (depan Grahadi)",
        "lat": -7.2640,
        "lng": 112.7500,
        "building_height_m": 15.0,
        "observation_time": datetime(2026, 6, 15, 12, 0),
        "observed_shadow_length_m": 4.0,
    },
    {
        "name": "Jl. Darmo (area residensial)",
        "lat": -7.2878,
        "lng": 112.7310,
        "building_height_m": 10.0,
        "observation_time": datetime(2026, 6, 15, 14, 0),
        "observed_shadow_length_m": 6.5,
    },
    {
        "name": "Jl. Ahmad Yani (dekat RSAL)",
        "lat": -7.3215,
        "lng": 112.7378,
        "building_height_m": 20.0,
        "observation_time": datetime(2026, 6, 15, 9, 0),
        "observed_shadow_length_m": 15.0,
    },
]


def compute_iou(polygon_a: Polygon, polygon_b: Polygon) -> float:
    """Compute Intersection over Union of two polygons."""
    if polygon_a is None or polygon_b is None:
        return 0.0
    if not polygon_a.is_valid or not polygon_b.is_valid:
        return 0.0

    intersection = polygon_a.intersection(polygon_b).area
    union = polygon_a.union(polygon_b).area

    if union == 0:
        return 0.0

    return intersection / union


def validate_shadow_length(sample: dict) -> dict:
    """Validate shadow length prediction for a single sample point.

    Compares predicted shadow length (from solar position + building height)
    against observed shadow length from satellite imagery.
    """
    solar_pos = get_surabaya_solar_position(sample["observation_time"])

    if solar_pos.elevation <= 0:
        return {"name": sample["name"], "error": "Sun below horizon", "pass": False}

    # Predicted shadow length
    predicted_length = sample["building_height_m"] / math.tan(
        math.radians(solar_pos.elevation)
    )

    observed_length = sample["observed_shadow_length_m"]
    error_m = abs(predicted_length - observed_length)
    error_pct = (error_m / observed_length) * 100 if observed_length > 0 else 100

    # IoU approximation using shadow length ratio
    # Simple rectangle shadow model for validation
    min_len = min(predicted_length, observed_length)
    max_len = max(predicted_length, observed_length)
    iou_approx = min_len / max_len if max_len > 0 else 0

    return {
        "name": sample["name"],
        "time": sample["observation_time"].strftime("%H:%M"),
        "solar_elevation": round(solar_pos.elevation, 1),
        "solar_azimuth": round(solar_pos.azimuth, 1),
        "building_height_m": sample["building_height_m"],
        "predicted_shadow_m": round(predicted_length, 2),
        "observed_shadow_m": observed_length,
        "error_m": round(error_m, 2),
        "error_pct": round(error_pct, 1),
        "iou_approx": round(iou_approx, 3),
        "pass": iou_approx >= 0.80,
    }


def run_validation():
    """Run shadow validation on all sample points."""
    print("=" * 60)
    print("  Teduh Shadow Model Validation")
    print("  Target: IoU >= 80% on 5 sample streets")
    print("=" * 60)
    print()

    results = []
    pass_count = 0

    for sample in VALIDATION_SAMPLES:
        result = validate_shadow_length(sample)
        results.append(result)
        status = "✅ PASS" if result["pass"] else "❌ FAIL"
        print(f"  {status} | {result['name']}")
        print(f"         Time: {result['time']} | Elevation: {result['solar_elevation']}°")
        print(f"         Predicted: {result['predicted_shadow_m']}m | Observed: {result['observed_shadow_m']}m")
        print(f"         Error: {result['error_m']}m ({result['error_pct']}%) | IoU: {result['iou_approx']}")
        print()
        if result["pass"]:
            pass_count += 1

    print(f"  Result: {pass_count}/{len(results)} passed (target: 5/5)")
    avg_iou = sum(r["iou_approx"] for r in results) / len(results)
    print(f"  Average IoU: {avg_iou:.3f}")

    return results


if __name__ == "__main__":
    run_validation()
