"""Pydantic schemas for API request/response validation."""

from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


# --- Route Request/Response ---

class Coordinate(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")


class UserProfileInput(BaseModel):
    heat_tolerance: str = Field(
        default="medium",
        description="Heat tolerance level: low, medium, high"
    )
    prefer_shade: bool = Field(default=True)


class RouteRequest(BaseModel):
    origin: Coordinate
    destination: Coordinate
    user_profile: Optional[UserProfileInput] = None
    departure_time: Optional[datetime] = None


class SegmentDetail(BaseModel):
    segment_id: int
    tcs_value: float
    shade_ratio: float
    apparent_temp: Optional[float] = None
    surface: Optional[str] = None
    length_m: float


class RouteResult(BaseModel):
    type: str  # "shortest" or "most_comfortable"
    distance_m: float
    duration_min: float
    sun_exposure_min: float
    avg_tcs: float
    within_heat_budget: bool
    geometry: dict  # GeoJSON LineString
    segments: list[SegmentDetail]


class HeatBudgetInfo(BaseModel):
    budget_limit_min: float
    recommended_route: str


class RouteResponse(BaseModel):
    routes: list[RouteResult]
    weather_alert: Optional[str] = None
    heat_budget: HeatBudgetInfo


# --- Dashboard Responses ---

class UHIHotspot(BaseModel):
    segment_id: int
    geometry: dict
    avg_lst: float
    avg_tcs: float
    street_name: Optional[str] = None
    shade_ratio: float


class UHISummary(BaseModel):
    total_segments: int
    critical_segments: int
    avg_city_tcs: float


class UHIResponse(BaseModel):
    hotspots: list[UHIHotspot]
    summary: UHISummary


class PriorityCorridor(BaseModel):
    corridor_name: str
    segments: list[int]
    avg_tcs: float
    pedestrian_volume: str
    nearest_transit: Optional[str] = None
    recommendation: str
    priority_score: float


class PriorityCorridorsResponse(BaseModel):
    corridors: list[PriorityCorridor]


class WalkabilityStats(BaseModel):
    total_transit_stops: int
    reachable_within_10min: int
    reachable_percentage: float
    avg_tcs_city: float
    worst_kecamatan: Optional[str] = None
    best_kecamatan: Optional[str] = None


# --- Thermal Heatmap ---

class ThermalSegment(BaseModel):
    segment_id: int
    tcs_value: float
    geometry: dict  # GeoJSON
