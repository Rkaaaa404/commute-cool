"""Dashboard API routes - Government analytics with real PostGIS data."""

from fastapi import APIRouter

from api.models.schemas import (
    UHIResponse,
    UHISummary,
    UHIHotspot,
    PriorityCorridorsResponse,
    PriorityCorridor,
    WalkabilityStats,
)
from api.db import get_conn

router = APIRouter()


@router.get("/uhi", response_model=UHIResponse)
async def get_uhi_hotspots():
    """Get Urban Heat Island hotspot map data.

    Returns segments with highest LST / lowest TCS for heatmap overlay.
    """
    async with get_conn() as conn:
        # Get summary stats
        summary_row = await conn.fetchrow("""
            SELECT
                COUNT(DISTINCT s.segment_id) as total_segments,
                COUNT(DISTINCT s.segment_id) FILTER (WHERE tcs.tcs_value < 0.4) as critical_segments,
                COALESCE(AVG(tcs.tcs_value), 0) as avg_city_tcs
            FROM segments s
            LEFT JOIN LATERAL (
                SELECT tcs_value FROM thermal_comfort_scores
                WHERE segment_id = s.segment_id
                ORDER BY computed_at DESC LIMIT 1
            ) tcs ON true
        """)

        # Get hotspot segments (lowest TCS / highest LST)
        hotspot_rows = await conn.fetch("""
            SELECT
                s.segment_id,
                s.name,
                ST_AsGeoJSON(s.geom)::json as geometry,
                COALESCE(rs.avg_lst, 36.0) as avg_lst,
                COALESCE(tcs.tcs_value, 0.3) as avg_tcs,
                COALESCE(tcs.shade_ratio, 0.1) as shade_ratio
            FROM segments s
            LEFT JOIN LATERAL (
                SELECT avg_lst FROM segment_raster_scores
                WHERE segment_id = s.segment_id
                ORDER BY computed_at DESC LIMIT 1
            ) rs ON true
            LEFT JOIN LATERAL (
                SELECT tcs_value, shade_ratio FROM thermal_comfort_scores
                WHERE segment_id = s.segment_id
                ORDER BY computed_at DESC LIMIT 1
            ) tcs ON true
            WHERE tcs.tcs_value IS NOT NULL AND tcs.tcs_value < 0.5
            ORDER BY tcs.tcs_value ASC
            LIMIT 100
        """)

    hotspots = [
        UHIHotspot(
            segment_id=row["segment_id"],
            geometry=row["geometry"],
            avg_lst=round(row["avg_lst"], 1),
            avg_tcs=round(row["avg_tcs"], 3),
            street_name=row["name"],
            shade_ratio=round(row["shade_ratio"], 3),
        )
        for row in hotspot_rows
    ]

    return UHIResponse(
        hotspots=hotspots,
        summary=UHISummary(
            total_segments=summary_row["total_segments"] or 0,
            critical_segments=summary_row["critical_segments"] or 0,
            avg_city_tcs=round(float(summary_row["avg_city_tcs"] or 0), 3),
        ),
    )


