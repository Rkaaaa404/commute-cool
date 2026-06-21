# Dokumen Desain Sistem (System Design Document) - COMMUTE-COOL

Sistem Navigasi Pejalan Kaki Berbasis Kenyamanan Termal untuk Mendukung Smart City (Studi Kasus: Kota Surabaya)

---

## 1. Arsitektur Sistem (System Architecture Overview)

COMMUTE-COOL menggunakan arsitektur **Lambda-lite** yang memisahkan batch processing (Spark) untuk data berat (satelit, OSM) dengan near-real-time layer untuk data cuaca & traffic, kemudian menyajikan hasil melalui serving layer yang melayani routing engine dan dashboard.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE LAYER                             │
│                                                                              │
│   ┌─────────────────────────┐          ┌──────────────────────────────┐      │
│   │   Mobile Navigation App │          │   Government Dashboard       │      │
│   │   (Leaflet/Mapbox GL)   │          │   (React + Chart.js)         │      │
│   └────────────┬────────────┘          └───────────────┬──────────────┘      │
└────────────────┼───────────────────────────────────────┼─────────────────────┘
                 │ REST API                              │ REST API
                 ▼                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                             API / SERVING LAYER                               │
│                                                                              │
│   ┌─────────────────────┐  ┌────────────────────┐  ┌─────────────────────┐  │
│   │  FastAPI Backend     │  │  GraphHopper       │  │  PostGIS Query      │  │
│   │  (Orchestrator)      │  │  (Routing Engine)  │  │  Service            │  │
│   └──────────┬──────────┘  └─────────┬──────────┘  └──────────┬──────────┘  │
└──────────────┼────────────────────────┼─────────────────────────┼────────────┘
               │                        │                         │
               ▼                        ▼                         ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           DATA SERVING STORE                                  │
│                                                                              │
│                    PostgreSQL + PostGIS (Spatial Database)                     │
│                                                                              │
│   ┌──────────────┐ ┌───────────────┐ ┌────────────┐ ┌────────────────────┐  │
│   │ segments     │ │ thermal_scores│ │ transit    │ │ edge_weights       │  │
│   │ (geometri    │ │ (TCS per ruas │ │ (halte,   │ │ (bobot routing     │  │
│   │  ruas jalan) │ │  per waktu)   │ │  stasiun) │ │  per edge)         │  │
│   └──────────────┘ └───────────────┘ └────────────┘ └────────────────────┘  │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       │ ETL (write)
                                       │
┌──────────────────────────────────────┴───────────────────────────────────────┐
│                       APACHE SPARK PROCESSING LAYER                           │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                    BATCH PROCESSING (PySpark + Sedona)                   │ │
│  │                                                                         │ │
│  │  [Job 1: Raster Segmentation] → [Job 2: Shadow Modeling] ─┐            │ │
│  │                                                            ├→ [Job 3:  │ │
│  │  [Job 4: Traffic/AQI Aggregation] ────────────────────────┘  Thermal   │ │
│  │                                                               Comfort  │ │
│  │                                                               Score]   │ │
│  │                                                                 │      │ │
│  │                                                                 ▼      │ │
│  │                                                   [Job 5: Weight Export]│ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │              MICRO-BATCH / STREAMING (Spark Structured Streaming)        │ │
│  │                                                                         │ │
│  │  [Weather Stream] ──→ Update suhu & kelembapan per segment (15 menit)   │ │
│  │  [Traffic Stream] ──→ Update congestion level per segment (15 menit)    │ │
│  │  [AQI Stream]     ──→ Update air quality index per segment (30 menit)   │ │
│  │  [BMKG RSS]       ──→ Trigger reroute alert jika cuaca ekstrem          │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ read (raw)
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          DATA LAKE (RAW STORAGE)                              │
│                          MinIO / Local File System                            │
│                                                                              │
│   /raw/raster/       → GeoTIFF (NDVI, LST) dari GEE                         │
│   /raw/osm/          → GeoJSON (buildings, trees, footways) dari Overpass    │
│   /raw/weather/      → JSON historis dari Open-Meteo & infoBMKG              │
│   /raw/traffic/      → JSON dari TomTom/HERE                                 │
│   /raw/aqi/          → JSON dari WAQI/OpenAQ                                 │
│   /raw/transit/      → CSV/GeoJSON halte & stasiun                           │
│   /raw/alerts/       → XML dari RSS Feed BMKG                                │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                                       │ ingestion
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION LAYER                                   │
│                        (Python Scripts / Schedulers)                          │
│                                                                              │
│   ┌───────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐  │
│   │ GEE Exporter  │ │ OSM Fetcher  │ │ Weather      │ │ Traffic/AQI      │  │
│   │ (periodik     │ │ (Overpass    │ │ Collector    │ │ Collector        │  │
│   │  mingguan)    │ │  harian)     │ │ (15 menit)   │ │ (15-30 menit)    │  │
│   └───────────────┘ └──────────────┘ └──────────────┘ └──────────────────┘  │
│                                                                              │
│   ┌───────────────┐ ┌──────────────┐                                        │
│   │ BMKG RSS      │ │ Transit Data │                                        │
│   │ Monitor       │ │ Loader       │                                        │
│   │ (5 menit)     │ │ (sekali/upd) │                                        │
│   └───────────────┘ └──────────────┘                                        │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Desain Data Model (Data Model Design)

