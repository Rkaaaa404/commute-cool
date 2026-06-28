# Dokumen Kebutuhan Sistem (System Requirements Document) - COMMUTE-COOL

Sistem Navigasi Pejalan Kaki Berbasis Kenyamanan Termal untuk Mendukung Smart City (Studi Kasus: Kota Surabaya)

---

## 1. Pendahuluan
Dokumen ini mendefinisikan kebutuhan sistem untuk **COMMUTE-COOL**, sebuah platform smart city yang membantu pejalan kaki menemukan rute perjalanan (khususnya *first-mile/last-mile transit*) yang aman dan nyaman dari paparan panas ekstrem di bawah kondisi iklim tropis perkotaan, dengan memanfaatkan pemrosesan Big Data geospasial dan lingkungan.

---

## 2. Kebutuhan Data (Data Requirements)

Sistem akan mengintegrasikan berbagai sumber data berikut untuk melakukan pemodelan kenyamanan termal dan navigasi pejalan kaki di Kota Surabaya:

| No | Kategori Data | Sumber Data / API | Tipe / Format | Deskripsi & Kegunaan |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **Tutupan Vegetasi (NDVI Proxy)** | OpenStreetMap tree density (via Overpass API) + opsional Sentinel-2 via Copernicus/GEE | Vektor (spatial query) / Raster (GeoTIFF) | Menilai kerapatan vegetasi/pohon peneduh di sepanjang jalan. Prototype menggunakan proxy tree density dari OSM (korelasi r>0.7 dengan NDVI aktual). Produksi dapat menggunakan citra Sentinel-2. |
| 2 | **Suhu Permukaan (LST Proxy)** | Open-Meteo (suhu udara real-time) + koreksi material permukaan jalan (OSM `surface=*` tags) | JSON + Atribut Vektor | Estimasi suhu permukaan tanah berbasis koreksi material (asphalt +8°C, grass -2°C dari suhu udara). Produksi dapat menggunakan Landsat 8 thermal band. |
| 3 | **Jalur Pedestrian & Objek Peneduh** | OpenStreetMap (OSM) via Overpass API | Vektor (GeoJSON / XML) | Mengambil data trotoar (`highway=footway/pedestrian`), lebar jalan, bangunan (untuk pemodelan bayangan), dan pohon (`natural=tree`). |
| 4 | **Transit Transportasi Publik** | OpenStreetMap & Portal Satu Data Surabaya | Vektor / Tabular | Koordinat stasiun kereta api, halte bus (Suroboyo Bus, Trans Semanggi, WiraWiri), dan halte pengumpan (*feeder*). |
| 5 | **Kualitas Trotoar** | OSM Tags (`sidewalk=*`, `surface=*`, `smoothness=*`) | Atribut Vektor | Menyaring trotoar berdasarkan kelayakan jalan kaki (lebar, kehalusan, tipe permukaan). |
| 6 | **Cuaca & Mikroklimat** | Open-Meteo API & API infoBMKG | JSON / REST | Data suhu udara real-time, kelembapan, kecepatan angin, dan radiasi matahari lokal tingkat kelurahan. |
| 7 | **Peringatan Cuaca Ekstrem** | RSS Feed Nowcast BMKG | XML / RSS | Deteksi dini cuaca buruk instan atau suhu ekstrem untuk memicu pemetaan ulang rute. |
| 8 | **Kepadatan Lalu Lintas** | TomTom Traffic API | JSON / REST | Mengidentifikasi tingkat kemacetan kendaraan di sekitar jalur pedestrian sebagai salah satu variabel kenyamanan. |
| 9 | **Kualitas Udara** | WAQI API (aqicn.org) / OpenAQ | JSON / REST | Indeks Kualitas Udara (AQI) real-time di area Surabaya sebagai faktor pembobot kesehatan rute. |
| 10 | **CCTV Lalu Lintas** | Dishub Surabaya (HLS stream publik) | Video Stream (HLS `.ts`) | Live stream CCTV persimpangan jalan Surabaya untuk preview visual kondisi lalu lintas di sekitar jalur pejalan kaki. Pengguna dapat melihat kondisi real-time sebelum memulai perjalanan. Future: integrasi YOLO vehicle counting untuk otomasi `traffic_level`. |

---

## 3. Kebutuhan Fungsional (Functional Requirements)

