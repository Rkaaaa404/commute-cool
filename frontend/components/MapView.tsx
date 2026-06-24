'use client';
import { useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
import maplibregl from 'maplibre-gl';
import type { Coordinate, RouteResponse, CCTVCamera } from '../types';
import { fetchThermalSegments, fetchNearbyCCTV, fetchTemperatureHeatmap } from '../services/api';
import type { LngLatBoundsLike } from 'maplibre-gl';

const SURABAYA_CENTER: [number, number] = [112.7521, -7.2575];
const LIBERTY_STYLE = 'https://tiles.openfreemap.org/styles/liberty';

/**
 * MapLibre GL expression untuk warna kategoris TCS (step-based).
 * 4 grade yang jelas dan distinct, lebih mudah dibaca dari gradien halus.
 *
 * TCS < 0.3  → Merah   #e63946  (Sangat Panas)
 * TCS < 0.5  → Oranye  #f4a261  (Panas)
 * TCS < 0.7  → Kuning  #e9c46a  (Sedang)
 * TCS ≥ 0.7  → Hijau   #1a936f  (Nyaman)
 */
const TCS_COLOR_EXPRESSION: maplibregl.ExpressionSpecification = [
  'step', ['get', 'tcs'],
  '#e63946',   // default (tcs < 0.3)
  0.3, '#f4a261',   // 0.3 ≤ tcs < 0.5
  0.5, '#e9c46a',   // 0.5 ≤ tcs < 0.7
  0.7, '#1a936f',   // tcs ≥ 0.7
];

/** Helpers */
function tcsGradeLabel(tcs: number): string {
  if (tcs >= 0.7) return '🟢 Nyaman';
  if (tcs >= 0.5) return '🟡 Sedang';
  if (tcs >= 0.3) return '🟠 Panas';
  return '🔴 Sangat Panas';
}

function tcsGradeColor(tcs: number): string {
  if (tcs >= 0.7) return '#1a936f';
  if (tcs >= 0.5) return '#e9c46a';
  if (tcs >= 0.3) return '#f4a261';
  return '#e63946';
}

export interface MapViewProps {
  origin: Coordinate | null;
  destination: Coordinate | null;
  routeData: RouteResponse | null;
  selectedRouteType: string | null;
  onMapClick: (coord: Coordinate) => void;
  onCCTVClick: (cam: CCTVCamera) => void;
  clickMode: 'origin' | 'destination';
  showTempHeatmap?: boolean;
}

export interface MapViewRef {
  flyTo: (coord: Coordinate) => void;
}

const MapView = forwardRef<MapViewRef, MapViewProps>(({
  origin,
  destination,
  routeData,
  selectedRouteType,
  onMapClick,
  onCCTVClick,
  clickMode,
  showTempHeatmap = false,
}, ref) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const originMarkerRef = useRef<maplibregl.Marker | null>(null);
  const destMarkerRef = useRef<maplibregl.Marker | null>(null);
  const cctvMarkersRef = useRef<maplibregl.Marker[]>([]);

  const onMapClickRef = useRef(onMapClick);
  onMapClickRef.current = onMapClick;

  useImperativeHandle(ref, () => ({
    flyTo: (coord: Coordinate) => {
      mapRef.current?.flyTo({
        center: [coord.lng, coord.lat],
        zoom: 16,
        essential: true,
      });
    },
  }));

  // ── Initialize map once ──────────────────────────────────────────────────
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
    });

    map.addControl(new maplibregl.NavigationControl(), 'bottom-right');
    map.addControl(new maplibregl.GeolocateControl({
      positionOptions: { enableHighAccuracy: true },
      trackUserLocation: false,
    }), 'bottom-right');

    map.on('load', () => {
      addBuildings(map);
      loadTCSLayer(map);
      loadTempHeatmapLayer(map);
    });

    // Reload TCS segments when user pans/zooms (viewport-based loading)
    // IMPORTANT: Never replace existing data with empty results to avoid
    // TCS colors disappearing when API returns 0 segments momentarily.
    map.on('moveend', () => {
      if (!map.getSource('thermal')) return;
      // Skip reload when TCS layer is hidden (UHI mode active)
      if (map.getLayer('thermal-line') &&
          map.getLayoutProperty('thermal-line', 'visibility') === 'none') return;
      const b = map.getBounds();
      const bbox = { west: b.getWest(), south: b.getSouth(), east: b.getEast(), north: b.getNorth() };
      fetchThermalSegments(bbox)
        .then(segments => {
          // GUARD: Only update data if we got results back.
          // If API returns empty (network blip, bbox too tight, etc.)
          // keep the existing data visible — do NOT clear it.
          if (!segments.length) return;
          const src = map.getSource('thermal') as maplibregl.GeoJSONSource | undefined;
          if (!src) return;
          const geojson: GeoJSON.FeatureCollection = {
            type: 'FeatureCollection',
            features: segments.map(seg => ({
              type: 'Feature' as const,
              geometry: seg.geometry,
              properties: { tcs: seg.tcs_value, segment_id: seg.segment_id },
            })),
          };
          src.setData(geojson);
        })
        .catch(err => console.warn('[Viewport] TCS reload failed:', err));
    });

    map.on('click', (e) => {
      onMapClickRef.current({ lat: e.lngLat.lat, lng: e.lngLat.lng });
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // ── Update cursor based on clickMode ────────────────────────────────────
  useEffect(() => {
    if (mapRef.current) {
      mapRef.current.getCanvas().style.cursor = clickMode === 'origin' ? 'crosshair' : 'cell';
    }
  }, [clickMode]);

  // ── Toggle between TCS and Temperature Heatmap layers ───────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const applyVisibility = () => {
      const tcsVisible = showTempHeatmap ? 'none' : 'visible';
      const tempVisible = showTempHeatmap ? 'visible' : 'none';
      (['thermal-glow', 'thermal-line'] as const).forEach(id => {
        if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', tcsVisible);
      });
      if (map.getLayer('temp-heatmap-layer')) {
        map.setLayoutProperty('temp-heatmap-layer', 'visibility', tempVisible);
      }

      // When switching BACK to TCS, always re-fetch to guarantee data is shown.
      // This prevents blank TCS map after coming back from UHI or any
      // state change that may have cleared the source data.
      if (!showTempHeatmap && map.getSource('thermal')) {
        const b = map.getBounds();
        const bbox = { west: b.getWest(), south: b.getSouth(), east: b.getEast(), north: b.getNorth() };
        fetchThermalSegments(bbox)
          .then(segments => {
            if (!segments.length) return;  // Guard: keep existing data if nothing returned
            const src = map.getSource('thermal') as maplibregl.GeoJSONSource | undefined;
            if (!src) return;
            const geojson: GeoJSON.FeatureCollection = {
              type: 'FeatureCollection',
              features: segments.map(seg => ({
                type: 'Feature' as const,
                geometry: seg.geometry,
                properties: { tcs: seg.tcs_value, segment_id: seg.segment_id },
              })),
            };
            src.setData(geojson);
          })
          .catch(err => console.warn('[TCS Toggle] Reload failed:', err));
      }
    };

    if (map.getLayer('thermal-line')) {
      applyVisibility();
    } else {
      map.once('idle', applyVisibility);
    }
  }, [showTempHeatmap]);

  // ── Update origin marker ─────────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    originMarkerRef.current?.remove();
    if (origin) {
      originMarkerRef.current = new maplibregl.Marker({ element: createPinMarker('A', '#457b9d') })
        .setLngLat([origin.lng, origin.lat])
        .addTo(map);
    }
  }, [origin]);

  // ── Update destination marker ────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    destMarkerRef.current?.remove();
    if (destination) {
      destMarkerRef.current = new maplibregl.Marker({ element: createPinMarker('B', '#e63946') })
        .setLngLat([destination.lng, destination.lat])
        .addTo(map);
    }
  }, [destination]);

  // ── Display routes and CCTV ──────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const applyRoutes = async () => {
      // Cleanup all previous route layers & sources
      ['route-0-outline', 'route-1-outline', 'route-0', 'route-1'].forEach(id => {
        if (map.getLayer(id)) map.removeLayer(id);
      });
      ['route-0', 'route-1'].forEach(id => {
        if (map.getSource(id)) map.removeSource(id);
      });

      // Clear old CCTV markers
      cctvMarkersRef.current.forEach(m => m.remove());
      cctvMarkersRef.current = [];

      if (!routeData) return;

      routeData.routes.forEach((route, i) => {
        if (!route.geometry?.coordinates?.length) return;
        const id = `route-${i}`;

        map.addSource(id, {
          type: 'geojson',
          data: { type: 'Feature', geometry: route.geometry, properties: {} },
        });

        const isSelected = selectedRouteType === route.type;
        const isComfy = route.type === 'most_comfortable';

        // White outline for selected route
        if (isSelected) {
          map.addLayer({
            id: `${id}-outline`,
            type: 'line',
            source: id,
            layout: { 'line-join': 'round', 'line-cap': 'round' },
            paint: {
              'line-color': '#ffffff',
              'line-width': 10,
              'line-opacity': 0.8,
            },
          });
        }

        map.addLayer({
          id,
          type: 'line',
          source: id,
          layout: { 'line-join': 'round', 'line-cap': 'round' },
          paint: {
            'line-color': isComfy ? '#1a936f' : '#457b9d',
            'line-width': isSelected ? 6 : 4,
            'line-opacity': isSelected ? 1.0 : 0.4,
          },
        });
      });

      // Fit map to route bounds
      if (routeData.routes.length > 0) {
        let minLng = 180, maxLng = -180, minLat = 90, maxLat = -90;
        routeData.routes.forEach(route => {
          route.geometry?.coordinates?.forEach(([lng, lat]) => {
            if (lng < minLng) minLng = lng;
            if (lng > maxLng) maxLng = lng;
            if (lat < minLat) minLat = lat;
            if (lat > maxLat) maxLat = lat;
          });
        });
        if (minLng === maxLng) { minLng -= 0.001; maxLng += 0.001; }
        if (minLat === maxLat) { minLat -= 0.001; maxLat += 0.001; }

        map.fitBounds(
          [[minLng, minLat], [maxLng, maxLat]] as LngLatBoundsLike,
          { padding: { top: 80, bottom: 80, left: 380, right: 80 }, maxZoom: 16 }
        );
      } else if (origin && destination) {
        map.fitBounds(
          [
            [Math.min(origin.lng, destination.lng) - 0.005, Math.min(origin.lat, destination.lat) - 0.005],
            [Math.max(origin.lng, destination.lng) + 0.005, Math.max(origin.lat, destination.lat) + 0.005],
          ],
          { padding: { top: 80, bottom: 80, left: 380, right: 80 }, maxZoom: 16 }
        );
      }

      // Fetch CCTV along the comfortable route
      const comfyRoute = routeData.routes.find(r => r.type === 'most_comfortable') || routeData.routes[0];
      if (comfyRoute?.geometry.coordinates.length > 0) {
        const coords = comfyRoute.geometry.coordinates;
        const samples = [
          coords[Math.floor(coords.length * 0.25)],
          coords[Math.floor(coords.length * 0.5)],
          coords[Math.floor(coords.length * 0.75)],
        ];

        const seenIds = new Set<string>();
        for (const pt of samples) {
          const cameras = await fetchNearbyCCTV(pt[1], pt[0], 800);
          cameras.forEach(cam => {
            if (!seenIds.has(cam.cctv_id)) {
              seenIds.add(cam.cctv_id);
              const el = createCCTVMarker();
              el.onclick = (e) => { e.stopPropagation(); onCCTVClick(cam); };
              const marker = new maplibregl.Marker({ element: el })
                .setLngLat([cam.lng, cam.lat])
                .addTo(map);
              cctvMarkersRef.current.push(marker);
            }
          });
        }
      }
    };

    if (map.isStyleLoaded()) applyRoutes();
    else map.once('load', applyRoutes);
  }, [routeData, selectedRouteType, origin, destination, onCCTVClick]);

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />;
});