### 2.1. Schema Database PostgreSQL/PostGIS

```sql
-- ============================================================
-- TABEL INTI: Segmen Jalan Pedestrian
-- ============================================================
CREATE TABLE segments (
    segment_id      SERIAL PRIMARY KEY,
    osm_way_id      BIGINT,
    name            VARCHAR(255),
    geom            GEOMETRY(LineString, 4326) NOT NULL,
    length_m        DOUBLE PRECISION,
    highway_type    VARCHAR(50),       -- footway, pedestrian, path, steps
    surface_type    VARCHAR(50),       -- asphalt, paving_stones, unpaved
    smoothness      VARCHAR(50),       -- excellent, good, intermediate, bad
    sidewalk_width  DOUBLE PRECISION,  -- meter (jika tersedia)
    has_shade_tree  BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_segments_geom ON segments USING GIST (geom);

-- ============================================================
-- TABEL: Bangunan (untuk shadow modeling)
-- ============================================================
CREATE TABLE buildings (
    building_id     SERIAL PRIMARY KEY,
    osm_id          BIGINT,
    geom            GEOMETRY(Polygon, 4326) NOT NULL,
    height_m        DOUBLE PRECISION,  -- tinggi bangunan estimasi
    levels          INTEGER            -- jumlah lantai (fallback jika height kosong)
);

CREATE INDEX idx_buildings_geom ON buildings USING GIST (geom);

-- ============================================================
-- TABEL: Pohon (untuk shadow modeling)
-- ============================================================
CREATE TABLE trees (
    tree_id         SERIAL PRIMARY KEY,
    osm_id          BIGINT,
    geom            GEOMETRY(Point, 4326) NOT NULL,
    height_m        DOUBLE PRECISION DEFAULT 8.0,  -- estimasi default pohon tropis
    crown_radius_m  DOUBLE PRECISION DEFAULT 4.0   -- radius tajuk
);

CREATE INDEX idx_trees_geom ON trees USING GIST (geom);

-- ============================================================
-- TABEL: Titik Transit Transportasi Publik
-- ============================================================
CREATE TABLE transit_stops (
    stop_id         SERIAL PRIMARY KEY,
    name            VARCHAR(255),
    geom            GEOMETRY(Point, 4326) NOT NULL,
    stop_type       VARCHAR(50),       -- bus_stop, train_station, feeder
    operator        VARCHAR(100),      -- Suroboyo Bus, Trans Semanggi, KAI, dll
    route_name      VARCHAR(255)
);

CREATE INDEX idx_transit_geom ON transit_stops USING GIST (geom);

-- ============================================================
-- TABEL: Skor NDVI & LST per Segmen (hasil Spark Job 1)
-- ============================================================
CREATE TABLE segment_raster_scores (
    id              SERIAL PRIMARY KEY,
    segment_id      INTEGER REFERENCES segments(segment_id),
    avg_ndvi        DOUBLE PRECISION,  -- 0.0 - 1.0 (semakin tinggi = semakin hijau)
    avg_lst         DOUBLE PRECISION,  -- deg C (Land Surface Temperature)
    computed_at     DATE NOT NULL,     -- tanggal komputasi (citra satelit periodik)
    UNIQUE(segment_id, computed_at)
);

-- ============================================================
-- TABEL: Rasio Bayangan per Segmen per Waktu (hasil Spark Job 2)
-- ============================================================
CREATE TABLE segment_shadows (
    id              SERIAL PRIMARY KEY,
    segment_id      INTEGER REFERENCES segments(segment_id),
    hour_of_day     SMALLINT NOT NULL, -- 6, 7, 8, ..., 17 (jam aktif pejalan kaki)
    shade_ratio     DOUBLE PRECISION,  -- 0.0 - 1.0 (proporsi segmen yang terteduh)
    computed_at     DATE NOT NULL,
    UNIQUE(segment_id, hour_of_day, computed_at)
);

-- ============================================================
-- TABEL: Thermal Comfort Score per Segmen (hasil Spark Job 3)
-- ============================================================
CREATE TABLE thermal_comfort_scores (
    id              SERIAL PRIMARY KEY,
    segment_id      INTEGER REFERENCES segments(segment_id),
    tcs_value       DOUBLE PRECISION NOT NULL,  -- 0.0 (sangat tidak nyaman) - 1.0 (sangat nyaman)
    apparent_temp   DOUBLE PRECISION,           -- deg C suhu semu di segmen ini
    shade_ratio     DOUBLE PRECISION,
    aqi_value       DOUBLE PRECISION,
    traffic_level   DOUBLE PRECISION,
    computed_at     TIMESTAMP NOT NULL,
    UNIQUE(segment_id, computed_at)
);

CREATE INDEX idx_tcs_segment_time ON thermal_comfort_scores (segment_id, computed_at DESC);

-- ============================================================
-- TABEL: Bobot Routing per Edge (hasil Spark Job 5)
-- ============================================================
CREATE TABLE edge_weights (
    id              SERIAL PRIMARY KEY,
    segment_id      INTEGER REFERENCES segments(segment_id),
    base_cost       DOUBLE PRECISION,  -- cost berdasarkan jarak murni
    thermal_penalty DOUBLE PRECISION,  -- penalti berdasarkan TCS (semakin panas = semakin besar)
    total_cost      DOUBLE PRECISION,  -- base_cost + thermal_penalty
    valid_from      TIMESTAMP NOT NULL,
    valid_until     TIMESTAMP NOT NULL
);

-- ============================================================
-- TABEL: Profil Pengguna (Personal Heat Budget)
-- ============================================================
CREATE TABLE user_profiles (
    user_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    heat_tolerance      VARCHAR(20) NOT NULL DEFAULT 'medium', -- low, medium, high
    max_sun_exposure_min INTEGER DEFAULT 15,   -- maks menit paparan matahari langsung
    age_group           VARCHAR(20),           -- child, adult, elderly
    created_at          TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- TABEL: Log Peringatan Cuaca (dari RSS BMKG)
-- ============================================================
CREATE TABLE weather_alerts (
    alert_id        SERIAL PRIMARY KEY,
    title           TEXT,
    description     TEXT,
    severity        VARCHAR(20),       -- minor, moderate, severe, extreme
    affected_area   GEOMETRY(Polygon, 4326),
    issued_at       TIMESTAMP,
    expires_at      TIMESTAMP,
    is_active       BOOLEAN DEFAULT TRUE
);
```

