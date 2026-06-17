"""CCTV API routes - Live camera preview endpoints with real PostGIS queries."""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from api.db import get_conn

router = APIRouter()

DISHUB_HLS_BASE = "http://36.66.208.101:5000/hls"


class CCTVCamera(BaseModel):
    cctv_id: str
    name: str
    stream_url: str
    lat: float
    lng: float
    distance_m: float


@router.get("/cctv/nearby", response_model=list[CCTVCamera])
async def get_nearby_cctvs(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius: float = Query(default=500, ge=50, le=2000, description="Search radius in meters"),
    limit: int = Query(default=5, ge=1, le=20, description="Max results"),
):
    """Find CCTV cameras near a coordinate.

    Returns nearby cameras with HLS stream URLs for live preview.
    """
    radius_deg = radius / 111320.0

    try:
        async with get_conn() as conn:
            rows = await conn.fetch("""
                SELECT
                    dishub_id,
                    name,
                    stream_url,
                    ST_X(geom) as lng,
                    ST_Y(geom) as lat,
                    ST_Distance(
                        geom::geography,
                        ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography
                    ) as distance_m
                FROM cctv_cameras
                WHERE is_active = TRUE
                  AND ST_DWithin(geom, ST_SetSRID(ST_MakePoint($1, $2), 4326), $3)
                ORDER BY geom <-> ST_SetSRID(ST_MakePoint($1, $2), 4326)
                LIMIT $4
            """, lng, lat, radius_deg, limit)

        return [
            CCTVCamera(
                cctv_id=row["dishub_id"],
                name=row["name"],
                stream_url=row["stream_url"],
                lng=row["lng"],
                lat=row["lat"],
                distance_m=round(row["distance_m"], 1),
            )
            for row in rows
        ]
    except Exception:
        return []


@router.get("/cctv/{cctv_id}/info")
async def get_cctv_info(cctv_id: str):
    """Get info and stream URL for a specific CCTV camera."""
    stream_url = f"{DISHUB_HLS_BASE}/{cctv_id}/stream311.ts"
    return {
        "cctv_id": cctv_id,
        "stream_url": stream_url,
        "hls_base": f"{DISHUB_HLS_BASE}/{cctv_id}/",
        "note": "Use HLS.js to play this stream in browser",
    }
