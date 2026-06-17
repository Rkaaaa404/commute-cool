/**
 * COMMUTE-COOL Government Dashboard
 * Data visualization for city planning & thermal comfort monitoring.
 */

const API_BASE = 'http://localhost:8000/api';
const DISHUB_CCTV_API = 'http://36.66.208.101:5000/cctvs';
const DISHUB_HLS_BASE = 'http://36.66.208.101:5000/hls';

// ===== LIVE DATA LOADING =====
async function loadDashboardData() {
    try {
        // Fetch walkability stats
        const walkRes = await fetch(`${API_BASE}/dashboard/walkability`);
        if (walkRes.ok) {
            const walk = await walkRes.json();
            const statCards = document.querySelectorAll('.stat-value');
            // Update stat cards if they exist
            if (statCards.length >= 3) {
                statCards[0].textContent = walk.total_transit_stops;
                statCards[1].textContent = `${walk.reachable_percentage.toFixed(0)}%`;
                statCards[2].textContent = walk.avg_tcs_city.toFixed(2);
            }
        }
    } catch (e) {
        console.log('[Dashboard] API not available, using static data');
    }
}
loadDashboardData();

// ===== TAB NAVIGATION =====
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');

        // Init maps on first tab switch
        if (tab.dataset.tab === 'uhi') initUHIMap();
        if (tab.dataset.tab === 'transit') initTransitMap();
        if (tab.dataset.tab === 'cctv') initCCTVMap();
    });
});

// ===== DATETIME =====
document.getElementById('datetime-display').textContent =
    new Date().toLocaleDateString('id-ID', {
        weekday: 'long', year: 'numeric', month: 'long',
        day: 'numeric', hour: '2-digit', minute: '2-digit'
    });

// ===== OVERVIEW: Walkability Chart =====
(function renderWalkabilityChart() {
    const ctx = document.getElementById('walkability-chart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Genteng', 'Tegalsari', 'Gubeng', 'Wonokromo', 'Sawahan', 'Bubutan', 'Simokerto', 'Tambaksari'],
            datasets: [{
                label: 'Avg TCS',
                data: [0.62, 0.48, 0.55, 0.41, 0.38, 0.44, 0.35, 0.50],
                backgroundColor: ctx2 => {
                    const v = ctx2.raw;
                    if (v >= 0.6) return 'rgba(46, 204, 113, 0.8)';
                    if (v >= 0.4) return 'rgba(243, 156, 18, 0.8)';
                    return 'rgba(231, 76, 60, 0.8)';
                },
                borderRadius: 6,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, max: 1.0, title: { display: true, text: 'TCS Score' },
                     grid: { color: '#f0f0f0' } },
                x: { title: { display: true, text: 'Kecamatan' } }
            }
        }
    });
})();

// ===== OVERVIEW: Temperature Chart =====
(function renderTempChart() {
    const ctx = document.getElementById('temp-chart').getContext('2d');
    const hours = ['06', '07', '08', '09', '10', '11', '12', '13', '14', '15', '16', '17'];
    const airTemp = [27, 28, 30, 32, 34, 35, 36, 36, 35, 34, 33, 31];
    const apparentTemp = [28, 30, 33, 36, 38, 40, 41, 41, 40, 38, 36, 33];
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: hours.map(h => h + ':00'),
            datasets: [
                { label: 'Suhu Udara (°C)', data: airTemp, borderColor: '#3498db', tension: 0.3, fill: false },
                { label: 'Apparent Temp (°C)', data: apparentTemp, borderColor: '#e74c3c', tension: 0.3, fill: false, borderDash: [5,5] }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom' } },
            scales: {
                y: { title: { display: true, text: '°C' }, grid: { color: '#f0f0f0' } },
                x: { title: { display: true, text: 'Jam (WIB)' } }
            }
        }
    });
})();