### 2.2. Data Flow Diagram per Spark Job

```
┌─────────────────────────────────────────────────────────────────┐
│                         SPARK JOB DEPENDENCIES                   │
└─────────────────────────────────────────────────────────────────┘

  [NDVI/LST Est.]  [OSM Fetch]        [Weather/Traffic/AQI Fetch]
       │                  │                        │
       ▼                  ▼                        ▼
  ┌─────────┐      ┌─────────────┐         ┌───────────┐
  │  Job 1  │      │   Job 2     │         │  Job 4    │
  │  NDVI/  │      │   Shadow    │         │  Traffic/ │
  │  LST    │      │   Modeling  │         │  AQI Agg  │
  └────┬────┘      └──────┬──────┘         └─────┬─────┘
       │                   │                      │
       └───────────────────┼──────────────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Job 3     │
                    │   Thermal   │
                    │   Comfort   │
                    │   Score     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Job 5     │
                    │   Graph     │
                    │   Weight    │
                    │   Export    │
                    └──────┬──────┘
                           │
                           ▼
                    [GraphHopper Reload]
```

---

## 3. Desain Modul (Module Design)

### 3.1. Modul Ingestion (`ingestion/`)

| Komponen | File | Responsibility | Schedule |
|:---|:---|:---|:---|
| NDVI/LST Estimator | `ndvi_lst_estimator.py` | Estimasi proxy NDVI (tree density) & LST (Open-Meteo + material correction) per segmen | Harian / on-demand |
| OSM Fetcher | `osm_fetcher.py` | Query Overpass API untuk buildings, trees, footways Surabaya | Harian |
| OSM Loader | `osm_loader.py` | Parse GeoJSON hasil fetch dan insert ke PostGIS | Setelah OSM Fetch |
| Weather Collector | `weather_collector.py` | Fetch data Open-Meteo (suhu, kelembapan, radiasi) | Setiap 15 menit |
| Traffic Collector | `traffic_collector.py` | Fetch TomTom traffic flow data | Setiap 15 menit |
| AQI Collector | `aqi_collector.py` | Fetch WAQI data Surabaya | Setiap 30 menit |
| BMKG RSS Monitor | `bmkg_rss_monitor.py` | Parse RSS feed peringatan dini BMKG | Setiap 5 menit |
| Transit Loader | `transit_loader.py` | Load data halte/stasiun dari OSM + seed SQL | On-demand |
| CCTV Registry | `cctv_registry.py` | Scrape daftar CCTV Dishub Surabaya (ID, nama, koordinat, stream URL) | On-demand / harian |

