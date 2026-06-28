"""End-to-End Test - Full pipeline flow verification.

Tests the complete flow:
1. Ingestion (weather fetch)
2. API health check
3. Route calculation (with demo fallback)
4. CCTV nearby lookup

Requires: API server running (uvicorn api.main:app)
"""

import pytest
import httpx

API_BASE = "http://localhost:8000"


@pytest.mark.asyncio
async def test_health_check():
    """API health endpoint returns 200."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_route_endpoint_validation():
    """Route endpoint validates Surabaya bbox."""
    async with httpx.AsyncClient() as client:
        # Valid Surabaya coordinates
        response = await client.post(f"{API_BASE}/api/route", json={
            "origin": {"lat": -7.2756, "lng": 112.7426},
            "destination": {"lat": -7.2650, "lng": 112.7508},
            "user_profile": {"heat_tolerance": "medium", "prefer_shade": True}
        })
    assert response.status_code == 200
    data = response.json()
    assert "routes" in data
    assert len(data["routes"]) == 2
    assert data["routes"][0]["type"] == "shortest"
    assert data["routes"][1]["type"] == "most_comfortable"


@pytest.mark.asyncio
async def test_route_outside_surabaya_rejected():
    """Coordinates outside Surabaya bbox are rejected."""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_BASE}/api/route", json={
            "origin": {"lat": -6.2, "lng": 106.8},  # Jakarta
            "destination": {"lat": -7.2650, "lng": 112.7508},
        })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_thermal_segments_endpoint():
    """Thermal segments endpoint returns list."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/api/segments/thermal")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_dashboard_uhi():
    """Dashboard UHI endpoint returns valid structure."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/api/dashboard/uhi")
    assert response.status_code == 200
    data = response.json()
    assert "hotspots" in data
    assert "summary" in data


@pytest.mark.asyncio
async def test_dashboard_corridors():
    """Priority corridors endpoint works."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/api/dashboard/priority-corridors")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_cctv_nearby():
    """CCTV nearby endpoint returns cameras."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE}/api/cctv/nearby",
            params={"lat": -7.2679, "lng": 112.7407, "radius": 500}
        )
    # May return empty if DB not seeded, but should not error
    assert response.status_code == 200


def test_weather_collector_import():
    """Weather collector can fetch data without error."""
    from ingestion.weather_collector import fetch_current_weather
    data = fetch_current_weather()
    assert "current" in data
    assert "temperature_2m" in data["current"]


def test_cctv_registry_fetch():
    """CCTV registry can fetch camera list from Dishub."""
    from ingestion.cctv_registry import fetch_cctv_list
    cameras = fetch_cctv_list()
    if not cameras:
        pytest.skip("Dishub Surabaya CCTV API is offline, skipping fetch assertion.")
    assert len(cameras) > 50  # Should have hundreds
    assert "id" in cameras[0]
    assert "lat" in cameras[0]
    assert "lng" in cameras[0]