// ===== OVERVIEW: Top Corridors =====
(function renderTopCorridors() {
    const data = [
        { name: 'Jl. Ahmad Yani (Wonokromo-Margorejo)', tcs: 0.20, lst: 43.2, shade: '3%', rec: 'Pohon + pelebaran trotoar' },
        { name: 'Jl. Basuki Rahmat (Tunjungan-Gub.Suryo)', tcs: 0.22, lst: 42.5, shade: '8%', rec: 'Pohon peneduh + kanopi' },
        { name: 'Jl. Pemuda (Gubeng-BG Junction)', tcs: 0.25, lst: 41.8, shade: '5%', rec: 'Pohon + shelter halte' },
        { name: 'Jl. Tunjungan (Genteng-Siola)', tcs: 0.28, lst: 40.2, shade: '12%', rec: 'Kanopi buatan' },
        { name: 'Jl. Urip Sumoharjo (Biliton-Gubeng)', tcs: 0.30, lst: 39.8, shade: '10%', rec: 'Pohon peneduh' },
    ];
    const tbody = document.getElementById('top-corridors-tbody');
    data.forEach((c, i) => {
        const cls = c.tcs < 0.25 ? 'tcs-low' : c.tcs < 0.4 ? 'tcs-med' : 'tcs-high';
        tbody.innerHTML += `<tr>
            <td><strong>${i+1}</strong></td><td>${c.name}</td>
            <td><span class="tcs-badge ${cls}">${c.tcs.toFixed(2)}</span></td>
            <td>${c.lst}°C</td><td>${c.shade}</td><td>${c.rec}</td>
        </tr>`;
    });
})();

// ===== CORRIDORS TAB =====
(function renderCorridorsTab() {
    const corridors = [
        { name: 'Jl. Ahmad Yani (Wonokromo - Margorejo)', tcs: 0.20, vol: 'Sangat Tinggi', transit: 'Halte Suroboyo Bus Wonokromo', rec: 'Pohon peneduh + pelebaran trotoar', cost: 'Rp 2.5 M' },
        { name: 'Jl. Basuki Rahmat (Tunjungan - Gub. Suryo)', tcs: 0.22, vol: 'Sangat Tinggi', transit: 'Halte Suroboyo Bus Tunjungan', rec: 'Pohon peneduh + kanopi', cost: 'Rp 3.2 M' },
        { name: 'Jl. Pemuda (Gubeng - BG Junction)', tcs: 0.25, vol: 'Tinggi', transit: 'Stasiun Gubeng', rec: 'Pohon + shelter', cost: 'Rp 1.8 M' },
        { name: 'Jl. Tunjungan (Genteng - Siola)', tcs: 0.28, vol: 'Tinggi', transit: 'Halte WiraWiri Siola', rec: 'Kanopi buatan', cost: 'Rp 4.1 M' },
        { name: 'Jl. Darmo (Diponegoro - Joyoboyo)', tcs: 0.31, vol: 'Sedang', transit: 'Halte Suroboyo Bus Darmo', rec: 'Pohon peneduh', cost: 'Rp 1.2 M' },
        { name: 'Jl. Kertajaya (ITS - Galaxy Mall)', tcs: 0.33, vol: 'Sedang', transit: 'Halte Trans Semanggi ITS', rec: 'Pohon + jalur hijau', cost: 'Rp 1.5 M' },
        { name: 'Jl. Raya Darmo Permai (Satelit)', tcs: 0.29, vol: 'Sedang', transit: 'Halte Feeder Satelit', rec: 'Kanopi + bangku teduh', cost: 'Rp 2.0 M' },
    ];
    const tbody = document.getElementById('corridor-tbody');
    corridors.forEach((c, i) => {
        const cls = c.tcs < 0.25 ? 'tcs-low' : c.tcs < 0.4 ? 'tcs-med' : 'tcs-high';
        tbody.innerHTML += `<tr>
            <td><strong>#${i+1}</strong></td><td>${c.name}</td>
            <td><span class="tcs-badge ${cls}">${c.tcs.toFixed(2)}</span></td>
            <td>${c.vol}</td><td>${c.transit}</td><td>${c.rec}</td><td>${c.cost}</td>
        </tr>`;
    });
})();

