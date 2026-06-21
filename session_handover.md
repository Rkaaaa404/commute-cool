# Laporan Handover Sesi — COMMUTE-COOL (`fp-dev`)

Dokumen ini merangkum seluruh perbaikan bug (fixes), pembaruan sistem (updates), proses trial & error yang dilakukan hingga masalah teratasi, serta pembelajaran penting (lessons learned) pada platform COMMUTE-COOL.

---

## Sesi Sebelumnya (21 Juni 2026 pagi)

### 🛠️ MapView Heatmap Crash
* **Masalah:** Peta visualisasi suhu di frontend mengalami crash total dengan error `Unknown expression "heatmap-value"` dari MapLibre GL.
* **Solusi:** Memperbaiki properti visualisasi di MapView.tsx dengan mengganti `heatmap-value` menggunakan ekspresi bawaan MapLibre yang benar, yaitu `heatmap-density`.

### 🛠️ Bbox Viewport-based Loading
* **Masalah:** Memuat seluruh segmen kota Surabaya ke browser pejalan kaki menyebabkan beban memori dan lag parah.
* **Solusi:** Mengimplementasikan kueri berbasis viewport bounding box menggunakan PostGIS `ST_MakeEnvelope` di API, serta mengintegrasikan event listener `map.on('moveend')` pada MapView.tsx agar hanya memuat segmen yang aktif terlihat di layar.

### 🛠️ Routing Dinamis 0.00 km — Percobaan Pertama
* **Masalah:** Navigasi selalu mengembalikan rute dengan jarak `0.00 km`.
* **Solusi saat itu:** Membangun topologi graph menggunakan pgRouting dengan `pgr_createTopology`. Kami membuat tabel `segments_noded` dan menyalin kolom metrik penting, lalu memanggil `pgr_createTopology` dengan tolerance `0.0001°`.
* **Catatan:** Solusi ini **belum sepenuhnya berhasil** — routing masih 0 km karena tolerance terlalu kecil.

### 🛠️ API Routing Query Hang & Timeout
* **Masalah:** Permintaan rute `/api/route` mengalami `ReadTimeout` (gagal merespons dalam 20 detik).
* **Solusi:** Mengoptimalkan kueri navigasi dengan mengganti kalkulasi on-the-fly `ST_Length` ke kolom pre-populated `sn.length_m`, memindahkan pemeriksaan weather alert ke tingkat Python, serta mengeliminasi join tabel redundan.

---

## Sesi Ini (21 Juni 2026 malam)

### 🛠️ Routing 0 km — Root Cause & Fix Definitif

**Diagnosis mendalam:**
1. Menjalankan query `pgr_connectedComponents` pada `segments_noded` — hasilnya: **graph sangat terfragmentasi** (komponen terbesar hanya 1.819 dari 69.373 nodes). Node sumber dan tujuan berada di komponen berbeda → tidak ada path → 0 km.
2. Penyebab: `pgr_createTopology` dengan tolerance `0.0001°` (±11 meter) terlalu kecil untuk menggabungkan endpoint segmen jalan OSM yang hampir bertemu namun tidak persis sama.
3. `pgr_analyzeGraph` mengkonfirmasi ada **174.952 intersections yang tidak ter-split** di data.

**Solusi akhir:**
- Rebuild topology dengan `pgr_createTopology(..., 0.0005, ...)` (±55 meter tolerance).
- Hasilnya: komponen terbesar meningkat dari 1.819 ke **21.429 nodes**.
- Test Dijkstra berhasil: 2 node di pusat Surabaya menghasilkan **rute 4.578 km, 29 edges**.
- Update `rebuild_topology.sql` dan `init.sql` dengan tolerance baru dan flag `clean:=true`.

**Endpoint baru:**
- `GET /api/debug/topology-status` — cek status tabel dan topology
- `POST /api/admin/rebuild-topology` — trigger rebuild dari API tanpa masuk Docker

### 🛠️ TCS Map Categorical Colors

