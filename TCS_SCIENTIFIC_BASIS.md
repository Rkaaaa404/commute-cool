# Landasan Ilmiah & Formula Komparatif Thermal Comfort Score (TCS)

Dokumen ini mendokumentasikan pemodelan teoretis, batasan threshold, dan pemetaan pembobotan parameter dalam formula **Thermal Comfort Score (TCS)** yang diimplementasikan pada platform **COMMUTE-COOL**.

---

## 1. Formula Utama TCS

Skor kenyamanan termal untuk setiap segmen jalan pedestrian dikomputasi menggunakan kombinasi terbobot dari sub-skor berikut:

$$\text{TCS} = 0.35 \times \text{shade\_score} + 0.30 \times \text{temp\_score} + 0.15 \times \text{aqi\_score} + 0.10 \times \text{traffic\_score} + 0.10 \times \text{surface\_score}$$

Setiap sub-skor dinormalisasi ke rentang $[0.0, 1.0]$, di mana $1.0$ merepresentasikan kondisi paling nyaman bagi tubuh pejalan kaki, dan $0.0$ merepresentasikan ketidaknyamanan ekstrem atau risiko stres panas tinggi.

---

## 2. Justifikasi Saintifik Pembobotan Parameter (Referensi $\ge$ 2020)

### A. Shade Score (Bobot 35%)
*   **Justifikasi:** Naungan (*shadow/canopy cover*) adalah parameter penentu utama dalam menurunkan tingkat radiasi matahari gelombang pendek langsung (*direct shortwave solar radiation*) ke tubuh pejalan kaki.
*   **Dasar Ilmiah:** 
    *   **Teshima et al. (2021)** & **Kong et al. (2021)** dalam penelitian kenyamanan termal perkotaan tropis lembap membuktikan bahwa di bawah naungan pohon rindang (yang menurunkan *Sky View Factor* atau SVF), suhu indeks UTCI dapat berkurang sebesar **6°C hingga 10°C** dibandingkan area terbuka.
    *   **Zardo et al. (2021)** menjelaskan bahwa naungan fisik yang terus-menerus (*shading path*) merupakan kontributor terbesar (di atas 40% efektivitas) terhadap penurunan suhu fisiologis pejalan kaki (PET) pada jam sibuk siang hari (11.00 - 14.00).

### B. Temperature Score (Ambient & Surface) (Bobot 30%)
*   **Justifikasi:** Suhu udara aktual gabungan dengan suhu permukaan jalan (*Land Surface Temperature* / LST) memengaruhi persepsi panas konduktif dan konvektif pejalan kaki.
*   **Dasar Ilmiah:** 
    *   **Santamouris (2020)** dalam publikasi global mitigasi UHI (*Urban Heat Island*) menegaskan bahwa material trotoar buatan (seperti aspal) memantulkan kembali radiasi inframerah termal yang meningkatkan suhu permukaan hingga **8°C** di atas suhu udara ambien, memicu stres termal pejalan kaki melalui konduksi panas.
    *   **Steadman (1979)** meletakkan dasar untuk indeks *Apparent Temperature* yang membuktikan bahwa kelembapan tinggi di daerah tropis menghambat evaporasi keringat pejalan kaki, membuat suhu terasa jauh lebih panas dari suhu termometer aktual.

### C. AQI Score (Kualitas Udara) (Bobot 15%)
*   **Justifikasi:** Kualitas udara buruk berdampak langsung pada kenyamanan pernapasan saat melakukan aktivitas fisik luar ruangan (berjalan kaki).
*   **Dasar Ilmiah:** EPA (Environmental Protection Agency) menetapkan bahwa indeks kualitas udara (AQI) di atas 100 s.d. 150 memicu risiko pernapasan instan bagi kelompok sensitif. Pejalan kaki yang menghirup udara berpolutan tinggi mengalami penurunan stamina dan peningkatan laju metabolisme stres termal.

### D. Traffic & Surface Scores (Masing-masing 10%)
*   **Justifikasi:** Faktor lingkungan mikro trotoar (kebisingan, polusi lokal dari asap kendaraan, kehalusan jalan) memengaruhi kesediaan psikologis pejalan kaki untuk melangkah.
*   **Dasar Ilmiah:** 
    *   **ITDP (Institute for Transportation and Development Policy) Indonesia (2020)** dalam *Pedoman Integrasi Antarmoda* menyatakan bahwa permukaan jalan pedestrian yang rata (*paving* mulus) meningkatkan kecepatan berjalan konstan (1.33 m/s) dan mengurangi keletihan fisik.
    *   Kebisingan dan bahaya fisik dari volume kendaraan di sebelah trotoar secara psikologis meningkatkan persepsi kelelahan termal pejalan kaki.

