# 📖 Panduan Developer — COMMUTE-COOL

> Panduan ini ditujukan untuk developer baru yang baru saja clone repo ini.  
> Baca dari atas ke bawah, lakukan langkah-langkahnya secara berurutan.

---

## 🧠 Tentang Proyek Ini

**COMMUTE-COOL** adalah sistem navigasi pejalan kaki berbasis **Thermal Comfort Score (TCS)** — bukan sekadar rute tercepat, melainkan rute yang paling nyaman dari paparan panas matahari.

**Studi kasus:** Kota Surabaya | Final Project Big Data | Semester 4

**Fitur utama:**
| Fitur | Deskripsi |
|---|---|
| 🗺️ Navigasi Termal | Bandingkan rute Terpendek vs Ternyaman |
| 🌡️ Thermal Heatmap | Visualisasi peta panas seluruh jalur pedestrian Surabaya |
| 📷 Live CCTV | Lihat kondisi jalan real-time dari 444 CCTV Dishub Surabaya |
| 📊 Dashboard Pemerintah | Statistik walkability, koridor prioritas penghijauan |
| 🧍 Personal Heat Budget | Rekomendasi rute disesuaikan toleransi panas pengguna |

---

## 🛠️ Tech Stack Lengkap

| Layer | Teknologi | Versi |
|---|---|---|
| **Frontend** | React + TypeScript + Vite | React 19, TS 6, Vite 8 |
| **UI Library** | Mantine UI | v9 |
| **Peta** | MapLibre GL JS | v5 |
| **Video CCTV** | HLS.js | v1.6 |
| **Backend API** | FastAPI (Python) | — |
| **DB Driver** | asyncpg (async PostgreSQL) | — |
| **Database** | PostgreSQL 15 + PostGIS + pgRouting | — |
| **Big Data** | Apache Spark 3.5 (PySpark) | — |
| **Geo Processing** | Apache Sedona 1.6 | — |
| **Routing Engine** | pgRouting (pgr_dijkstra) | — |
| **Deployment** | Docker Compose | 3 services |

---

## 📁 Struktur Folder & Fungsinya

```
commute-cool/
│
├── 📂 frontend/                ← FRONTEND (React + TypeScript + Vite)
│   └── src/
│       ├── components/         ← Komponen UI (MapView, SearchPanel, dll)
│       ├── pages/              ← Halaman (NavigationPage, DashboardPage)
│       ├── services/           ← Pemanggil API (api.ts)
│       └── types/              ← TypeScript interfaces
│
├── 📂 api/                     ← BACKEND (FastAPI Python)
│   ├── main.py                 ← Entry point FastAPI
│   ├── db.py                   ← Koneksi asyncpg ke PostgreSQL
│   ├── routes/                 ← Endpoint API
│   │   ├── navigation.py       ← POST /api/route, GET /api/segments/thermal
│   │   ├── dashboard.py        ← GET /api/dashboard/*
│   │   └── cctv.py             ← GET /api/cctv/nearby
│   ├── models/
│   │   ├── schemas.py          ← Pydantic request/response models
│   │   └── database.py         ← SQLAlchemy ORM (referensi)
│   └── services/               ← Business logic (routing, heat budget, dll)
│
├── 📂 spark_jobs/              ← BIG DATA PIPELINE (PySpark + Sedona)
│   ├── run_pipeline.py         ← Orchestrator pipeline (jalankan semua job)
│   ├── job_raster_segment.py   ← Job 1: NDVI/LST (vegetasi & suhu permukaan)
│   ├── job_shadow_model.py     ← Job 2: Shadow ratio (bayangan bangunan/pohon)
│   ├── job_traffic_aqi.py      ← Job 4: Traffic & kualitas udara per segmen
│   ├── job_thermal_comfort.py  ← Job 3: Hitung TCS (formula utama)
│   ├── job_graph_weight.py     ← Job 5: Export TCS → edge weight pgRouting
│   └── config.py               ← Konfigurasi JDBC & variabel global
│
├── 📂 ingestion/               ← PENGUMPULAN DATA (Python scripts)
│   ├── osm_fetcher.py          ← Ambil data jalan/bangunan/pohon dari OSM
│   ├── osm_loader.py           ← Load GeoJSON ke PostGIS
│   ├── weather_collector.py    ← Open-Meteo API (cuaca real-time)
│   ├── aqi_collector.py        ← WAQI API (kualitas udara)
│   ├── traffic_collector.py    ← TomTom API (kepadatan lalu lintas)
│   ├── cctv_registry.py        ← Registrasi 444 CCTV Dishub Surabaya
│   └── scheduler.py            ← Penjadwalan update data berkala
│
├── 📂 database/                ← SKEMA DATABASE
│   ├── init.sql                ← DDL schema + pgRouting topology function
│   └── seed_transit.sql        ← Data awal: halte transit Surabaya
│
├── 📂 routing/                 ← ROUTING SERVICE
│   ├── route_service.py        ← Logika pgr_dijkstra
│   ├── personal_budget.py      ← Kalkulasi heat budget personal
│   ├── heat_exposure.py        ← Kalkulasi paparan panas
│   └── alert_rerouter.py       ← Rerouting saat ada peringatan cuaca
│
├── 📂 validation/              ← VALIDASI HASIL
│   ├── validate_shadow.py      ← Validasi akurasi model bayangan
│   └── validate_thermal.py     ← Validasi hasil TCS
│
├── 📂 tests/                   ← UNIT TESTS (pytest)
│
├── docker-compose.yml          ← Orkestrasi 3 Docker services
├── Dockerfile.api              ← Image untuk FastAPI (Python 3.11-slim)
├── Dockerfile.spark            ← Image untuk Spark + Sedona JARs
├── Dockerfile.postgres         ← Image untuk PostgreSQL + PostGIS + pgRouting
├── .env.example                ← Template environment variables
├── requirements.txt            ← Python deps (umum)
├── requirements-docker.txt     ← Python deps untuk container API
└── requirements-spark.txt      ← Python deps untuk container Spark
```

