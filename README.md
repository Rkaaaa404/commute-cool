# 🌳 COMMUTE-COOL

**Sistem Navigasi Pejalan Kaki Berbasis Kenyamanan Termal untuk Mendukung Smart City**

Studi Kasus: Kota Surabaya | Final Project Big Data | Semester 4

---

## Deskripsi

COMMUTE-COOL membantu pejalan kaki menemukan rute yang **bukan hanya tercepat, tetapi juga paling nyaman dan aman dari paparan panas matahari**. Sistem menggabungkan data cuaca real-time, pemodelan bayangan gedung/pohon, kualitas udara, kepadatan lalu lintas, dan kualitas trotoar untuk menghasilkan **Thermal Comfort Score (TCS)** per segmen jalan.

Fitur utama:
- **Personal Heat Budget** — rekomendasi rute disesuaikan dengan toleransi panas pengguna (lansia, anak, dewasa aktif)
- **Commute-First Routing** — optimasi khusus untuk first-mile/last-mile menuju halte/stasiun
- **Live CCTV Preview** — lihat kondisi jalan real-time dari 444 CCTV Dishub Surabaya sebelum berangkat
- **City-Wide Thermal Heatmap** — visualisasi kenyamanan termal seluruh jalur pedestrian Surabaya
- **Dashboard Pemerintah** — peta UHI hotspot, koridor prioritas penghijauan, statistik walkability

---

## Tech Stack

| Layer | Teknologi |
|---|---|
| Processing | Apache Spark 3.5 (PySpark) + Apache Sedona 1.6 (local mode) |
| Database | PostgreSQL 15 + PostGIS 3.3 |
| Backend API | FastAPI + asyncpg (async, no ORM overhead) |
| Frontend | MapLibre GL JS 4.7 (3D buildings) + OpenFreeMap |
| Routing Engine | GraphHopper (custom thermal weighting) |
| CCTV Streaming | HLS.js + Dishub Surabaya streams |
| Deployment | Docker Compose (4 services, satu perintah) |

### Requirements Files (3 file, bukan duplikasi)

| File | Digunakan Oleh | Isi |
|------|---------------|-----|
| `requirements.txt` | Local development (tanpa Docker) | Semua deps: PySpark + FastAPI + ingestion |
| `requirements-docker.txt` | `Dockerfile.api` | Hanya FastAPI + asyncpg + ingestion (tanpa PySpark, image kecil) |
| `requirements-spark.txt` | `Dockerfile.spark` | Hanya PySpark + Sedona + pvlib (tanpa FastAPI) |

> Split supaya tiap Docker container hanya install deps yang dibutuhkan — API image ~200MB vs kalau include PySpark ~700MB.

### Sumber Data (semua gratis, tanpa payment)

| Data | Sumber | Tipe |
|---|---|---|
| Cuaca real-time | Open-Meteo API | REST JSON |
| Jalur & bangunan | OpenStreetMap (Overpass API) | GeoJSON |
| Kualitas udara | WAQI API (aqicn.org) | REST JSON |
| Traffic | TomTom Traffic API | REST JSON |
| Peringatan cuaca | BMKG RSS Feed | XML |
| CCTV lalu lintas | Dishub Surabaya (HLS stream) | Video |
| NDVI proxy | Tree density dari OSM | Spatial query |
| LST proxy | Open-Meteo + koreksi material | Calculated |

---

