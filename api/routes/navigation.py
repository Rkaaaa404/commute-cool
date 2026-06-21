"""Navigation API routes - pgRouting with TCS-weighted costs."""
from __future__ import annotations

import json
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from api.models.schemas import RouteRequest, RouteResponse
from api.db import get_conn

router = APIRouter()

# Penalty multiplier per heat tolerance level
# Applies only to the "most_comfortable" route cost calculation.
# Low tolerance → higher penalty on hot segments → Dijkstra aggressively seeks shade.
# High tolerance → lower penalty → prefers shorter/faster routes.
_PENALTY_MULT = {"low": 1.75, "medium": 1.25, "high": 0.8}


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

        # Route 1: Shortest (base cost = distance/speed, unaffected by tolerance)
        shortest = await _run_pgr_route(conn, source_node, target_node, "shortest", budget_limit, heat_tolerance)

        # Route 2: Most comfortable (total cost = distance + thermal penalty weighted by tolerance)
        comfortable = await _run_pgr_route(conn, source_node, target_node, "most_comfortable", budget_limit, heat_tolerance)

        # Get active weather warning summary if any
        alert_row = await conn.fetchrow("""
            SELECT title, severity, description
            FROM weather_alerts
            WHERE is_active = TRUE
              AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY severity DESC, issued_at DESC
            LIMIT 1
        """)
        
        weather_alert_str = None
        if alert_row:
            weather_alert_str = f"[{alert_row['severity'].upper()}] {alert_row['title']}: {alert_row['description']}"

    return RouteResponse(
        routes=[shortest, comfortable],
        weather_alert=weather_alert_str,
        heat_budget={"budget_limit_min": budget_limit, "recommended_route": "most_comfortable"},
    )


async def _find_nearest_node(conn, lng: float, lat: float) -> int | None:
    """Find the nearest pgRouting node to a coordinate."""
    row = await conn.fetchrow("""
        SELECT id FROM segments_noded_vertices_pgr
        ORDER BY the_geom <-> ST_SetSRID(ST_MakePoint($1, $2), 4326)
        LIMIT 1
    """, lng, lat)
    return row["id"] if row else None


async def _run_pgr_route(conn, source: int, target: int, route_type: str, budget_limit: float, heat_tolerance: str = "medium") -> dict:
    """Run pgr_dijkstra and build route response."""
    penalty_mult = _PENALTY_MULT.get(heat_tolerance, 1.25)

    # Check for active severe/extreme weather alerts
    alert_row = await conn.fetchrow("""
        SELECT alert_id FROM weather_alerts
        WHERE is_active = TRUE
          AND (expires_at IS NULL OR expires_at > NOW())
          AND severity IN ('severe', 'extreme')
        LIMIT 1
    """)
    has_active_alert = alert_row is not None

    # Choose cost column and joins based on route type
    if route_type == "shortest":
        # Shortest route is purely distance-based, tolerance has no effect
        cost_sql = "COALESCE(sn.length_m, 50) / 1.33"  # walking speed m/s
        joins_sql = ""
    else:
        # Comfortable route: thermal penalty is scaled by the user's tolerance multiplier
        # TCS=1.0 (cool) → no extra penalty; TCS=0.0 (hot) → max penalty
        cost_sql = f"(COALESCE(sn.length_m, 50) / 1.33) * (1.0 + (1.0 - COALESCE(tcs.tcs_value, 0.5)) * {penalty_mult})"
        joins_sql = """
                  LEFT JOIN LATERAL (
                      SELECT tcs_value FROM thermal_comfort_scores
                      WHERE segment_id = sn.old_id
                      ORDER BY computed_at DESC LIMIT 1
                  ) tcs ON true
        """

    # Build weather alert penalty sql
    if has_active_alert:
        alert_penalty_sql = """(
                            CASE WHEN EXISTS (
                                SELECT 1 FROM weather_alerts wa
                                WHERE wa.is_active = TRUE
                                  AND (wa.expires_at IS NULL OR wa.expires_at > NOW())
                                  AND wa.severity IN (''severe'', ''extreme'')
                                  AND ST_Intersects(sn.geom, wa.affected_area)
                            ) THEN 100.0 ELSE 1.0 END
                        )"""
    else:
        alert_penalty_sql = "1.0"

    # pgr_dijkstra query with edge_weights join
    try:
        rows = await conn.fetch(f"""
            SELECT
                r.seq,
                sn.old_id as segment_id,
                sn.length_m as length_m,
                s.surface_type,
                COALESCE(tcs.tcs_value, 0.5) as tcs_value,
                COALESCE(tcs.shade_ratio, 0.2) as shade_ratio,
                COALESCE(tcs.apparent_temp, 34.0) as apparent_temp,
                ST_AsGeoJSON(sn.geom) as geom_json
            FROM pgr_dijkstra(
                'SELECT sn.id, sn.source::integer, sn.target::integer,
                        ({cost_sql}) * {alert_penalty_sql} as cost,
                        ({cost_sql}) * {alert_penalty_sql} as reverse_cost
                  FROM segments_noded sn
                  {joins_sql}
                  WHERE sn.source IS NOT NULL AND sn.target IS NOT NULL',
                $1::bigint, $2::bigint, directed := false
            ) r
            JOIN segments_noded sn ON r.edge = sn.id
            JOIN segments s ON sn.old_id = s.segment_id
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


@router.get("/segments/tcs")
async def get_tcs_segments(
    west: Optional[float] = Query(None, description="Bbox west longitude"),
    south: Optional[float] = Query(None, description="Bbox south latitude"),
    east: Optional[float] = Query(None, description="Bbox east longitude"),
    north: Optional[float] = Query(None, description="Bbox north latitude"),
):
    """Get TCS segments, optionally filtered to a viewport bounding box.

    When bbox params are provided (west/south/east/north), only segments
    within that viewport are returned — enabling efficient viewport-based
    loading in the frontend map.
    """
    async with get_conn() as conn:
        if all(isinstance(v, (int, float)) for v in [west, south, east, north]):
            # Viewport-filtered query using PostGIS GIST index
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
                WHERE ST_Intersects(
                    s.geom,
                    ST_MakeEnvelope($1, $2, $3, $4, 4326)
                )
                LIMIT 3000
            """, west, south, east, north)
        else:
            # No bbox: return all (initial load)
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


