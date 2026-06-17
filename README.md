# COMMUTE-COOL

**Sistem Navigasi Pejalan Kaki Berbasis Kenyamanan Termal untuk Mendukung Smart City**

Studi Kasus: Kota Surabaya | Final Project Big Data | Semester 4

---

## Deskripsi

COMMUTE-COOL membantu pejalan kaki menemukan rute yang bukan hanya tercepat, tetapi juga paling nyaman dari paparan panas matahari. Sistem menggabungkan data cuaca real-time, pemodelan bayangan gedung/pohon, kualitas udara, kepadatan lalu lintas, dan kualitas trotoar untuk menghasilkan Thermal Comfort Score (TCS) per segmen jalan.

Fitur utama:
- **Personal Heat Budget** -- rekomendasi rute disesuaikan dengan toleransi panas pengguna
- **pgRouting + TCS Weighting** -- routing graph-based yang memperhitungkan kenyamanan termal sebagai cost
- **City-Wide Thermal Heatmap** -- visualisasi kenyamanan termal seluruh jalur pedestrian Surabaya
- **Live CCTV Preview** -- lihat kondisi jalan real-time dari 444 CCTV Dishub Surabaya
- **Dashboard Pemerintah** -- koridor prioritas penghijauan, statistik walkability (data real dari pipeline)

---

## 🔥 Pembaruan Penting: Sistem Rute Ekstra Presisi & Optimasi Performa
Aplikasi ini baru saja mendapatkan peningkatan skala besar pada sistem *database*:
1. **Routing 100% Akurat (Zero 0km Bug):** Data jalan raya OpenStreetMap kini dipecah secara persisi tinggi pada setiap persimpangan *(node network topology)*. Menghasilkan >105.000 patahan jalan yang memastikan rute ditarik dari titik ke titik dengan sempurna, tidak lagi tembus tembok atau jalan buntu.
2. **Kinerja Super Cepat (GIST Index & JOIN Optimization):** Kueri *Dijkstra* untuk navigasi pejalan kaki dan kueri analitik halaman Dashboard telah dioptimasi dengan *Spatial Index (GIST)* serta *Direct Join*. Pencarian rute yang sebelumnya *timeout* kini berjalan **dalam waktu kurang dari 2 detik**!
3. **Data Persisten (Permanen):** Seluruh data hasil komputasi *topology* dan *Thermal Comfort Score* **tersimpan secara permanen** di dalam Docker Volume (`pgdata`). Anda **TIDAK PERLU** menunggu 15 menit lagi meskipun laptop/PC dimatikan. Cukup jalankan `docker compose up -d` dan `npm run dev`, semuanya akan langsung siap!

---

## Tech Stack

| Layer | Teknologi |
|---|---|
| Processing | Apache Spark 3.5 (PySpark) + Apache Sedona 1.6 |
| Database | PostgreSQL 15 + PostGIS 3.3 + pgRouting 3.6 |
| Routing | pgRouting (pgr_dijkstra) dengan `segments_noded` topology |
| Backend API | FastAPI + asyncpg (Python) |
| Frontend | Next.js (App Router) + TypeScript + Mantine UI + MapLibre |
| Map | MapLibre GL JS (3D, free, no token) + OpenFreeMap |
| CCTV | HLS.js + Dishub Surabaya streams |
| Deployment | Docker Compose (Persistent Volumes) |

### Sumber Data (semua gratis)

| Data | Sumber | Tipe |
|---|---|---|
| Cuaca real-time | Open-Meteo API | REST JSON |
| Jalur, bangunan, pohon | OpenStreetMap (Overpass API) | GeoJSON |
| Kualitas udara | WAQI API (aqicn.org) | REST JSON |
| Traffic | TomTom Traffic API | REST JSON |
| Peringatan cuaca | BMKG RSS Feed | XML |
| CCTV lalu lintas | Dishub Surabaya (HLS) | Video |
| NDVI proxy | Tree density dari OSM | Spatial query |
| LST proxy | Open-Meteo + koreksi material | Calculated |

