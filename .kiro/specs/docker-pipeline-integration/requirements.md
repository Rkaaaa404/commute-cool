# Requirements Document

## Introduction

Dokumen ini mendefinisikan kebutuhan sistem untuk fitur **Docker Pipeline Integration** pada platform COMMUTE-COOL. Fitur ini mengkonsolidasikan seluruh stack (database, Spark pipeline, backend API, dan frontend) ke dalam satu orkestrasi Docker Compose yang dapat di-deploy dengan satu perintah (`docker compose up --build`). Selain itu, fitur ini menghilangkan penggunaan data dummy dan menggantinya dengan pipeline data real berbasis Apache Spark yang mengambil data dari API eksternal (Open-Meteo, TomTom, WAQI) serta memproses data geospasial OSM menjadi Thermal Comfort Score (TCS) yang tersimpan di PostgreSQL/PostGIS.

---

## Glossary

- **Docker_Compose**: Alat orkestrasi container yang mendefinisikan dan menjalankan multi-container Docker application via file YAML
- **Spark_Pipeline**: Rangkaian job pemrosesan data berbasis Apache Spark + Sedona yang berjalan secara sekuensial dalam satu container
- **API_Service**: Backend FastAPI yang menyajikan data PostGIS ke frontend melalui endpoint REST
- **Frontend_Service**: Nginx web server yang menyajikan file statis (navigation + dashboard) dan mem-proxy request `/api/` ke API_Service
- **PostgreSQL_Service**: Database PostgreSQL dengan ekstensi PostGIS untuk penyimpanan data geospasial
- **TCS**: Thermal Comfort Score — skor kenyamanan termal per segmen jalan (0.0 = sangat panas, 1.0 = nyaman)
- **Heatmap_Overlay**: Layer visualisasi city-wide di peta navigasi yang menampilkan gradasi warna TCS per segmen jalan
- **Fallback_Mechanism**: Mekanisme alternatif yang menggunakan PostgreSQL langsung apabila Spark job gagal
- **asyncpg**: Driver PostgreSQL asinkron untuk Python yang digunakan API_Service untuk query database

---

## Requirements

### Requirement 1: Docker Compose Single-Command Deployment

**User Story:** Sebagai developer/penguji, saya ingin menjalankan seluruh stack COMMUTE-COOL dengan satu perintah, sehingga saya tidak perlu membuka banyak terminal atau mengkonfigurasi service secara terpisah.

#### Acceptance Criteria

1. WHEN pengguna menjalankan `docker compose up --build`, THE Docker_Compose SHALL membangun dan menjalankan 4 services: PostgreSQL_Service, Spark_Pipeline, API_Service, dan Frontend_Service, dimana keempat service memasuki status running dalam waktu maksimal 120 detik pada koneksi internet yang stabil
2. THE Docker_Compose SHALL mendefinisikan dependency order sehingga PostgreSQL_Service dinyatakan sehat (healthcheck menggunakan `pg_isready` berhasil dengan interval 5 detik, timeout 3 detik, dan maksimal 10 percobaan) sebelum Spark_Pipeline dan API_Service dimulai
3. THE Docker_Compose SHALL mengekspos PostgreSQL_Service pada host port 5432, API_Service pada host port 8000, dan Frontend_Service pada host port 3000
4. WHEN PostgreSQL_Service container pertama kali dibuat, THE PostgreSQL_Service SHALL menjalankan init.sql dan seed_transit.sql secara otomatis (melalui `/docker-entrypoint-initdb.d/`) untuk menginisialisasi schema dan data transit
5. THE Docker_Compose SHALL menggunakan named volumes (`pgdata`, `spark_data`) untuk persistensi data sehingga data tetap tersedia setelah `docker compose down` dan `docker compose up` berikutnya tanpa flag `--volumes`
6. THE Docker_Compose SHALL TIDAK menggunakan MinIO sebagai object storage — seluruh data raw disimpan secara lokal dalam volume container
7. IF PostgreSQL_Service gagal mencapai status healthy setelah 10 kali percobaan healthcheck, THEN THE Docker_Compose SHALL tidak memulai Spark_Pipeline dan API_Service, dan container PostgreSQL_Service menampilkan status unhealthy pada `docker compose ps`
8. THE Docker_Compose SHALL mendefinisikan restart policy `unless-stopped` pada API_Service dan Frontend_Service sehingga kedua service otomatis restart jika terjadi crash tanpa intervensi manual

