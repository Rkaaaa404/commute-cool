"""Dashboard API routes - Government analytics with real PostGIS data."""

import json
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
        # Get summary stats using only the latest TCS for each segment
        summary_row = await conn.fetchrow("""
            WITH latest_tcs AS (
                SELECT DISTINCT ON (segment_id) segment_id, tcs_value
                FROM thermal_comfort_scores
                ORDER BY segment_id, computed_at DESC
            )
            SELECT
                COUNT(DISTINCT s.segment_id) as total_segments,
                COUNT(DISTINCT s.segment_id) FILTER (WHERE tcs.tcs_value < 0.4) as critical_segments,
                COALESCE(AVG(tcs.tcs_value), 0) as avg_city_tcs
            FROM segments s
            LEFT JOIN latest_tcs tcs ON tcs.segment_id = s.segment_id
        """)

        # Get hotspot segments (lowest TCS / highest LST) using latest scores
        hotspot_rows = await conn.fetch("""
            WITH latest_tcs AS (
                SELECT DISTINCT ON (segment_id) segment_id, tcs_value, shade_ratio
                FROM thermal_comfort_scores
                ORDER BY segment_id, computed_at DESC
            )
            SELECT
                s.segment_id,
                s.name,
                ST_AsGeoJSON(s.geom) as geometry,
                COALESCE(rs.avg_lst, 36.0) as avg_lst,
                COALESCE(tcs.tcs_value, 0.3) as avg_tcs,
                COALESCE(tcs.shade_ratio, 0.1) as shade_ratio
            FROM latest_tcs tcs
            JOIN segments s ON s.segment_id = tcs.segment_id
            LEFT JOIN segment_raster_scores rs ON rs.segment_id = tcs.segment_id
            WHERE tcs.tcs_value < 0.5
            ORDER BY tcs.tcs_value ASC
            LIMIT 100
        """)

    hotspots = [
        UHIHotspot(
            segment_id=row["segment_id"],
            geometry=json.loads(row["geometry"]) if isinstance(row["geometry"], str) else row["geometry"],
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
            WITH latest_tcs AS (
                SELECT DISTINCT ON (segment_id) segment_id, tcs_value, apparent_temp, shade_ratio, aqi_value, traffic_level
                FROM thermal_comfort_scores
                ORDER BY segment_id, computed_at DESC
            ),
            corridors AS (
                SELECT
                    COALESCE(s.name, 'Unnamed ' || s.highway_type || ' corridor') as corridor_name,
                    ARRAY_AGG(s.segment_id) as segment_ids,
                    AVG(COALESCE(tcs.tcs_value, 0.5)) as avg_tcs,
                    AVG(COALESCE(tcs.shade_ratio, 0.2)) as avg_shade,
                    AVG(COALESCE(tcs.apparent_temp, 34.0)) as avg_temp,
                    AVG(COALESCE(tcs.aqi_value, 50.0)) as avg_aqi,
                    AVG(COALESCE(tcs.traffic_level, 0.3)) as avg_traffic,
                    ST_Centroid(ST_Collect(s.geom)) as corridor_center
                FROM latest_tcs tcs
                JOIN segments s ON s.segment_id = tcs.segment_id
                WHERE tcs.tcs_value < 0.55
                GROUP BY COALESCE(s.name, 'Unnamed ' || s.highway_type || ' corridor')
            )
            SELECT
                corridor_name,
                segment_ids,
                avg_tcs,
                avg_shade,
                avg_temp,
                avg_aqi,
                avg_traffic,
                -- Count nearby transit stops
                (SELECT COUNT(*) FROM transit_stops t
                 WHERE ST_DWithin(t.geom, corridor_center, 0.003)) as max_transit,
                -- Nearest transit stop name
                (SELECT t.name FROM transit_stops t
                 ORDER BY t.geom <-> corridor_center LIMIT 1) as nearest_transit_name,
                -- Priority score
                (1.0 - avg_tcs) * 0.6 + LEAST(
                    (SELECT COUNT(*) FROM transit_stops t
                     WHERE ST_DWithin(t.geom, corridor_center, 0.003))::float / 3.0,
                    1.0
                ) * 0.4 as priority_score
            FROM corridors
            ORDER BY priority_score DESC
            LIMIT 15
        """)

    corridors = []
    for row in rows:
        transit_count = row["max_transit"] or 0
        volume = "high" if transit_count >= 2 else ("medium" if transit_count >= 1 else "low")
        avg_tcs = float(row["avg_tcs"])
        avg_shade = float(row["avg_shade"])
        avg_temp = float(row["avg_temp"])
        avg_aqi = float(row["avg_aqi"])
        avg_traffic = float(row["avg_traffic"])

        # Dynamically build recommendations based on actual physical bottlenecks
        recs = []
        if avg_shade < 0.25:
            recs.append("Tanam pohon peneduh / pergola")
        if avg_temp > 35.5:
            recs.append("Material permukaan jalan dingin (cool pavement)")
        if avg_aqi > 100.0 or avg_traffic > 0.45:
            recs.append("Barikade vegetasi penyerap polusi (green barrier)")
        
        # Fallback recommendations if thresholds aren't crossed
        if not recs:
            if avg_tcs < 0.4:
                recs.append("Prioritas Tinggi: Intervensi kenyamanan terpadu")
            else:
                recs.append("Sedang: Perawatan rutin trotoar & vegetasi")

        rec = " & ".join(recs)

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
    10-minute walk (~750m walking radius). Comfortable access means the
    average TCS of surrounding segments is > 0.55.
    """
    async with get_conn() as conn:
        row = await conn.fetchrow("""
            WITH latest_tcs AS (
                SELECT DISTINCT ON (segment_id) segment_id, tcs_value
                FROM thermal_comfort_scores
                ORDER BY segment_id, computed_at DESC
            ),
            transit_access AS (
                SELECT
                    ts.stop_id,
                    AVG(tcs.tcs_value) as avg_surrounding_tcs
                FROM transit_stops ts
                LEFT JOIN segments s ON ST_DWithin(s.geom, ts.geom, 0.007)
                LEFT JOIN latest_tcs tcs ON tcs.segment_id = s.segment_id
                GROUP BY ts.stop_id
            )
            SELECT
                COUNT(*) as total_stops,
                COUNT(*) FILTER (WHERE avg_surrounding_tcs > 0.55) as reachable,
                COALESCE(
                    COUNT(*) FILTER (WHERE avg_surrounding_tcs > 0.55)::float / NULLIF(COUNT(*), 0) * 100,
                    0
                ) as reachable_pct
            FROM transit_access
        """)

        # Get city-wide average TCS using only the latest values from the last 24 hours
        tcs_row = await conn.fetchrow("""
            WITH latest_tcs AS (
                SELECT DISTINCT ON (segment_id) segment_id, tcs_value
                FROM thermal_comfort_scores
                WHERE computed_at > NOW() - INTERVAL '24 hours'
                ORDER BY segment_id, computed_at DESC
            )
            SELECT COALESCE(AVG(tcs_value), 0) as avg_tcs
            FROM latest_tcs
        """)

        avg_tcs = float(tcs_row["avg_tcs"]) if tcs_row["avg_tcs"] else 0.0

    return WalkabilityStats(
        total_transit_stops=row["total_stops"] or 0,
        reachable_within_10min=row["reachable"] or 0,
        reachable_percentage=round(float(row["reachable_pct"] or 0), 1),
        avg_tcs_city=round(avg_tcs, 3),
    )


@router.get("/active-alerts")
async def get_active_alerts():
    """Get active weather warnings."""
    async with get_conn() as conn:
        rows = await conn.fetch("""
            SELECT title, severity, description, issued_at, expires_at
            FROM weather_alerts
            WHERE is_active = TRUE
              AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY severity DESC, issued_at DESC
        """)
    return [
        {
            "title": row["title"],
            "severity": row["severity"],
            "description": row["description"],
            "issued_at": str(row["issued_at"]) if row["issued_at"] else None,
            "expires_at": str(row["expires_at"]) if row["expires_at"] else None,
        }
        for row in rows
    ]


@router.get("/temperature-heatmap")
async def get_temperature_heatmap():
    """Get centroids of segments with apparent temperatures for lightweight map rendering."""
    async with get_conn() as conn:
        rows = await conn.fetch("""
            SELECT
                s.segment_id,
                tcs.apparent_temp as temp,
                ST_AsGeoJSON(ST_Centroid(s.geom)) as geom_json
            FROM segments s
            INNER JOIN LATERAL (
                SELECT apparent_temp
                FROM thermal_comfort_scores
                WHERE segment_id = s.segment_id
                ORDER BY computed_at DESC
                LIMIT 1
            ) tcs ON true
            WHERE tcs.apparent_temp IS NOT NULL
            LIMIT 2000
        """)
        
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": json.loads(row["geom_json"]) if isinstance(row["geom_json"], str) else row["geom_json"],
                "properties": {
                    "temp": float(row["temp"]),
                    "segment_id": row["segment_id"]
                }
            }
            for row in rows
        ]
    }
    return geojson


