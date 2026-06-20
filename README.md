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

## Arsitektur & Medallion HDFS Data Lakehouse

COMMUTE-COOL mengimplementasikan arsitektur **Data Lakehouse** dengan pemisahan layer **Medallion (Bronze, Silver, Gold)** menggunakan **HDFS (Hadoop Distributed File System)** sebagai media penyimpanan Big Data dan **Apache Spark** sebagai engine pemrosesan data terdistribusi.

```
Docker Compose (HDFS Data Lakehouse + Serving Layer)
+-----------------------------------------------------------------------------------------+
|                                                                                         |
| [ Ingestion Layer ] ──► [ HDFS Bronze ] ──► [ HDFS Silver ] ──► [ HDFS Gold ]           |
|  Cuaca, AQI, Traffic      (Raw JSON)         (Parquet Clnd)     (Parquet Aggr)          |
|                                                                   │                     |
|                                                                   ▼ [Spark JDBC Sink]   |
| [ API (FastAPI) ] ◄── [ Serving Layer (PostgreSQL/PostGIS) ] ◄────┘                     |
|   POST /api/route                                                                       |
|   GET /api/dashboard/temperature-heatmap                                                |
|   GET /api/dashboard/active-alerts                                                      |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
                                          ^
                                          | REST API http://localhost:8000
                                          |
+-----------------------------------------------------------------------------------------+
| [ Frontend Layer (lokal, npm run dev) ]                                                 |
|   Next.js (App Router) + Mantine UI + MapLibre GL JS (Hardware-Accelerated Heatmap)     |
+-----------------------------------------------------------------------------------------+
```

### Alur Data Medallion

1. **Bronze Layer:** Data JSON cuaca, kemacetan, kualitas udara, dan RSS BMKG diunggah langsung ke `hdfs://namenode:9000/lakehouse/bronze/`.
2. **Silver Layer:** Spark membersihkan data Bronze, menstandarkan tipe data/skema, melakukan interpolasi spasial, dan menyimpan hasilnya sebagai **Parquet terpartisi** di `hdfs://namenode:9000/lakehouse/silver/`.
3. **Gold Layer:** Spark menghitung LST/NDVI proxy, memproyeksikan bayangan 3D gedung & pohon, serta menghitung Thermal Comfort Score (TCS) dan *edge weights* navigasi. Hasilnya disimpan sebagai **Parquet** di `hdfs://namenode:9000/lakehouse/gold/`.
4. **Serving Layer:** Data Gold disinkronkan ke PostgreSQL/PostGIS agar API FastAPI dapat melakukan kueri pgRouting (`pgr_dijkstra`) dengan latency sangat rendah (< 2 detik).

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

### Step 2: Jalankan Backend & Database (Docker)

Buka terminal di root folder, lalu jalankan:
```powershell
docker compose up -d --build
```

**⚠️ PENTING UNTUK CLONE PERTAMA KALI (FIRST TIME SETUP):**
Saat pertama kali dijalankan, sistem tidak memiliki data. Kontainer `spark-pipeline` akan mengunduh jalanan Surabaya dari OpenStreetMap, memotong-motongnya menjadi 105.000 titik persimpangan (*node topology*), dan menghitung nilai *Thermal Comfort Score* (TCS) masing-masing jalan.
- Proses ini memakan waktu sekitar **10-15 menit** (tergantung koneksi dan CPU).
- Anda bisa melihat progress-nya dengan command: `docker logs -f commute_cool_spark`
- Tunggu hingga kontainer `spark-pipeline` selesai dan berstatus `exited (0)`.

**💡 UNTUK PENGGUNAAN SELANJUTNYA:**
Karena sistem menggunakan *Persistent Volume* (`pgdata`), data rute yang sudah di-generate **tidak akan hilang**. Besoknya, Anda tidak perlu menunggu 15 menit lagi. Cukup ketik `docker compose up -d` dan API akan menyala dalam hitungan detik.

### Step 3: Verifikasi API & Database

Pastikan data rute dan panas sudah berhasil masuk ke database:
```powershell
docker exec commute_cool_db psql -U cc_user -d commute_cool -c "SELECT COUNT(*) FROM thermal_comfort_scores;"
```
*(Harus menampilkan angka > 105000)*

### Step 4: Jalankan Frontend (Next.js)

Buka terminal baru, pindah ke folder frontend:
```powershell
cd frontend
npm install
npm run dev
```

Buka browser Anda di: `http://localhost:3000`

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
- ITDP Indonesia (2020). Pedoman Teknis Trotoar Terintegrasi dan Integrasi Antarmoda.
- Kong, L., et al. (2021). Assessment of Pedestrian Thermal Comfort under Different Tree Canopy Configurations in Tropical Urban Environments. Building and Environment, Vol. 195.
- Teshima, Y., et al. (2021). Microclimate and Pedestrian Thermal Comfort in Tropical High-Density Cities: The Effect of Shade Trees on UTCI. Sustainable Cities and Society, Vol. 72.
- Santamouris, M. (2020). Recent progress in cool phytotechnologies and pavement cooling to mitigate urban heat island. Solar Energy, Vol. 200.
- Zardo, F., et al. (2021). Shading paths: A spatial optimization model to minimize pedestrian heat stress along walking routes in hot cities. Landscape and Urban Planning, Vol. 214.

---

## Tim

Final Project Big Data -- Semester 4
