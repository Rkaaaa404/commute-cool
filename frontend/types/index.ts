export interface Coordinate {
  lat: number;
  lng: number;
}

export interface SegmentDetail {
  segment_id: number;
  tcs_value: number;
  shade_ratio: number;
  apparent_temp: number;
  surface: string | null;
  length_m: number;
}

export interface RouteResult {
  type: 'shortest' | 'most_comfortable';
  distance_m: number;
  duration_min: number;
  sun_exposure_min: number;
  avg_tcs: number;
  within_heat_budget: boolean;
  geometry: GeoJSON.LineString;
  segments: SegmentDetail[];
}

export interface HeatBudget {
  budget_limit_min: number;
  recommended_route: string;
}

export interface RouteResponse {
  routes: RouteResult[];
  weather_alert: string | null;
  heat_budget: HeatBudget;
}

export interface ThermalSegment {
  segment_id: number;
  tcs_value: number;
  geometry: GeoJSON.LineString;
}

export interface CCTVCamera {
  cctv_id: string;
  name: string;
  stream_url: string;
  lat: number;
  lng: number;
  distance_m: number;
}

export type HeatTolerance = 'low' | 'medium' | 'high';