---

## Arsitektur

```
Docker Compose (Backend)
+-------------------------------------------------------------------+
|                                                                   |
|  spark-pipeline (one-shot)         api (FastAPI :8000)            |
|  Ingest APIs -> 5 Spark Jobs       POST /api/route (pgRouting)    |
|  Build pgRouting topology          GET /api/segments/thermal      |
|  -> exit 0                         GET /api/dashboard/*           |
|                                    GET /api/cctv/nearby           |
|         |  JDBC                         |  asyncpg                |
|         v                               v                         |
|  postgres (PostGIS + pgRouting :5432)                             |
|  segments + TCS + edge_weights + routing topology                 |
+-------------------------------------------------------------------+
                          ^
                          | REST API http://localhost:8000
                          |
+-------------------------------------------------------------------+
|  Frontend (lokal, npm run dev)                                    |
|  Next.js (App Router) + Mantine UI + MapLibre GL JS               |
|  Heatmap overlay + route display + CCTV modal + dashboard         |
+-------------------------------------------------------------------+
```

### Pipeline Data Flow

```
1. Ingestion: Open-Meteo + WAQI + TomTom -> data/raw/ (JSON)
2. OSM Load: GeoJSON -> PostGIS (segments, buildings, trees)
3. Node Topology: Ekstraksi persimpangan murni (ST_Node -> `segments_noded`)
4. pgRouting: Build network topology (`pgr_createTopology` untuk 105k patahan)
5. Spark Job 1: NDVI/LST (tree density + surface correction)
6. Spark Job 2: Shadow Modeling (solar position + building/tree geometry)
7. Spark Job 3: Traffic + AQI Aggregation per segment
8. Spark Job 4: Thermal Comfort Score (weighted formula)
9. Map Properties: Pewarisan nilai TCS ke pecahan topologi jalan lama
10. API: `pgr_dijkstra` on `segments_noded` -> route + TCS data
```

---

## Routing Engine

COMMUTE-COOL menggunakan pgRouting (extension PostgreSQL) untuk graph-based routing:

- **Shortest route**: `pgr_dijkstra` dengan cost = jarak/kecepatan jalan kaki
- **Most comfortable route**: `pgr_dijkstra` dengan cost = `edge_weights.total_cost` (jarak + thermal penalty)

Thermal penalty dihitung dari TCS:
```
total_cost = base_cost * (1 + (1 - TCS) * 2)
```
- TCS = 1.0 (nyaman) -> penalty 1x (tanpa tambahan)
- TCS = 0.5 (sedang) -> penalty 2x
- TCS = 0.0 (panas) -> penalty 3x

Ini membuat router secara alami menghindari segmen panas dan memilih rute yang lebih teduh.

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- Node.js 18+ (untuk frontend)

### Step 1: Setup Environment

```powershell
copy .env.example .env
```

Edit `.env`, isi API keys (opsional, pipeline tetap jalan tanpa mereka):
```
TOMTOM_API_KEY=your_key
WAQI_API_TOKEN=your_token
```

### Step 2: Jalankan Backend (Docker)

```powershell
docker compose up --build
```

Services:
- **postgres** -- PostgreSQL + PostGIS + pgRouting, auto-init schema
- **spark-pipeline** -- Fetch API data, load OSM, build topology, run 5 Spark jobs, exit
- **api** -- FastAPI on http://localhost:8000

Tunggu spark-pipeline selesai (exit 0). Pertama kali butuh 5-10 menit.

### Step 3: Jalankan Frontend

```powershell
cd frontend
npm install
npm run dev
```

Buka http://localhost:3000

### Verifikasi Data

```powershell
docker exec commute_cool_db psql -U cc_user -d commute_cool -c "SELECT COUNT(*) FROM thermal_comfort_scores;"
```

Harus > 0 setelah pipeline selesai.