---

## 🔄 Alur Data (Flow) Sistem

```
[Sumber Data Eksternal]
  Open-Meteo (cuaca) ─┐
  WAQI (AQI) ─────────┤
  TomTom (traffic) ───┤──► [ingestion/] ──► data/raw/ (JSON)
  OSM (jalur/pohon) ──┘

[Spark Pipeline - berjalan sekali saat startup Docker]
  data/raw/ + PostGIS ──► spark_jobs/run_pipeline.py
    Job 1: NDVI/LST            (vegetasi & suhu permukaan)
    Job 2: Shadow Modeling     (bayangan bangunan & pohon)
    Job 4: Traffic + AQI       (agregasi per segmen jalan)
    Job 3: Thermal Comfort     (hitung TCS tiap segmen)
    Job 5: Graph Weight Export (TCS → biaya routing)
        ↓
  PostgreSQL (PostGIS + pgRouting)
    → tabel: segments, buildings, trees
    → tabel: thermal_comfort_scores
    → tabel: edge_weights (untuk pgRouting)

[Backend - FastAPI berjalan terus]
  GET  /api/segments/thermal    → data heatmap
  POST /api/route               → pgr_dijkstra (2 rute: tercepat vs ternyaman)
  GET  /api/dashboard/*         → statistik walkability
  GET  /api/cctv/nearby         → daftar CCTV terdekat

[Frontend - React berjalan di mesin lokal]
  MapLibre GL JS  ← render peta + heatmap + rute
  Mantine UI      ← komponen UI (panel, modal, tabel)
  HLS.js          ← streaming CCTV
  services/api.ts ← semua panggilan ke FastAPI
```

---

## ✅ Cara Setup dari Nol (Baru Clone)

### Prerequisites yang Dibutuhkan

| Software | Versi Min | Untuk |
|---|---|---|
| **Docker Desktop** | Latest | Menjalankan backend (DB + Spark + API) |
| **Node.js** | 18+ | Menjalankan frontend |
| **Git** | Any | Sudah di-clone ✔ |

> Python **tidak perlu** diinstall secara lokal — semua Python code (FastAPI, Spark) jalan di dalam Docker.

---

### Langkah 1 — Buat file `.env`

```powershell
# Di folder root commute-cool/
copy .env.example .env
```

Lalu buka `.env` dan isi (opsional, pipeline tetap jalan tanpa API key):

```env
TOMTOM_API_KEY=isi_disini_kalau_punya   # https://developer.tomtom.com/
WAQI_API_TOKEN=isi_disini_kalau_punya   # https://aqicn.org/data-platform/token/
```