### 3.2. Modul Spark Processing (`spark_jobs/`)

| Komponen | File | Input | Output |
|:---|:---|:---|:---|
| NDVI/LST Proxy Segmentation | `job_raster_segment.py` | Trees + segments + surface tags (PostGIS) + Open-Meteo temp | `segment_raster_scores` table |
| Shadow Modeling | `job_shadow_model.py` | buildings + trees + segments + solar position | `segment_shadows` table |
| Traffic/AQI Aggregation | `job_traffic_aqi.py` | JSON traffic + AQI data + segments | `segment_traffic_aqi` (internal) |
| Thermal Comfort Score | `job_thermal_comfort.py` | Output Job 1, 2, 4 + weather data | `thermal_comfort_scores` table |
| Graph Weight Export | `job_graph_weight.py` | `thermal_comfort_scores` | `edge_weights` table + JSON file |

### 3.3. Modul Routing Engine (`routing/`)

| Komponen | File | Responsibility |
|:---|:---|:---|
| GraphHopper Custom Model | `thermal_weighting.java` / config | Custom weighting yang membaca `edge_weights` sebagai penalti |
| Route Comparator | `route_service.py` | Menyajikan 2 rute: terpendek vs ternyaman |
| Heat Exposure Calculator | `heat_exposure.py` | Menghitung total paparan panas (menit di bawah matahari) per rute |
| Personal Budget Filter | `personal_budget.py` | Memfilter/menolak rute yang melebihi heat budget pengguna |
| Alert Rerouter | `alert_rerouter.py` | Memblokir segmen yang terdampak peringatan cuaca aktif |

### 3.4. Modul API Backend (`api/`)

| Endpoint | Method | Deskripsi |
|:---|:---|:---|
| `/api/route` | POST | Input: origin, destination, user_profile → Output: rute terpendek + ternyaman |
| `/api/route/{id}/details` | GET | Detail rute: per-segment TCS, shade%, paparan panas |
| `/api/segments/thermal` | GET | Thermal Comfort Score semua segmen (untuk peta heatmap) |
| `/api/dashboard/uhi` | GET | Data hotspot UHI untuk dashboard pemerintah |
| `/api/dashboard/priority-corridors` | GET | Rekomendasi koridor penghijauan |
| `/api/dashboard/walkability` | GET | Statistik walkability & aksesibilitas transit |
| `/api/alerts/active` | GET | Peringatan cuaca aktif |
| `/api/user/profile` | POST/PUT | Buat/update profil heat tolerance pengguna |
| `/api/cctv/nearby` | GET | Daftar CCTV terdekat dari koordinat (dengan stream URL) |
| `/api/cctv/{cctv_id}/stream` | GET | Redirect/proxy ke HLS stream URL CCTV spesifik |

### 3.5. Modul Dashboard & Frontend (`frontend/`)

| Komponen | Teknologi | Fitur |
|:---|:---|:---|
| Navigation App | **MapLibre GL JS** (3D buildings) + OpenFreeMap tiles | Peta interaktif 3D Surabaya, input origin/destination via klik, visualisasi rute dengan gradasi warna TCS, panel perbandingan rute, live CCTV preview |
| Government Dashboard | React + Chart.js + MapLibre | Peta UHI heatmap, grafik walkability, tabel koridor prioritas penghijauan |

---

## 4. Desain Algoritma Inti (Core Algorithm Design)

### 4.1. Thermal Comfort Score (TCS) Formula

```
TCS = w1 * f_shade(shade_ratio, ndvi) 
    + w2 * f_temp(apparent_temperature, lst)
    + w3 * f_air(aqi_value)
    + w4 * f_traffic(congestion_level)
    + w5 * f_surface(surface_quality)

Dimana:
- w1 = 0.35  (bobot keteduhan - faktor dominan)
- w2 = 0.30  (bobot suhu)
- w3 = 0.15  (bobot kualitas udara)
- w4 = 0.10  (bobot kepadatan lalu lintas)
- w5 = 0.10  (bobot kualitas permukaan trotoar)

Setiap f_x() mengembalikan nilai normalisasi 0.0 - 1.0
TCS final: 0.0 (sangat tidak nyaman) → 1.0 (sangat nyaman)
```

**Detail Sub-Fungsi:**

