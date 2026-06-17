import type { RouteResponse, ThermalSegment, CCTVCamera, HeatTolerance, Coordinate } from '../types';

const API_BASE = 'http://localhost:8000/api';

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

export async function fetchThermalSegments(): Promise<ThermalSegment[]> {
  const res = await fetch(`${API_BASE}/segments/thermal`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchNearbyCCTV(lat: number, lng: number, radius = 500): Promise<CCTVCamera[]> {
  try {
    const res = await fetch(`${API_BASE}/cctv/nearby?lat=${lat}&lng=${lng}&radius=${radius}&limit=5`);
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

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
