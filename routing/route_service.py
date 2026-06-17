"""Route Service - Main routing orchestrator.

Integrates GraphHopper custom-weighted routing with heat budget validation.
Produces two route options: shortest and most comfortable.
"""

import os
from typing import Optional

import httpx

from routing.heat_exposure import calculate_heat_exposure
from routing.personal_budget import check_heat_budget

GRAPHHOPPER_URL = os.getenv("GRAPHHOPPER_URL", "http://localhost:8989")


async def calculate_routes(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    heat_tolerance: str = "medium",
    departure_hour: int = 12,
) -> dict:
    """Calculate both shortest and most comfortable routes.

    Args:
        origin_lat, origin_lng: Start point coordinates.
        dest_lat, dest_lng: End point coordinates.
        heat_tolerance: User's heat tolerance (low/medium/high).
        departure_hour: Hour of departure (for shadow calculation).

    Returns:
        Dict with 'shortest' and 'comfortable' route details.
    """
    # Route 1: Shortest (standard GraphHopper, no thermal penalty)
    shortest = await _query_graphhopper(
        origin_lat, origin_lng, dest_lat, dest_lng,
        profile="foot",
        custom_model=None,
    )

    # Route 2: Most Comfortable (with thermal penalty weighting)
    comfortable = await _query_graphhopper(
        origin_lat, origin_lng, dest_lat, dest_lng,
        profile="foot",
        custom_model="thermal_comfort",
    )

    # Calculate heat exposure for both routes
    if shortest:
        shortest["heat_exposure"] = calculate_heat_exposure(
            shortest.get("segments", []), departure_hour
        )
        shortest["heat_budget"] = check_heat_budget(
            shortest["heat_exposure"]["total_sun_minutes"],
            heat_tolerance,
        )

    if comfortable:
        comfortable["heat_exposure"] = calculate_heat_exposure(
            comfortable.get("segments", []), departure_hour
        )
        comfortable["heat_budget"] = check_heat_budget(
            comfortable["heat_exposure"]["total_sun_minutes"],
            heat_tolerance,
        )

    return {
        "shortest": shortest,
        "comfortable": comfortable,
    }


async def _query_graphhopper(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    profile: str = "foot",
    custom_model: Optional[str] = None,
) -> Optional[dict]:
    """Query GraphHopper routing engine.

    Args:
        custom_model: If set, uses custom thermal weighting model.

    Returns:
        Route dict with distance, duration, geometry, and segments.
    """
    params = {
        "point": [f"{origin_lat},{origin_lng}", f"{dest_lat},{dest_lng}"],
        "profile": profile,
        "points_encoded": "false",  # Get full GeoJSON coordinates
        "details": ["street_name", "distance", "time"],
    }

    if custom_model:
        params["ch.disable"] = "true"
        # Custom model JSON for thermal weighting
        params["custom_model"] = _get_thermal_model()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{GRAPHHOPPER_URL}/route", params=params)
            response.raise_for_status()
            data = response.json()

        if "paths" not in data or not data["paths"]:
            return None

        path = data["paths"][0]
        return {
            "distance_m": path.get("distance", 0),
            "duration_ms": path.get("time", 0),
            "geometry": path.get("points", {}),
            "segments": [],  # TODO: map to our segment IDs
        }

    except (httpx.HTTPError, Exception) as e:
        print(f"[Routing] GraphHopper error: {e}")
        return None


def _get_thermal_model() -> dict:
    """Get custom model JSON for thermal-weighted routing."""
    return {
        "priority": [
            {
                "if": "thermal_comfort < 0.3",
                "multiply_by": "0.3",  # Strongly avoid hot segments
            },
            {
                "if": "thermal_comfort < 0.5",
                "multiply_by": "0.6",  # Moderately avoid
            },
            {
                "if": "thermal_comfort >= 0.7",
                "multiply_by": "1.0",  # Prefer comfortable segments
            },
        ],
    }