```python
def f_shade(shade_ratio, ndvi):
    """Semakin teduh = semakin nyaman"""
    # shade_ratio: 0-1 dari shadow model
    # ndvi: 0-1 dari citra satelit (canopy density)
    combined = 0.7 * shade_ratio + 0.3 * min(ndvi * 2, 1.0)
    return combined

def f_temp(apparent_temp, lst):
    """Normalisasi suhu: semakin dingin = semakin nyaman"""
    # Range Surabaya: 28 C (nyaman) - 45 C (sangat panas)
    temp_combined = 0.6 * apparent_temp + 0.4 * lst
    score = 1.0 - (temp_combined - 28) / (45 - 28)
    return max(0.0, min(1.0, score))

def f_air(aqi):
    """AQI 0-50 = baik (1.0), 150+ = sangat buruk (0.0)"""
    score = 1.0 - (aqi / 150)
    return max(0.0, min(1.0, score))

def f_traffic(congestion):
    """congestion 0-1, semakin macet = semakin tidak nyaman (asap, bising)"""
    return 1.0 - congestion

def f_surface(surface_type, smoothness):
    """Scoring berdasarkan tipe & kehalusan permukaan"""
    surface_scores = {
        'asphalt': 0.9, 'paving_stones': 0.85, 'concrete': 0.8,
        'compacted': 0.6, 'gravel': 0.4, 'unpaved': 0.3, 'sand': 0.2
    }
    smoothness_scores = {
        'excellent': 1.0, 'good': 0.8, 'intermediate': 0.6,
        'bad': 0.3, 'very_bad': 0.1
    }
    s = surface_scores.get(surface_type, 0.5)
    sm = smoothness_scores.get(smoothness, 0.5)
    return 0.5 * s + 0.5 * sm
```

### 4.2. Shadow Modeling Algorithm

```python
import math

def compute_shadow_polygon(obj_geom, obj_height, latitude, longitude, datetime_val):
    """
    Menghitung poligon bayangan dari sebuah objek (gedung/pohon)
    berdasarkan posisi matahari pada waktu tertentu.
    """
    # Step 1: Hitung posisi matahari
    solar_elevation = get_solar_elevation(latitude, longitude, datetime_val)
    solar_azimuth = get_solar_azimuth(latitude, longitude, datetime_val)
    
    # Step 2: Hitung panjang bayangan
    if solar_elevation <= 0:
        return None  # Matahari di bawah horizon, tidak ada bayangan
    
    shadow_length = obj_height / math.tan(math.radians(solar_elevation))
    
    # Step 3: Hitung arah bayangan (berlawanan dengan azimuth matahari)
    shadow_direction = (solar_azimuth + 180) % 360
    
    # Step 4: Proyeksi bayangan
    # Untuk bangunan (polygon): offset setiap vertex ke arah shadow_direction
    # Untuk pohon (point): buat ellipse/circle dengan radius = shadow_length
    shadow_polygon = project_shadow(obj_geom, shadow_length, shadow_direction)
    
    return shadow_polygon

def compute_segment_shade_ratio(segment_geom, shadows_gdf, segment_buffer=2.0):
    """
    Menghitung proporsi segmen jalan yang terteduh.
    Buffer 2m = lebar rata-rata trotoar.
    """
    segment_area = segment_geom.buffer(segment_buffer)
    total_area = segment_area.area
    
    shaded_area = segment_area.intersection(shadows_gdf.unary_union).area
    shade_ratio = shaded_area / total_area
    
    return shade_ratio  # 0.0 - 1.0
```

### 4.3. Personal Heat Budget Algorithm

```python
def check_heat_budget(route_segments, user_profile, thermal_scores):
    """
    Memeriksa apakah total paparan panas di rute masih dalam
    batas toleransi pengguna.
    """
    # Toleransi berdasarkan profil
    max_exposure = {
        'low': 10,     # maks 10 menit di bawah matahari langsung
        'medium': 20,  # maks 20 menit
        'high': 35     # maks 35 menit
    }
    
    budget_minutes = max_exposure[user_profile.heat_tolerance]
    
    # Hitung total paparan per segmen
    total_sun_minutes = 0.0
    for seg in route_segments:
        tcs = thermal_scores[seg.segment_id]
        seg_walk_time = seg.length_m / 80.0  # asumsi 80m/menit kecepatan jalan
        sun_exposure = seg_walk_time * (1.0 - tcs.shade_ratio)
        total_sun_minutes += sun_exposure
    
    is_within_budget = total_sun_minutes <= budget_minutes
    
    return {
        'within_budget': is_within_budget,
        'total_sun_exposure_min': round(total_sun_minutes, 1),
        'budget_limit_min': budget_minutes,
        'budget_remaining_min': round(budget_minutes - total_sun_minutes, 1)
    }
```

### 4.4. Routing Cost Modification (GraphHopper Custom Model)

