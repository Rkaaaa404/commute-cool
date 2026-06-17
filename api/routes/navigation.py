"""Navigation API routes - Route calculation with real PostGIS data."""
from __future__ import annotations

import json
from fastapi import APIRouter, HTTPException

from api.models.schemas import RouteRequest, RouteResponse, ThermalSegment
from api.db import get_conn

router = APIRouter()


@router.post("/route", response_model=RouteResponse)
async def calculate_route(request: RouteRequest):
    """Calculate shortest and most comfortable routes using PostGIS data.

    Uses pgRouting-style greedy walk: start from origin, greedily pick
    the next connected/nearest segment heading toward destination.
    """
    for point, label in [(request.origin, "origin"), (request.destination, "destination")]:
        if not (-7.35 <= point.lat <= -7.20 and 112.60 <= point.lng <= 112.85):
            raise HTTPException(
                status_code=400,
                detail=f"{label} coordinates are outside Surabaya area"
            )

    heat_tolerance = "medium"
    budget_limit = 15.0
    if request.user_profile:
        heat_tolerance = request.user_profile.heat_tolerance
        budget_limit = {"low": 8.0, "medium": 15.0, "high": 25.0}.get(heat_tolerance, 15.0)

    origin_lng, origin_lat = request.origin.lng, request.origin.lat
    dest_lng, dest_lat = request.destination.lng, request.destination.lat

    async with get_conn() as conn:
        # Build a proper ordered route using greedy nearest-segment walking
        # Strategy: find segments ordered by distance from the straight line,
        # then chain them by endpoint proximity (greedy path construction)

        # Expand search area to find more candidate segments
        min_lng = min(origin_lng, dest_lng) - 0.008
        max_lng = max(origin_lng, dest_lng) + 0.008
        min_lat = min(origin_lat, dest_lat) - 0.008
        max_lat = max(origin_lat, dest_lat) + 0.008

        # Get candidate segments with their actual line geometries
        rows = await conn.fetch("""
            SELECT
                s.segment_id,
                s.length_m,
                s.surface_type,
                COALESCE(tcs.tcs_value, 0.5) as tcs_value,
                COALESCE(tcs.shade_ratio, 0.2) as shade_ratio,
                COALESCE(tcs.apparent_temp, 34.0) as apparent_temp,
                COALESCE(ew.total_cost, COALESCE(s.length_m, 50) * 1.5) as total_cost,
                ST_AsGeoJSON(s.geom) as geom_json,
                ST_X(ST_StartPoint(s.geom)) as start_lng,
                ST_Y(ST_StartPoint(s.geom)) as start_lat,
                ST_X(ST_EndPoint(s.geom)) as end_lng,
                ST_Y(ST_EndPoint(s.geom)) as end_lat,
                ST_Distance(
                    s.geom::geography,
                    ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography
                ) as dist_from_origin,
                ST_Distance(
                    s.geom::geography,
                    ST_SetSRID(ST_MakePoint($3, $4), 4326)::geography
                ) as dist_from_dest
            FROM segments s
            LEFT JOIN LATERAL (
                SELECT tcs_value, shade_ratio, apparent_temp
                FROM thermal_comfort_scores
                WHERE segment_id = s.segment_id
                ORDER BY computed_at DESC LIMIT 1
            ) tcs ON true
            LEFT JOIN LATERAL (
                SELECT total_cost
                FROM edge_weights
                WHERE segment_id = s.segment_id
                ORDER BY valid_from DESC LIMIT 1
            ) ew ON true
            WHERE s.geom && ST_MakeEnvelope($5, $6, $7, $8, 4326)
            ORDER BY dist_from_origin ASC
            LIMIT 150
        """, origin_lng, origin_lat, dest_lng, dest_lat,
             min_lng, min_lat, max_lng, max_lat)

        if not rows:
            return _empty_response(budget_limit)

        # Build segments list with endpoint info
        candidates = []
        for row in rows:
            candidates.append({
                "segment_id": row["segment_id"],
                "length_m": row["length_m"] or 50.0,
                "surface_type": row["surface_type"],
                "tcs_value": row["tcs_value"],
                "shade_ratio": row["shade_ratio"],
                "apparent_temp": row["apparent_temp"],
                "total_cost": row["total_cost"],
                "geom": row["geom_json"],
                "start_lng": row["start_lng"],
                "start_lat": row["start_lat"],
                "end_lng": row["end_lng"],
                "end_lat": row["end_lat"],
                "dist_from_origin": row["dist_from_origin"],
                "dist_from_dest": row["dist_from_dest"],
            })

        # Greedy path: shortest route (minimize distance)
        shortest_path = _greedy_path(
            candidates, origin_lng, origin_lat, dest_lng, dest_lat,
            cost_key="length_m", max_segments=20
        )

        # Greedy path: comfortable route (minimize thermal penalty)
        comfortable_path = _greedy_path(
            candidates, origin_lng, origin_lat, dest_lng, dest_lat,
            cost_key="total_cost", max_segments=20, prefer_tcs=True
        )

        shortest_route = _build_route(shortest_path, "shortest", budget_limit)
        comfortable_route = _build_route(comfortable_path, "most_comfortable", budget_limit)

    return RouteResponse(
        routes=[shortest_route, comfortable_route],
        weather_alert=None,
        heat_budget={
            "budget_limit_min": budget_limit,
            "recommended_route": "most_comfortable",
        },
    )


