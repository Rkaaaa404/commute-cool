# Laporan Handover Sesi — COMMUTE-COOL (`fp-dev`)

Dokumen ini merangkum status pengerjaan, perubahan kode yang telah diimplementasikan, status sistem saat ini, serta langkah-langkah selanjutnya untuk menyelesaikan dan memverifikasi perbaikan pada platform COMMUTE-COOL.

---

## 1. Status Pekerjaan Saat Ini

Berikut adalah status checklist dari perbaikan bug dan peningkatan fitur yang diminta:

| Fitur / Perbaikan | Status | Catatan / Lokasi Berkas |
| :--- | :---: | :--- |
| **Fix 1: MapView Heatmap Crash** | ✅ Selesai | Mengubah `heatmap-value` menjadi `heatmap-density` di [MapView.tsx](file:///d:/main-storage/documents/kuliah/sem4/bigdata/fp-dev/frontend/components/MapView.tsx#L389). |
| **Fix 2: Viewport-based Loading (Bbox)** | ✅ Selesai | Mengintegrasikan kueri viewport menggunakan bounding box (`map.on('moveend')`) di [MapView.tsx](file:///d:/main-storage/documents/kuliah/sem4/bigdata/fp-dev/frontend/components/MapView.tsx) agar frontend hanya merender segmen yang terlihat. |
| **Fix 3: Routing Dinamis (Heat Tolerance)** | ✅ Selesai | Menambahkan multiplier penalti toleransi panas (Low: 1.75x, Medium: 1.25x, High: 0.8x) ke dalam formula biaya pgRouting di [navigation.py](file:///d:/main-storage/documents/kuliah/sem4/bigdata/fp-dev/api/routes/navigation.py). |
| **Fix 4: Pembersihan Duplikasi Ingestion** | ✅ Selesai | Menambahkan fungsi *safe delete* pada data lama sebelum memuat data OSM baru di [osm_loader.py](file:///d:/main-storage/documents/kuliah/sem4/bigdata/fp-dev/ingestion/osm_loader.py). |
| **Fix 5: Filter Kategori Jalan OSM (Aman)** | ✅ Selesai | Mengubah filter Overpass di [osm_fetcher.py](file:///d:/main-storage/documents/kuliah/sem4/bigdata/fp-dev/ingestion/osm_fetcher.py) agar menyertakan semua jalan ramah pejalan kaki, mengecualikan tol/jalan cepat (`motorway`, `trunk`), dan memasukkan jalan arteri (`primary`) hanya jika memiliki tag `sidewalk`. |
| **Fix 6: Rebuild Topologi (pgRouting)** | 🔄 Berjalan | Sedang melakukan proses pemecahan segmen yang saling berpotongan menggunakan `pgr_nodeNetwork` di container database (`commute_cool_db`). |
| **Fix 7: Pengujian E2E & Uji Manual** | ❌ Belum | Harus dijalankan setelah proses rekonstruksi topologi (Fix 6) selesai sepenuhnya. |

---

## 2. Detail Masalah & Solusi yang Diimplementasikan

### A. Heatmap Crash
* **Masalah:** MapLibre GL mengalami crash dengan pesan error `Unknown expression "heatmap-value"` saat mencoba menggambar lapisan heatmap.
* **Solusi:** Memperbaiki ekspresi visualisasi dari `heatmap-value` menjadi ekspresi bawaan MapLibre yang benar, yaitu `heatmap-density`.

### B. Masalah Routing 0.00 km (Disconnected Graph)
* **Masalah:** Semua rute navigasi menghasilkan jarak 0.00 km dan durasi 0 menit. Hal ini disebabkan karena fungsi routing langsung diaplikasikan pada tabel mentah `segments` tanpa dipecah di titik perpotongan (tidak ada node interkoneksi), sehingga pgRouting menganggap titik asal dan tujuan berada di pulau graf yang terisolasi.
* **Solusi:**
  1. Mengubah mekanisme pembentukan topologi di [init.sql](file:///d:/main-storage/documents/kuliah/sem4/bigdata/fp-dev/database/init.sql) agar menggunakan `pgr_nodeNetwork('segments', ...)` untuk membuat tabel noded `segments_noded`.
  2. Membangun topologi di atas `segments_noded` dengan `pgr_createTopology('segments_noded', ...)`.
  3. Memperbarui referensi vertex di pipeline Spark ([run_pipeline.py](file:///d:/main-storage/documents/kuliah/sem4/bigdata/fp-dev/spark_jobs/run_pipeline.py)) ke tabel `segments_noded_vertices_pgr`.

### C. Kategori Jalan Pejalan Kaki & Penalti Panas
* **Masalah:** Sebelumnya indikator TCS hanya muncul di jalur khusus pejalan kaki (sehingga cakupan sangat sempit), atau menyertakan jalan tol yang tidak aman. Selain itu, tingkat toleransi panas pengguna belum mempengaruhi penentuan rute.
* **Solusi:**
  * Membagi jalan menjadi 2 kategori di `osm_fetcher.py`:
    * **Kategori A (Selalu Masuk):** `footway`, `pedestrian`, `path`, `steps`, `living_street`, `residential`, `tertiary`, `secondary`, `unclassified`, `service`.
    * **Kategori B (Bersyarat):** `primary` hanya jika memiliki atribut `sidewalk` (`both`, `left`, `right`, `yes`).
    * **Pengecualian Mutlak:** Jalan `trunk` dan `motorway` dibuang demi keamanan pejalan kaki.
  * Menghitung cost sql dinamis untuk rute ternyaman (`most_comfortable`) di API navigasi:
    $$\text{Cost} = \frac{\text{length\_m}}{1.33} \times (1.0 + (1.0 - \text{TCS}) \times \text{multiplier})$$
    * Di mana multiplier adalah: **1.75** (Toleransi Low), **1.25** (Toleransi Medium), dan **0.8** (Toleransi High).

---

## 3. Status Terkini Docker & Database

* **Docker Containers:**
  * `commute_cool_db` (Postgres/PostGIS): **Running & Healthy**
  * `commute_cool_api` (FastAPI): **Running**
  * `commute_cool_namenode` & `commute_cool_datanode` (HDFS): **Running**
  * `commute_cool_spark`: **Exited** (selesai mengeksekusi pipeline)
* **Status Query Rebuild Topologi:**
  * Saat ini fungsi `build_routing_topology()` sedang memproses tabel `segments` yang berukuran **115.160 segmen** (jumlah bertambah karena perluasan cakupan tipe jalan).
  * Proses `pgr_nodeNetwork` melakukan pengecekan spasial yang intensif sehingga memerlukan waktu sekitar 5–15 menit di Docker Windows.

---

## 4. Langkah Selanjutnya (Petunjuk Verifikasi)

Jika Anda melanjutkan sesi ini, ikuti langkah-langkah berikut secara berurutan:

### Langkah 1: Pastikan Proses Rebuild Topologi Selesai
Periksa apakah tabel `segments_noded` sudah terbentuk dan terisi dengan menjalankan perintah berikut di terminal:
```powershell
docker exec commute_cool_db psql -U cc_user -d commute_cool -c "SELECT COUNT(*) FROM segments_noded; SELECT COUNT(*) FROM segments_noded_vertices_pgr;"
```
* **Kondisi Sukses:** Kueri di atas mengembalikan jumlah baris yang valid (tidak error "relation does not exist").
* *Catatan:* Jika kueri mengembalikan error, periksa status kueri yang sedang aktif dengan:
  ```powershell
  docker exec commute_cool_db psql -U cc_user -d commute_cool -c "SELECT pid, state, query, age(clock_timestamp(), query_start) FROM pg_stat_activity WHERE state != 'idle';"
  ```

### Langkah 2: Jalankan Pengujian Otomatis (E2E)
Setelah topologi selesai dibangun di database, jalankan pengujian backend menggunakan pytest:
```powershell
.venv\Scripts\pytest tests/test_e2e.py -v
```
* **Kondisi Sukses:** Test case `test_route_endpoint_validation` lulus dan mengembalikan rute dengan `distance_m > 0`.

### Langkah 3: Verifikasi Manual di Browser
1. Buka frontend di browser: `http://localhost:3001` (atau port 3000 jika sudah kosong).
2. **Peta Suhu (Heatmap):** Masuk ke halaman peta suhu, aktifkan toggle heatmap, dan pastikan tidak ada pesan error merah atau crash di Developer Console (F12).
3. **Viewport Loading:** Lakukan zoom-in/zoom-out atau geser peta, periksa tab *Network* di F12, pastikan request ke `/api/segments/tcs?bbox=...` terpanggil secara dinamis dengan koordinat bbox yang sesuai.
4. **Navigasi / Routing:**
   * Tentukan titik asal dan tujuan di Surabaya yang terhubung jalan raya.
   * Pastikan jarak rute ternyaman dan rute terpendek tidak bernilai 0.
   * Coba ubah opsi toleransi panas pengguna (*Rendah*, *Sedang*, *Tinggi*).
   * Verifikasi bahwa jalur rute ternyaman berubah secara dinamis menyesuaikan tingkat toleransi (toleransi rendah akan memilih jalur yang lebih teduh meskipun memutar).

### Langkah 4: Pembersihan File Sementara
Setelah verifikasi berhasil, hapus berkas kueri sementara di database:
```powershell
Remove-Item database\rebuild_topology.sql
```

---

## 5. Ringkasan Perubahan Berkas

Berikut adalah ringkasan perubahan berkas penting dalam repositori ini:
* **Frontend:**
  * [MapView.tsx](file:///d:/main-storage/documents/kuliah/sem4/bigdata/fp-dev/frontend/components/MapView.tsx) - Perbaikan visualisasi heatmap & reload segmen berbasis viewport bounds.
  * [api.ts](file:///d:/main-storage/documents/kuliah/sem4/bigdata/fp-dev/frontend/services/api.ts) - Penambahan parameter bounding box pada pemanggilan endpoint segmen.
* **Backend:**
  * [navigation.py](file:///d:/main-storage/documents/kuliah/sem4/bigdata/fp-dev/api/routes/navigation.py) - Logika penalti toleransi panas & endpoint `/api/segments/tcs` terintegrasi PostGIS.
  * [init.sql](file:///d:/main-storage/documents/kuliah/sem4/bigdata/fp-dev/database/init.sql) - Migrasi ke model jaringan topologi `pgr_nodeNetwork`.
  * [osm_fetcher.py](file:///d:/main-storage/documents/kuliah/sem4/bigdata/fp-dev/ingestion/osm_fetcher.py) - Overpass query filter jalan aman pejalan kaki.
  * [osm_loader.py](file:///d:/main-storage/documents/kuliah/sem4/bigdata/fp-dev/ingestion/osm_loader.py) - Pencegahan data ganda dengan safe delete.