```python
def compute_edge_cost(segment, base_time_seconds, tcs_value, user_profile):
    """
    Memodifikasi cost routing berdasarkan Thermal Comfort Score.
    
    Logika: Segmen dengan TCS rendah (panas) mendapat penalti waktu,
    sehingga routing engine cenderung menghindarinya.
    """
    # Penalti maksimum: 3x waktu asli (segmen sangat panas dianggap 3x lebih "jauh")
    MAX_PENALTY_MULTIPLIER = 3.0
    
    # TCS = 1.0 (sangat nyaman) -> multiplier = 1.0 (tanpa penalti)
    # TCS = 0.0 (sangat panas)  -> multiplier = 3.0 (penalti maksimum)
    thermal_multiplier = 1.0 + (1.0 - tcs_value) * (MAX_PENALTY_MULTIPLIER - 1.0)
    
    # Untuk rute "terpendek": gunakan base cost tanpa modifikasi
    shortest_cost = base_time_seconds
    
    # Untuk rute "ternyaman": gunakan modified cost
    comfort_cost = base_time_seconds * thermal_multiplier
    
    return {
        'shortest_cost': shortest_cost,
        'comfort_cost': comfort_cost
    }
```

---

## 5. Desain API (API Design)

### 5.1. Route Request & Response

**Request:**
```json
POST /api/route
{
    "origin": {
        "lat": -7.2756,
        "lng": 112.7426
    },
    "destination": {
        "lat": -7.2650,
        "lng": 112.7508
    },
    "user_profile": {
        "heat_tolerance": "low",
        "prefer_shade": true
    },
    "departure_time": "2026-06-15T10:00:00+07:00"
}
```

**Response:**
```json
{
    "routes": [
        {
            "type": "shortest",
            "distance_m": 1250,
            "duration_min": 15.6,
            "sun_exposure_min": 12.3,
            "avg_tcs": 0.42,
            "within_heat_budget": false,
            "geometry": { "type": "LineString", "coordinates": [] },
            "segments": [
                {
                    "segment_id": 1024,
                    "tcs_value": 0.35,
                    "shade_ratio": 0.20,
                    "apparent_temp": 38.2,
                    "surface": "asphalt",
                    "length_m": 180
                }
            ]
        },
        {
            "type": "most_comfortable",
            "distance_m": 1480,
            "duration_min": 18.5,
            "sun_exposure_min": 5.1,
            "avg_tcs": 0.78,
            "within_heat_budget": true,
            "geometry": { "type": "LineString", "coordinates": [] },
            "segments": []
        }
    ],
    "weather_alert": null,
    "heat_budget": {
        "budget_limit_min": 10,
        "recommended_route": "most_comfortable"
    }
}
```

### 5.2. Dashboard Endpoints

**UHI Hotspot Map:**
```json
GET /api/dashboard/uhi

Response:
{
    "hotspots": [
        {
            "segment_id": 2045,
            "geom": { "type": "LineString", "coordinates": [] },
            "avg_lst": 42.3,
            "avg_tcs": 0.18,
            "street_name": "Jl. Pemuda",
            "shade_ratio": 0.05,
            "pedestrian_traffic": "high"
        }
    ],
    "summary": {
        "total_segments": 15420,
        "critical_segments": 2341,
        "avg_city_tcs": 0.52
    }
}
```

**Priority Corridors:**
```json
GET /api/dashboard/priority-corridors

Response:
{
    "corridors": [
        {
            "corridor_name": "Jl. Basuki Rahmat (Segmen Tunjungan - Gubernur Suryo)",
            "segments": [2045, 2046, 2047, 2048],
            "avg_tcs": 0.22,
            "pedestrian_volume": "very_high",
            "nearest_transit": "Halte Suroboyo Bus Tunjungan",
            "recommendation": "Penanaman pohon peneduh + kanopi buatan",
            "priority_score": 0.95
        }
    ]
}
```

---

## 6. Desain Frontend / UI

### 6.1. Navigation App (Mobile-First)

```
+-------------------------------------+
|  [search] Cari tujuan...            |
+-------------------------------------+
|                                     |
|         [PETA INTERAKTIF]           |
|                                     |
|    Rute divisualisasikan dengan     |
|    gradasi warna:                   |
|    Hijau  = TCS > 0.7 (teduh)      |
|    Kuning = TCS 0.4-0.7            |
|    Merah  = TCS < 0.4 (panas)      |
|                                     |
|    Origin ----------- Destination   |
|                                     |
+-------------------------------------+
|  Pilih Rute:                        |
|                                     |
|  +-----------------------------+    |
|  | Terpendek      1.2 km       |    |
|  |   15 min / 12 min sun      |    |
|  |   [!] Melebihi heat budget  |    |
|  +-----------------------------+    |
|                                     |
|  +-----------------------------+    |
|  | Ternyaman      1.5 km  [v] |    |
|  |   18 min / 5 min sun       |    |
|  |   Avg TCS: 0.78            |    |
|  +-----------------------------+    |
|                                     |
+-------------------------------------+
|  Profil: Toleransi Rendah           |
|  Suhu saat ini: 34 C               |
|  AQI: 68 (Sedang)                  |
+-------------------------------------+
```

### 6.2. Government Dashboard