def _greedy_path(
    candidates: list[dict],
    origin_lng: float, origin_lat: float,
    dest_lng: float, dest_lat: float,
    cost_key: str = "length_m",
    max_segments: int = 20,
    prefer_tcs: bool = False,
) -> list[dict]:
    """Build an ordered path by greedily picking nearest connected segments.

    Starts from the segment nearest to origin, then at each step picks
    the nearest unvisited segment whose start/end is close to the current
    position, while making progress toward destination.
    """
    if not candidates:
        return []

    def _dist(lng1, lat1, lng2, lat2):
        """Approximate distance in degrees (good enough for ordering)."""
        return ((lng1 - lng2) ** 2 + (lat1 - lat2) ** 2) ** 0.5

    # Start from the segment closest to origin
    current_lng, current_lat = origin_lng, origin_lat
    used = set()
    path = []

    for _ in range(max_segments):
        # Check if we're close enough to destination
        if _dist(current_lng, current_lat, dest_lng, dest_lat) < 0.0005:
            break

        best = None
        best_score = float('inf')

        for seg in candidates:
            if seg["segment_id"] in used:
                continue

            # Distance from current position to this segment's start or end
            d_start = _dist(current_lng, current_lat, seg["start_lng"], seg["start_lat"])
            d_end = _dist(current_lng, current_lat, seg["end_lng"], seg["end_lat"])
            connectivity = min(d_start, d_end)

            # Only consider segments that are reasonably close (connected)
            if connectivity > 0.006:  # ~600m threshold for sparse networks
                continue

            # Progress toward destination
            seg_mid_lng = (seg["start_lng"] + seg["end_lng"]) / 2
            seg_mid_lat = (seg["start_lat"] + seg["end_lat"]) / 2
            progress = _dist(seg_mid_lng, seg_mid_lat, dest_lng, dest_lat)

            # Score: balance connectivity + progress + cost
            if prefer_tcs:
                # Comfortable route: heavily weight TCS
                cost_factor = (1.0 - seg["tcs_value"]) * 0.01
            else:
                # Shortest route: weight by length
                cost_factor = (seg["length_m"] or 50) * 0.00001

            score = connectivity * 3.0 + progress * 1.0 + cost_factor

            if score < best_score:
                best_score = score
                best = seg

        if best is None:
            break

        path.append(best)
        used.add(best["segment_id"])

        # Move current position to the far end of this segment
        d_start = _dist(current_lng, current_lat, best["start_lng"], best["start_lat"])
        d_end = _dist(current_lng, current_lat, best["end_lng"], best["end_lat"])

        if d_start < d_end:
            # Entered from start, exit from end
            current_lng, current_lat = best["end_lng"], best["end_lat"]
        else:
            # Entered from end, exit from start
            current_lng, current_lat = best["start_lng"], best["start_lat"]

    return path


