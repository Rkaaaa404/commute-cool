# Teduh

**Sistem Navigasi Pejalan Kaki Berbasis Kenyamanan Termal untuk Mendukung Smart City**

Studi Kasus: Kota Surabaya | Final Project Big Data | Semester 4

> 📖 **Dokumen terkait:** panduan presentasi & pemahaman teknis E2E di [docs/PENCERDASAN.md](docs/PENCERDASAN.md) · deployment gratis (Vercel + AWS Lambda + Supabase) di [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## Deskripsi

Teduh membantu pejalan kaki menemukan rute yang bukan hanya tercepat, tetapi juga paling nyaman dari paparan panas matahari. Sistem menggabungkan data cuaca real-time, pemodelan bayangan gedung/pohon, kualitas udara, kepadatan lalu lintas, dan kualitas trotoar untuk menghasilkan Thermal Comfort Score (TCS) per segmen jalan.

Fitur utama:
- **Personal Heat Budget** -- rekomendasi rute disesuaikan dengan toleransi panas pengguna
- **pgRouting + TCS Weighting** -- routing graph-based yang memperhitungkan kenyamanan termal sebagai cost
- **City-Wide Thermal Heatmap** -- visualisasi kenyamanan termal seluruh jalur pedestrian Surabaya
- **Live CCTV Preview** -- lihat kondisi jalan real-time dari 444 CCTV Dishub Surabaya
- **Dashboard Pemerintah** -- koridor prioritas penghijauan, statistik walkability (data real dari pipeline)
- **Prediksi & Simulasi Panas AI/ML** -- simulasi interaktif dampak intervensi tata kota (penghijauan & cool pavement) berbasis Spark MLlib

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
| Deployment | Docker Compose (lokal) · Vercel + AWS Lambda + Supabase (online, lihat [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)) |

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

Teduh mengimplementasikan arsitektur **Data Lakehouse** dengan pemisahan layer **Medallion (Bronze, Silver, Gold)** menggunakan **HDFS (Hadoop Distributed File System)** sebagai media penyimpanan Big Data dan **Apache Spark** sebagai engine pemrosesan data terdistribusi.

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

Teduh menggunakan pgRouting (extension PostgreSQL) untuk graph-based routing di atas jaringan jalan yang telah di-node (`segments_noded`):

- **Shortest route**: `pgr_dijkstra` dengan cost = `base_cost` (waktu tempuh standar pejalan kaki tanpa penalti panas).
- **Most comfortable route**: `pgr_dijkstra` dengan cost = `total_cost` (waktu tempuh standar + penalti paparan panas dinamis berdasarkan toleransi pengguna).

### Formula Biaya Navigasi (Cost)
Biaya perjalanan (dalam satuan detik) dihitung secara dinamis di API navigasi:
$$\text{Cost} = \text{base\_cost} \times (1.0 + (1.0 - \text{TCS}) \times \text{multiplier})$$

Di mana:
1. **$\text{base\_cost}$**: Merupakan waktu tempuh standar (dalam detik) di segmen jalan tersebut tanpa memperhitungkan paparan panas.
   $$\text{base\_cost} = \frac{\text{length\_m}}{1.33\text{ m/s}}$$
   *(Mengasumsikan kecepatan rata-rata berjalan pejalan kaki adalah 1.33 m/s atau ~4.8 km/jam).*
2. **$\text{TCS}$**: *Thermal Comfort Score* segmen tersebut (rentang $0.0$ hingga $1.0$).
3. **$\text{multiplier}$**: Tingkat penalti panas berdasarkan profil toleransi panas pengguna (*Personal Heat Budget*):
   * **Rendah (Low)**: $1.75$ — Penalti sangat tinggi pada jalan panas agar pgRouting agresif mencari jalur teduh.
   * **Sedang (Medium)**: $1.25$ — Penalti seimbang.
   * **Tinggi (High)**: $0.8$ — Penalti rendah, lebih menoleransi jalan panas demi rute yang lebih singkat.

### Personal Heat Budget (Batas Paparan Panas)
Setiap tingkat toleransi panas memiliki batas durasi paparan sinar matahari langsung yang direkomendasikan (*budget limit*):
* **Rendah (Low)**: Maksimal **8 menit**
* **Sedang (Medium)**: Maksimal **15 menit**
* **Tinggi (High)**: Maksimal **25 menit**

> [!NOTE]
> **Bagaimana jika tidak ada rute yang memenuhi batas budget?**
> Jika rute terbaik yang tersedia di lapangan melebihi batas waktu paparan di atas, sistem **tetap mencarikan dan mengembalikan rute** navigasi ternyaman yang ada. Namun, API akan menyertakan flag `"within_heat_budget": false` dalam respon JSON. Frontend mendeteksi flag ini untuk menampilkan peringatan visual ke pejalan kaki bahwa rute terpilih melebihi batas nyaman tubuh mereka, tetapi rute tetap digambar di peta.

---

## Prediksi & Simulasi Panas AI/ML

Teduh mengintegrasikan pemodelan prediktif berbasis machine learning untuk membantu perencana kota menganalisis efektivitas langkah mitigasi panas (UHI) secara interaktif.

### Model Machine Learning (PySpark MLlib)
*   **Algoritma:** `DecisionTreeRegressor` (dari library `pyspark.ml.regression`).
*   **Target (Label):** `tcs_value` (Thermal Comfort Score).
*   **Fitur Input (Assembled Features):**
    1.  `avg_ndvi` (Kerapatan vegetasi/indeks hijau)
    2.  `avg_lst` (Suhu permukaan jalan)
    3.  `avg_shade` (Rasio keteduhan rata-rata)
    4.  `congestion_ratio` (Rasio kemacetan lalu lintas)
    5.  `aqi_value` (Kualitas udara AQI)
*   **Tujuan:** Mempelajari hubungan non-linear dari kondisi lingkungan perkotaan terhadap tingkat kenyamanan pejalan kaki.

### Simulasi Skenario Intervensi
Model AI yang telah dilatih digunakan untuk menjalankan simulasi "What-If" pada seluruh segmen jalan Surabaya:
1.  **🌿 Skenario Hijau (Green Scenario):** Mensimulasikan program penanaman pohon kota secara masif dengan menaikkan nilai `avg_ndvi` sebesar `+0.25` (maksimal `0.72`).
2.  **❄️ Skenario Cool Pavement:** Mensimulasikan penggantian aspal dengan material pemantul panas (*cool pavement*), menurunkan suhu permukaan (`avg_lst`) sebesar `-3.5°C`.

Hasil prediksi dari kedua skenario ini dibandingkan dengan kondisi asli (`current_tcs`) untuk menghitung persentase potensi perbaikan kenyamanan jalan (`improvement_pct`).

### Letak Berkas Kode & Implementasi
*   **Spark ML Pipeline:** [job_tcs_predictor.py](spark_jobs/job_tcs_predictor.py) — Melatih model regresi pohon keputusan menggunakan HDFS data lakehouse, menjalankan proyeksi skenario hijau & cool pavement, lalu menyimpannya ke tabel `tcs_simulations` di database PostgreSQL.
*   **Backend API Endpoints:** [dashboard.py](api/routes/dashboard.py) (endpoint `GET /api/dashboard/heat-prediction`) — Menyediakan data statistik agregat kota, tren jam-demi-jam per skenario, dan daftar 50 segmen jalan terpanas (Top 50 Hottest) beserta proyeksi mitigasinya.
*   **Frontend Dashboard UI:**
    *   [page.tsx](frontend/app/page.tsx) — Integrasi menu tab baru `🔥 Prediksi Panas` dan pemanggilan API.
    *   [HeatPredictionTab.tsx](frontend/components/HeatPredictionTab.tsx) — Halaman dashboard interaktif yang dilengkapi:
        *   **Hourly Simulator Slider:** Menggeser jam (06:00 - 21:00 WIB) untuk mensimulasikan kurva temperatur harian Surabaya.
        *   **Scenario Toggles:** Memilih skenario tata kota (Saat Ini, +Pohon, +Cooling) untuk melihat respons perbaikan TCS kota dan jalan terpanas secara real-time.
        *   **Mantine charts & tables:** Visualisasi grafik tren TCS harian kota dan tabel interaktif "Top 20 Zona Terpanas" (menampilkan street name, current TCS, improvements, dan severity status).

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

## Thermal Comfort Score (TCS) & Urban Heat Island (UHI)

### A. Formula Utama TCS
Setiap segmen jalan dihitung tingkat kenyamanan termalnya (skala $0.0$ hingga $1.0$) setiap jam:
$$\text{TCS} = 0.35 \times \text{shade\_score} + 0.30 \times \text{temp\_score} + 0.15 \times \text{aqi\_score} + 0.10 \times \text{traffic\_score} + 0.10 \times \text{surface\_score}$$

Di mana sub-skor didefinisikan sebagai berikut:

1. **Shade Score (Naungan - Bobot 35%):**
   $$\text{shade\_score} = 0.7 \times \text{shade\_ratio} + 0.3 \times \text{ndvi\_proxy}$$
   *   `shade_ratio`: Rasio jalan tertutup bayangan bangunan/pohon (kalkulasi elevasi matahari dinamis berdasarkan koordinat Surabaya).
   *   `ndvi_proxy`: Kerapatan vegetasi berdasarkan jumlah pohon (`natural=tree` di OSM) dalam radius 30m.

2. **Temperature Score (Suhu Terasa & Permukaan - Bobot 30%):**
   $$\text{temp\_score} = 1.0 - \frac{T_{gabungan} - T_{min}}{T_{max} - T_{min}}$$
   *   $T_{gabungan} = 0.6 \times \text{apparent\_temp} + 0.4 \times \text{LST}$
   *   $\text{apparent\_temp}$: Suhu semu yang dirasakan tubuh pejalan kaki (diperoleh dari Open-Meteo).
   *   $\text{LST}$: Land Surface Temperature (suhu aspal = suhu udara + koreksi material trotoar: Asphalt +8°C, Concrete +6°C, Paving +4°C, Grass -2°C).
   *   $T_{min} = 28^\circ\text{C}$ (Threshold dingin nyaman), $T_{max} = 45^\circ\text{C}$ (Threshold panas ekstrem).

3. **AQI Score (Kualitas Udara - Bobot 15%):**
   $$\text{aqi\_score} = 1.0 - \frac{\text{AQI\_value}}{150.0} \quad (\text{dibatasi di rentang } [0.0, 1.0])$$
   *   Jika AQI melampaui 150 (sangat tidak sehat), skor pernapasan otomatis anjlok ke 0.0.

4. **Traffic Score (Kepadatan Lalu Lintas - Bobot 10%):**
   *   Mengevaluasi paparan polusi suara dan gas buang lokal kendaraan berdasarkan kemacetan lalu lintas real-time (`congestion_ratio` dari TomTom API).

5. **Surface Score (Kualitas Trotoar - Bobot 10%):**
   *   Ditentukan dari material paving/concrete (`surface_type`) dan kerataan jalan (`smoothness`).

### B. UHI (Urban Heat Island) Hotspot
Visualisasi peta UHI (*City-Wide Thermal Heatmap*) memetakan daerah kantong panas di perkotaan dengan menampilkan segmen jalan yang memiliki LST (*Land Surface Temperature*) tertinggi dan TCS terendah.

Visualisasi di peta dikelompokkan ke dalam **4 grade warna kategoris**:
- 🟢 **Nyaman** (TCS ≥ 0.7) — hijau gelap, teduh dan sejuk
- 🟡 **Sedang** (TCS 0.5–0.7) — kuning, cukup nyaman
- 🟠 **Panas** (TCS 0.3–0.5) — oranye, terasa panas
- 🔴 **Sangat Panas** (TCS < 0.3) — merah, hindari

Legenda grade TCS ditampilkan di pojok kiri bawah peta navigasi.

---

## Struktur Project

```
teduh/
|-- api/                          FastAPI backend
|   |-- main.py                   App entry + CORS + lifespan
|   |-- lambda_handler.py         AWS Lambda entry point (Mangum)
|   |-- requirements.txt          API deps (Docker + Lambda)
|   |-- Makefile                  AWS SAM build for Lambda
|   |-- db.py                     asyncpg connection pool (env-tunable)
|   |-- routes/
|   |   |-- navigation.py         pgRouting route + TCS segments + debug/admin (token-protected)
|   |   |-- dashboard.py          UHI, corridors, walkability, heat prediction
|   |   +-- cctv.py               CCTV spatial query
|   +-- models/schemas.py         Pydantic models
|-- spark_jobs/                   PySpark + Sedona processing
|   |-- run_pipeline.py           Full pipeline orchestrator (--skip-ingest = Spark jobs only)
|   |-- config.py                 Shared JDBC config
|   |-- job_raster_segment.py     Job 1: NDVI/LST
|   |-- job_shadow_model.py       Job 2: Shadow ratio
|   |-- job_thermal_comfort.py    Job 3: TCS calculation
|   |-- job_traffic_aqi.py        Job 4: Traffic aggregation
|   |-- job_graph_weight.py       Job 5: Edge weights
|   |-- job_tcs_predictor.py      Job 6: AI/ML simulations (MLlib)
|   +-- utils/                    Solar position, shadow geometry, normalization
|-- ingestion/                    Data collection scripts (APIs, OSM, HDFS client, scheduler)
|-- validation/                   Validasi model bayangan & termal
|-- tests/                        Unit & e2e tests (pytest)
|-- frontend/                     Next.js App Router
|   |-- app/                      page.tsx (dashboard), navigasi/page.tsx
|   |-- components/               MapView, SearchPanel, RoutePanel, TCSLegend, CCTVModal, ...
|   |-- services/api.ts           Centralized typed API calls
|   +-- types/index.ts            TypeScript interfaces
|-- database/
|   |-- init.sql                  Schema + pgRouting topology function
|   |-- seed_transit.sql          Data halte/stasiun transit
|   +-- rebuild_topology.sql      Standalone topology rebuild script
|-- scripts/sync_to_supabase.sh   Snapshot tabel serving lokal -> Supabase
|-- notebooks/                    Notebook eksplorasi pipeline Big Data & ML
|-- docs/                         PENCERDASAN.md, DEPLOYMENT.md, Rubrik.csv
|-- docker-compose.yml            Services: postgres, spark-pipeline, api, hadoop
|-- Dockerfile.{api,spark,postgres}
|-- template.yaml, samconfig.toml   AWS SAM (Lambda) deployment
|-- requirements-spark.txt        Spark container deps
|-- requirements.txt              Local dev (semua deps + pytest)
+-- .env.example                  Environment template
```

---

## Deployment (Online, Gratis)

| Layer | Layanan |
|---|---|
| Frontend | Vercel (Hobby) |
| API | AWS Lambda + Function URL (AWS SAM) |
| Database | Supabase Free (PostGIS + pgRouting) |
| Pipeline | Tetap lokal via Docker Compose, lalu snapshot ke Supabase |

Langkah lengkap ada di **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.

---

## Testing

```powershell
# Unit tests
pip install -r requirements.txt
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
