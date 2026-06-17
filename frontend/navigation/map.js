/**
 * COMMUTE-COOL Map Module
 * MapLibre GL JS with 3D buildings - No API key needed
 *
 * Uses OpenFreeMap tiles (completely free, no registration)
 */

// --- Configuration ---
const SURABAYA_CENTER = [112.7521, -7.2575]; // [lng, lat]
const INITIAL_ZOOM = 14;
const INITIAL_PITCH = 50; // 3D tilt angle
const INITIAL_BEARING = -17;

// API URL - direct to FastAPI backend (no nginx proxy in dev mode)
const API_BASE_URL = 'http://localhost:8000/api';

// Free tile sources (no API key required)
const MAP_STYLE = {
    version: 8,
    name: 'COMMUTE-COOL Surabaya',
    sources: {
        'osm-tiles': {
            type: 'raster',
            tiles: [
                'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
            ],
            tileSize: 256,
            attribution: '&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>'
        },
        'openmaptiles': {
            type: 'vector',
            url: 'https://tiles.openfreemap.org/planet'
        }
    },
    layers: [
        {
            id: 'osm-raster',
            type: 'raster',
            source: 'osm-tiles',
            minzoom: 0,
            maxzoom: 19
        }
    ]
};

// Simpler style using OpenFreeMap's pre-built style
const LIBERTY_STYLE = 'https://tiles.openfreemap.org/styles/liberty';

// --- State ---
let map;
let originMarker = null;
let destMarker = null;
let originCoords = null;
let destCoords = null;
let routeLayers = [];
let clickMode = 'origin'; // 'origin' or 'destination'

// --- Initialize Map ---
function initMap() {
    map = new maplibregl.Map({
        container: 'map',
        style: LIBERTY_STYLE,
        center: SURABAYA_CENTER,
        zoom: INITIAL_ZOOM,
        pitch: INITIAL_PITCH,
        bearing: INITIAL_BEARING,
        maxBounds: [[112.55, -7.40], [112.90, -7.15]], // Surabaya bounds
        antialias: true,
    });

    map.addControl(new maplibregl.NavigationControl(), 'bottom-right');
    map.addControl(new maplibregl.GeolocateControl({
        positionOptions: { enableHighAccuracy: true },
        trackUserLocation: false
    }), 'bottom-right');

    map.on('load', () => {
        add3DBuildings();
        setupClickHandler();
        loadThermalHeatmap();
        loadCCTVMarkers();
        console.log('[COMMUTE-COOL] Map loaded with 3D buildings + CCTV');
    });
}

// --- 3D Buildings Layer ---
function add3DBuildings() {
    // Check if the source has building data
    const layers = map.getStyle().layers;
    const labelLayerId = layers.find(
        (layer) => layer.type === 'symbol' && layer.layout && layer.layout['text-field']
    );

    // Add 3D building extrusion layer
    if (map.getSource('openmaptiles')) {
        map.addLayer(
            {
                id: '3d-buildings',
                source: 'openmaptiles',
                'source-layer': 'building',
                type: 'fill-extrusion',
                minzoom: 14,
                paint: {
                    'fill-extrusion-color': [
                        'interpolate',
                        ['linear'],
                        ['get', 'render_height'],
                        0, '#e8e0d8',
                        20, '#d4c8b8',
                        50, '#c0b0a0'
                    ],
                    'fill-extrusion-height': [
                        'interpolate',
                        ['linear'],
                        ['zoom'],
                        14, 0,
                        15, ['get', 'render_height']
                    ],
                    'fill-extrusion-base': ['get', 'render_min_height'],
                    'fill-extrusion-opacity': 0.75,
                },
            },
            labelLayerId ? labelLayerId.id : undefined
        );
    }
}

// --- Click Handler for Origin/Destination ---
function setupClickHandler() {
    map.on('click', (e) => {
        const { lng, lat } = e.lngLat;

        if (clickMode === 'origin') {
            setOrigin(lng, lat);
            clickMode = 'destination';
        } else {
            setDestination(lng, lat);
            clickMode = 'origin';
        }

        updateCalculateButton();
    });

    // Update cursor
    map.getCanvas().style.cursor = 'crosshair';
}