MapView.displayName = 'MapView';
export default MapView;

// ── Helper: create custom DOM pin marker ────────────────────────────────────
function createPinMarker(label: string, color: string): HTMLDivElement {
  const el = document.createElement('div');
  el.style.cssText = `width:24px;height:24px;border-radius:50%;background:${color};border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;color:white;font-size:11px;font-weight:bold;`;
  el.innerHTML = label;
  return el;
}

// ── Helper: create CCTV camera marker ───────────────────────────────────────
function createCCTVMarker(): HTMLDivElement {
  const el = document.createElement('div');
  el.style.cssText = 'width:24px;height:24px;background:white;border-radius:4px;box-shadow:0 2px 5px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:16px;';
  el.innerHTML = '📷';
  return el;
}

// ── Map layer: 3D Buildings ──────────────────────────────────────────────────
function addBuildings(map: maplibregl.Map) {
  if (!map.getSource('openmaptiles')) return;
  const layers = map.getStyle().layers || [];
  const labelLayer = layers.find(l => l.type === 'symbol' && (l as any).layout?.['text-field']);

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

// ── Map layer: TCS Comfort Line Layer ───────────────────────────────────────
async function loadTCSLayer(map: maplibregl.Map) {
  try {
    const segments = await fetchThermalSegments();
    if (!segments.length) return;

    const geojson: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: segments.map(seg => ({
        type: 'Feature' as const,
        geometry: seg.geometry,
        properties: { tcs: seg.tcs_value, segment_id: seg.segment_id },
      })),
    };

    map.addSource('thermal', { type: 'geojson', data: geojson });

    // Soft glow layer (background halo)
    map.addLayer({
      id: 'thermal-glow',
      type: 'line',
      source: 'thermal',
      paint: {
        'line-color': TCS_COLOR_EXPRESSION,
        'line-width': ['interpolate', ['linear'], ['zoom'], 12, 5, 16, 12],
        'line-opacity': 0.25,
        'line-blur': 4,
      },
    });

    // Crisp categorical color layer
    map.addLayer({
      id: 'thermal-line',
      type: 'line',
      source: 'thermal',
      paint: {
        'line-color': TCS_COLOR_EXPRESSION,
        'line-width': ['interpolate', ['linear'], ['zoom'], 12, 2, 16, 5],
        'line-opacity': 0.85,
      },
    });

    // Detailed popup on segment click
    map.on('click', 'thermal-line', (e) => {
      const props = e.features?.[0]?.properties;
      if (!props) return;
      const tcs = Number(props.tcs);
      const grade = tcsGradeLabel(tcs);
      const color = tcsGradeColor(tcs);
      new maplibregl.Popup({ closeOnClick: true })
        .setLngLat(e.lngLat)
        .setHTML(`
          <div style="font-size:12px;font-family:Inter,sans-serif;padding:4px 2px">
            <div style="font-weight:700;color:${color};font-size:13px">${grade}</div>
            <div style="color:#555;margin-top:2px">TCS: <b>${tcs.toFixed(3)}</b></div>
            <div style="color:#888;font-size:11px;margin-top:1px">Klik rute untuk detail segmen</div>
          </div>
        `)
        .addTo(map);
    });

    // Pointer cursor on hover
    map.on('mouseenter', 'thermal-line', () => {
      map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', 'thermal-line', () => {
      map.getCanvas().style.cursor = '';
    });
  } catch (err) {
    console.error('[TCS Layer] Failed to load:', err);
  }
}