// ===== TRANSIT TAB =====
(function renderTransitTab() {
    // Transit access chart
    const ctx = document.getElementById('transit-chart').getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Nyaman (TCS>0.6)', 'Sedang (0.3-0.6)', 'Panas (TCS<0.3)'],
            datasets: [{
                data: [32, 45, 23],
                backgroundColor: ['#2ecc71', '#f39c12', '#e74c3c'],
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' },
                title: { display: true, text: 'Kenyamanan Akses Halte (% ruas jalan radius 800m)' }
            }
        }
    });

    // Transit table
    const stops = [
        { name: 'Stasiun Gubeng', type: 'KAI', op: 'KAI', tcs: 0.45, reach: 128 },
        { name: 'Halte Tunjungan', type: 'Bus', op: 'Suroboyo Bus', tcs: 0.38, reach: 85 },
        { name: 'Halte Darmo', type: 'Bus', op: 'Suroboyo Bus', tcs: 0.52, reach: 72 },
        { name: 'Halte ITS', type: 'Bus', op: 'Trans Semanggi', tcs: 0.61, reach: 95 },
        { name: 'Stasiun Pasar Turi', type: 'KAI', op: 'KAI', tcs: 0.42, reach: 110 },
        { name: 'Halte Joyoboyo', type: 'Bus', op: 'Suroboyo Bus', tcs: 0.55, reach: 68 },
    ];
    const tbody = document.getElementById('transit-tbody');
    stops.forEach(s => {
        const cls = s.tcs < 0.4 ? 'tcs-low' : s.tcs < 0.6 ? 'tcs-med' : 'tcs-high';
        tbody.innerHTML += `<tr>
            <td><strong>${s.name}</strong></td><td>${s.type}</td><td>${s.op}</td>
            <td><span class="tcs-badge ${cls}">${s.tcs.toFixed(2)}</span></td><td>${s.reach} segmen</td>
        </tr>`;
    });
})();

// ===== UHI MAP (initialized on tab switch) =====
let uhiMapInstance = null;
function initUHIMap() {
    if (uhiMapInstance) return;
    uhiMapInstance = new maplibregl.Map({
        container: 'uhi-map',
        style: 'https://tiles.openfreemap.org/styles/liberty',
        center: [112.7521, -7.2575], zoom: 12, pitch: 30
    });
    uhiMapInstance.on('load', () => {
        // Simulated UHI hotspot circles
        const hotspots = [
            { lng: 112.7407, lat: -7.2679, intensity: 0.9, name: 'Jl. Basuki Rahmat' },
            { lng: 112.7378, lat: -7.3215, intensity: 0.95, name: 'Jl. Ahmad Yani' },
            { lng: 112.7500, lat: -7.2640, intensity: 0.8, name: 'Jl. Pemuda' },
            { lng: 112.7381, lat: -7.2611, intensity: 0.75, name: 'Jl. Tunjungan' },
            { lng: 112.7381, lat: -7.2757, intensity: 0.85, name: 'Jl. Urip Sumoharjo' },
            { lng: 112.7310, lat: -7.2878, intensity: 0.6, name: 'Jl. Darmo' },
            { lng: 112.7630, lat: -7.2805, intensity: 0.5, name: 'Jl. Kertajaya' },
        ];
        hotspots.forEach(h => {
            const color = h.intensity > 0.8 ? '#e74c3c' : h.intensity > 0.6 ? '#f39c12' : '#f1c40f';
            new maplibregl.Marker({ color })
                .setLngLat([h.lng, h.lat])
                .setPopup(new maplibregl.Popup().setHTML(
                    `<strong>${h.name}</strong><br>Heat Intensity: ${(h.intensity*100).toFixed(0)}%`
                ))
                .addTo(uhiMapInstance);
        });
    });
}