function setOrigin(lng, lat) {
    originCoords = [lng, lat];

    if (originMarker) originMarker.remove();

    const el = document.createElement('div');
    el.className = 'marker-origin';
    originMarker = new maplibregl.Marker({ element: el })
        .setLngLat([lng, lat])
        .addTo(map);

    document.getElementById('origin-input').value =
        `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
}

function setDestination(lng, lat) {
    destCoords = [lng, lat];

    if (destMarker) destMarker.remove();

    const el = document.createElement('div');
    el.className = 'marker-dest';
    destMarker = new maplibregl.Marker({ element: el })
        .setLngLat([lng, lat])
        .addTo(map);

    document.getElementById('dest-input').value =
        `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
}

function updateCalculateButton() {
    const btn = document.getElementById('calculate-btn');
    btn.disabled = !(originCoords && destCoords);
}

// --- Route Display ---
function displayRoutes(routeData) {
    clearRoutes();

    routeData.routes.forEach((route, index) => {
        if (!route.geometry || !route.geometry.coordinates || route.geometry.coordinates.length === 0) {
            return;
        }

        const layerId = `route-${index}`;

        // If route has per-segment TCS data, render with gradient colors
        if (route.segments && route.segments.length > 0 && route.geometry.coordinates.length > 2) {
            displayRouteWithTCSGradient(route, layerId);
        } else {
            // Fallback: single-color route line
            map.addSource(layerId, {
                type: 'geojson',
                data: {
                    type: 'Feature',
                    geometry: route.geometry,
                    properties: { type: route.type, avg_tcs: route.avg_tcs }
                }
            });

            const color = route.type === 'most_comfortable' ? '#27ae60' : '#3498db';
            const width = route.type === 'most_comfortable' ? 6 : 4;
            const opacity = route.type === 'most_comfortable' ? 0.9 : 0.6;

            map.addLayer({
                id: layerId,
                type: 'line',
                source: layerId,
                layout: {
                    'line-join': 'round',
                    'line-cap': 'round'
                },
                paint: {
                    'line-color': color,
                    'line-width': width,
                    'line-opacity': opacity
                }
            });
        }

        routeLayers.push(layerId);
    });

    // Fit map to show both routes
    if (originCoords && destCoords) {
        const bounds = new maplibregl.LngLatBounds()
            .extend(originCoords)
            .extend(destCoords);
        map.fitBounds(bounds, { padding: 80, pitch: 45 });
    }
}

function displayRouteWithTCSGradient(route, layerId) {
    /**
     * Render route as multiple line segments, each colored by its TCS value.
     * Green (TCS > 0.7) → Yellow (0.4-0.7) → Red (< 0.4)
     */
    const features = [];
    const coords = route.geometry.coordinates;
    const segments = route.segments;

    // Match segments to coordinate pairs
    for (let i = 0; i < segments.length && i < coords.length - 1; i++) {
        const seg = segments[i];
        const tcs = seg.tcs_value || 0.5;

        features.push({
            type: 'Feature',
            geometry: {
                type: 'LineString',
                coordinates: [coords[i], coords[i + 1]]
            },
            properties: {
                tcs: tcs,
                segment_id: seg.segment_id
            }
        });
    }

    // If we have more coords than segments, add remaining with avg TCS
    if (coords.length - 1 > segments.length) {
        for (let i = segments.length; i < coords.length - 1; i++) {
            features.push({
                type: 'Feature',
                geometry: {
                    type: 'LineString',
                    coordinates: [coords[i], coords[i + 1]]
                },
                properties: { tcs: route.avg_tcs }
            });
        }
    }

    const geojson = { type: 'FeatureCollection', features };

    map.addSource(layerId, { type: 'geojson', data: geojson });

    map.addLayer({
        id: layerId,
        type: 'line',
        source: layerId,
        layout: {
            'line-join': 'round',
            'line-cap': 'round'
        },
        paint: {
            'line-color': [
                'interpolate',
                ['linear'],
                ['get', 'tcs'],
                0.0, '#e74c3c',
                0.3, '#e67e22',
                0.5, '#f39c12',
                0.7, '#f1c40f',
                0.85, '#2ecc71',
                1.0, '#27ae60'
            ],
            'line-width': route.type === 'most_comfortable' ? 7 : 5,
            'line-opacity': route.type === 'most_comfortable' ? 0.9 : 0.65
        }
    });
}