---

### Requirement 2: Real Data Pipeline — Ingestion

**User Story:** Sebagai sistem, saya ingin mengambil data real dari API eksternal saat pipeline dijalankan, sehingga Thermal Comfort Score dihitung berdasarkan kondisi aktual, bukan data dummy.

#### Acceptance Criteria

1. WHEN Spark_Pipeline dimulai, THE Spark_Pipeline SHALL mengambil data cuaca real-time dari Open-Meteo API untuk koordinat Surabaya (-7.2575, 112.7521), mencakup minimal parameter: temperature_2m, relative_humidity_2m, apparent_temperature, wind_speed_10m, direct_radiation, diffuse_radiation, dan cloud_cover, lalu menyimpan respons JSON ke direktori raw storage dengan format nama file berisi timestamp
2. WHEN Spark_Pipeline dimulai, THE Spark_Pipeline SHALL mengambil data Air Quality Index (AQI) dari WAQI API menggunakan token yang dikonfigurasi via environment variable WAQI_API_TOKEN, memvalidasi bahwa respons memiliki status "ok", dan menyimpan data AQI ke direktori raw storage
3. WHEN Spark_Pipeline dimulai, THE Spark_Pipeline SHALL mengambil data kepadatan lalu lintas dari TomTom Traffic API menggunakan API key yang dikonfigurasi via environment variable TOMTOM_API_KEY untuk 8 titik jalan utama Surabaya (Jl. Basuki Rahmat, Jl. Tunjungan, Jl. Darmo, Jl. Ahmad Yani, Jl. Pemuda, Jl. Urip Sumoharjo, Jl. Raya Darmo Permai, Jl. Kertajaya), mengumpulkan current_speed, free_flow_speed, dan congestion_ratio per titik
4. WHEN Spark_Pipeline dimulai, THE Spark_Pipeline SHALL memuat file GeoJSON lokal (footways.geojson, buildings.geojson, trees.geojson) dari direktori data/raw/osm/ ke tabel PostGIS (segments, buildings, trees) dengan SRID 4326, menggunakan strategi ON CONFLICT DO NOTHING untuk menghindari duplikasi data
5. IF salah satu API eksternal tidak merespons dalam 30 detik atau mengembalikan HTTP error (4xx/5xx), THEN THE Spark_Pipeline SHALL melanjutkan pipeline menggunakan data dari file raw storage terakhir yang tersedia sebagai fallback, dan mencatat log warning yang mengindikasikan API mana yang gagal
6. IF environment variable WAQI_API_TOKEN atau TOMTOM_API_KEY tidak diset atau kosong, THEN THE Spark_Pipeline SHALL melewatkan pengambilan data dari API yang bersangkutan, mencatat log warning, dan melanjutkan pipeline dengan sumber data lain yang tersedia tanpa menghentikan proses

---

### Requirement 3: Real Data Pipeline — Spark Processing Jobs

**User Story:** Sebagai sistem, saya ingin memproses data geospasial menggunakan Apache Spark + Sedona untuk menghasilkan Thermal Comfort Score per segmen jalan, sehingga routing engine dapat memberikan rekomendasi rute ternyaman.

#### Acceptance Criteria