## Arsitektur

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     Docker Compose (Backend)                              │
│                                                                          │
│  ┌──────────────────────────────────┐  ┌──────────────────────────────┐ │
│  │  spark-pipeline (one-shot)       │  │  api (FastAPI)               │ │
│  │  Ingest APIs → 5 Spark Jobs      │  │  :8000 asyncpg               │ │
│  │  → writes to PostGIS → exit      │  │  POST /api/route             │ │
│  └──────────────┬───────────────────┘  │  GET /api/segments/thermal   │ │
│                 │ JDBC                  │  GET /api/dashboard/*        │ │
│                 ▼                       │  GET /api/cctv/nearby        │ │
│  ┌──────────────────────────────────┐  └───────────────┬──────────────┘ │
│  │  postgres (PostGIS)              │←─────────────────┘ asyncpg        │
│  │  :5432                           │                                    │
│  │  segments + TCS + edge_weights   │                                    │
│  └──────────────────────────────────┘                                    │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↑ REST API (http://localhost:8000)
                                    │
┌───────────────────────────────────┴──────────────────────────────────────┐
│                     Frontend (Lokal, tanpa Docker)                        │
│                     :3000 (live-server / python http.server)              │
│                                                                          │
│  navigation/  → MapLibre 3D + heatmap + route + CCTV markers            │
│  dashboard/   → Chart.js + UHI map + corridors + transit                 │
└──────────────────────────────────────────────────────────────────────────┘
```

### Pipeline Data Flow

```
Open-Meteo + WAQI + TomTom → data/raw/ (JSON)
OSM GeoJSON → PostGIS (segments, buildings, trees)
                ↓
    Spark Job 1: NDVI/LST (tree density + surface correction)
    Spark Job 2: Shadow Modeling (solar position + geometry)
    Spark Job 4: Traffic & AQI Aggregation
                ↓
    Spark Job 3: Thermal Comfort Score (TCS formula)
                ↓
    Spark Job 5: Graph Weight Export (routing penalties)
                ↓
    PostGIS → FastAPI → Frontend (heatmap + routes)
```

---

## Struktur Project

```
commute-cool/
├── api/                        # FastAPI backend (asyncpg, no ORM)
│   ├── main.py                 # App entry + lifespan pool management
│   ├── db.py                   # asyncpg connection pool
│   ├── routes/
│   │   ├── navigation.py      # POST /api/route + GET /api/segments/thermal
│   │   ├── dashboard.py       # GET /api/dashboard/* (UHI, corridors, walkability)
│   │   └── cctv.py            # GET /api/cctv/nearby (spatial query)
│   └── models/
│       ├── schemas.py          # Pydantic request/response models
│       └── database.py         # SQLAlchemy ORM (reference, not used at runtime)
├── spark_jobs/                 # PySpark + Sedona batch processing
│   ├── run_pipeline.py         # Full pipeline orchestrator (7 steps + fallbacks)
│   ├── config.py               # Shared JDBC config from DATABASE_URL env var
│   ├── job_raster_segment.py   # Job 1: NDVI/LST per segment
│   ├── job_shadow_model.py     # Job 2: Shadow ratio per hour (6-17 WIB)
│   ├── job_traffic_aqi.py      # Job 4: Traffic geocoding + AQI uniform
│   ├── job_thermal_comfort.py  # Job 3: TCS calculation (weighted formula)
│   ├── job_graph_weight.py     # Job 5: Routing weight export (1x-3x penalty)
│   └── utils/
│       ├── solar_position.py   # Sun elevation/azimuth (pvlib)
│       ├── shadow_geometry.py  # Shadow polygon projection (Shapely)
│       └── normalization.py    # Score normalization (0-1)
├── ingestion/                  # Data collection scripts
│   ├── config.py               # API URLs, bounding box, paths
│   ├── osm_fetcher.py          # Download OSM data Surabaya (Overpass)
│   ├── osm_loader.py           # Load GeoJSON → PostGIS
│   ├── weather_collector.py    # Open-Meteo (suhu, kelembapan, radiasi)
│   ├── traffic_collector.py    # TomTom (8 titik jalan utama)
│   ├── aqi_collector.py        # WAQI (AQI Surabaya)
│   ├── bmkg_rss_monitor.py     # BMKG RSS peringatan cuaca
│   ├── ndvi_lst_estimator.py   # NDVI/LST proxy (fallback non-Spark)
│   ├── cctv_registry.py        # 444 CCTV Dishub Surabaya
│   ├── transit_loader.py       # Load halte/stasiun ke DB
│   └── scheduler.py            # APScheduler orchestration
├── routing/                    # Routing engine integration
│   ├── route_service.py        # GraphHopper custom weighting
│   ├── heat_exposure.py        # Sun exposure calculator per rute
│   ├── personal_budget.py      # Heat budget validation
│   └── alert_rerouter.py       # Weather alert blocking
├── frontend/
│   ├── navigation/             # User-facing navigation app
│   │   ├── index.html          # MapLibre 3D + route UI + heatmap toggle
│   │   ├── map.js              # Map logic + TCS heatmap overlay + gradient routes
│   │   ├── route-panel.js      # Route comparison panel
│   │   ├── cctv-preview.js     # Live CCTV modal (HLS.js)
│   │   └── styles.css
│   └── dashboard/              # Government analytics dashboard
│       ├── index.html          # UHI map + charts + corridors + CCTV monitor
│       ├── dashboard.js        # Charts, maps, API integration
│       └── dashboard.css
├── database/
│   ├── init.sql                # Full PostGIS schema (all tables + indexes)
│   └── seed_transit.sql        # Halte/stasiun Surabaya
├── data/raw/                   # Raw ingested data (JSON, GeoJSON)
│   ├── osm/                    # footways, buildings, trees GeoJSON
│   ├── weather/                # Open-Meteo responses
│   └── transit/                # Transit stop data
├── validation/
│   ├── validate_shadow.py      # Shadow model accuracy (IoU)
│   └── validate_thermal.py     # Thermal model accuracy (MAE)
├── tests/
│   ├── test_normalization.py   # 16 unit tests
│   ├── test_solar_position.py  # 6 unit tests
│   └── test_e2e.py             # Integration tests
├── docker-compose.yml          # 4 services: postgres, spark, api, frontend
├── Dockerfile.api              # Python 3.11-slim, FastAPI only
├── Dockerfile.spark            # Spark 3.5 + Sedona JARs pre-downloaded
├── nginx.conf                  # Static serving + API reverse proxy
├── requirements.txt            # Full local dev (semua deps dalam 1 file)
├── requirements-docker.txt     # Docker: API container only (tanpa PySpark)
├── requirements-spark.txt      # Docker: Spark container only (tanpa FastAPI)
├── .dockerignore               # Build optimization
├── .env.example                # Environment variables template
└── .kiro/specs/                # Project documentation
    ├── requirement.md
    ├── design.md
    └── tasks.md
```

---

## Quick Start

### Prerequisites

- Docker & Docker Compose (untuk PostgreSQL + Spark pipeline + API)
- Node.js (untuk frontend dev server) — atau bisa pakai `python -m http.server`

### Step 1: Jalankan Backend (Docker)

```powershell
docker compose up --build
```

Ini menjalankan 3 services:
1. **postgres** — PostgreSQL/PostGIS, auto-init schema + transit seed
2. **spark-pipeline** — Fetch API → Load OSM → 5 Spark jobs → exit
3. **api** — FastAPI on http://localhost:8000

Tunggu sampai `spark-pipeline` exit (data sudah masuk DB), lalu API siap serve data.

### Step 2: Jalankan Frontend (Lokal)

```powershell
cd frontend
npx live-server --port=3000 --cors --open=/navigation/
```

Atau tanpa Node.js:
```powershell
python -m http.server 3000 --directory frontend
```

### Akses

| URL | Fungsi |
|-----|--------|
| http://localhost:3000/navigation/ | Navigation app + thermal heatmap |
| http://localhost:3000/dashboard/ | Government dashboard |
| http://localhost:8000/docs | API Swagger documentation |
| http://localhost:8000/api/segments/thermal | Raw thermal data (JSON) |

### Monitoring

```powershell
# Lihat progress spark pipeline
docker compose logs -f spark-pipeline

# Cek services
docker compose ps

# Verify data exists
docker exec commute_cool_db psql -U cc_user -d commute_cool -c "SELECT COUNT(*) FROM thermal_comfort_scores"
```

---

## Local Development (Tanpa Docker)

### Prerequisites

- Python 3.11+
- PostgreSQL 15 + PostGIS 3.3
- Git

### Setup

```powershell
git clone <repo-url>
cd commute-cool

# Virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
copy .env.example .env
# Edit .env — isi WAQI_API_TOKEN dan TOMTOM_API_KEY
```

### Jalankan Database

```powershell
docker compose up -d postgres

# Seed transit data
Get-Content database/seed_transit.sql | docker exec -i commute_cool_db psql -U cc_user -d commute_cool
```

### Ingestion

```powershell
python -m ingestion.osm_fetcher          # Download OSM Surabaya (2-5 min)
python -m ingestion.osm_loader           # Load ke PostGIS
python -m ingestion.weather_collector    # Fetch cuaca real-time
python -m ingestion.cctv_registry        # Load 444 CCTV
python -m ingestion.ndvi_lst_estimator   # Estimasi NDVI & LST
python -m ingestion.transit_loader       # Load transit stops
```

### Spark Processing (opsional)

```powershell
# Jalankan pipeline lengkap
python -m spark_jobs.run_pipeline
```

### API Backend

```powershell
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```powershell
python -m http.server 3000 --directory frontend
```

Buka http://localhost:3000/navigation/

---

## Cara Menggunakan

### Navigation App

1. Buka peta 3D Surabaya (http://localhost:3000)
2. City-wide thermal heatmap otomatis muncul (hijau=teduh, merah=panas)
3. **Klik pertama** di peta → set titik awal (marker biru)
4. **Klik kedua** → set tujuan (marker merah)
5. Klik **"Cari Rute"**
6. Lihat 2 opsi rute:
   - 🏃 **Terpendek** — jarak minimum
   - 🌳 **Ternyaman** — thermal comfort optimal
7. Klik **"📹 Lihat Kondisi Jalan"** untuk preview CCTV live
8. Pilih rute dan jalan!

### Government Dashboard

- **Overview** — Statistik kota (total segments, critical, avg TCS)
- **Peta UHI** — Hotspot Urban Heat Island
- **Koridor Hijau** — Rekomendasi penghijauan per koridor
- **Akses Transit** — Walkability per halte/stasiun
- **CCTV Monitor** — 444 kamera live dari Dishub

---

## API Endpoints

| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `/api/route` | POST | Hitung rute shortest + comfortable |
| `/api/segments/thermal` | GET | Semua segmen + TCS (max 2000, untuk heatmap) |
| `/api/dashboard/uhi` | GET | UHI hotspot segments (TCS < 0.5) |
| `/api/dashboard/priority-corridors` | GET | Koridor prioritas penghijauan |
| `/api/dashboard/walkability` | GET | Statistik aksesibilitas transit |
| `/api/cctv/nearby` | GET | CCTV terdekat dari koordinat |
| `/health` | GET | Health check |

---

## Testing

```powershell
# Unit tests (22 tests)
python -m pytest tests/test_normalization.py tests/test_solar_position.py -v

# Validation scripts
$env:PYTHONPATH="."; python validation/validate_shadow.py
$env:PYTHONPATH="."; python validation/validate_thermal.py

# E2E tests (butuh API running)
python -m pytest tests/test_e2e.py -v
```

---

## Thermal Comfort Score (TCS) Formula

```
TCS = 0.35 × f_shade(shade_ratio, ndvi)
    + 0.30 × f_temp(apparent_temp, lst)
    + 0.15 × f_air(aqi)
    + 0.10 × f_traffic(congestion)
    + 0.10 × f_surface(material, smoothness)

Output: 0.0 (sangat tidak nyaman) → 1.0 (sangat nyaman)
```

**Normalisasi:**
- Temperature: range 28°C (nyaman) → 45°C (extreme)
- AQI: range 0 (baik) → 150 (buruk)
- Traffic: 0 (lancar) → 1 (macet total)
- Surface: scoring per material (asphalt=0.9, grass=0.4, unpaved=0.3)

**Routing Penalty:**
```
total_cost = base_cost × (1 + (1 − TCS) × 2)
```
TCS=1.0 → penalty 1x | TCS=0.5 → penalty 2x | TCS=0.0 → penalty 3x

**Visualisasi di peta:**
- 🟢 **Hijau** (TCS > 0.7) — teduh, nyaman
- 🟡 **Kuning** (TCS 0.4-0.7) — sedang
- 🔴 **Merah** (TCS < 0.4) — panas, tidak nyaman

---

## Fallback Mechanism

Jika Apache Spark gagal (Sedona JAR issue, memory error), pipeline **tetap menghasilkan data** menggunakan PostgreSQL langsung:

| Spark Job | Fallback |
|-----------|----------|
| Job 1 (NDVI/LST) | `ingestion/ndvi_lst_estimator.py` |
| Job 2 (Shadow) | PostGIS proximity estimation |
| Job 3 (TCS) | PostgreSQL INSERT...SELECT with formula |
| Job 5 (Weights) | PostgreSQL direct computation |

Semua fallback menghasilkan output ke tabel yang sama — API dan frontend tetap berfungsi normal.

---

## Referensi

- Althoff et al. (2017). "Large-scale physical activity data reveal worldwide activity inequality." *Nature*, 547, 336-339.
- Copernicus Climate Change Service. "Global Climate Highlights 2024."
- ITDP Indonesia. "Pedoman Integrasi Antarmoda."
- Middel et al. (2016). "Impact of urban form and design on mid-afternoon microclimate in Phoenix Local Climate Zones." *Landscape and Urban Planning*, 122, 16-28.

---

## Tim

Final Project Big Data — Semester 4

---

## Lisensi

Educational/Academic Use — Gemastik Smart City Category