```
+------------------------------------------------------------------+
|  COMMUTE-COOL Dashboard | Kota Surabaya | 15 Juni 2026, 10:00    |
+------------------------------------------------------------------+
|                                                                  |
|  +----------------------------+  +----------------------------+  |
|  |  Peta UHI Hotspot         |  |  Statistik Kota            |  |
|  |  [Heatmap overlay pada    |  |  Total Ruas Jalan: 15.420  |  |
|  |   peta Surabaya]          |  |  Ruas Kritis:      2.341   |  |
|  |                           |  |  Avg TCS Kota:     0.52    |  |
|  |                           |  |  Halte Terjangkau: 78%     |  |
|  +----------------------------+  +----------------------------+  |
|                                                                  |
|  +-----------------------------------------------------------+  |
|  |  Koridor Prioritas Penghijauan            [Export CSV]     |  |
|  |  #  Koridor              TCS   Volume  Rekomendasi         |  |
|  |  1  Jl. Basuki Rahmat   0.22  Tinggi  Pohon + Kanopi      |  |
|  |  2  Jl. Tunjungan       0.28  Tinggi  Kanopi buatan       |  |
|  |  3  Jl. Darmo           0.31  Sedang  Pohon peneduh       |  |
|  |  4  Jl. Ahmad Yani      0.25  Tinggi  Pohon + shelter     |  |
|  +-----------------------------------------------------------+  |
|                                                                  |
|  +----------------------------+  +----------------------------+  |
|  |  Walkability Score         |  |  First/Last Mile Access    |  |
|  |  [Bar chart per kecamatan] |  |  [Radius coverage map     |  |
|  |                           |  |   dari setiap halte]       |  |
|  +----------------------------+  +----------------------------+  |
+------------------------------------------------------------------+
```

---

## 7. Project Structure

```
commute-cool/
├── README.md
├── docker-compose.yml              # PostgreSQL/PostGIS + MinIO + Spark
├── requirements.txt                # Python dependencies
│
├── ingestion/                      # Data collection scripts
│   ├── __init__.py
│   ├── ndvi_lst_estimator.py       # NDVI/LST proxy estimation (tree density + material correction)
│   ├── osm_fetcher.py             # Overpass API -> GeoJSON
│   ├── osm_loader.py              # GeoJSON -> PostGIS loader
│   ├── weather_collector.py       # Open-Meteo & infoBMKG -> JSON
│   ├── traffic_collector.py       # TomTom/HERE -> JSON
│   ├── aqi_collector.py           # WAQI/OpenAQ -> JSON
│   ├── bmkg_rss_monitor.py        # RSS Feed parser
│   ├── transit_loader.py          # Halte/stasiun data loader
│   └── scheduler.py               # Cron/APScheduler orchestration
│
├── spark_jobs/                     # Apache Spark batch processing
│   ├── __init__.py
│   ├── job_raster_segment.py      # Job 1: NDVI/LST -> per-segment scores
│   ├── job_shadow_model.py        # Job 2: Shadow polygon projection
│   ├── job_traffic_aqi.py         # Job 4: Traffic & AQI aggregation
│   ├── job_thermal_comfort.py     # Job 3: TCS calculation
│   ├── job_graph_weight.py        # Job 5: Export routing weights
│   └── utils/
│       ├── solar_position.py      # Sun elevation & azimuth calculator
│       ├── shadow_geometry.py     # Shadow projection functions
│       └── normalization.py       # Score normalization helpers
│
├── routing/                        # Routing engine integration
│   ├── __init__.py
│   ├── route_service.py           # Main routing orchestrator
│   ├── heat_exposure.py           # Paparan panas calculator
│   ├── personal_budget.py         # Heat budget filter
│   ├── alert_rerouter.py          # Weather alert rerouting
│   └── graphhopper_config/
│       └── custom_model.json      # GraphHopper custom weighting config
│
├── api/                            # FastAPI backend
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   ├── routes/
│   │   ├── navigation.py         # /api/route endpoints
│   │   ├── dashboard.py          # /api/dashboard/* endpoints
│   │   ├── alerts.py             # /api/alerts endpoints
│   │   └── users.py              # /api/user/profile endpoints
│   ├── models/
│   │   ├── schemas.py            # Pydantic request/response models
│   │   └── database.py           # SQLAlchemy/PostGIS models
│   └── services/
│       ├── routing_service.py    # Business logic routing
│       └── dashboard_service.py  # Business logic dashboard
│
├── frontend/                       # Web UI
│   ├── navigation/                # Mobile-first navigation app
│   │   ├── index.html
│   │   ├── map.js                # Leaflet/Mapbox map logic
│   │   ├── route-panel.js        # Route comparison panel
│   │   └── styles.css
│   └── dashboard/                 # Government dashboard (React)
│       ├── package.json
│       ├── src/
│       │   ├── App.jsx
│       │   ├── components/
│       │   │   ├── UHIMap.jsx
│       │   │   ├── CorridorTable.jsx
│       │   │   ├── WalkabilityChart.jsx
│       │   │   └── TransitAccessMap.jsx
│       │   └── services/
│       │       └── api.js
│       └── public/
│
├── database/                       # Database setup
│   ├── init.sql                   # Schema creation (dari Section 2.1)
│   └── seed_transit.sql           # Seed data halte/stasiun Surabaya
│
├── tests/                          # Unit & integration tests
│   ├── test_thermal_comfort.py
│   ├── test_shadow_model.py
│   ├── test_routing.py
│   └── test_api.py
│
├── validation/                     # Model validation scripts
│   ├── validate_shadow.py         # IoU comparison with satellite imagery
│   └── validate_thermal.py        # In-situ measurement comparison
│
├── notebooks/                      # Jupyter notebooks (eksplorasi & demo)
│   ├── 01_explore_ndvi_lst.ipynb
│   ├── 02_shadow_model_demo.ipynb
│   ├── 03_thermal_score_analysis.ipynb
│   └── 04_routing_comparison.ipynb
│
└── docs/
    ├── requirement.md
    ├── design.md                  # (dokumen ini)
    └── presentation/
```

