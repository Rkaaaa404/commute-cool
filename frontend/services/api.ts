/**
 * Teduh API Service
 *
 * Semua request ke backend FastAPI terpusat di sini.
 * Base URL dikonfigurasi via environment variable NEXT_PUBLIC_API_URL.
 */

import type { RouteResponse, ThermalSegment, CCTVCamera, HeatTolerance, Coordinate } from '../types';

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api';

// ── Navigation & Routing ─────────────────────────────────────────────────────

export async function fetchRoute(
  origin: Coordinate,
  destination: Coordinate,
  tolerance: HeatTolerance = 'medium'
): Promise<RouteResponse> {
  const res = await fetch(`${API_BASE}/route`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      origin,
      destination,
      user_profile: { heat_tolerance: tolerance, prefer_shade: true },
      departure_time: new Date().toISOString(),
    }),
  });
  if (!res.ok) throw new Error(`Route API error: ${res.status}`);
  return res.json();
}

// ── Map Data ─────────────────────────────────────────────────────────────────

export async function fetchThermalSegments(
  bbox?: { west: number; south: number; east: number; north: number }
): Promise<ThermalSegment[]> {
  try {
    let url = `${API_BASE}/segments/tcs`;
    if (bbox) {
      const params = new URLSearchParams({
        west: String(bbox.west),
        south: String(bbox.south),
        east: String(bbox.east),
        north: String(bbox.north),
      });
      url += `?${params.toString()}`;
    }
    const res = await fetch(url);
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export async function fetchTemperatureHeatmap(): Promise<GeoJSON.FeatureCollection> {
  try {
    const res = await fetch(`${API_BASE}/dashboard/temperature-heatmap`);
    if (!res.ok) return { type: 'FeatureCollection', features: [] };
    return res.json();
  } catch {
    return { type: 'FeatureCollection', features: [] };
  }
}

// ── CCTV ─────────────────────────────────────────────────────────────────────

export async function fetchNearbyCCTV(lat: number, lng: number, radius = 500): Promise<CCTVCamera[]> {
  try {
    const res = await fetch(`${API_BASE}/cctv/nearby?lat=${lat}&lng=${lng}&radius=${radius}&limit=5`);
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

// ── Weather ───────────────────────────────────────────────────────────────────

export async function fetchWeather(): Promise<{ temp: number; apparent: number } | null> {
  try {
    const res = await fetch(
      'https://api.open-meteo.com/v1/forecast?latitude=-7.2575&longitude=112.7521&current=temperature_2m,apparent_temperature'
    );
    if (!res.ok) return null;
    const data = await res.json();
    return {
      temp: data.current.temperature_2m,
      apparent: data.current.apparent_temperature,
    };
  } catch {
    return null;
  }
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export async function fetchDashboardUHI(): Promise<{
  summary: { total_segments: number; critical_segments: number; avg_city_tcs: number };
} | null> {
  try {
    const res = await fetch(`${API_BASE}/dashboard/uhi`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function fetchPriorityCorridors(): Promise<{
  corridors: Array<{
    corridor_name: string;
    avg_tcs: number;
    pedestrian_volume: string;
    nearest_transit: string | null;
    recommendation: string;
    priority_score: number;
  }>;
} | null> {
  try {
    const res = await fetch(`${API_BASE}/dashboard/priority-corridors`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function fetchWalkabilityStats(): Promise<{
  total_transit_stops: number;
  reachable_within_10min: number;
  reachable_percentage: number;
  avg_tcs_city: number;
} | null> {
  try {
    const res = await fetch(`${API_BASE}/dashboard/walkability`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function fetchActiveAlerts(): Promise<Array<{
  title: string;
  description: string;
  severity: string;
}>> {
  try {
    const res = await fetch(`${API_BASE}/dashboard/active-alerts`, { cache: 'no-store' });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export interface HeatZone {
  segment_id: number;
  street_name: string;
  highway_type: string;
  has_shade_tree: boolean;
  current_tcs: number;
  apparent_temp: number;
  shade_ratio: number;
  predicted_tcs_green: number;
  predicted_tcs_cool: number;
  improvement_pct: number;
  severity: 'critical' | 'hot' | 'warm';
}

export interface HourlyTrendPoint {
  hour: number;
  label: string;
  tcs_current: number;
  tcs_green_scenario: number;
  tcs_cool_scenario: number;
  apparent_temp: number;
}

export interface HeatPredictionData {
  summary: {
    total_segments: number;
    hot_segments: number;
    warm_segments: number;
    cool_segments: number;
    hot_percentage: number;
    avg_city_tcs: number;
    avg_apparent_temp: number;
    max_apparent_temp: number;
    peak_heat_hour: number;
  };
  hourly_trend: HourlyTrendPoint[];
  hot_zones: HeatZone[];
}

export async function fetchHeatPrediction(): Promise<HeatPredictionData | null> {
  try {
    const res = await fetch(`${API_BASE}/dashboard/heat-prediction`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
