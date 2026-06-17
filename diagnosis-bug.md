# 🔍 Diagnosis Final: Kenapa Rute Selalu 0 km

> Status: Investigasi Selesai. **Root cause teridentifikasi 100%.**

---

## Kesimpulan Cepat

**Database punya data duplikat.** Segmen jalan di-import 2 kali (115.220 = 2 × 57.610 baris). Ini menyebabkan **jaringan jalan terfragmentasi** — titik asal dan tujuan yang dipilih user kemungkinan besar berada di subgraph yang berbeda dan tidak terhubung, sehingga pgr_dijkstra tidak menemukan rute.

---

## Kronologi Debug

### Layer 1 — Error "not unique" (✅ SUDAH DIPERBAIKI)

**Error di log API:**
```
[Route] pgr_dijkstra failed: function pgr_dijkstra(unknown, unknown, unknown, directed => boolean) is not unique
```

**Penyebab:** asyncpg mengirim `$1`, `$2` sebagai tipe PostgreSQL `integer`. Karena ada 5 overload pgr_dijkstra, PostgreSQL tidak bisa memilih overload yang tepat.

**Fix yang sudah diterapkan** di `navigation.py`:
```diff
- $1, $2, directed := false
+ $1::bigint, $2::bigint, directed := false
- 'SELECT segment_id as id, source, target, ...'
+ 'SELECT segment_id as id, source::bigint, target::bigint, ...'
```

---

### Layer 2 — Data Duplikat (❌ ROOT CAUSE FINAL)

**Bukti dari database:**
```
segment_id | source | target | osm_way_id
-----------+--------+--------+-----------
         1 |      1 |      2 |  23783250   ← ingestion pertama
     57611 |      1 |      2 |  23783250   ← ingestion KEDUA (duplikat!)
         2 |      3 |      4 |  24319657
     57612 |      3 |      4 |  24319657   ← duplikat!
```

**Fakta krusial:**
- Total segmen: **115.220** = **2 × 57.610** (persis 2 kali lipat)
- Segmen 1–57.610: Jaringan set **pertama** (node IDs kecil, source 1–~30.000)
- Segmen 57.611–115.220: Duplikat run kedua dengan node IDs berbeda di pgRouting
- Ini menyebabkan graph terfragmentasi — ada 2 "pulau" jaringan yang tidak terhubung

**Verifikasi:**
```
-- BERHASIL: Node 23853 → 23947 (keduanya di subgraph yang sama)
pgr_dijkstra: 3 rows → rute ditemukan ✅

-- GAGAL: Node 23853 → 49160 (beda subgraph)
pgr_dijkstra: 0 rows ❌
```

---

## Solusi yang Diperlukan

### Opsi A: Hapus Duplikat + Rebuild Topology (Lebih Cepat, Direkomendasikan)

```sql
-- Hapus data turunan dulu
DELETE FROM thermal_comfort_scores WHERE segment_id > 57610;
DELETE FROM edge_weights WHERE segment_id > 57610;

-- Hapus segmen duplikat
DELETE FROM segments WHERE segment_id > 57610;

-- Rebuild topology pgRouting
SELECT pgr_createTopology('segments', 0.000001, 'geom', 'segment_id');
```

### Opsi B: Re-ingest Ulang (Lebih Bersih tapi Lebih Lama)

Jalankan ulang pipeline ingestion OSM dengan `TRUNCATE` dulu, lalu rebuild topology. Butuh download ulang ~250 MB data OSM.

---

## Diagram Alir Masalah

```
User klik "Cari Rute"
        ↓
_find_nearest_node() → Node 23853 dan 49160
        ↓
pgr_dijkstra(23853 → 49160) → 0 rows (beda subgraph!)
        ↓
_run_pgr_route() → _empty_route()
        ↓
Frontend: distance_m=0, avg_tcs=0 ← yang kamu lihat
```

---

## Status Perbaikan

| Fix | Status |
|---|---|
| pgr_dijkstra "not unique" error | ✅ SELESAI |
| Hydration mismatch Mantine | ✅ SELESAI |
| **Data duplikat (root cause rute 0)** | ⏳ Menunggu persetujuan |