---

### Langkah 2 — Jalankan Backend (Docker)

```powershell
# Di folder root commute-cool/
docker compose up --build
```

**Yang terjadi di balik layar:**

| Service | Container | Port | Fungsi |
|---|---|---|---|
| `postgres` | `commute_cool_db` | `5432` | PostgreSQL + PostGIS + pgRouting |
| `spark-pipeline` | `commute_cool_spark` | — | Fetch data + 5 Spark jobs → lalu exit |
| `api` | `commute_cool_api` | `8000` | FastAPI aktif terus |

> ⏳ **Proses pertama kali ~5–10 menit** karena Spark men-download JARs dan memproses data OSM Surabaya.

Tunggu sampai terlihat log seperti:
```
commute_cool_spark exited with code 0   ← Pipeline selesai, data sudah ada
```

---

### Langkah 3 — Jalankan Frontend

```powershell
# Masuk ke folder frontend
cd frontend

# Install semua dependencies Node.js (hanya perlu dilakukan sekali)
npm install

# Jalankan dev server
npm run dev
```

Buka browser ke: **http://localhost:3000**

---

### Langkah 4 — Verifikasi Sistem Berjalan

```powershell
# Cek API hidup
curl http://localhost:8000/health

# Cek data sudah ada di database
docker exec commute_cool_db psql -U cc_user -d commute_cool -c "SELECT COUNT(*) FROM thermal_comfort_scores;"
# Harus > 0

# Cek docs API (Swagger UI)
# Buka http://localhost:8000/docs di browser
```

---

## ✏️ Panduan Edit Kode

### 🖥️ Edit Frontend

| Mau edit apa? | File/Folder yang diedit |
|---|---|
| Halaman Navigasi (peta & panel rute) | `frontend/src/pages/NavigationPage.tsx` |
| Halaman Dashboard (statistik) | `frontend/src/pages/DashboardPage.tsx` |
| Komponen peta (MapLibre) | `frontend/src/components/MapView.tsx` |
| Panel pencarian lokasi | `frontend/src/components/SearchPanel.tsx` |
| Panel hasil rute | `frontend/src/components/RoutePanel.tsx` |
| Modal CCTV | `frontend/src/components/CCTVModal.tsx` |
| Semua panggilan ke API backend | `frontend/src/services/api.ts` |
| TypeScript interfaces/types | `frontend/src/types/index.ts` |
| Entry point app | `frontend/src/App.tsx` |

**Setelah edit frontend:** Vite Hot Reload otomatis — browser langsung update tanpa restart.

---

### ⚙️ Edit Backend (API)

| Mau edit apa? | File yang diedit |
|---|---|
| Tambah/ubah endpoint navigasi & heatmap | `api/routes/navigation.py` |
| Tambah/ubah endpoint dashboard | `api/routes/dashboard.py` |
| Tambah/ubah endpoint CCTV | `api/routes/cctv.py` |
| Ubah koneksi database | `api/db.py` |
| Tambah/ubah Pydantic schema (request/response) | `api/models/schemas.py` |
| Ubah logika routing pgRouting | `api/routes/navigation.py` |
| Tambah service/business logic | `api/services/` |

**Setelah edit backend:**
```powershell
# Restart container API saja (tidak perlu rebuild semua)
docker compose restart api

# Atau rebuild kalau ada perubahan dependencies
docker compose up --build api
```

---

### 🗄️ Edit Database / Schema

| Mau edit apa? | File yang diedit |
|---|---|
| Skema tabel (DDL) | `database/init.sql` |
| Data awal transit/halte | `database/seed_transit.sql` |

> ⚠️ **Perhatian:** Perubahan di `init.sql` hanya diterapkan saat PostgreSQL pertama kali diinisialisasi.  
> Untuk reset database dan terapkan perubahan baru:
> ```powershell
> docker compose down -v   # Hapus volume (data hilang!)
> docker compose up --build
> ```

---

### 🔥 Edit Spark Pipeline (Big Data)