@router.get("/segments/thermal")
async def get_thermal_segments():
    """Alias for /segments/tcs — backward compatibility."""
    return await get_tcs_segments(None, None, None, None)


@router.get("/debug/topology-status")
async def topology_status():
    """Diagnostik status topologi pgRouting.

    Mengembalikan jumlah edge, vertex, dan contoh connectivity.
    Gunakan endpoint ini untuk memverifikasi topologi routing sudah benar.
    """
    async with get_conn() as conn:
        noded_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='segments_noded')"
        )
        vertices_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='segments_noded_vertices_pgr')"
        )

        if not noded_exists:
            return {"status": "error", "message": "Tabel segments_noded tidak ditemukan. Jalankan rebuild topology."}

        edge_count = await conn.fetchval("SELECT COUNT(*) FROM segments_noded")
        vertex_count = await conn.fetchval("SELECT COUNT(*) FROM segments_noded_vertices_pgr") if vertices_exists else 0
        null_source = await conn.fetchval("SELECT COUNT(*) FROM segments_noded WHERE source IS NULL OR target IS NULL")
        segments_count = await conn.fetchval("SELECT COUNT(*) FROM segments")

        sample_node = await conn.fetchval(
            "SELECT id FROM segments_noded_vertices_pgr ORDER BY the_geom <-> ST_SetSRID(ST_MakePoint(112.7521, -7.2575), 4326) LIMIT 1"
        ) if vertices_exists else None

        return {
            "status": "ok" if (null_source == 0 and edge_count > 0) else "warning",
            "segments_total": segments_count,
            "noded_edges": edge_count,
            "noded_vertices": vertex_count,
            "edges_with_null_topology": null_source,
            "sample_center_node_id": sample_node,
            "topology_ready": null_source == 0 and edge_count > 0 and vertex_count > 0,
        }


@router.post("/admin/rebuild-topology")
async def rebuild_topology():
    """Rebuild pgRouting topology dari tabel segments.

    Eksekusi fungsi build_routing_topology() yang akan:
    1. Drop & recreate tabel segments_noded
    2. Jalankan pgr_createTopology dengan tolerance 0.0005 derajat (~55m)

    PERHATIAN: Proses ini memakan waktu 1-5 menit.
    """
    async with get_conn() as conn:
        try:
            await conn.execute("SELECT build_routing_topology()")
            edge_count = await conn.fetchval("SELECT COUNT(*) FROM segments_noded")
            vertex_count = await conn.fetchval("SELECT COUNT(*) FROM segments_noded_vertices_pgr")
            null_count = await conn.fetchval(
                "SELECT COUNT(*) FROM segments_noded WHERE source IS NULL OR target IS NULL"
            )
            return {
                "status": "success",
                "message": "Topology rebuilt successfully",
                "noded_edges": edge_count,
                "noded_vertices": vertex_count,
                "null_topology_edges": null_count,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Topology rebuild failed: {str(e)}")
