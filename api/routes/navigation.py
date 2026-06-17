"""Navigation API routes - pgRouting with TCS-weighted costs."""
from __future__ import annotations

import json
from fastapi import APIRouter, HTTPException

from api.models.schemas import RouteRequest, RouteResponse
from api.db import get_conn

router = APIRouter()


@router.post("/route", response_model=RouteResponse)
async def calculate_route(request: RouteRequest):
    """Calculate shortest and most comfortable routes using pgRouting + TCS.

    - Shortest: pgr_dijkstra with base_cost (distance-only)
    - Most comfortable: pgr_dijkstra with total_cost (TCS penalty applied)
    """
    for point, label in [(request.origin, "origin"), (request.destination, "destination")]:
        if not (-7.35 <= point.lat <= -7.20 and 112.60 <= point.lng <= 112.85):
            raise HTTPException(status_code=400, detail=f"{label} di luar area Surabaya")

    heat_tolerance = "medium"
    budget_limit = 15.0
    if request.user_profile:
        heat_tolerance = request.user_profile.heat_tolerance
        budget_limit = {"low": 8.0, "medium": 15.0, "high": 25.0}.get(heat_tolerance, 15.0)

    origin = request.origin
    dest = request.destination

    async with get_conn() as conn:
        # Find nearest network nodes to origin and destination
        source_node = await _find_nearest_node(conn, origin.lng, origin.lat)
        target_node = await _find_nearest_node(conn, dest.lng, dest.lat)

        if not source_node or not target_node:
            return _empty_response(budget_limit)

        if source_node == target_node:
            return _empty_response(budget_limit)

        # Route 1: Shortest (base cost = distance/speed)
        shortest = await _run_pgr_route(conn, source_node, target_node, "shortest", budget_limit)

        # Route 2: Most comfortable (total cost = distance + thermal penalty)
        comfortable = await _run_pgr_route(conn, source_node, target_node, "most_comfortable", budget_limit)

    return RouteResponse(
        routes=[shortest, comfortable],
        weather_alert=None,
        heat_budget={"budget_limit_min": budget_limit, "recommended_route": "most_comfortable"},
    )


async def _find_nearest_node(conn, lng: float, lat: float) -> int | None:
    """Find the nearest pgRouting node to a coordinate."""
    row = await conn.fetchrow("""
        SELECT id FROM segments_vertices_pgr
        ORDER BY the_geom <-> ST_SetSRID(ST_MakePoint($1, $2), 4326)
        LIMIT 1
    """, lng, lat)
    return row["id"] if row else None


async def _run_pgr_route(conn, source: int, target: int, route_type: str, budget_limit: float) -> dict:
    """Run pgr_dijkstra and build route response."""
    # Choose cost column based on route type
    if route_type == "shortest":
        cost_sql = "COALESCE(s.length_m, 50) / 1.33"  # walking speed m/s
    else:
        cost_sql = "COALESCE(ew.total_cost, COALESCE(s.length_m, 50) / 1.33)"

    # pgr_dijkstra query with edge_weights join
    try:
        rows = await conn.fetch(f"""
            SELECT
                r.seq,
                r.edge as segment_id,
                s.length_m,
                s.surface_type,
                COALESCE(tcs.tcs_value, 0.5) as tcs_value,
                COALESCE(tcs.shade_ratio, 0.2) as shade_ratio,
                COALESCE(tcs.apparent_temp, 34.0) as apparent_temp,
                ST_AsGeoJSON(s.geom) as geom_json
            FROM pgr_dijkstra(
                'SELECT segment_id as id, source, target,
                        {cost_sql} as cost,
                        {cost_sql} as reverse_cost
                 FROM segments s
                 LEFT JOIN LATERAL (
                     SELECT total_cost FROM edge_weights
                     WHERE segment_id = s.segment_id
                     ORDER BY valid_from DESC LIMIT 1
                 ) ew ON true',
                $1, $2, directed := false
            ) r
            JOIN segments s ON r.edge = s.segment_id
            LEFT JOIN LATERAL (
                SELECT tcs_value, shade_ratio, apparent_temp
                FROM thermal_comfort_scores
                WHERE segment_id = s.segment_id
                ORDER BY computed_at DESC LIMIT 1
            ) tcs ON true
            WHERE r.edge > 0
            ORDER BY r.seq
        """, source, target)
    except Exception as e:
        # pgRouting might not find a path
        print(f"[Route] pgr_dijkstra failed: {e}")
        return _empty_route(route_type)

    if not rows:
        return _empty_route(route_type)

    # Build ordered geometry and stats
    all_coords = []
    total_distance = 0.0
    total_tcs = 0.0
    total_shade = 0.0
    segments = []

    for row in rows:
        geom = json.loads(row["geom_json"]) if isinstance(row["geom_json"], str) else row["geom_json"]
        length = row["length_m"] or 0
        total_distance += length
        total_tcs += row["tcs_value"]
        total_shade += row["shade_ratio"]

        # Chain coordinates (connect segments properly)
        if geom and "coordinates" in geom:
            coords = geom["coordinates"]
            if all_coords:
                # Check if we need to reverse
                last = all_coords[-1]
                d_fwd = (last[0] - coords[0][0])**2 + (last[1] - coords[0][1])**2
                d_rev = (last[0] - coords[-1][0])**2 + (last[1] - coords[-1][1])**2
                if d_rev < d_fwd:
                    coords = list(reversed(coords))
                # Skip duplicate point
                if coords and ((last[0] - coords[0][0])**2 + (last[1] - coords[0][1])**2) < 1e-10:
                    coords = coords[1:]
            all_coords.extend(coords)

        segments.append({
            "segment_id": row["segment_id"],
            "tcs_value": round(row["tcs_value"], 3),
            "shade_ratio": round(row["shade_ratio"], 3),
            "apparent_temp": round(row["apparent_temp"], 1),
            "surface": row["surface_type"],
            "length_m": round(length, 1),
        })

    n = len(rows)
    avg_tcs = total_tcs / n if n > 0 else 0.5
    avg_shade = total_shade / n if n > 0 else 0.2
    duration_min = total_distance / 75.0  # 4.5 km/h
    sun_exposure = duration_min * (1.0 - avg_shade)

    return {
        "type": route_type,
        "distance_m": round(total_distance, 1),
        "duration_min": round(duration_min, 1),
        "sun_exposure_min": round(sun_exposure, 1),
        "avg_tcs": round(avg_tcs, 3),
        "within_heat_budget": sun_exposure <= budget_limit,
        "geometry": {"type": "LineString", "coordinates": all_coords},
        "segments": segments[:15],
    }


def _empty_route(route_type: str) -> dict:
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


def _empty_response(budget_limit: float) -> RouteResponse:
    return RouteResponse(
        routes=[_empty_route("shortest"), _empty_route("most_comfortable")],
        weather_alert=None,
        heat_budget={"budget_limit_min": budget_limit, "recommended_route": "most_comfortable"},
    )


@router.get("/segments/thermal")
async def get_thermal_segments():
    """Get segments with TCS values for heatmap overlay."""
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
