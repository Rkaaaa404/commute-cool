# 🗺️ Panduan Setup Developer (Branch dev) — COMMUTE-COOL

Panduan ini ditujukan untuk developer/anggota tim yang baru saja melakukan `git pull` atau clone pertama kali ke branch `dev`. Ikuti langkah-langkah di bawah ini secara berurutan agar sistem, database, dan fitur routing berjalan dengan sempurna di komputer lokal Anda.

---

## 🛠️ Prasyarat (Prerequisites)

Sebelum memulai, pastikan perangkat Anda sudah terinstall:
1. **Docker Desktop** (versi terbaru)
2. **Node.js** (versi 18 ke atas)
3. **Git**

> 💡 **Catatan Penting:** Anda **tidak perlu** menginstall Python atau Apache Spark secara lokal di sistem Anda. Semua backend API (FastAPI) dan pengolahan data besar (Spark Pipeline) akan dijalankan secara otomatis di dalam container Docker.

---

## 🚀 Langkah-Langkah Setup

### Langkah 1: Stop PostgreSQL Lokal (Jika Ada)
Sistem ini menggunakan PostgreSQL versi 15 di dalam Docker yang berjalan pada port default `5432`. Jika Anda sudah memiliki PostgreSQL lokal yang berjalan pada komputer host Anda:
* Docker tidak akan bisa menggunakan port `5432`, atau
* Backend API akan salah menyambung ke database lokal Anda yang kosong.

**Cara Mematikan PostgreSQL lokal di Windows:**
Buka Command Prompt/PowerShell sebagai Administrator, lalu jalankan:
```powershell
net stop postgresql
```

---

### Langkah 2: Buat File Konfigurasi Environment (`.env`)
Salin berkas template environment variabel [`.env.example`](file:///d:/main-storage/documents/kuliah/sem4/bigdata/fp-dev/.env.example) menjadi `.env`:
```powershell
copy .env.example .env
```
Secara default, nilai database URL di `.env` sudah diatur ke `localhost` (untuk eksekusi lokal) dan di dalam Docker Compose menggunakan service name database.

---

### Langkah 3: Jalankan Backend & Spark Pipeline (Docker)
Jalankan seluruh service backend menggunakan Docker Compose. Proses build pertama kali membutuhkan koneksi internet untuk mengunduh library dan memproses data awal OSM Surabaya.

```powershell
docker compose up --build
```

**⚠️ PERHATIAN SAAT STARTUP PERTAMA KALI (~5-15 Menit):**
1. Docker akan membuat database PostgreSQL dan mengaktifkan extension PostGIS + pgRouting via [`init.sql`](file:///d:/main-storage/documents/kuliah/sem4/bigdata/fp-dev/database/init.sql).
2. Service `spark-pipeline` akan mengunduh data jalan, gedung, dan pepohonan Surabaya langsung dari OpenStreetMap (OSM) via Overpass API.
3. Spark akan memproses perhitungan Thermal Comfort Score (TCS) dan membangun topologi jaringan jalan.
4. **Pantau logs pipeline** hingga selesai dengan perintah:
   ```powershell
   docker compose logs -f spark-pipeline
   ```
5. Tunggu sampai muncul pesan:
   `commute_cool_spark exited with code 0`
   Jika kontainer Spark sudah selesai (`exited`), database Anda sudah terisi penuh oleh data jalan dan siap digunakan untuk routing.

---

### Langkah 4: Jalankan Frontend (React + TypeScript + Vite)
Buka terminal baru, masuk ke direktori `frontend`, pasang dependensi, lalu jalankan development server:

```powershell
cd frontend
npm install
npm run dev
```
Buka browser Anda dan akses **[http://localhost:3000](http://localhost:3000)**.

---

## 🔍 Cara Verifikasi & Diagnosis Routing

Jika Anda mengalami masalah routing (rute bernilai `0.00 km` atau garis rute tidak muncul di peta), lakukan diagnosis dengan langkah berikut:

### 1. Cek Status Topologi Database
Panggil endpoint diagnostik berikut di browser Anda:
👉 **[http://localhost:8000/api/debug/topology-status](http://localhost:8000/api/debug/topology-status)**

Perhatikan nilai JSON yang dikembalikan:
```json
{
  "status": "ok",
  "segments_total": 69373,
  "noded_edges": 69373,
  "noded_vertices": 21429,
  "edges_with_null_topology": 0,
  "sample_center_node_id": 1,
  "topology_ready": true
}
```
* **`topology_ready` harus `true`**. Jika `false`, atau `noded_edges` bernilai `0`, jaringan jalan belum di-node/topologi routing belum dibuat.
* **`edges_with_null_topology` harus `0`**.

### 2. Solusi Jika Topologi Belum Siap / Kosong
Jika data sudah masuk tetapi status topologi menunjukkan `topology_ready: false`, Anda bisa memicu pembangunan ulang topologi secara instan via API menggunakan perintah `curl` atau melalui dokumentasi Swagger (`http://localhost:8000/docs`):

```powershell
curl -X POST http://localhost:8000/api/admin/rebuild-topology
```
Proses ini akan memanggil fungsi [`build_routing_topology()`](file:///d:/main-storage/documents/kuliah/sem4/bigdata/fp-dev/database/init.sql#L207-L244) untuk menghubungkan persimpangan jalan di Surabaya dengan toleransi `0.0005°` (~55 meter).

---

## ❓ Troubleshooting & Pertanyaan Umum

* **T: Kenapa routing menghasilkan rute 0 km?**
  * **J:** Kemungkinan data OSM belum terunduh sepenuhnya oleh `spark-pipeline` saat startup pertama kali, atau database Anda kosong. Pastikan kontainer Spark sudah selesai berjalan dengan sukses. Cek status via `/api/debug/topology-status`.

* **T: Kenapa API backend mengembalikan status HTTP 400 (di luar area Surabaya)?**
  * **J:** Batasan wilayah routing dibatasi ketat di [`navigation.py`](file:///d:/main-storage/documents/kuliah/sem4/bigdata/fp-dev/api/routes/navigation.py#L27-L29). Pastikan marker origin dan destination yang Anda taruh di peta berada di dalam area kota Surabaya (Latitude: `-7.35` s.d `-7.20` dan Longitude: `112.60` s.d `112.85`).

* **T: Bagaimana cara me-reset total database dan mengulangi proses ingestion?**
  * **J:** Anda bisa menghapus seluruh volume Docker untuk membersihkan database lama, lalu jalankan ulang compose:
    ```powershell
    docker compose down -v
    docker compose up --build
    ```

---

*Selamat berkolaborasi di branch dev! Jika ada kendala di luar panduan ini, silakan hubungi tim dev.*