function displayThermalSegments(segments) {
    /**
     * Render thermal heatmap overlay: all pedestrian segments colored by TCS.
     * Green (TCS > 0.7) → Yellow (0.4-0.7) → Red (< 0.4)
     * Uses two layers: glow (wider, blurred) + crisp line on top.
     */
    // Remove existing layers if present
    ['thermal-glow', 'thermal-layer'].forEach(id => {
        if (map.getLayer(id)) map.removeLayer(id);
    });
    if (map.getSource('thermal-segments')) {
        map.removeSource('thermal-segments');
    }

    if (!segments || segments.length === 0) return;

    const geojson = {
        type: 'FeatureCollection',
        features: segments.map(seg => ({
            type: 'Feature',
            geometry: seg.geometry,
            properties: {
                tcs: seg.tcs_value,
                segment_id: seg.segment_id
            }
        }))
    };

    map.addSource('thermal-segments', { type: 'geojson', data: geojson });

    // Glow layer (wider, semi-transparent for heat effect)
    map.addLayer({
        id: 'thermal-glow',
        type: 'line',
        source: 'thermal-segments',
        paint: {
            'line-color': [
                'interpolate',
                ['linear'],
                ['get', 'tcs'],
                0.0, '#e74c3c',
                0.3, '#e67e22',
                0.5, '#f39c12',
                0.7, '#f1c40f',
                0.85, '#2ecc71',
                1.0, '#27ae60'
            ],
            'line-width': [
                'interpolate', ['linear'], ['zoom'],
                12, 6,
                16, 14
            ],
            'line-opacity': 0.35,
            'line-blur': 3
        }
    });

    // Crisp line layer on top
    map.addLayer({
        id: 'thermal-layer',
        type: 'line',
        source: 'thermal-segments',
        paint: {
            'line-color': [
                'interpolate',
                ['linear'],
                ['get', 'tcs'],
                0.0, '#e74c3c',
                0.3, '#e67e22',
                0.5, '#f39c12',
                0.7, '#f1c40f',
                0.85, '#2ecc71',
                1.0, '#27ae60'
            ],
            'line-width': [
                'interpolate', ['linear'], ['zoom'],
                12, 2,
                16, 5
            ],
            'line-opacity': 0.8
        }
    });

    // Add click interaction for segment info
    map.on('click', 'thermal-layer', (e) => {
        const props = e.features[0].properties;
        const tcs = props.tcs.toFixed(2);
        const level = tcs >= 0.7 ? 'Nyaman' : (tcs >= 0.4 ? 'Sedang' : 'Panas');
        const color = tcs >= 0.7 ? '#1a936f' : (tcs >= 0.4 ? '#f4a261' : '#e63946');
        new maplibregl.Popup({ closeOnClick: true })
            .setLngLat(e.lngLat)
            .setHTML(`<div style="font-family:Inter,sans-serif;font-size:12px;"><strong style="color:${color}">TCS: ${tcs}</strong><br><span style="color:#667085">${level} &middot; Segment #${props.segment_id}</span></div>`)
            .addTo(map);
    });

    map.on('mouseenter', 'thermal-layer', () => {
        map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', 'thermal-layer', () => {
        map.getCanvas().style.cursor = 'crosshair';
    });
}

function clearRoutes() {
    routeLayers.forEach(layerId => {
        if (map.getLayer(layerId)) map.removeLayer(layerId);
        if (map.getSource(layerId)) map.removeSource(layerId);
    });
    routeLayers = [];
}

// --- API Calls ---
async function calculateRoute() {
    if (!originCoords || !destCoords) return;

    const tolerance = document.getElementById('tolerance-select').value;

    const requestBody = {
        origin: { lat: originCoords[1], lng: originCoords[0] },
        destination: { lat: destCoords[1], lng: destCoords[0] },
        user_profile: { heat_tolerance: tolerance, prefer_shade: true },
        departure_time: new Date().toISOString()
    };

    try {
        const response = await fetch(`${API_BASE_URL}/route`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) throw new Error(`API error: ${response.status}`);

        const data = await response.json();
        displayRoutes(data);
        showRoutePanel(data);

    } catch (error) {
        console.error('[Route]', error);
        // Show demo/fallback data
        showDemoRoute();
    }
}

async function loadThermalHeatmap() {
    /**
     * Load all segments with TCS values and display as a city-wide heatmap overlay.
     */
    try {
        const response = await fetch(`${API_BASE_URL}/segments/thermal`);
        if (!response.ok) {
            console.log('[Thermal] API returned', response.status);
            return;
        }
        const segments = await response.json();
        if (!segments || segments.length === 0) {
            console.log('[Thermal] No thermal data yet. Run spark pipeline to generate TCS data.');
            return;
        }
        console.log(`[Thermal] Loaded ${segments.length} segments for heatmap`);
        displayThermalSegments(segments);
    } catch (error) {
        console.log('[Thermal] API not available:', error.message);
    }
}