// ── Map layer: Temperature Heatmap (UHI) ────────────────────────────────────
async function loadTempHeatmapLayer(map: maplibregl.Map) {
  try {
    const tempGeojson = await fetchTemperatureHeatmap();
    map.addSource('temp-heatmap', { type: 'geojson', data: tempGeojson });

    map.addLayer({
      id: 'temp-heatmap-layer',
      type: 'heatmap',
      source: 'temp-heatmap',
      maxzoom: 18,
      paint: {
        'heatmap-weight': ['interpolate', ['linear'], ['get', 'temp'], 28, 0, 45, 1],
        'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 12, 1, 18, 3],
        'heatmap-color': [
          'interpolate', ['linear'], ['heatmap-density'],
          0,   'rgba(33,102,172,0)',
          0.2, 'rgb(103,169,207)',
          0.4, 'rgb(209,229,240)',
          0.6, 'rgb(253,219,199)',
          0.8, 'rgb(239,138,98)',
          1,   'rgb(178,24,43)',
        ],
        'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 12, 15, 18, 40],
        'heatmap-opacity': 0.8,
      },
    });

    // Hidden by default — toggled by layer switcher
    map.setLayoutProperty('temp-heatmap-layer', 'visibility', 'none');
  } catch (err) {
    console.error('[Temp Heatmap] Failed to load:', err);
  }
}