1. WHEN data OSM telah dimuat ke PostGIS, THE Spark_Pipeline SHALL menjalankan Job 1 (NDVI/LST) yang menghitung tree density proxy per segmen menggunakan Sedona spatial join dengan buffer 30m, dan mengestimasi LST berdasarkan suhu udara + faktor koreksi material permukaan (asphalt: +8°C, concrete: +6°C, paving_stones: +4°C, compacted: +3°C, gravel: +2°C, grass: −2°C, default: +4°C)
2. WHEN Job 1 selesai, THE Spark_Pipeline SHALL menjalankan Job 2 (Shadow Modeling) yang menghitung shade_ratio (0.0–1.0) per segmen untuk setiap jam dari pukul 06:00 hingga 17:00 WIB berdasarkan posisi matahari (pvlib) dan geometri bangunan/pohon dalam radius 50m dari segmen
3. WHEN data traffic dan AQI tersedia, THE Spark_Pipeline SHALL menjalankan Job 4 (Traffic & AQI Aggregation) yang meng-geocode data traffic ke segmen terdekat menggunakan Sedona spatial distance query dan menetapkan nilai AQI uniform dari WAQI untuk seluruh segmen
4. WHEN Job 1, Job 2, dan Job 4 selesai, THE Spark_Pipeline SHALL menjalankan Job 3 (Thermal Comfort Score) yang menggabungkan semua layer menggunakan formula: TCS = 0.35×shade + 0.30×temp_normalized + 0.15×aqi_normalized + 0.10×traffic_normalized + 0.10×surface_score, dengan normalisasi temperatur pada rentang 28°C–45°C, AQI pada rentang 0–150, traffic pada rentang 0.0–1.0, dan menghasilkan nilai TCS akhir antara 0.0 (sangat tidak nyaman) hingga 1.0 (sangat nyaman)
5. WHEN Job 3 selesai, THE Spark_Pipeline SHALL menjalankan Job 5 (Graph Weight Export) yang mengkonversi TCS menjadi routing edge weights dengan formula: total_cost = base_cost × (1 + (1 − TCS) × 2), dimana base_cost = panjang_segmen / 1.33 m/s, menghasilkan penalty multiplier antara 1.0× (TCS=1.0) hingga 3.0× (TCS=0.0), dan menyimpan hasilnya ke tabel edge_weights dengan masa berlaku 1 jam
6. THE Spark_Pipeline SHALL menjalankan semua job secara sekuensial dalam mode `local[*]` (single-node, multi-thread)
7. WHEN seluruh pipeline selesai tanpa error, THE Spark_Pipeline container SHALL exit dengan kode 0
8. IF salah satu Spark job gagal, THEN THE Spark_Pipeline SHALL menjalankan mekanisme fallback (komputasi langsung via PostGIS SQL) untuk job yang gagal tersebut dan melanjutkan pipeline ke step berikutnya
9. IF seluruh pipeline gagal sebelum selesai (database tidak tersedia setelah 30 percobaan koneksi dengan interval 2 detik), THEN THE Spark_Pipeline container SHALL exit dengan kode 1

---

### Requirement 4: PostgreSQL Fallback Mechanism

**User Story:** Sebagai sistem, saya ingin memiliki mekanisme fallback apabila Spark job gagal, sehingga data TCS tetap tersedia meskipun ada masalah pada Spark/Sedona.

#### Acceptance Criteria

1. IF Spark job gagal (misalnya Sedona JAR issue, ClassNotFoundException, atau error pada spatial join), THEN THE Spark_Pipeline SHALL menjalankan fallback yang menghitung TCS menggunakan query PostgreSQL langsung (INSERT INTO thermal_comfort_scores ... SELECT ...) berdasarkan data API yang sudah di-fetch pada tahap ingestion dan data tabel segment_raster_scores serta segment_shadows
2. WHEN fallback dijalankan, THE Spark_Pipeline SHALL tetap menghasilkan tabel thermal_comfort_scores dan edge_weights di PostGIS dengan kolom dan tipe data yang identik dengan output Spark normal (segment_id, tcs_value, apparent_temp, shade_ratio, aqi_value, traffic_level, computed_at)
3. IF fallback juga gagal (misalnya PostgreSQL timeout atau data prerequisite tidak ada), THEN THE Spark_Pipeline SHALL exit dengan kode non-zero dan mencatat full stack trace ke stdout untuk debugging via `docker compose logs spark-pipeline`
4. THE Spark_Pipeline SHALL mencatat log yang jelas mengindikasikan apakah TCS dihitung via Spark (primary) atau via PostGIS (fallback), sehingga developer dapat memverifikasi jalur eksekusi mana yang berjalan