---

## 8. Deployment & Infrastructure

### 8.1. Development Environment (untuk FP)

```yaml
# docker-compose.yml (simplified for local dev)
version: '3.8'
services:
  postgres:
    image: postgis/postgis:15-3.3
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: commute_cool
      POSTGRES_USER: cc_user
      POSTGRES_PASSWORD: cc_dev_pass
    volumes:
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
      - pgdata:/var/lib/postgresql/data

  minio:
    image: minio/minio
    ports: ["9000:9000", "9001:9001"]
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data

  spark-master:
    image: bitnami/spark:3.5
    ports: ["8080:8080", "7077:7077"]
    environment:
      SPARK_MODE: master

  spark-worker:
    image: bitnami/spark:3.5
    environment:
      SPARK_MODE: worker
      SPARK_MASTER_URL: spark://spark-master:7077

  graphhopper:
    image: graphhopper/graphhopper:latest
    ports: ["8989:8989"]
    volumes:
      - ./routing/graphhopper_config:/data

  api:
    build: ./api
    ports: ["8000:8000"]
    depends_on: [postgres, graphhopper]

volumes:
  pgdata:
  minio_data:
```

### 8.2. Scheduling (Job Orchestration)

| Job | Frekuensi | Trigger |
|:---|:---|:---|
| GEE Export (NDVI/LST) | Mingguan (Senin 02:00) | Cron |
| OSM Fetch | Harian (03:00) | Cron |
| Spark Job 1 (Raster Segment) | Setelah GEE Export selesai | Event-driven |
| Spark Job 2 (Shadow Model) | Setelah OSM Fetch + setiap jam 06:00-17:00 | Cron (hourly) |
| Spark Job 4 (Traffic/AQI) | Setiap 15 menit | Cron |
| Spark Job 3 (TCS) | Setelah Job 1/2/4 selesai, minimal setiap 30 menit | Event-driven |
| Spark Job 5 (Weight Export) | Setelah Job 3 selesai | Event-driven |
| GraphHopper Reload | Setelah Job 5 selesai | API trigger |
| BMKG RSS Check | Setiap 5 menit | Cron |

---

## 9. Mapping ke Functional Requirements

| Requirement | Modul Desain | Komponen Utama |
|:---|:---|:---|
| F-01, F-02, F-03 | Ingestion + Spark Job 1 | `ndvi_lst_estimator.py` + `job_raster_segment.py` |
| F-04, F-05 | Spark Job 2 | `job_shadow_model.py` + `solar_position.py` |
| F-06 | Spark Job 3 | `job_thermal_comfort.py` (formula TCS) |
| F-07 | Routing module | `personal_budget.py` |
| F-08 | Routing + Spark Job 5 | `job_graph_weight.py` + GraphHopper custom model |
| F-09 | API + Routing | `route_service.py` + `/api/route` |
| F-10 | Routing | `heat_exposure.py` |
| F-11 | Ingestion + Routing | `bmkg_rss_monitor.py` + `alert_rerouter.py` |
| F-12 | API + Dashboard | `/api/dashboard/uhi` + `UHIMap.jsx` |
| F-13 | API + Dashboard | `/api/dashboard/priority-corridors` + `CorridorTable.jsx` |
| F-14 | API + Dashboard | `/api/dashboard/walkability` + `WalkabilityChart.jsx` |
| F-15 | Ingestion + API + Frontend | `cctv_registry.py` + `/api/cctv/nearby` + `cctv-preview.js` |
| F-16 | Future Work | YOLO vehicle counting pipeline (pengganti TomTom) |
