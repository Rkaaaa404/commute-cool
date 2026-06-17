import { useEffect, useRef, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import type { Coordinate, RouteResponse } from '../types';
import { fetchThermalSegments } from '../services/api';

const SURABAYA_CENTER: [number, number] = [112.7521, -7.2575];
const LIBERTY_STYLE = 'https://tiles.openfreemap.org/styles/liberty';

interface Props {
  origin: Coordinate | null;
  destination: Coordinate | null;
  routeData: RouteResponse | null;
  onMapClick: (coord: Coordinate) => void;
}

export default function MapView({ origin, destination, routeData, onMapClick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const originMarkerRef = useRef<maplibregl.Marker | null>(null);
  const destMarkerRef = useRef<maplibregl.Marker | null>(null);

  // Initialize map
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: LIBERTY_STYLE,
      center: SURABAYA_CENTER,
      zoom: 14,
      pitch: 45,
      bearing: -17,
      maxBounds: [[112.55, -7.40], [112.90, -7.15]],
      antialias: true,
    });

    map.addControl(new maplibregl.NavigationControl(), 'bottom-right');

    map.on('load', () => {
      addBuildings(map);
      loadHeatmap(map);
    });

    map.on('click', (e) => {
      onMapClick({ lat: e.lngLat.lat, lng: e.lngLat.lng });
    });

    map.getCanvas().style.cursor = 'crosshair';
    mapRef.current = map;

    return () => { map.remove(); mapRef.current = null; };
  }, []);

  // Update click handler ref
  const onMapClickRef = useRef(onMapClick);
  onMapClickRef.current = onMapClick;

  // Update origin marker
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    originMarkerRef.current?.remove();
    if (origin) {
      const el = document.createElement('div');
      el.style.cssText = 'width:14px;height:14px;border-radius:50%;background:#457b9d;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);';
      originMarkerRef.current = new maplibregl.Marker({ element: el })
        .setLngLat([origin.lng, origin.lat])
        .addTo(map);
    }
  }, [origin]);

  // Update destination marker
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    destMarkerRef.current?.remove();
    if (destination) {
      const el = document.createElement('div');
      el.style.cssText = 'width:14px;height:14px;border-radius:50%;background:#e63946;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);';
      destMarkerRef.current = new maplibregl.Marker({ element: el })
        .setLngLat([destination.lng, destination.lat])
        .addTo(map);
    }
  }, [destination]);

  // Display routes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    // Remove old routes
    ['route-0', 'route-1'].forEach(id => {
      if (map.getLayer(id)) map.removeLayer(id);
      if (map.getSource(id)) map.removeSource(id);
    });

    if (!routeData) return;

    routeData.routes.forEach((route, i) => {
      if (!route.geometry?.coordinates?.length) return;
      const id = `route-${i}`;
      const isComfy = route.type === 'most_comfortable';

      map.addSource(id, {
        type: 'geojson',
        data: { type: 'Feature', geometry: route.geometry, properties: {} },
      });

      map.addLayer({
        id,
        type: 'line',
        source: id,
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: {
          'line-color': isComfy ? '#1a936f' : '#457b9d',
          'line-width': isComfy ? 6 : 4,
          'line-opacity': isComfy ? 0.9 : 0.6,
        },
      });
    });

    // Fit bounds
    if (origin && destination) {
      map.fitBounds(
        [[Math.min(origin.lng, destination.lng) - 0.005, Math.min(origin.lat, destination.lat) - 0.005],
         [Math.max(origin.lng, destination.lng) + 0.005, Math.max(origin.lat, destination.lat) + 0.005]],
        { padding: 80, pitch: 40 }
      );
    }
  }, [routeData, origin, destination]);

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />;
}

function addBuildings(map: maplibregl.Map) {
  if (!map.getSource('openmaptiles')) return;
  const layers = map.getStyle().layers || [];
  const labelLayer = layers.find(l => l.type === 'symbol' && l.layout?.['text-field']);

  map.addLayer({
    id: '3d-buildings',
    source: 'openmaptiles',
    'source-layer': 'building',
    type: 'fill-extrusion',
    minzoom: 14,
    paint: {
      'fill-extrusion-color': '#ddd5cc',
      'fill-extrusion-height': ['interpolate', ['linear'], ['zoom'], 14, 0, 15, ['get', 'render_height']],
      'fill-extrusion-base': ['get', 'render_min_height'],
      'fill-extrusion-opacity': 0.7,
    },
  }, labelLayer?.id);
}

async function loadHeatmap(map: maplibregl.Map) {
  const segments = await fetchThermalSegments();
  if (!segments.length) return;

  const geojson = {
    type: 'FeatureCollection' as const,
    features: segments.map(seg => ({
      type: 'Feature' as const,
      geometry: seg.geometry,
      properties: { tcs: seg.tcs_value, segment_id: seg.segment_id },
    })),
  };

  map.addSource('thermal', { type: 'geojson', data: geojson });

  map.addLayer({
    id: 'thermal-glow',
    type: 'line',
    source: 'thermal',
    paint: {
      'line-color': ['interpolate', ['linear'], ['get', 'tcs'], 0, '#e63946', 0.3, '#f4a261', 0.5, '#e9c46a', 0.7, '#88d498', 1, '#1a936f'],
      'line-width': ['interpolate', ['linear'], ['zoom'], 12, 5, 16, 12],
      'line-opacity': 0.3,
      'line-blur': 3,
    },
  });

  map.addLayer({
    id: 'thermal-line',
    type: 'line',
    source: 'thermal',
    paint: {
      'line-color': ['interpolate', ['linear'], ['get', 'tcs'], 0, '#e63946', 0.3, '#f4a261', 0.5, '#e9c46a', 0.7, '#88d498', 1, '#1a936f'],
      'line-width': ['interpolate', ['linear'], ['zoom'], 12, 2, 16, 4],
      'line-opacity': 0.8,
    },
  });

  map.on('click', 'thermal-line', (e) => {
    const props = e.features?.[0]?.properties;
    if (!props) return;
    const tcs = Number(props.tcs).toFixed(2);
    const label = Number(tcs) >= 0.7 ? 'Nyaman' : Number(tcs) >= 0.4 ? 'Sedang' : 'Panas';
    new maplibregl.Popup({ closeOnClick: true })
      .setLngLat(e.lngLat)
      .setHTML(`<div style="font-size:12px"><b>TCS: ${tcs}</b><br/><span style="color:#666">${label}</span></div>`)
      .addTo(map);
  });

  map.on('mouseenter', 'thermal-line', () => { map.getCanvas().style.cursor = 'pointer'; });
  map.on('mouseleave', 'thermal-line', () => { map.getCanvas().style.cursor = 'crosshair'; });
}
