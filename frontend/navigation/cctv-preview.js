/**
 * COMMUTE-COOL CCTV Preview Module
 * Shows live HLS stream from Dishub Surabaya CCTV cameras.
 * User can preview road conditions before starting their walk.
 *
 * Uses HLS.js for cross-browser HLS playback.
 */

// HLS.js loaded from CDN (added to index.html)
const CCTV_API_BASE = 'http://localhost:8000/api';
const DISHUB_HLS_BASE = 'http://36.66.208.101:5000/hls';

// --- CCTV Modal HTML (injected once) ---
function injectCCTVModal() {
    if (document.getElementById('cctv-modal')) return;

    const modal = document.createElement('div');
    modal.id = 'cctv-modal';
    modal.className = 'cctv-modal hidden';
    modal.innerHTML = `
        <div class="cctv-modal-backdrop" onclick="closeCCTVModal()"></div>
        <div class="cctv-modal-content">
            <div class="cctv-modal-header">
                <h3 id="cctv-modal-title">Live CCTV</h3>
                <button class="close-btn" onclick="closeCCTVModal()">&times;</button>
            </div>
            <div class="cctv-video-container">
                <video id="cctv-video" controls autoplay muted playsinline></video>
                <div id="cctv-loading" class="cctv-loading">Memuat stream...</div>
                <div id="cctv-error" class="cctv-error hidden">
                    Stream tidak tersedia.
                    <br><small>CCTV mungkin sedang offline atau tidak dapat diakses dari jaringan ini.</small>
                </div>
            </div>
            <div class="cctv-modal-footer">
                <span id="cctv-distance-badge"></span>
                <span class="cctv-source">Sumber: Dishub Surabaya</span>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    // Add styles
    const style = document.createElement('style');
    style.textContent = `
        .cctv-modal {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .cctv-modal.hidden { display: none; }
        .cctv-modal-backdrop {
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.6);
        }
        .cctv-modal-content {
            position: relative;
            background: white;
            border-radius: 16px;
            width: 90%;
            max-width: 640px;
            overflow: hidden;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }
        .cctv-modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 18px;
            border-bottom: 1px solid #eee;
        }
        .cctv-modal-header h3 {
            font-size: 16px;
            margin: 0;
            color: #2c3e50;
        }
        .cctv-video-container {
            position: relative;
            background: #1a1a2e;
            min-height: 200px;
        }
        .cctv-video-container video {
            width: 100%;
            display: block;
        }
        .cctv-loading {
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            color: white;
            font-size: 14px;
        }
        .cctv-error {
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            color: #e74c3c;
            text-align: center;
            font-size: 14px;
        }
        .cctv-error.hidden { display: none; }
        .cctv-modal-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 18px;
            font-size: 12px;
            color: #777;
            border-top: 1px solid #eee;
        }
        #cctv-distance-badge {
            background: #eaf6ec;
            color: #27ae60;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 600;
        }
    `;
    document.head.appendChild(style);
}

// --- Open CCTV Modal ---
let hlsInstance = null;

function openCCTVModal(cctvId, cctvName, distanceM) {
    injectCCTVModal();

    const modal = document.getElementById('cctv-modal');
    const video = document.getElementById('cctv-video');
    const title = document.getElementById('cctv-modal-title');
    const loading = document.getElementById('cctv-loading');
    const errorEl = document.getElementById('cctv-error');
    const badge = document.getElementById('cctv-distance-badge');

    // Reset state
    modal.classList.remove('hidden');
    loading.style.display = 'block';
    errorEl.classList.add('hidden');
    video.style.display = 'none';

    title.textContent = cctvName || 'Live CCTV';
    badge.textContent = distanceM ? `${Math.round(distanceM)}m dari rute` : '';

    // Build HLS stream URL
    const streamUrl = `${DISHUB_HLS_BASE}/${cctvId}/stream311.ts`;
    // For HLS.js, we need the playlist URL, not the .ts segment directly
    // The Dishub system likely serves segments; try direct video src first
    const hlsPlaylistUrl = `${DISHUB_HLS_BASE}/${cctvId}/index.m3u8`;

    // Try HLS.js playback
    if (typeof Hls !== 'undefined' && Hls.isSupported()) {
        if (hlsInstance) {
            hlsInstance.destroy();
        }
        hlsInstance = new Hls({
            maxLoadingDelay: 4,
            maxBufferLength: 10,
            liveSyncDuration: 3,
        });

        hlsInstance.loadSource(hlsPlaylistUrl);
        hlsInstance.attachMedia(video);

        hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
            loading.style.display = 'none';
            video.style.display = 'block';
            video.play().catch(() => {});
        });

        hlsInstance.on(Hls.Events.ERROR, (event, data) => {
            if (data.fatal) {
                loading.style.display = 'none';
                errorEl.classList.remove('hidden');
                console.warn('[CCTV] HLS error:', data);
            }
        });
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
        // Native HLS support (Safari)
        video.src = hlsPlaylistUrl;
        video.addEventListener('loadedmetadata', () => {
            loading.style.display = 'none';
            video.style.display = 'block';
            video.play().catch(() => {});
        });
        video.addEventListener('error', () => {
            loading.style.display = 'none';
            errorEl.classList.remove('hidden');
        });
    } else {
        loading.style.display = 'none';
        errorEl.classList.remove('hidden');
        errorEl.innerHTML = 'Browser tidak mendukung HLS playback.';
    }
}

function closeCCTVModal() {
    const modal = document.getElementById('cctv-modal');
    const video = document.getElementById('cctv-video');

    if (hlsInstance) {
        hlsInstance.destroy();
        hlsInstance = null;
    }
    video.src = '';
    modal.classList.add('hidden');
}

// --- Find Nearby CCTVs for a Route ---
async function findNearbyCCTVs(lat, lng, radius = 500) {
    try {
        const response = await fetch(
            `${CCTV_API_BASE}/cctv/nearby?lat=${lat}&lng=${lng}&radius=${radius}&limit=3`
        );
        if (response.ok) {
            return await response.json();
        }
    } catch (e) {
        console.log('[CCTV] API not available');
    }

    // Fallback: query Dishub directly and find closest
    return await findNearbyCCTVsDirect(lat, lng);
}

async function findNearbyCCTVsDirect(lat, lng) {
    // Fallback: fetch all CCTVs from Dishub and find nearest
    try {
        const response = await fetch('http://36.66.208.101:5000/cctvs');
        if (!response.ok) return [];
        const allCctvs = await response.json();

        // Calculate distances and sort
        const withDistance = allCctvs.map(cam => ({
            cctv_id: cam.id,
            name: cam.name,
            lat: cam.lat,
            lng: cam.lng,
            stream_url: `${DISHUB_HLS_BASE}/${cam.id}/stream311.ts`,
            distance_m: haversineDistance(lat, lng, cam.lat, cam.lng),
        }));

        withDistance.sort((a, b) => a.distance_m - b.distance_m);
        return withDistance.slice(0, 3);
    } catch (e) {
        return [];
    }
}

function haversineDistance(lat1, lng1, lat2, lng2) {
    const R = 6371000;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLng/2) * Math.sin(dLng/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

// --- Add CCTV Button to Route Panel ---
function addCCTVButtonToRouteCard(cardElement, routeMidpointLat, routeMidpointLng) {
    const btn = document.createElement('button');
    btn.className = 'cctv-preview-btn';
    btn.innerHTML = 'Lihat Kondisi Jalan';

    btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        btn.textContent = 'Mencari CCTV terdekat...';

        const cctvs = await findNearbyCCTVs(routeMidpointLat, routeMidpointLng);

        if (cctvs.length > 0) {
            const nearest = cctvs[0];
            openCCTVModal(nearest.cctv_id, nearest.name, nearest.distance_m);
        } else {
            btn.textContent = 'Tidak ada CCTV terdekat';
            setTimeout(() => { btn.innerHTML = 'Lihat Kondisi Jalan'; }, 2000);
        }
    });

    cardElement.appendChild(btn);
}
