# COMMUTE-COOL
## Sistem Navigasi Pejalan Kaki Berbasis Kenyamanan Termal untuk Mendukung Smart City

## Deskripsi Umum

**COMMUTE-COOL** adalah ide sistem smart city yang dirancang untuk membantu masyarakat menemukan rute berjalan kaki yang **bukan hanya tercepat, tetapi juga paling nyaman dan aman dari paparan panas matahari**. Dalam banyak kota di Indonesia, masalah panas ekstrem, minimnya pohon peneduh, dan jalur pejalan kaki yang terbuka sering membuat orang enggan berjalan kaki, terutama saat menuju halte, stasiun, kampus, kantor, atau fasilitas umum lainnya. Akibatnya, mobilitas ramah lingkungan menjadi kurang diminati karena perjalanan kaki terasa tidak nyaman dan berisiko menyebabkan stres panas.

Melalui COMMUTE-COOL, sistem akan menggabungkan **data sensor panas lingkungan, data cuaca, informasi bayangan dari pepohonan dan bangunan, serta analisis spasial jalur kota** untuk menghasilkan rekomendasi rute yang lebih teduh dan lebih aman bagi pengguna. Dengan kata lain, sistem ini tidak hanya memikirkan “jalur tercepat”, tetapi juga “jalur terbaik untuk tubuh manusia di bawah kondisi panas kota”.

---

# Masalah yang Ingin Diselesaikan

Saat ini, aplikasi navigasi umum hanya berfokus pada rute terpendek atau waktu tercepat. Padahal, dalam kondisi iklim tropis, jalur terpendek belum tentu menjadi jalur yang paling aman dan nyaman. Seorang pejalan kaki bisa saja menempuh jarak lebih singkat, namun harus melewati area terbuka tanpa keteduhan (*shade*), terpapar radiasi matahari langsung dalam durasi lama, sehingga meningkatkan risiko stres panas (*heat stress*).

