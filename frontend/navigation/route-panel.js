/**
 * COMMUTE-COOL Route Panel Module
 * Displays route comparison cards with thermal comfort data.
 */

// --- Show Route Panel ---
function showRoutePanel(routeData) {
    const panel = document.getElementById('route-panel');
    const cardsContainer = document.getElementById('route-cards');

    // Clear previous cards
    cardsContainer.innerHTML = '';

    // Generate route cards
    routeData.routes.forEach((route, index) => {
        const card = createRouteCard(route, index);
        cardsContainer.appendChild(card);
    });

    // Show weather info if available
    updateWeatherDisplay();

    // Show panel
    panel.classList.remove('hidden');
}

function createRouteCard(route, index) {
    const card = document.createElement('div');
    card.className = `route-card ${!route.within_heat_budget ? 'over-budget' : ''} ${index === 1 ? 'active' : ''}`;

    const typeLabel = route.type === 'shortest' ? 'Terpendek' : 'Ternyaman';
    const distanceKm = (route.distance_m / 1000).toFixed(1);

    let badge = '';
    if (!route.within_heat_budget) {
        badge = '<span class="route-badge badge-warning">Melebihi Budget</span>';
    } else if (route.type === 'most_comfortable') {
        badge = '<span class="route-badge badge-ok">Rekomendasi</span>';
    }

    const tcsColor = getTCSColor(route.avg_tcs);
    const tcsPercent = Math.round(route.avg_tcs * 100);

    card.innerHTML = `
        <div class="route-card-header">
            <span class="route-type">${typeLabel}</span>
            ${badge}
        </div>
        <div class="route-stats">
            <span class="stat">${distanceKm} km</span>
            <span class="stat">${route.duration_min.toFixed(0)} min</span>
            <span class="stat">${route.sun_exposure_min.toFixed(0)} min sinar</span>
            <span class="stat"><span style="color:${tcsColor}; font-weight:700;">TCS ${route.avg_tcs.toFixed(2)}</span></span>
        </div>
        <div class="tcs-bar-container">
            <div class="tcs-bar" style="width:${tcsPercent}%; background:${tcsColor}; height:3px; border-radius:3px; transition: width 0.3s;"></div>
        </div>
    `;

    // Click to highlight route on map
    card.addEventListener('click', () => {
        document.querySelectorAll('.route-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        highlightRoute(index);
    });

    // Add CCTV preview button
    if (route.geometry && route.geometry.coordinates && route.geometry.coordinates.length > 1) {
        const coords = route.geometry.coordinates;
        const midIdx = Math.floor(coords.length / 2);
        const midLat = coords[midIdx][1];
        const midLng = coords[midIdx][0];
        if (typeof addCCTVButtonToRouteCard === 'function') {
            addCCTVButtonToRouteCard(card, midLat, midLng);
        }
    }

    return card;
}

function highlightRoute(index) {
    // Dim other routes, highlight selected
    routeLayers.forEach((layerId, i) => {
        if (map.getLayer(layerId)) {
            map.setPaintProperty(layerId, 'line-opacity', i === index ? 0.95 : 0.3);
            map.setPaintProperty(layerId, 'line-width', i === index ? 7 : 3);
        }
    });
}

// --- Helper: TCS to Color ---
function getTCSColor(tcs) {
    if (tcs >= 0.7) return '#2ecc71';
    if (tcs >= 0.4) return '#f39c12';
    return '#e74c3c';
}

// --- Weather Display ---
async function updateWeatherDisplay() {
    try {
        const response = await fetch(
            'https://api.open-meteo.com/v1/forecast?latitude=-7.2575&longitude=112.7521&current=temperature_2m,apparent_temperature'
        );
        if (response.ok) {
            const data = await response.json();
            const temp = data.current.temperature_2m;
            const apparent = data.current.apparent_temperature;
            document.getElementById('temp-display').textContent = `${temp}\u00B0C (terasa ${apparent}\u00B0C)`;
        }
    } catch (e) {
        document.getElementById('temp-display').textContent = '33\u00B0C';
    }

    document.getElementById('aqi-display').textContent = 'AQI: 52';
}

// --- Close Panel ---
document.getElementById('close-panel').addEventListener('click', () => {
    document.getElementById('route-panel').classList.add('hidden');
    clearRoutes();
});