---

### Requirement 5: Backend API dengan Real PostGIS Queries

**User Story:** Sebagai frontend application, saya ingin mengakses endpoint API yang mengembalikan data real dari PostGIS, sehingga peta dan dashboard menampilkan informasi aktual bukan placeholder.

#### Acceptance Criteria

1. THE API_Service SHALL menggunakan asyncpg connection pool (minimum 2 koneksi, maksimum 10 koneksi, command timeout 30 detik) untuk semua query database, diinisialisasi saat aplikasi startup dan ditutup saat shutdown menggunakan lifespan pattern
2. WHEN request POST /api/route diterima dengan koordinat origin dan destination, THE API_Service SHALL mencari segments dalam corridor (bounding box antara origin dan destination dengan buffer ±0.003 derajat), melakukan join dengan thermal_comfort_scores dan edge_weights, lalu mengembalikan 2 rute (shortest dan most_comfortable) beserta geometri GeoJSON LineString, dengan maksimum 50 segmen per pencarian
3. WHEN request GET /api/segments/thermal diterima, THE API_Service SHALL mengembalikan seluruh segments beserta nilai TCS terbaru per segmen (computed_at paling akhir), maksimum 2000 segmen, dalam format GeoJSON dengan field segment_id, tcs_value, dan geometry
4. WHEN request GET /api/dashboard/uhi diterima, THE API_Service SHALL mengembalikan segments dengan TCS < 0.5 (maksimum 100 segmen, diurutkan dari TCS terendah) beserta summary statistics berupa avg_city_tcs, critical_segments (jumlah segmen dengan TCS < 0.4), dan total_segments
5. WHEN request GET /api/dashboard/priority-corridors diterima, THE API_Service SHALL mengembalikan maksimum 15 koridor segmen dengan TCS < 0.55 yang memiliki halte transit dalam radius 300 meter (ST_DWithin 0.003 derajat), diurutkan berdasarkan priority_score tertinggi
6. WHEN request GET /api/dashboard/walkability diterima, THE API_Service SHALL mengembalikan persentase halte transit yang memiliki minimal 1 segmen jalur pejalan kaki dengan TCS > 0.5 dalam radius 750 meter (ST_DWithin 0.007 derajat) dari halte tersebut
7. WHEN request GET /api/cctv/nearby diterima dengan parameter lat, lng, radius (default 500 meter, maksimum 2000 meter), dan limit (default 5, maksimum 20), THE API_Service SHALL melakukan spatial query (ST_DWithin) untuk menemukan kamera CCTV aktif dalam radius tersebut dan mengembalikan cctv_id, name, stream_url HLS, koordinat, dan distance_m
8. IF database connection tidak tersedia atau query melebihi timeout 30 detik, THEN THE API_Service SHALL mengembalikan response error dengan HTTP status code 503, beserta pesan yang mengindikasikan jenis kegagalan (koneksi gagal atau query timeout), tanpa mengekspos detail internal server
9. IF request POST /api/route diterima dengan koordinat origin atau destination di luar bounding box Surabaya (lat: -7.35 sampai -7.20, lng: 112.60 sampai 112.85), THEN THE API_Service SHALL mengembalikan response error dengan HTTP status code 400 beserta pesan yang mengindikasikan koordinat berada di luar area layanan

---

### Requirement 6: Frontend Thermal Heatmap Overlay

**User Story:** Sebagai pengguna navigasi, saya ingin melihat city-wide thermal heatmap di peta, sehingga saya dapat menilai kondisi kenyamanan termal seluruh area sebelum memilih rute.

#### Acceptance Criteria