async function loadThermalSegments() {
    // Alias for backward compatibility
    return loadThermalHeatmap();
}

// --- Demo/Fallback Route (when API is not running) ---
function showDemoRoute() {
    const demoData = {
        routes: [
            {
                type: 'shortest',
                distance_m: 1250,
                duration_min: 15.6,
                sun_exposure_min: 12.3,
                avg_tcs: 0.42,
                within_heat_budget: false,
                geometry: {
                    type: 'LineString',
                    coordinates: originCoords && destCoords ? [
                        originCoords,
                        [(originCoords[0] + destCoords[0]) / 2, (originCoords[1] + destCoords[1]) / 2],
                        destCoords
                    ] : []
                },
                segments: []
            },
            {
                type: 'most_comfortable',
                distance_m: 1480,
                duration_min: 18.5,
                sun_exposure_min: 5.1,
                avg_tcs: 0.78,
                within_heat_budget: true,
                geometry: {
                    type: 'LineString',
                    coordinates: originCoords && destCoords ? [
                        originCoords,
                        [originCoords[0] + 0.002, originCoords[1] - 0.001],
                        [(originCoords[0] + destCoords[0]) / 2 + 0.001, (originCoords[1] + destCoords[1]) / 2 - 0.0005],
                        [destCoords[0] - 0.001, destCoords[1] + 0.0005],
                        destCoords
                    ] : []
                },
                segments: []
            }
        ],
        weather_alert: null,
        heat_budget: { budget_limit_min: 15, recommended_route: 'most_comfortable' }
    };

    displayRoutes(demoData);
    showRoutePanel(demoData);
}

// --- Event Listeners ---
document.getElementById('calculate-btn').addEventListener('click', calculateRoute);

// Heatmap toggle
document.getElementById('heatmap-toggle').addEventListener('change', (e) => {
    const visibility = e.target.checked ? 'visible' : 'none';
    ['thermal-glow', 'thermal-layer'].forEach(id => {
        if (map.getLayer(id)) {
            map.setLayoutProperty(id, 'visibility', visibility);
        }
    });
});

// --- CCTV Markers on Navigation Map ---
let cctvMarkersVisible = true;
let cctvMarkerElements = [];

async function loadCCTVMarkers() {
    /**
     * Load CCTV cameras and display as clickable markers on the navigation map.
     * Uses Dishub API directly or our backend as fallback.
     */
    try {
        // Try our API first (nearby center of Surabaya)
        let cameras = [];
        try {
            const res = await fetch(`${API_BASE_URL}/cctv/nearby?lat=-7.2575&lng=112.7521&radius=5000&limit=20`);
            if (res.ok) cameras = await res.json();
        } catch (e) { /* fallback below */ }

        // Fallback: try Dishub directly
        if (cameras.length === 0) {
            try {
                const res = await fetch('http://36.66.208.101:5000/cctvs');
                if (res.ok) {
                    const all = await res.json();
                    cameras = all.slice(0, 30).map(cam => ({
                        cctv_id: cam.id,
                        name: cam.name,
                        lat: cam.lat,
                        lng: cam.lng,
                        stream_url: `http://36.66.208.101:5000/hls/${cam.id}/index.m3u8`
                    }));
                }
            } catch (e) { /* no CCTV available */ }
        }

        if (cameras.length === 0) {
            console.log('[CCTV] No cameras available');
            return;
        }

        console.log(`[CCTV] Loaded ${cameras.length} cameras`);

        cameras.forEach(cam => {
            const el = document.createElement('div');
            el.className = 'marker-cctv';
            el.innerHTML = '<svg viewBox="0 0 24 24" fill="white"><path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/></svg>';
            el.title = cam.name;

            const marker = new maplibregl.Marker({ element: el })
                .setLngLat([cam.lng, cam.lat])
                .addTo(map);

            el.addEventListener('click', (e) => {
                e.stopPropagation();
                if (typeof openCCTVModal === 'function') {
                    openCCTVModal(cam.cctv_id, cam.name, null);
                }
            });

            cctvMarkerElements.push(marker);
        });
    } catch (error) {
        console.log('[CCTV] Could not load cameras:', error.message);
    }
}

// Initialize
initMap();