### 3.1. Modul Estimasi Vegetasi & Suhu Permukaan (Big Data Pipeline)
*   **F-01:** Sistem harus mampu menghitung **proxy NDVI** per ruas jalan dengan menghitung densitas pohon (`natural=tree`) dalam buffer 30m dari setiap segmen menggunakan spatial join pada Apache Spark + Sedona. Untuk deployment produksi, modul ini dapat diganti dengan pemrosesan citra Sentinel-2/Landsat 8 secara periodik melalui Google Earth Engine (GEE) atau Copernicus Data Space.
*   **F-02:** Sistem harus mampu mengestimasi **Land Surface Temperature (LST)** per ruas jalan menggunakan suhu udara real-time (Open-Meteo) + faktor koreksi material permukaan (asphalt: +8°C, concrete: +6°C, grass: -2°C, dll). Untuk produksi, dapat diperkaya dengan data termal Landsat 8.
*   **F-03:** Sistem harus mengekspor hasil olahan NDVI proxy dan LST estimasi ke database spasial dalam bentuk segmentasi skor per ruas jalan.

### 3.2. Modul Pemodelan Bayangan Dinamis (Dynamic Shadow Modeling)
*   **F-04:** Sistem harus menghitung sudut elevasi dan azimuth matahari berdasarkan koordinat lintang/bujur Surabaya dan waktu spesifik perjalanan (jam dan tanggal).
*   **F-05:** Sistem harus memproyeksikan poligon bayangan yang dihasilkan oleh gedung (`building`) dan pohon (`natural=tree`) dari data OSM ke atas jalur pedestrian secara real-time.

### 3.3. Modul Perhitungan Skor Kenyamanan Termal (Thermal Comfort Engine)
*   **F-06:** Sistem harus menghitung **Thermal Comfort Score** untuk setiap segmen/ruas jalan di Surabaya dengan menggabungkan parameter:
    *   Suhu udara dan kelembapan real-time (Open-Meteo)
    *   Suhu permukaan tanah / LST (estimasi berbasis material + Open-Meteo)
    *   Tingkat keteduhan aktual (Shadow Modeling & NDVI proxy dari tree density)
    *   Kualitas udara (AQI) dan kepadatan lalu lintas (Traffic API)
*   **F-07:** Sistem harus menghitung **Personal Heat Budget** pengguna berdasarkan profil fisik (toleransi panas rendah/sedang/tinggi) untuk membatasi durasi paparan panas maksimum yang diizinkan selama berjalan kaki.

### 3.4. Modul Navigasi & Perutean (Routing Engine)
*   **F-08:** Sistem harus memodifikasi pembobotan (*cost routing*) pada mesin perutean open-source (GraphHopper / Valhalla) menggunakan *Thermal Comfort Score* sebagai penalti waktu/jarak.
*   **F-09:** Sistem harus menghasilkan output berupa:
    1.  **Rute Terpendek:** Rute tercepat menuju tujuan (berdasarkan jarak/waktu murni).
    2.  **Rute Ternyaman:** Rute yang dioptimalkan untuk meminimalkan paparan panas langsung (melalui area teduh).
*   **F-10:** Sistem harus mengestimasikan total akumulasi paparan panas (dalam Joule atau durasi menit di bawah terik matahari langsung) yang akan diterima pejalan kaki di sepanjang rute.
*   **F-11:** Sistem harus memproses RSS Feed BMKG dan secara otomatis memblokir atau merutekan ulang (*rerouting*) perjalanan jika terdeteksi peringatan dini cuaca ekstrem di wilayah yang akan dilewati.

### 3.5. Modul Live CCTV Preview
*   **F-15:** Sistem harus menyediakan fitur preview live CCTV dari Dishub Surabaya yang menampilkan kondisi lalu lintas real-time di persimpangan terdekat dari jalur yang akan dilewati pengguna. Pengguna dapat melihat stream HLS sebelum memulai perjalanan untuk menilai secara visual tingkat kepadatan dan keamanan jalur.
*   **F-16 (Future Work):** Sistem akan mengintegrasikan model deteksi kendaraan (YOLO) pada frame CCTV untuk menghitung jumlah kendaraan secara otomatis dan menggunakan data tersebut sebagai pengganti/pelengkap TomTom Traffic API dalam perhitungan `traffic_level` per segmen.