| Mau edit apa? | File yang diedit |
|---|---|
| Formula TCS (Thermal Comfort Score) | `spark_jobs/job_thermal_comfort.py` |
| Model bayangan (shadow modeling) | `spark_jobs/job_shadow_model.py` |
| Kalkulasi NDVI/LST | `spark_jobs/job_raster_segment.py` |
| Agregasi traffic & AQI | `spark_jobs/job_traffic_aqi.py` |
| Export edge weight ke pgRouting | `spark_jobs/job_graph_weight.py` |
| Jalankan ulang semua pipeline | `spark_jobs/run_pipeline.py` |

**Setelah edit Spark jobs:**
```powershell
# Rebuild dan jalankan ulang pipeline Spark
docker compose up --build spark-pipeline
```

---

### 📡 Edit Ingestion (Pengambilan Data)

| Mau edit apa? | File yang diedit |
|---|---|
| Ambil data cuaca | `ingestion/weather_collector.py` |
| Ambil data AQI | `ingestion/aqi_collector.py` |
| Ambil data traffic | `ingestion/traffic_collector.py` |
| Ambil data peta OSM | `ingestion/osm_fetcher.py` |
| Load OSM ke PostGIS | `ingestion/osm_loader.py` |
| Daftar CCTV Surabaya | `ingestion/cctv_registry.py` |
| Jadwal update data | `ingestion/scheduler.py` |

---

## 🐳 Docker — Referensi Cepat

```powershell
# Jalankan semua (pertama kali / setelah edit Dockerfile)
docker compose up --build

# Jalankan tanpa rebuild (sudah pernah build)
docker compose up

# Hentikan semua
docker compose down

# Hentikan dan hapus volume (RESET DATABASE)
docker compose down -v

# Cek status container
docker compose ps

# Lihat log semua service
docker compose logs -f

# Lihat log service tertentu
docker compose logs -f api
docker compose logs -f spark-pipeline
docker compose logs -f postgres

# Masuk ke dalam container database
docker exec -it commute_cool_db psql -U cc_user -d commute_cool

# Restart satu service
docker compose restart api
```

---

## 🌐 URL & Port Layanan

| Layanan | URL | Keterangan |
|---|---|---|
| **Frontend** | http://localhost:3000 | React app (Vite dev server) |
| **Backend API** | http://localhost:8000 | FastAPI |
| **Swagger Docs** | http://localhost:8000/docs | Dokumentasi & testing API |
| **ReDoc** | http://localhost:8000/redoc | Dokumentasi API alternatif |
| **PostgreSQL** | localhost:5432 | DB: `commute_cool`, User: `cc_user`, Pass: `cc_dev_pass` |

---

## 🧪 Testing

```powershell
# Jalankan unit tests (dari root folder)
python -m pytest tests/ -v

# Test endpoint API
curl http://localhost:8000/health

# Test routing
curl -X POST http://localhost:8000/api/route `
  -H "Content-Type: application/json" `
  -d '{"origin":{"lat":-7.27,"lng":112.75},"destination":{"lat":-7.26,"lng":112.74}}'
```

---

## ❓ Troubleshooting Umum

| Masalah | Solusi |
|---|---|
| `docker compose` not found | Gunakan `docker-compose` (dengan dash) atau update Docker Desktop |
| Port 5432 sudah dipakai | Hentikan PostgreSQL lokal: `net stop postgresql` |
| Port 8000 sudah dipakai | Hentikan service lain yang pakai port 8000 |
| `npm install` error | Pastikan Node.js ≥ 18: `node --version` |
| Frontend tidak bisa connect ke API | Pastikan Docker backend sudah running dan port 8000 terbuka |
| `thermal_comfort_scores` count = 0 | Tunggu spark-pipeline selesai (exit code 0), atau lihat: `docker logs commute_cool_spark` |
| Database tidak bisa connect | Cek PostgreSQL health: `docker compose ps` |

---

## 📌 Ringkasan Quick Start (TL;DR)

```powershell
# 1. Buat .env
copy .env.example .env

# 2. Jalankan backend (tunggu spark-pipeline exit 0, ~10 menit pertama kali)
docker compose up --build

# 3. Di terminal baru, jalankan frontend
cd frontend
npm install
npm run dev

# 4. Buka browser
# Frontend : http://localhost:3000
# API Docs : http://localhost:8000/docs
```

---

*Panduan ini dibuat berdasarkan isi repo pada Juni 2026. Update sesuai kebutuhan jika ada perubahan struktur.*