// ===== TRANSIT MAP =====
let transitMapInstance = null;
function initTransitMap() {
    if (transitMapInstance) return;
    transitMapInstance = new maplibregl.Map({
        container: 'transit-map',
        style: 'https://tiles.openfreemap.org/styles/liberty',
        center: [112.7521, -7.2575], zoom: 12
    });
    transitMapInstance.on('load', () => {
        const stops = [
            { lng: 112.7520, lat: -7.2656, name: 'Stasiun Gubeng', color: '#e74c3c' },
            { lng: 112.7251, lat: -7.2485, name: 'Stasiun Pasar Turi', color: '#e74c3c' },
            { lng: 112.7407, lat: -7.2679, name: 'Halte Basuki Rahmat', color: '#3498db' },
            { lng: 112.7311, lat: -7.2981, name: 'Halte Joyoboyo', color: '#3498db' },
            { lng: 112.7942, lat: -7.2818, name: 'Halte ITS', color: '#27ae60' },
            { lng: 112.7380, lat: -7.3045, name: 'Halte Wonokromo', color: '#3498db' },
        ];
        stops.forEach(s => {
            new maplibregl.Marker({ color: s.color })
                .setLngLat([s.lng, s.lat])
                .setPopup(new maplibregl.Popup().setText(s.name))
                .addTo(transitMapInstance);
        });
    });
}

// ===== CCTV MAP (loads all 444 cameras) =====
let cctvMapInstance = null;
let hlsDashInstance = null;

async function initCCTVMap() {
    if (cctvMapInstance) return;
    cctvMapInstance = new maplibregl.Map({
        container: 'cctv-map',
        style: 'https://tiles.openfreemap.org/styles/liberty',
        center: [112.7521, -7.2750], zoom: 12
    });

    try {
        const res = await fetch(DISHUB_CCTV_API);
        const cameras = await res.json();

        cctvMapInstance.on('load', () => {
            cameras.forEach(cam => {
                const el = document.createElement('div');
                el.style.cssText = 'width:10px;height:10px;background:#e74c3c;border-radius:50%;border:2px solid white;cursor:pointer;';
                el.title = cam.name;

                new maplibregl.Marker({ element: el })
                    .setLngLat([cam.lng, cam.lat])
                    .addTo(cctvMapInstance);

                el.addEventListener('click', () => openCCTVDashModal(cam.id, cam.name));
            });
        });
    } catch (e) {
        console.warn('[CCTV] Could not load camera list');
    }
}

function openCCTVDashModal(cctvId, name) {
    const modal = document.getElementById('cctv-modal');
    const video = document.getElementById('modal-video');
    const title = document.getElementById('modal-title');
    const status = document.getElementById('modal-status');

    modal.classList.remove('hidden');
    title.textContent = `📹 ${name}`;
    status.textContent = 'Memuat stream...';
    video.style.display = 'none';

    const hlsUrl = `${DISHUB_HLS_BASE}/${cctvId}/index.m3u8`;

    if (Hls.isSupported()) {
        if (hlsDashInstance) hlsDashInstance.destroy();
        hlsDashInstance = new Hls({ maxLoadingDelay: 4, liveSyncDuration: 3 });
        hlsDashInstance.loadSource(hlsUrl);
        hlsDashInstance.attachMedia(video);
        hlsDashInstance.on(Hls.Events.MANIFEST_PARSED, () => {
            status.textContent = `Live — ${name}`;
            video.style.display = 'block';
            video.play().catch(() => {});
        });
        hlsDashInstance.on(Hls.Events.ERROR, (_, d) => {
            if (d.fatal) status.textContent = '❌ Stream offline / tidak tersedia';
        });
    } else {
        status.textContent = 'Browser tidak mendukung HLS';
    }
}

function closeCCTVDashModal() {
    document.getElementById('cctv-modal').classList.add('hidden');
    if (hlsDashInstance) { hlsDashInstance.destroy(); hlsDashInstance = null; }
    document.getElementById('modal-video').src = '';
}