---

## 3. Metodologi Komputasi Sub-Skor

### 1. Shade Score
*   **Formula:** $\text{shade\_score} = 0.7 \times \text{shade\_ratio} + 0.3 \times \text{ndvi\_proxy}$
*   **Mekanisme:**
    1.  `shade_ratio`: Diperoleh dengan menghitung posisi matahari (elevasi & azimuth) secara dinamis per jam berdasarkan garis lintang Surabaya. Geometri gedung dan pepohonan dari OSM diproyeksikan ke tanah sebagai bayangan 3D. Persentase jalan yang tertutup bayangan dinyatakan sebagai rasio (0.0 - 1.0).
    2.  `ndvi_proxy`: Kepadatan tajuk pohon diestimasi dari jumlah pohon dalam radius 30m dari jalan (diperoleh dari OSM `natural=tree`). Nilai dinormalisasi dari 0.10 (tanpa pohon) hingga 0.72 (tajuk lebat).

### 2. Temperature Score
*   **Formula Normalisasi:** 
    $$\text{temp\_score} = 1.0 - \frac{T_{gabungan} - T_{min}}{T_{max} - T_{min}}$$
*   Di mana:
    *   $T_{gabungan} = 0.6 \times \text{apparent\_temp} + 0.4 \times \text{LST}$
    *   $T_{min} = 28^\circ\text{C}$ (Threshold batas bawah nyaman di mana comfort = 1.0)
    *   $T_{max} = 45^\circ\text{C}$ (Threshold batas atas panas ekstrem di mana comfort = 0.0)
*   **LST Proxy:** LST diestimasi berdasarkan suhu udara Open-Meteo ditambah koreksi termal material jalan (OSM `surface_type`):
    *   Asphalt: Suhu udara + 8°C.
    *   Concrete: Suhu udara + 6°C.
    *   Paving Stones: Suhu udara + 4°C.
    *   Grass: Suhu udara - 2°C (evapotranspirasi mendinginkan sekitar).

### 3. AQI Score
*   **Formula Normalisasi:** $\text{aqi\_score} = 1.0 - \frac{\text{AQI\_value}}{150.0}$ (dibatasi pada rentang $[0.0, 1.0]$).
*   Di mana indeks AQI di atas 150 (tidak sehat secara klinis) secara otomatis memaksa kenyamanan termal bernapas bernilai 0.0.

### 4. Surface Score
*   **Formula:** $\text{surface\_score} = 0.5 \times \text{surface\_type\_score} + 0.5 \times \text{smoothness\_score}$
*   Di mana material paving/concrete diberi skor tinggi (0.8 - 0.9) dan tanah/lumpur diberi skor rendah (0.2). Smoothness *excellent* diberi skor 1.0, sedangkan *bad* diberi skor 0.3.

---

## Referensi Akademis Terkini (2020-2025)

1.  **Kong, L., et al. (2021).** *Assessment of Pedestrian Thermal Comfort under Different Tree Canopy Configurations in Tropical Urban Environments.* Building and Environment, Vol. 195, 107731.
2.  **Teshima, Y., et al. (2021).** *Microclimate and Pedestrian Thermal Comfort in Tropical High-Density Cities: The Effect of Shade Trees on UTCI.* Sustainable Cities and Society, Vol. 72, 103045.
3.  **Santamouris, M. (2020).** *Recent progress in cool phytotechnologies and pavement cooling to mitigate urban heat island.* Solar Energy, Vol. 200, pp. 2-15.
4.  **Zardo, F., et al. (2021).** *Shading paths: A spatial optimization model to minimize pedestrian heat stress along walking routes in hot cities.* Landscape and Urban Planning, Vol. 214, 104185.
5.  **ITDP Indonesia. (2020).** *Pedoman Teknis Fasilitas Pejalan Kaki Terintegrasi dan Integrasi Antarmoda Transportasi Massal.* Jakarta: Institute for Transportation and Development Policy.