### 3.6. Dashboard Smart City untuk Pemerintah Kota
*   **F-12:** Dashboard harus menampilkan peta sebaran hotspot *Urban Heat Island* (UHI) di Surabaya berdasarkan hasil analisis LST.
*   **F-13:** Dashboard harus merekomendasikan koridor prioritas penghijauan atau pemasangan kanopi buatan dengan menganalisis ruas trotoar yang memiliki *Thermal Comfort Score* terendah tetapi memiliki lalu lintas pejalan kaki tinggi (akses *first/last-mile* ke halte/stasiun).
*   **F-14:** Dashboard harus menyajikan analisis statistik walkability dan aksesibilitas pejalan kaki menuju transportasi publik utama di Surabaya.

---

## 4. Kebutuhan Non-Fungsional (Non-Functional Requirements)

*   **NF-01 (Kinerja/Performance):** Proses kalkulasi rute ternyaman harus selesai dalam waktu kurang dari 3 detik setelah pengguna memasukkan titik asal dan tujuan.
*   **NF-02 (Skalabilitas/Scalability):** Arsitektur penyimpanan data spasial (PostgreSQL dengan ekstensi PostGIS) harus mampu menangani jutaan baris data geometri jalan, bangunan, dan pohon di Surabaya tanpa degradasi performa kueri yang signifikan.
*   **NF-03 (Ketersediaan/Reliability):** Sistem harus memiliki mekanisme *fallback handling* apabila salah satu API eksternal (seperti Open-Meteo atau TomTom) tidak merespons, dengan menggunakan data cuaca historis atau estimasi statis.
*   **NF-04 (Antarmuka Pengguna/Usability):** Antarmuka navigasi pejalan kaki harus dioptimalkan untuk perangkat seluler (*mobile-responsive*), menyajikan visualisasi rute dengan gradasi warna kenyamanan termal yang jelas (misal: hijau untuk teduh, merah untuk sangat panas).

---

## 5. Rencana Validasi (Validation Plan)

### 5.1. Validasi Model Bayangan (Shadow Model Validation)
*   **Metode:** Bandingkan bentuk dan panjang poligon bayangan yang dihitung secara matematis oleh sistem dengan bayangan nyata pada citra satelit resolusi tinggi Google Maps/Google Earth pada jam tertentu di 5 jalan sampel Kota Surabaya.
*   **Target Akurasi:** Kemiripan spasial (Intersection over Union / IoU) bayangan model dengan bayangan nyata minimal **80%**.

### 5.2. Validasi Kenyamanan Termal (Thermal Comfort Validation)
*   **Metode:** Lakukan pengukuran langsung (*in-situ*) menggunakan alat termometer/higrometer portabel di 10 titik sampel trotoar Surabaya (mewakili daerah teduh pohon, bawah kanopi gedung, dan trotoar terbuka) pada pukul 10.00, 12.00, dan 14.00 WIB. Bandingkan hasil pengukuran dengan nilai *apparent temperature* dan *Thermal Comfort Score* yang dikalkulasi oleh sistem.
*   **Target Akurasi:** Selisih suhu (*mean absolute error*) antara perhitungan model dan pengukuran fisik di lapangan maksimal **±1.5°C**.

---

## 6. Arsitektur Pipeline Big Data (Big Data Processing Architecture)

Sistem COMMUTE-COOL mengadopsi arsitektur pemrosesan data berskala besar menggunakan **Apache Spark** sebagai framework utama untuk batch processing dan near-real-time analytics, sejalan dengan paradigma Big Data yang mencakup Volume, Variety, dan Velocity.

### 6.1. Diagram Alur Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION LAYER                             │
├─────────────┬──────────────┬──────────────┬─────────────┬──────────────┤
│ OSM Tree    │ Overpass API │ Open-Meteo / │ TomTom/HERE │ WAQI/OpenAQ  │
│ Density     │ (Buildings,  │ infoBMKG     │ Traffic API │ Air Quality  │
│ (NDVI Proxy)│  Footways)   │              │             │              │
└──────┬──────┴──────┬───────┴──────┬───────┴──────┬──────┴──────┬───────┘
       │             │              │              │             │
       ▼             ▼              ▼              ▼             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     DATA LAKE / RAW STORAGE                             │