@router.get("/priority-corridors", response_model=PriorityCorridorsResponse)
async def get_priority_corridors():
    """Get recommended corridors for greening/canopy installation.

    Ranks by: lowest TCS + proximity to transit stops (high pedestrian volume).
    """
    async with get_conn() as conn:
        rows = await conn.fetch("""
            WITH segment_scores AS (
                SELECT
                    s.segment_id,
                    s.name,
                    s.highway_type,
                    COALESCE(tcs.tcs_value, 0.5) as tcs_value,
                    -- Count nearby transit stops (proxy for pedestrian volume)
                    (SELECT COUNT(*) FROM transit_stops t
                     WHERE ST_DWithin(t.geom, s.geom, 0.003)) as nearby_transit,
                    -- Nearest transit stop name
                    (SELECT t.name FROM transit_stops t
                     ORDER BY t.geom <-> s.geom LIMIT 1) as nearest_transit_name
                FROM segments s
                LEFT JOIN LATERAL (
                    SELECT tcs_value FROM thermal_comfort_scores
                    WHERE segment_id = s.segment_id
                    ORDER BY computed_at DESC LIMIT 1
                ) tcs ON true
            )
            SELECT
                COALESCE(name, 'Unnamed ' || highway_type || ' corridor') as corridor_name,
                ARRAY_AGG(segment_id) as segment_ids,
                AVG(tcs_value) as avg_tcs,
                MAX(nearby_transit) as max_transit,
                nearest_transit_name,
                -- Priority score: lower TCS + higher pedestrian volume = higher priority
                (1.0 - AVG(tcs_value)) * 0.6 + LEAST(MAX(nearby_transit)::float / 3.0, 1.0) * 0.4 as priority_score
            FROM segment_scores
            WHERE tcs_value < 0.55
            GROUP BY COALESCE(name, 'Unnamed ' || highway_type || ' corridor'), nearest_transit_name
            ORDER BY priority_score DESC
            LIMIT 15
        """)

    corridors = []
    for row in rows:
        transit_count = row["max_transit"] or 0
        volume = "high" if transit_count >= 2 else ("medium" if transit_count >= 1 else "low")
        avg_tcs = float(row["avg_tcs"])

        if avg_tcs < 0.3:
            rec = "Urgent: Tambah kanopi + pohon rindang segera"
        elif avg_tcs < 0.4:
            rec = "Prioritas: Tanam pohon peneduh, pertimbangkan pergola"
        else:
            rec = "Sedang: Tambah vegetasi ground cover + bangku teduh"

        corridors.append(PriorityCorridor(
            corridor_name=row["corridor_name"],
            segments=row["segment_ids"][:10],
            avg_tcs=round(avg_tcs, 3),
            pedestrian_volume=volume,
            nearest_transit=row["nearest_transit_name"],
            recommendation=rec,
            priority_score=round(float(row["priority_score"]), 3),
        ))

    return PriorityCorridorsResponse(corridors=corridors)


@router.get("/walkability", response_model=WalkabilityStats)
async def get_walkability_stats():
    """Get walkability and transit accessibility statistics.

    Calculates percentage of transit stops reachable within comfortable
    10-minute walk (~750m with TCS > 0.5 average).
    """
    async with get_conn() as conn:
        row = await conn.fetchrow("""
            WITH transit_access AS (
                SELECT
                    ts.stop_id,
                    ts.name,
                    -- Count comfortable segments within 750m walking distance
                    (SELECT COUNT(*) FROM segments s
                     INNER JOIN thermal_comfort_scores tcs ON tcs.segment_id = s.segment_id
                     WHERE ST_DWithin(s.geom, ts.geom, 0.007)  -- ~750m
                       AND tcs.tcs_value > 0.5
                    ) as comfortable_paths
                FROM transit_stops ts
            )
            SELECT
                COUNT(*) as total_stops,
                COUNT(*) FILTER (WHERE comfortable_paths > 0) as reachable,
                COALESCE(
                    COUNT(*) FILTER (WHERE comfortable_paths > 0)::float / NULLIF(COUNT(*), 0) * 100,
                    0
                ) as reachable_pct
            FROM transit_access
        """)

        # Get city-wide average TCS
        tcs_row = await conn.fetchrow("""
            SELECT COALESCE(AVG(tcs_value), 0) as avg_tcs
            FROM thermal_comfort_scores
            WHERE computed_at > NOW() - INTERVAL '24 hours'
        """)

        avg_tcs = float(tcs_row["avg_tcs"]) if tcs_row["avg_tcs"] else 0.0

    return WalkabilityStats(
        total_transit_stops=row["total_stops"] or 0,
        reachable_within_10min=row["reachable"] or 0,
        reachable_percentage=round(float(row["reachable_pct"] or 0), 1),
        avg_tcs_city=round(avg_tcs, 3),
    )