@router.get("/simulations")
async def get_tcs_simulations():
    """Get AI/ML scenario simulation comparison results.
    
    Ranks segments that would benefit most from urban greening/tree planting.
    """
    async with get_conn() as conn:
        rows = await conn.fetch("""
            SELECT
                s.segment_id,
                s.name as street_name,
                ST_AsGeoJSON(s.geom) as geometry,
                sim.current_tcs,
                sim.predicted_tcs_green,
                sim.predicted_tcs_cool,
                sim.tcs_improvement_green,
                sim.tcs_improvement_cool
            FROM tcs_simulations sim
            JOIN segments s ON s.segment_id = sim.segment_id
            ORDER BY sim.tcs_improvement_green DESC
            LIMIT 50
        """)
        
    return [
        {
            "segment_id": row["segment_id"],
            "street_name": row["street_name"] or f"Segment #{row['segment_id']}",
            "geometry": json.loads(row["geometry"]) if isinstance(row["geometry"], str) else row["geometry"],
            "current_tcs": round(row["current_tcs"], 3),
            "predicted_tcs_green": round(row["predicted_tcs_green"], 3),
            "predicted_tcs_cool": round(row["predicted_tcs_cool"], 3),
            "tcs_improvement_green": round(row["tcs_improvement_green"], 3),
            "tcs_improvement_cool": round(row["tcs_improvement_cool"], 3),
        }
        for row in rows
    ]