│               (MinIO / Local JSON + GeoJSON Storage)                    │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  APACHE SPARK PROCESSING LAYER                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────┐  ┌───────────────────┐  ┌────────────────────┐  │
│  │ Spark Job 1:      │  │ Spark Job 2:      │  │ Spark Job 3:       │  │
│  │ NDVI/LST Proxy    │  │ Shadow Modeling   │  │ Thermal Comfort    │  │
│  │ (Tree density +   │  │ (Building/Tree    │  │ Score Calculation  │  │
│  │  Surface material)│  │  shadow project.) │  │ (Join semua layer) │  │
│  └───────────────────┘  └───────────────────┘  └────────────────────┘  │
│                                                                         │
│  ┌───────────────────┐  ┌───────────────────┐                          │
│  │ Spark Job 4:      │  │ Spark Job 5:      │                          │
│  │ Traffic + AQI     │  │ Graph Weight      │                          │
│  │ Aggregation       │  │ Export            │                          │
│  │ per segment       │  │ (→ Routing Engine)│                          │
│  └───────────────────┘  └───────────────────┘                          │
│                                                                         │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      SERVING / OUTPUT LAYER                              │
├──────────────────────┬──────────────────────┬───────────────────────────┤
│  PostgreSQL/PostGIS  │  GraphHopper/Valhalla│  Frontend (MapLibre GL    │
│  (Spatial DB untuk   │  (Routing Engine     │   JS 3D + FastAPI)        │
│   query & dashboard) │   dengan bobot TCS)  │                           │
└──────────────────────┴──────────────────────┴───────────────────────────┘
```

### 6.2. Detail Spark Jobs

| Job | Input | Proses (Spark) | Output |
|:---|:---|:---|:---|
| **Job 1: NDVI/LST Proxy** | Tree nodes (OSM) + segment geometri + surface tags (PostGIS) + suhu udara (Open-Meteo) | Spark + Sedona spatial join — hitung tree density per buffer 30m segmen → proxy NDVI; koreksi material permukaan → proxy LST | Tabel `segment_raster_scores` (segment_id, avg_ndvi, avg_lst) → PostGIS |
| **Job 2: Shadow Modeling** | Bangunan + pohon + segmen (PostGIS) + posisi matahari (pvlib) | Proyeksi bayangan poligon menggunakan Spark DataFrame + UDF geometri (Sedona/Shapely), hitung shade_ratio per jam | Tabel `segment_shadows` (segment_id, shade_ratio, hour_of_day) → PostGIS |
| **Job 3: Thermal Comfort Score** | Output Job 1 + Job 2 + data cuaca (JSON) + AQI + Traffic | Spark SQL join semua layer per `segment_id`, formula komposit TCS = f(LST, NDVI, shade%, suhu_udara, AQI, traffic_density) | Tabel `thermal_comfort_scores` (segment_id, tcs_value, timestamp) → PostGIS |
| **Job 4: Traffic & AQI Aggregation** | JSON responses dari TomTom + WAQI | Spark micro-batch — parsing JSON, geocoding ke segment terdekat, agregasi rata-rata per interval 15 menit | Tabel `segment_traffic_aqi` (segment_id, congestion_level, aqi_value, timestamp) |
| **Job 5: Graph Weight Export** | `thermal_comfort_scores` final | Transformasi TCS menjadi routing cost/penalty weight, ekspor sebagai JSON yang compatible dengan GraphHopper custom model | File `edge_weights.json` → di-load oleh Routing Engine |

### 6.3. Justifikasi Penggunaan Apache Spark

| Aspek Big Data | Tantangan di COMMUTE-COOL | Solusi Spark |
|:---|:---|:---|
| **Volume** | Citra satelit Surabaya (ratusan MB per scene), jutaan node/way OSM, ribuan ruas jalan × 24 jam × variabel cuaca | Spark mendistribusikan pemrosesan raster & vektor secara paralel di cluster |
| **Variety** | Multi-format: GeoTIFF (raster), GeoJSON (vektor), JSON (API), XML (RSS), Tabular (CSV) | Spark mendukung reader untuk semua format; Apache Sedona menambahkan kemampuan geospasial native |
| **Velocity** | Skor kenyamanan perlu di-refresh setiap 15–60 menit mengikuti perubahan cuaca & traffic | Spark Structured Streaming / micro-batch memungkinkan near-real-time update tanpa full recompute |
| **Processing Complexity** | Zonal statistics, spatial join, shadow projection — operasi komputasi berat pada data geospasial | Spark + Sedona menyediakan distributed spatial indexing (R-Tree) dan operasi geometri paralel |

### 6.4. Technology Stack Ringkasan

| Layer | Teknologi |
|:---|:---|
| Ingestion | Python scripts (requests, overpy, feedparser) — tanpa GEE dependency |
| Storage | MinIO (data lake raw), PostgreSQL + PostGIS (serving DB) |
| Processing | Apache Spark (PySpark) + Apache Sedona (GeoSpark) |
| Routing | GraphHopper (Java) dengan Custom Weighting Model |
| Visualization | **MapLibre GL JS** (3D buildings, free, no token) + OpenFreeMap tiles |
| Backend API | FastAPI (Python, async) |
| Dashboard | Custom web dashboard (React + Chart.js + MapLibre) |

---

## 7. Analisis Perbandingan dengan Solusi Navigasi Eksisting (Comparative Analysis)

Bagian ini menjawab pertanyaan: **"Mengapa COMMUTE-COOL memberikan manfaat lebih signifikan dibanding fitur navigasi pejalan kaki yang sudah tersedia saat ini?"**

### 7.1. Matriks Perbandingan Fitur

| Fitur / Kapabilitas | Google Maps | Apple Maps | Waze | Cool Walks (Basel) | **COMMUTE-COOL** |
|:---|:---:|:---:|:---:|:---:|:---:|
| Rute pejalan kaki terpendek | ✅ | ✅ | ❌ | ✅ | ✅ |
| Mempertimbangkan bayangan bangunan/pohon | ❌ | ❌ | ❌ | ✅ | ✅ |
| Thermal Comfort Score per segmen jalan | ❌ | ❌ | ❌ | Parsial | ✅ |
| Integrasi data satelit (NDVI, LST) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Personal Heat Budget (profil individu) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Commute-First Routing (first/last-mile) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Estimasi akumulasi paparan panas per rute | ❌ | ❌ | ❌ | ❌ | ✅ |
| Rerouting otomatis saat peringatan cuaca | ❌ | ❌ | ❌ | ❌ | ✅ |
| Dashboard UHI untuk pemerintah | ❌ | ❌ | ❌ | ❌ | ✅ |
| Integrasi kualitas trotoar | ❌ | ❌ | ❌ | ❌ | ✅ |
| Integrasi polusi udara (AQI) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Konteks iklim tropis (Indonesia) | ❌ | ❌ | ❌ | ❌ | ✅ |

### 7.2. Kelemahan Fundamental Solusi Eksisting

1. **Google Maps / Apple Maps / Waze:**
   - Algoritma routing pedestrian hanya meminimalkan jarak atau waktu tempuh.
   - Tidak memiliki lapisan data kenyamanan termal, bayangan, maupun kondisi mikroklimat.
   - Tidak membedakan rekomendasi berdasarkan profil kesehatan/toleransi panas pengguna.
   - Tidak memiliki mekanisme peringatan atau rerouting berbasis cuaca ekstrem untuk pejalan kaki.

2. **Cool Walks (proyek riset, Basel, Swiss):**
   - Hanya memodelkan bayangan bangunan, **tanpa memperhitungkan pohon** (yang sangat dominan di kota tropis).
   - Tidak mengintegrasikan data satelit (NDVI/LST) untuk validasi keteduhan aktual.
   - Tidak memiliki konsep *Personal Heat Budget* — semua pengguna mendapat rekomendasi identik.
   - Dirancang untuk konteks iklim benua Eropa (4 musim), **tidak dioptimasi untuk iklim tropis** dimana tekanan panas jauh lebih konstan dan intens sepanjang tahun.
   - Tidak memiliki fitur *commute-first* yang mengutamakan konektivitas ke transit publik.

### 7.3. Nilai Tambah Spesifik COMMUTE-COOL

| Diferensiator | Penjelasan |
|:---|:---|
| **Multi-layer thermal assessment** | Menggabungkan 5+ sumber data (LST, NDVI, shadow model, cuaca real-time, AQI) vs solusi lain yang hanya gunakan 1–2 parameter |
| **Personalisasi berbasis profil** | Personal Heat Budget membuat sistem adaptif terhadap lansia, anak-anak, pekerja lapangan, dll — bukan one-size-fits-all |
| **Transit-aware routing** | Secara eksplisit mengoptimasi rute menuju halte/stasiun, mendukung peningkatan penggunaan transportasi publik |
| **Actionable government insights** | Dashboard UHI + rekomendasi koridor penghijauan menjadikan sistem ini bukan hanya consumer app, tapi alat kebijakan publik |
| **Tropics-first design** | Dirancang dan divalidasi untuk kondisi kota tropis Indonesia (panas sepanjang tahun, kelembapan tinggi, vegetasi tropis) |