**Perubahan:**
- Ubah MapLibre color expression dari `interpolate` (gradasi halus) ke `step` (4 grade kategoris):
  - `< 0.3` → 🔴 Merah (#e63946) — "Sangat Panas"
  - `0.3–0.5` → 🟠 Oranye (#f4a261) — "Panas"
  - `0.5–0.7` → 🟡 Kuning (#e9c46a) — "Sedang"
  - `≥ 0.7` → 🟢 Hijau (#1a936f) — "Nyaman"
- Tambahkan legenda TCS di pojok kiri bawah peta (komponen `TCSLegend.tsx`).
- Komponen `TCSLegend.tsx` juga mengekspor helper fungsi `tcsToColor`, `tcsToLabel`, `tcsToBadgeColor` yang dipakai oleh `RoutePanel.tsx` dan `app/page.tsx`.

### 🛠️ Frontend Refactor

**File baru:**
- `frontend/components/TCSLegend.tsx` — legenda + shared TCS color constants
- `frontend/components/MapLayerSwitcher.tsx` — extracted layer switcher control

**File dimodifikasi:**
- `frontend/components/MapView.tsx` — pisahkan `loadTCSLayer()` dan `loadTempHeatmapLayer()`, ekstrak marker helpers ke fungsi terpisah, gunakan step color expression
- `frontend/components/RoutePanel.tsx` — hapus local `tcsColor`/`tcsBadgeColor`, import dari `TCSLegend`
- `frontend/services/api.ts` — sentralisasi `API_BASE` via env var, tambah typed dashboard functions
- `frontend/app/page.tsx` — hapus hardcoded `API_BASE`, gunakan fungsi dari `api.ts`
- `frontend/app/navigasi/page.tsx` — gunakan komponen baru, ekstrak style ke konstanta

### 🛠️ Directory Cleanup

**Dihapus:**
- `frontend_vite_backup/` — backup Vite lama, tidak relevan lagi
- `diagnosis-bug.md` — sudah outdated
- `test_api_logic.py` (root) — duplikat dari `tests/`
- `test_asyncpg.py` (root) — duplikat dari `tests/`
- `database/rebuild_topology_v2.sql` — experimental, diganti dengan `rebuild_topology.sql` yang diupdate

**Ditambahkan ke `.gitignore`:**
- `frontend/.next/`, `frontend/out/`, `frontend/.vercel/`
- `frontend_vite_backup/`

---

## Status Saat ini

| Komponen | Status |
|---|---|
| Routing (0 km bug) | ✅ FIXED — tolerance 0.0005°, 21K+ nodes terhubung |
| TCS Map Colors | ✅ DONE — 4 grade kategoris + legenda di peta |
| Frontend Refactor | ✅ DONE — komponen diekstrak, API sentralisasi |
| Directory Cleanup | ✅ DONE — file tidak terpakai dihapus |
| Documentation | ✅ DONE — README, README_TECHNICAL, session_handover diupdate |

---

## Hal yang Belum Selesai / Perlu Diperhatikan

1. **Graph masih terfragmentasi sebagian** — komponen terbesar 21K dari total 69K nodes. Untuk routing yang lebih baik, perlu `pgr_nodeNetwork` (spatial splitting di persimpangan) tapi prosesnya >50 menit. Saat ini routing sudah berfungsi untuk sebagian besar titik di Surabaya pusat.

2. **`routing/` directory** — belum dihapus karena berisi kode yang mungkin dirujuk di spark jobs. Perlu dikonfirmasi apakah bisa dihapus.

3. **Tidak ada `NEXT_PUBLIC_API_URL` di `.env`** — saat ini fallback ke `http://localhost:8000/api`. Jika deploy ke server lain, tambahkan env var ini ke `frontend/.env.local`.

---

## Pembelajaran Penting

1. **pgr_createTopology tolerance sangat kritis**: Tolerance `0.0001°` (11m) tidak cukup untuk data OSM pedestrian yang endpoint-nya bisa berbeda beberapa puluh meter. Gunakan minimal `0.0005°` (55m).
2. **pgr_connectedComponents sebagai diagnostik**: Selalu jalankan `pgr_connectedComponents` setelah rebuild topology untuk memastikan main component mencakup sebagian besar nodes. Jika tidak, routing tidak akan berfungsi meskipun topologi dibangun.
3. **DRY untuk konstanta warna TCS**: Mendefinisikan warna TCS di satu tempat (TCSLegend.tsx) dan mengimpornya di komponen lain mencegah inkonsistensi visual yang sulit di-debug.
4. **`clean:=true` wajib saat rebuild**: Tanpa flag ini, `pgr_createTopology` tidak akan mengupdate tabel yang sudah ada.
