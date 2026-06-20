# Sistem Navigasi Pejalan Kaki Berbasis Kenyamanan Termal untuk Mendukung Smart City

## Masalah
1. Budaya Jalan Kaki Terendah:
Rata-rata warga Indonesia hanya berjalan 3.513 langkah/hari (Studi Stanford di Nature).
2. Suhu Ekstrem & Urban Heat:
Rekor tahun terpanas 2024 (data BMKG & Copernicus) meningkatkan suhu semu perkotaan menjadi 37°C - 43°C.
3. Masalah First/Last-Mile Transit:
Masyarakat enggan ke halte/stasiun karena rute pedestrian gersang (analisis PWK Undip & ITDP).

## Unik/Keterbaruan
1. Kelemahan Google/Waze/Apple Maps:
Hanya menghitung rute tercepat/terpendek tanpa mengindahkan paparan panas matahari, keberadaan naungan (shade), serta kenyamanan termal.
2. Diferensiasi dari Solusi Global:
Dibanding proyek sejenis (seperti Cool Walks), COMMUTE-COOL mengintegrasikan:
- Personal Heat Budget (profil toleransi panas individu).
- Commute-First Routing (fokus pada transit transportasi umum).
- Dynamic real-time weather & alerts.

## Dampak
1. Sumber Data Integratif:
- Cuaca: Open-Meteo API & API infoBMKG.
- Spasial: Overpass API (OSM) untuk rute & data bayangan bangunan/pohon.
- RSS Feed BMKG & berita ANTARA News untuk deteksi kondisi ekstrem.
2. Solusi Nyata:
- Rute teduh real-time untuk pejalan kaki.
- Dashboard tata kota untuk membantu pemda menentukan titik prioritas penghijauan & kanopi

## Inovasi
1. Shadow Modeling:
Algoritma proyeksi bayangan dinamis gedung/pohon berdasarkan sudut azimuth & elevasi matahari secara berkala.

2. Routing Cost Engine:
Modifikasi bobot pencarian rute pada engine open-source (GraphHopper / Valhalla) berbasis indeks kenyamanan termal.

3. Algoritma Heat Budget:
Menyaring rute secara adaptif sesuai limit toleransi panas tubuh pengguna.

4. RSS Parser Rerouting:
Rerouting otomatis instan jika BMKG merilis peringatan cuaca buruk."