1. WHEN peta navigasi selesai dimuat (map load event), THE Frontend_Service SHALL secara otomatis mengambil data dari GET /api/segments/thermal dan merender heatmap overlay di atas peta dengan maksimum 2000 segmen
2. IF permintaan GET /api/segments/thermal gagal (network error atau HTTP status non-2xx) atau mengembalikan array kosong, THEN THE Frontend_Service SHALL tetap menampilkan peta tanpa heatmap overlay dan mencatat pesan error ke console log tanpa menampilkan error kepada pengguna
3. THE Frontend_Service SHALL merender heatmap menggunakan dual-layer: glow layer (line-blur 3px, line-width 6px pada zoom 12 hingga 14px pada zoom 16) untuk efek visual dan crisp line layer (line-width 2px pada zoom 12 hingga 5px pada zoom 16) untuk presisi segmen
4. THE Frontend_Service SHALL menggunakan gradasi warna kontinu berdasarkan nilai TCS: merah (TCS ≤ 0.3), oranye (TCS 0.3–0.5), kuning (TCS 0.5–0.7), hijau (TCS ≥ 0.7)
5. WHEN pengguna mengklik segmen pada heatmap, THE Frontend_Service SHALL menampilkan popup yang berisi: nilai TCS segmen (2 desimal), indikator warna (merah/kuning/hijau), dan ID segmen
6. THE Frontend_Service SHALL menyediakan toggle checkbox di panel legend yang dalam keadaan default tercentang (checked), untuk menampilkan atau menyembunyikan kedua layer heatmap (glow dan crisp) secara bersamaan
7. THE Frontend_Service SHALL menggunakan zoom-dependent line width dengan interpolasi linear dari zoom level 12 (minimum) hingga zoom level 16 (maksimum) sehingga garis heatmap menyesuaikan ketebalan secara proporsional berdasarkan level zoom peta

---

### Requirement 7: Nginx Reverse Proxy dan Static Serving

**User Story:** Sebagai pengguna, saya ingin mengakses navigasi dan dashboard melalui satu URL (port 3000) dengan API yang ter-proxy secara transparan, sehingga tidak perlu mengetahui port API terpisah.

#### Acceptance Criteria

1. THE Frontend_Service SHALL menyajikan file statis navigasi dari path `/` (root) yang di-map ke direktori `/usr/share/nginx/html/navigation/`, dan file statis dashboard dari path `/dashboard` yang di-map ke direktori `/usr/share/nginx/html/dashboard/`, melalui Nginx pada container port 80 (mapped ke host port 3000)
2. WHEN request masuk dengan path prefix `/api/`, THE Frontend_Service SHALL mem-proxy request tersebut ke API_Service di `http://api:8000/api/` dengan meneruskan header Host, X-Real-IP, dan X-Forwarded-For
3. WHEN request masuk dengan path `/health`, THE Frontend_Service SHALL mem-proxy request tersebut ke `http://api:8000/health` untuk health check
4. THE Frontend_Service SHALL menggunakan directive `try_files $uri $uri/ /index.html` untuk menangani client-side routing pada navigation app
5. IF API_Service tidak tersedia saat proxy, THEN THE Frontend_Service SHALL mengembalikan HTTP 502 Bad Gateway kepada client

---

### Requirement 8: Container Build Optimization

**User Story:** Sebagai developer, saya ingin build Docker image yang efisien dan cepat, sehingga waktu iterasi development tidak terganggu oleh proses build yang lama.

#### Acceptance Criteria

1. THE Docker_Compose SHALL menggunakan .dockerignore yang mengecualikan minimal direktori dan file berikut: .venv, .git, .pytest_cache, __pycache__, *.pyc, .kiro, notebooks, docs, *.md, .gitignore, .dockerignore, docker-compose.yml, nginx.conf, dan frontend
2. THE Dockerfile untuk API_Service SHALL menggunakan image base python:3.11-slim, meng-copy requirements-docker.txt dan menginstall dependencies sebelum meng-copy application code, sehingga perubahan source code tidak men-trigger reinstall dependencies (Docker layer caching)
3. THE Dockerfile untuk Spark_Pipeline SHALL men-download semua Spark dan Sedona JAR dependencies (PostgreSQL JDBC, Sedona Spark shaded, dan datasketches) ke dalam /opt/spark/jars/ pada saat build, dan setiap JAR file harus tersedia di path tersebut setelah build selesai tanpa memerlukan network access saat runtime
4. THE Docker_Compose SHALL memisahkan requirements file: requirements-docker.txt (tanpa PySpark/Sedona) untuk API container dan requirements-spark.txt (dengan PySpark dan Apache Sedona) untuk Spark container
5. WHEN source code berubah tanpa perubahan pada requirements file, THEN THE Docker build SHALL menggunakan cached layer untuk dependency installation sehingga hanya layer COPY application code dan seterusnya yang di-rebuild