def _build_route(segments: list[dict], route_type: str, budget_limit: float) -> dict:
    """Build a RouteResult from an ordered segment list."""
    if not segments:
        return {
            "type": route_type,
            "distance_m": 0,
            "duration_min": 0,
            "sun_exposure_min": 0,
            "avg_tcs": 0,
            "within_heat_budget": True,
            "geometry": {"type": "LineString", "coordinates": []},
            "segments": [],
        }

    total_distance = sum(s["length_m"] for s in segments)
    avg_tcs = sum(s["tcs_value"] for s in segments) / len(segments)
    duration_min = total_distance / 75.0  # 4.5 km/h

    sun_exposure = 0
    for s in segments:
        seg_time = s["length_m"] / 75.0
        sun_exposure += seg_time * (1.0 - s["shade_ratio"])

    within_budget = sun_exposure <= budget_limit

    # Build ordered geometry by chaining segment geometries
    all_coords = []
    for s in segments:
        geom = s["geom"]
        if isinstance(geom, str):
            geom = json.loads(geom)
        if not geom or "coordinates" not in geom:
            continue
        coords = geom["coordinates"]
        if all_coords:
            # Check if we need to reverse this segment to connect
            last = all_coords[-1]
            first_of_seg = coords[0]
            last_of_seg = coords[-1]

            d_forward = ((last[0] - first_of_seg[0])**2 + (last[1] - first_of_seg[1])**2)
            d_reverse = ((last[0] - last_of_seg[0])**2 + (last[1] - last_of_seg[1])**2)

            if d_reverse < d_forward:
                coords = list(reversed(coords))

            # Skip first point if it's very close to last (avoid duplication)
            if len(coords) > 0:
                d = ((last[0] - coords[0][0])**2 + (last[1] - coords[0][1])**2)
                if d < 0.0000001:
                    coords = coords[1:]

        all_coords.extend(coords)

    segment_details = [
        {
            "segment_id": s["segment_id"],
            "tcs_value": round(s["tcs_value"], 3),
            "shade_ratio": round(s["shade_ratio"], 3),
            "apparent_temp": round(s["apparent_temp"], 1),
            "surface": s["surface_type"],
            "length_m": round(s["length_m"], 1),
        }
        for s in segments
    ]

    return {
        "type": route_type,
        "distance_m": round(total_distance, 1),
        "duration_min": round(duration_min, 1),
        "sun_exposure_min": round(sun_exposure, 1),
        "avg_tcs": round(avg_tcs, 3),
        "within_heat_budget": within_budget,
        "geometry": {"type": "LineString", "coordinates": all_coords},
        "segments": segment_details,
    }


def _empty_response(budget_limit: float) -> RouteResponse:
    """Return empty response when no segments found."""
    empty_route = {
        "type": "shortest",
        "distance_m": 0,
        "duration_min": 0,
        "sun_exposure_min": 0,
        "avg_tcs": 0,
        "within_heat_budget": True,
        "geometry": {"type": "LineString", "coordinates": []},
        "segments": [],
    }
    return RouteResponse(
        routes=[
            {**empty_route, "type": "shortest"},
            {**empty_route, "type": "most_comfortable"},
        ],
        weather_alert=None,
        heat_budget={"budget_limit_min": budget_limit, "recommended_route": "most_comfortable"},
    )


@router.get("/segments/thermal")
async def get_thermal_segments():
    """Get all segments with current TCS values for heatmap overlay."""
    async with get_conn() as conn:
        rows = await conn.fetch("""
            SELECT
                s.segment_id,
                tcs.tcs_value,
                ST_AsGeoJSON(s.geom) as geometry
            FROM segments s
            INNER JOIN LATERAL (
                SELECT tcs_value
                FROM thermal_comfort_scores
                WHERE segment_id = s.segment_id
                ORDER BY computed_at DESC
                LIMIT 1
            ) tcs ON true
            ORDER BY tcs.tcs_value ASC
            LIMIT 2000
        """)

    return [
        {
            "segment_id": row["segment_id"],
            "tcs_value": round(row["tcs_value"], 3),
            "geometry": json.loads(row["geometry"]) if isinstance(row["geometry"], str) else row["geometry"],
        }
        for row in rows
    ]