Urgensi dari masalah ini didukung oleh data, fakta ilmiah, serta dokumen kebijakan berikut:
1. **Rendahnya Budaya Berjalan Kaki:** Berdasarkan studi global dari Stanford University yang dipublikasikan di jurnal ilmiah [*Nature*](https://doi.org/10.1038/nature23018), Indonesia menempati peringkat terendah dalam kebiasaan berjalan kaki di dunia dengan rata-rata hanya **3.513 langkah per hari**. Naskah ilmiah lengkap studi ini dapat diakses secara resmi di [Repositori NIH PMC5774986](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5774986/). Kurangnya keteduhan jalan dan paparan suhu ekstrem menjadi faktor lingkungan yang dominan menghambat niat masyarakat untuk berjalan kaki.
2. **Rekor Suhu Terpanas & Efek UHI:** Berdasarkan data Badan Meteorologi, Klimatologi, dan Geofisika (BMKG) serta badan iklim dunia, **tahun 2024 dikonfirmasi sebagai tahun terpanas sepanjang sejarah pencatatan** dengan anomali suhu mencapai 0,8°C di Indonesia (lihat laporan global di [Copernicus Global Climate Highlights 2024](https://climate.copernicus.eu/global-climate-highlights-2024) dan portal nasional di [BMKG](https://www.bmkg.go.id)). Ketika suhu ekstrem ini dikombinasikan dengan efek *Urban Heat Island* (UHI) di area perkotaan, suhu yang dirasakan tubuh (*apparent temperature*) pejalan kaki di jalanan terbuka dapat melonjak hingga **37°C - 43°C**.
3. **Krisis Integrasi Transit Pejalan Kaki (First-Mile/Last-Mile):** Keberhasilan peralihan masyarakat ke transportasi publik sangat bergantung pada aksesibilitas dan kenyamanan berjalan kaki menuju stasiun/halte. Hal ini dibahas secara ilmiah dalam jurnal penelitian tata kota [PWK Undip: Dampak TOD terhadap Walkability](https://ejournal.undip.ac.id/index.php/pwk/article/view/52284), serta panduan praktis pembangunan trotoar terintegrasi dari [ITDP Indonesia: Pedoman Integrasi Antarmoda](https://itdp-indonesia.org/wp-content/uploads/2020/03/Pedoman-Integrasi-Antarmoda.pdf).

---

# Gagasan Utama COMMUTE-COOL

COMMUTE-COOL bekerja sebagai **navigasi cerdas berbasis kenyamanan termal**. Sistem ini akan membantu pengguna memilih rute berjalan kaki yang mempertimbangkan tingkat panas, tingkat teduh, dan risiko paparan matahari di sepanjang perjalanan.

Berbeda dari navigasi biasa, COMMUTE-COOL menilai rute berdasarkan beberapa faktor, seperti:

- Tingkat bayangan dari pohon dan bangunan.
- Suhu dan kelembapan lingkungan.
- Intensitas panas pada jam tertentu.
- Jarak tempuh.
- Kondisi pengguna secara personal.

Hasil akhirnya adalah rute yang lebih seimbang: tetap efisien, tetapi juga lebih aman dan nyaman untuk ditempuh.

---

# Fitur Unggulan COMMUTE-COOL

## 1. Personal Heat Budget

Fitur ini menjadi pembeda utama COMMUTE-COOL.

**Personal Heat Budget** adalah konsep yang menyesuaikan rekomendasi rute berdasarkan kemampuan atau toleransi panas setiap pengguna. Artinya, tidak semua orang akan mendapatkan rute yang sama karena kebutuhan dan kondisi tubuh tiap pengguna berbeda.

Contoh:

- Pengguna yang sering berjalan kaki mungkin memiliki toleransi panas lebih tinggi.
- Lansia dan anak-anak membutuhkan jalur yang lebih aman.
- Pengguna yang sedang terburu-buru dapat memilih kompromi antara kecepatan dan kenyamanan.
- Pengguna yang sensitif terhadap panas akan diarahkan ke jalur dengan paparan matahari paling rendah.

Fitur ini membuat sistem tidak hanya melihat kondisi lingkungan, tetapi juga memahami kondisi pengguna. Dengan demikian, rekomendasi menjadi lebih personal, relevan, dan aman.

Secara sederhana, fitur ini menjawab pertanyaan:

> "Seberapa lama dan seberapa besar paparan panas yang masih aman untuk pengguna ini?"

---

## 2. Commute-First Routing

Fitur unggulan kedua adalah **Commute-First Routing**.

Fitur ini berfokus pada kebutuhan perjalanan komuter sehari-hari, seperti:

- Rumah ke halte.
- Rumah ke stasiun.
- Stasiun ke kantor.
- Kampus ke transportasi publik.
- Titik awal menuju fasilitas umum.

COMMUTE-COOL tidak hanya memikirkan perjalanan berjalan kaki biasa, tetapi secara khusus mengoptimalkan **first-mile dan last-mile transportation**, yaitu bagian perjalanan yang paling sering dilakukan pejalan kaki ketika menggunakan transportasi umum.

Dengan pendekatan ini, pengguna akan mendapatkan pengalaman perjalanan yang lebih nyaman sehingga penggunaan transportasi publik dapat meningkat.

Secara sederhana, fitur ini menjawab pertanyaan:

> "Bagaimana cara terbaik berjalan kaki menuju transportasi umum atau tujuan akhir tanpa terpapar panas berlebihan?"

---

# Cara Kerja Sistem

### 1. Pengumpulan Data

Sistem mengumpulkan data secara real-time dan terprogram dari beberapa sumber utama:

- **Data Cuaca & Indeks Kenyamanan Termal:** 
  - Mengintegrasikan parameter suhu, kelembapan, angin, dan radiasi matahari dari [Open-Meteo API](https://open-meteo.com/en/docs) guna memproyeksikan suhu semu (*apparent temperature*).
  - Mengambil prakiraan cuaca lokal tingkat kelurahan melalui [API resmi infoBMKG](https://github.com/infoBMKG/data-cuaca).
- **Data Spasial Jalur & Objek Peneduh:**
  - Mengunduh infrastruktur jalan pejalan kaki, vegetasi (`natural=tree`), dan ketinggian gedung menggunakan query terprogram pada [OSM Wiki - Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API), yang diuji coba secara visual via [Overpass Turbo Sandbox](https://overpass-turbo.eu).
- **Peringatan Dini Cuaca Ekstrem:**
  - Memanfaatkan RSS Feed Peringatan Dini Cuaca dari BMKG ([Peringatan Dini (Bahasa Indonesia)](https://www.bmkg.go.id/alerts/nowcast/id) atau [Peringatan Dini (Bahasa Inggris)](https://www.bmkg.go.id/alerts/nowcast/en)) untuk memblokir rute tertentu jika terdeteksi suhu ekstrem atau cuaca buruk secara real-time.

### 2. Analisis Jalur

Setiap jalur akan dinilai berdasarkan:

- Tingkat paparan matahari.
- Tingkat teduh.
- Risiko panas.
- Jarak tempuh.
- Waktu perjalanan.

### 3. Penyesuaian Personal Heat Budget

Sistem menyesuaikan hasil analisis dengan profil pengguna sehingga rekomendasi yang diberikan sesuai dengan kondisi individu.

### 4. Penyajian Hasil

Pengguna dapat melihat:

- Rute paling nyaman.
- Rute alternatif.
- Tingkat risiko panas.
- Persentase area teduh.
- Estimasi waktu perjalanan.

---

# Dashboard Smart City untuk Pemerintah

Selain aplikasi pengguna, COMMUTE-COOL menyediakan dashboard analitik bagi pemerintah kota.

Dashboard ini dapat digunakan untuk:

- Mengidentifikasi area dengan tingkat panas tinggi.
- Menentukan lokasi prioritas penanaman pohon.
- Menentukan kebutuhan pembangunan kanopi atau fasilitas peneduh.
- Mengevaluasi kenyamanan jalur pejalan kaki.
- Mendukung perencanaan tata kota berbasis data.

Dengan demikian, COMMUTE-COOL tidak hanya bermanfaat bagi individu, tetapi juga menjadi alat bantu pengambilan keputusan bagi pemerintah daerah.

---

# Manfaat COMMUTE-COOL

## Bagi Masyarakat

- Mengurangi risiko stres panas.
- Membantu memilih rute yang lebih nyaman.
- Mendukung gaya hidup sehat melalui berjalan kaki.
- Meningkatkan kenyamanan penggunaan transportasi publik.

## Bagi Pemerintah

- Menyediakan data panas perkotaan secara lebih rinci.
- Membantu perencanaan penghijauan kota.
- Mendukung pembangunan kota yang ramah pejalan kaki.
- Menjadi dasar pengambilan keputusan berbasis data.

## Bagi Lingkungan

- Mendorong penggunaan transportasi umum.
- Mengurangi ketergantungan terhadap kendaraan pribadi.
- Mendukung pembangunan kota yang berkelanjutan.

---

# Nilai Kebaruan (Novelty)

Keunggulan utama COMMUTE-COOL terletak pada kombinasi empat elemen utama:

1. Navigasi berbasis kenyamanan termal.
2. Pemanfaatan data panas lingkungan secara real-time.
3. Personal Heat Budget yang menyesuaikan rekomendasi dengan karakteristik pengguna.
4. Commute-First Routing yang berfokus pada kebutuhan perjalanan komuter.

Kombinasi ini menjadikan COMMUTE-COOL lebih dari sekadar aplikasi navigasi, tetapi sebagai platform smart city yang menghubungkan kesehatan masyarakat, mobilitas perkotaan, dan perencanaan tata ruang.

---

# Kesimpulan

COMMUTE-COOL merupakan solusi smart city yang membantu masyarakat menemukan rute berjalan kaki yang lebih teduh, nyaman, dan aman dari paparan panas matahari. Dengan fitur unggulan **Personal Heat Budget** dan **Commute-First Routing**, sistem mampu memberikan pengalaman navigasi yang lebih personal dan relevan untuk kondisi kota tropis seperti Indonesia. Selain meningkatkan kenyamanan pengguna, COMMUTE-COOL juga menyediakan data strategis yang dapat dimanfaatkan pemerintah untuk membangun kota yang lebih hijau, sehat, ramah pejalan kaki, dan berkelanjutan.

---

# Referensi dan Sumber Data

### 1. Referensi Ilmiah & Berita (Urgensi & Relevansi)
*   **Studi Langkah Kaki Global Stanford University:** 
    *   Jurnal Resmi Nature: [Nature Publication DOI: 10.1038/nature23018](https://doi.org/10.1038/nature23018)
    *   Naskah Ilmiah Lengkap (NIH PMC): [NCBI PubMed Central Article PMC5774986](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5774986/)
*   **Informasi Iklim & Rekor Suhu Nasional:**
    *   Laporan Global Rekor Terpanas: [Copernicus Global Climate Highlights 2024](https://climate.copernicus.eu/global-climate-highlights-2024)
    *   Portal Resmi Informasi Iklim: [BMKG Portal Resmi](https://www.bmkg.go.id)
*   **Kebijakan & Penelitian Transit Pejalan Kaki (First-Mile/Last-Mile):**
    *   Jurnal Ilmiah Tata Kota (Undip PWK): [PWK Undip - Dampak TOD terhadap Walkability](https://ejournal.undip.ac.id/index.php/pwk/article/view/52284)
    *   Panduan Teknis Resmi Integrasi: [ITDP Indonesia - Pedoman Integrasi Antarmoda PDF](https://itdp-indonesia.org/wp-content/uploads/2020/03/Pedoman-Integrasi-Antarmoda.pdf)
    *   Studi Kasus Integrasi Transportasi: [ITDP - Lessons Learned from Jakarta's Integrated Transport](https://itdp-indonesia.org/publication/lessons-learned-from-jakartas-journey-to-integrated-and-resilient-transport-systems/)

### 2. Data API (Integrasi & Perutean Teknis)
*   **API Cuaca & Indeks Kenyamanan Termal:**
    *   Open-Meteo: [Open-Meteo API Documentation](https://open-meteo.com/en/docs)
    *   API infoBMKG: [GitHub infoBMKG - Data Cuaca](https://github.com/infoBMKG/data-cuaca)
*   **API Data Spasial & Pemodelan Bayangan (Shadow Modeling):**
    *   Overpass API (OpenStreetMap): [OSM Wiki - Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API)
    *   Overpass Turbo: [Overpass Turbo Sandbox](https://overpass-turbo.eu)
*   **API Mesin Navigasi (Routing Engines):**
    *   GraphHopper: [GraphHopper GitHub Repository](https://github.com/graphhopper/graphhopper)
    *   Valhalla: [Valhalla GitHub Repository](https://github.com/valhalla/valhalla) (dan [Dokumentasi Valhalla](https://valhalla.github.io))

### 3. Data RSS Feed (Peringatan Dini & Berita)
*   **Peringatan Dini Cuaca Ekstrem BMKG:**
    *   Bahasa Indonesia: [BMKG Weather Alerts (ID)](https://www.bmkg.go.id/alerts/nowcast/id)
    *   Bahasa Inggris: [BMKG Weather Alerts (EN)](https://www.bmkg.go.id/alerts/nowcast/en)
*   **RSS Feed Berita Smart City & Urbanisasi (ANTARA News):**
    *   Kategori Metro: [ANTARA News - Metro Feed](https://www.antaranews.com/rss/metro.xml)
    *   Kategori Teknologi: [ANTARA News - Tekno Feed](https://www.antaranews.com/rss/tekno.xml)