---

### Requirement 9: Environment Configuration via Docker

**User Story:** Sebagai developer, saya ingin semua konfigurasi (database URL, API keys) di-inject melalui environment variables di docker-compose.yml, sehingga tidak ada hardcoded credentials di source code.

#### Acceptance Criteria

1. THE Docker_Compose SHALL menyediakan environment variable DATABASE_URL (format: `postgresql://cc_user:cc_dev_pass@postgres:5432/commute_cool`) untuk Spark_Pipeline dan API_Service yang menunjuk ke PostgreSQL_Service menggunakan hostname internal `postgres` (bukan localhost atau IP)
2. THE Docker_Compose SHALL menyediakan environment variable TOMTOM_API_KEY dan WAQI_API_TOKEN pada Spark_Pipeline dan API_Service untuk services yang membutuhkan akses API eksternal
3. THE Spark_Pipeline SHALL membaca konfigurasi JDBC connection dari environment variable DATABASE_URL melalui modul `spark_jobs/config.py` yang di-import oleh semua Spark jobs, tanpa hardcoded connection string di file job individual
4. IF environment variable DATABASE_URL tidak tersedia atau kosong saat startup, THEN THE API_Service SHALL gagal startup dalam 5 detik pertama dengan pesan error ke stdout yang menyebutkan: "Missing required environment variable: DATABASE_URL"
5. THE Docker_Compose SHALL menyediakan environment variable ASYNC_DATABASE_URL (format: `postgresql+asyncpg://...`) khusus untuk API_Service yang digunakan oleh asyncpg connection pool
6. Seluruh source code Python (api/, spark_jobs/, ingestion/) SHALL TIDAK mengandung hardcoded credentials database atau API keys — semua harus dibaca dari environment variable atau file .env

---

### Requirement 10: Penghapusan MinIO dan Data Dummy

**User Story:** Sebagai developer, saya ingin menghilangkan dependency pada MinIO dan seed data dummy, sehingga arsitektur lebih sederhana dan data yang tersaji selalu berasal dari pemrosesan real.

#### Acceptance Criteria

1. THE Docker_Compose SHALL TIDAK mendefinisikan service MinIO dan TIDAK mendefinisikan volume bernama `minio_data` — seluruh penyimpanan data raw menggunakan named volume `spark_data` yang di-mount ke container Spark
2. THE Spark_Pipeline SHALL TIDAK mereferensikan atau memuat file seed_tcs.sql, seed dummy SQL script, atau INSERT statis ke tabel `thermal_comfort_scores` — seluruh data TCS berasal dari hasil pemrosesan Spark jobs yang menulis ke PostgreSQL melalui JDBC
3. WHEN pipeline selesai berjalan (container spark-pipeline exit code 0 dalam waktu maksimal 300 detik), THE PostgreSQL_Service SHALL memiliki data TCS yang diverifikasi dengan: (a) query `SELECT COUNT(*) FROM thermal_comfort_scores` mengembalikan hasil > 0, dan (b) kolom `computed_at` pada record terbaru memiliki timestamp dalam 10 menit terakhir dari waktu pipeline selesai
4. IF Spark_Pipeline gagal (exit code ≠ 0 atau timeout melebihi 300 detik), THEN THE PostgreSQL_Service SHALL mempertahankan data TCS dari eksekusi pipeline sebelumnya (jika ada) tanpa melakukan rollback atau penghapusan tabel `thermal_comfort_scores`