---

## Cara Menggunakan

### Navigasi

1. Buka tab Navigasi di http://localhost:3000
2. Klik peta untuk set titik awal (atau ketik nama lokasi + Enter)
3. Klik lagi untuk set tujuan
4. Klik "Cari Rute"
5. Bandingkan 2 rute: Terpendek vs Ternyaman
6. Lihat TCS score, durasi sinar matahari, dan heat budget

### Dashboard

1. Buka tab Dashboard
2. Lihat statistik real dari pipeline (total segmen, segmen kritis, avg TCS)
3. Tab "Koridor Prioritas" -- ranking jalan yang butuh penghijauan
4. Tab "Walkability" -- aksesibilitas transit

---

## Thermal Comfort Score (TCS)

```
TCS = 0.35 * shade_score
    + 0.30 * temperature_score
    + 0.15 * aqi_score
    + 0.10 * traffic_score
    + 0.10 * surface_score

Range: 0.0 (sangat panas) -> 1.0 (sangat nyaman)
```

Visualisasi di peta:
- Hijau (TCS > 0.7) -- teduh, nyaman
- Kuning (TCS 0.4-0.7) -- sedang
- Merah (TCS < 0.4) -- panas

---

## Struktur Project

```
commute-cool/
|-- api/                         FastAPI backend
|   |-- main.py                  App entry + lifespan
|   |-- db.py                    asyncpg connection pool
|   |-- routes/
|   |   |-- navigation.py       pgRouting route + thermal heatmap
|   |   |-- dashboard.py        UHI, corridors, walkability
|   |   +-- cctv.py             CCTV spatial query
|   +-- models/
|       |-- schemas.py           Pydantic models
|       +-- database.py          SQLAlchemy ORM (reference)
|-- spark_jobs/                  PySpark + Sedona processing
|   |-- run_pipeline.py          Full pipeline orchestrator
|   |-- config.py                Shared JDBC config
|   |-- job_raster_segment.py    Job 1: NDVI/LST
|   |-- job_shadow_model.py      Job 2: Shadow ratio
|   |-- job_traffic_aqi.py       Job 4: Traffic aggregation
|   |-- job_thermal_comfort.py   Job 3: TCS calculation
|   |-- job_graph_weight.py      Job 5: Edge weights
|   +-- utils/                   Solar position, shadow geometry, normalization
|-- ingestion/                   Data collection scripts
|-- frontend/                    React + Mantine + Vite
|   |-- src/
|   |   |-- components/          MapView, SearchPanel, RoutePanel, CCTVModal
|   |   |-- pages/               NavigationPage, DashboardPage
|   |   |-- services/api.ts      Typed API calls
|   |   +-- types/index.ts       TypeScript interfaces
|   +-- package.json
|-- database/
|   |-- init.sql                 Schema + pgRouting topology function
|   +-- seed_transit.sql         Transit stops
|-- docker-compose.yml           3 services: postgres, spark, api
|-- Dockerfile.api               Python 3.11-slim
|-- Dockerfile.spark             Spark 3.5 + Sedona JARs
|-- requirements-docker.txt      API deps
|-- requirements-spark.txt       Spark deps
+-- .env.example                 Environment template
```

---

## Testing

```powershell
# Unit tests
cd ..
python -m pytest tests/ -v

# API health check
curl http://localhost:8000/health

# Verify routing works
curl -X POST http://localhost:8000/api/route -H "Content-Type: application/json" -d "{\"origin\":{\"lat\":-7.27,\"lng\":112.75},\"destination\":{\"lat\":-7.26,\"lng\":112.74}}"
```

---

## Referensi

- Althoff et al. (2017). Large-scale physical activity data reveal worldwide activity inequality. Nature, 547.
- Copernicus Climate Change Service. Global Climate Highlights 2024.
- ITDP Indonesia. Pedoman Integrasi Antarmoda.

---

## Tim

Final Project Big Data -- Semester 4
