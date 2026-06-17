'use client';
import { useEffect, useRef, forwardRef, useImperativeHandle } from 'react';
import maplibregl from 'maplibre-gl';
import type { Coordinate, RouteResponse, CCTVCamera } from '../types';
import { fetchThermalSegments, fetchNearbyCCTV } from '../services/api';

const SURABAYA_CENTER: [number, number] = [112.7521, -7.2575];
const LIBERTY_STYLE = 'https://tiles.openfreemap.org/styles/liberty';

export interface MapViewProps {
  origin: Coordinate | null;
  destination: Coordinate | null;
  routeData: RouteResponse | null;
  selectedRouteType: string | null;
  onMapClick: (coord: Coordinate) => void;
  onCCTVClick: (cam: CCTVCamera) => void;
  clickMode: 'origin' | 'destination';
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
  clickMode 
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
    }
  }));

  // Initialize map once
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
      loadHeatmap(map);
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

  // Update cursor based on clickMode
  useEffect(() => {
    if (mapRef.current) {
      mapRef.current.getCanvas().style.cursor = clickMode === 'origin' ? 'crosshair' : 'cell';
    }
  }, [clickMode]);

  // Update origin marker
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    originMarkerRef.current?.remove();
    if (origin) {
      const el = document.createElement('div');
      el.style.cssText = 'width:20px;height:20px;border-radius:50%;background:#457b9d;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;color:white;font-size:10px;font-weight:bold;';
      el.innerHTML = 'A';
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
      el.style.cssText = 'width:20px;height:20px;border-radius:50%;background:#e63946;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;color:white;font-size:10px;font-weight:bold;';
      el.innerHTML = 'B';
      destMarkerRef.current = new maplibregl.Marker({ element: el })
        .setLngLat([destination.lng, destination.lat])
        .addTo(map);
    }
  }, [destination]);

  // Display routes and CCTV
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const applyRoutes = async () => {
      // Cleanup all route layers including outlines
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

        // Add outline for selected route
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

      if (origin && destination) {
        map.fitBounds(
          [
            [Math.min(origin.lng, destination.lng) - 0.005, Math.min(origin.lat, destination.lat) - 0.005],
            [Math.max(origin.lng, destination.lng) + 0.005, Math.max(origin.lat, destination.lat) + 0.005],
          ],
          { padding: {top: 80, bottom: 350, left: 80, right: 80}, pitch: 40 }
        );
      }

      // Fetch CCTV along the comfortable route
      const comfyRoute = routeData.routes.find(r => r.type === 'most_comfortable') || routeData.routes[0];
      if (comfyRoute && comfyRoute.geometry.coordinates.length > 0) {
        const coords = comfyRoute.geometry.coordinates;
        // Sample 3 points along the route to find cameras
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
              
              const el = document.createElement('div');
              el.style.cssText = 'width:24px;height:24px;background:white;border-radius:4px;box-shadow:0 2px 5px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:16px;';
              el.innerHTML = '📷';
              el.onclick = (e) => {
                e.stopPropagation();
                onCCTVClick(cam);
              };

              const marker = new maplibregl.Marker({ element: el })
                .setLngLat([cam.lng, cam.lat])
                .addTo(map);
              
              cctvMarkersRef.current.push(marker);
            }
          });
        }
      }
    };

    if (map.isStyleLoaded()) {
      applyRoutes();
    } else {
      map.once('load', applyRoutes);
    }
  }, [routeData, selectedRouteType, origin, destination, onCCTVClick]);

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />;
});

MapView.displayName = 'MapView';
export default MapView;

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

async function loadHeatmap(map: maplibregl.Map) {
  try {
    const segments = await fetchThermalSegments();
    if (!segments.length) {
      return;
    }

    const geojson: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: segments.map(seg => ({
        type: 'Feature' as const,
        geometry: seg.geometry,
        properties: { tcs: seg.tcs_value, segment_id: seg.segment_id },
      })),
    };

    map.addSource('thermal', { type: 'geojson', data: geojson });

    // Glow layer
    map.addLayer({
      id: 'thermal-glow',
      type: 'line',
      source: 'thermal',
      paint: {
        'line-color': ['interpolate', ['linear'], ['get', 'tcs'],
          0, '#e63946', 0.3, '#f4a261', 0.5, '#e9c46a', 0.7, '#88d498', 1, '#1a936f'],
        'line-width': ['interpolate', ['linear'], ['zoom'], 12, 5, 16, 12],
        'line-opacity': 0.3,
        'line-blur': 3,
      },
    });

    // Crisp layer
    map.addLayer({
      id: 'thermal-line',
      type: 'line',
      source: 'thermal',
      paint: {
        'line-color': ['interpolate', ['linear'], ['get', 'tcs'],
          0, '#e63946', 0.3, '#f4a261', 0.5, '#e9c46a', 0.7, '#88d498', 1, '#1a936f'],
        'line-width': ['interpolate', ['linear'], ['zoom'], 12, 2, 16, 5],
        'line-opacity': 0.75,
      },
    });

    // Click popup
    map.on('click', 'thermal-line', (e) => {
      const props = e.features?.[0]?.properties;
      if (!props) return;
      const tcs = Number(props.tcs).toFixed(2);
      const label = Number(tcs) >= 0.7 ? 'Nyaman' : Number(tcs) >= 0.4 ? 'Sedang' : 'Panas';
      const color = Number(tcs) >= 0.7 ? '#1a936f' : Number(tcs) >= 0.4 ? '#f4a261' : '#e63946';
      new maplibregl.Popup({ closeOnClick: true })
        .setLngLat(e.lngLat)
        .setHTML(`<div style="font-size:12px;font-family:Inter,sans-serif"><b style="color:${color}">TCS: ${tcs}</b><br/><span style="color:#666">${label}</span></div>`)
        .addTo(map);
    });
  } catch (err) {
    console.error('[Heatmap] Failed to load:', err);
  }
}