@router.get("/heat-prediction")
async def get_heat_prediction():
    """Prediksi zona panas harian menggunakan data dari Spark pipeline.

    Mengembalikan:
    - hot_zones: 50 segmen dengan TCS terendah, beserta prediksi skenario hijau/cooling
    - hourly_trend: Simulasi rata-rata TCS kota per jam (06:00-21:00)
    - summary: Statistik ringkasan area panas
    """
    # Surabaya typical daily temperature curve multipliers (relative to baseline)
    # Normalized so that 12:00 = peak heat (factor=1.0), 06:00 = coolest (factor=-0.15)
    HOURLY_HEAT_FACTOR = {
        6:  -0.15,
        7:  -0.10,
        8:  -0.04,
        9:   0.02,
        10:  0.08,
        11:  0.13,
        12:  0.16,
        13:  0.15,
        14:  0.13,
        15:  0.08,
        16:  0.02,
        17: -0.03,
        18: -0.08,
        19: -0.11,
        20: -0.13,
        21: -0.14,
    }

    async with get_conn() as conn:
        # Get top 50 hottest segments with simulation predictions
        hot_rows = await conn.fetch("""
            WITH latest_tcs AS (
                SELECT DISTINCT ON (segment_id)
                    segment_id, tcs_value, apparent_temp, shade_ratio, aqi_value
                FROM thermal_comfort_scores
                ORDER BY segment_id, computed_at DESC
            )
            SELECT
                s.segment_id,
                COALESCE(s.name, s.highway_type || ' #' || s.segment_id::text) as street_name,
                s.highway_type,
                s.has_shade_tree,
                tcs.tcs_value as current_tcs,
                tcs.apparent_temp,
                tcs.shade_ratio,
                tcs.aqi_value,
                sim.predicted_tcs_green,
                sim.predicted_tcs_cool,
                sim.tcs_improvement_green,
                sim.tcs_improvement_cool,
                sim.simulated_at
            FROM latest_tcs tcs
            JOIN tcs_simulations sim ON tcs.segment_id = sim.segment_id
            JOIN segments s ON tcs.segment_id = s.segment_id
            ORDER BY tcs.tcs_value ASC
            LIMIT 50
        """)

        # City-wide aggregate stats
        agg_row = await conn.fetchrow("""
            WITH latest_tcs AS (
                SELECT DISTINCT ON (segment_id) tcs_value, apparent_temp
                FROM thermal_comfort_scores
                ORDER BY segment_id, computed_at DESC
            )
            SELECT
                COUNT(*) FILTER (WHERE tcs_value < 0.5) as hot_count,
                COUNT(*) FILTER (WHERE tcs_value BETWEEN 0.5 AND 0.65) as warm_count,
                COUNT(*) FILTER (WHERE tcs_value > 0.65) as cool_count,
                COUNT(*) as total_count,
                AVG(tcs_value) as avg_tcs,
                AVG(apparent_temp) as avg_apparent_temp,
                MAX(apparent_temp) as max_apparent_temp
            FROM latest_tcs
        """)

        # Average TCS and simulation values for hourly trend base
        trend_base = await conn.fetchrow("""
            WITH latest_tcs AS (
                SELECT DISTINCT ON (segment_id) segment_id, tcs_value
                FROM thermal_comfort_scores
                ORDER BY segment_id, computed_at DESC
            )
            SELECT
                AVG(tcs.tcs_value) as avg_current_tcs,
                AVG(sim.predicted_tcs_green) as avg_green_tcs,
                AVG(sim.predicted_tcs_cool) as avg_cool_tcs
            FROM latest_tcs tcs
            JOIN tcs_simulations sim ON tcs.segment_id = sim.segment_id
        """)

    avg_tcs = float(trend_base["avg_current_tcs"] or 0.68)
    avg_green = float(trend_base["avg_green_tcs"] or 0.72)
    avg_cool = float(trend_base["avg_cool_tcs"] or 0.70)

    # Build hourly trend data — simulate TCS changes throughout the day
    hourly_trend = []
    for hour, factor in HOURLY_HEAT_FACTOR.items():
        tcs_current = round(max(0.1, min(1.0, avg_tcs - factor * 0.3)), 3)
        tcs_green = round(max(0.1, min(1.0, avg_green - factor * 0.22)), 3)
        tcs_cool = round(max(0.1, min(1.0, avg_cool - factor * 0.18)), 3)
        apparent_temp = round(float(agg_row["avg_apparent_temp"] or 32.5) + factor * 4.5, 1)
        hourly_trend.append({
            "hour": hour,
            "label": f"{hour:02d}:00",
            "tcs_current": tcs_current,
            "tcs_green_scenario": tcs_green,
            "tcs_cool_scenario": tcs_cool,
            "apparent_temp": apparent_temp,
        })

    total = int(agg_row["total_count"] or 1)
    hot_count = int(agg_row["hot_count"] or 0)
    warm_count = int(agg_row["warm_count"] or 0)
    cool_count = int(agg_row["cool_count"] or 0)

    # Build hot zones list
    hot_zones = []
    for row in hot_rows:
        current = float(row["current_tcs"])
        green = float(row["predicted_tcs_green"])
        cool_pred = float(row["predicted_tcs_cool"])
        improvement_pct = round((green - current) / max(current, 0.01) * 100, 1)
        hot_zones.append({
            "segment_id": row["segment_id"],
            "street_name": row["street_name"],
            "highway_type": row["highway_type"] or "path",
            "has_shade_tree": row["has_shade_tree"] or False,
            "current_tcs": round(current, 3),
            "apparent_temp": round(float(row["apparent_temp"] or 32.5), 1),
            "shade_ratio": round(float(row["shade_ratio"] or 0.0), 2),
            "predicted_tcs_green": round(green, 3),
            "predicted_tcs_cool": round(cool_pred, 3),
            "improvement_pct": improvement_pct,
            "severity": "critical" if current < 0.45 else "hot" if current < 0.55 else "warm",
        })

    return {
        "summary": {
            "total_segments": total,
            "hot_segments": hot_count,
            "warm_segments": warm_count,
            "cool_segments": cool_count,
            "hot_percentage": round(hot_count / total * 100, 1),
            "avg_city_tcs": round(float(agg_row["avg_tcs"] or 0.68), 3),
            "avg_apparent_temp": round(float(agg_row["avg_apparent_temp"] or 32.5), 1),
            "max_apparent_temp": round(float(agg_row["max_apparent_temp"] or 35.0), 1),
            "peak_heat_hour": 12,
        },
        "hourly_trend": hourly_trend,
        "hot_zones": hot_zones,
    }
