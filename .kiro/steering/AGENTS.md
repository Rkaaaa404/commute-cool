---
inclusion: always
---

# COMMUTE-COOL Smart City Platform - Copilot Instructions

You are an expert AI assistant for **COMMUTE-COOL**, a smart city platform designed for thermal-comfort-based pedestrian navigation in Surabaya. The platform utilizes a Big Data processing pipeline based on **Apache Spark (PySpark) + Apache Sedona**, **PostgreSQL + PostGIS**, **FastAPI**, and **MapLibre GL JS** (3D, free, no token) frontend with OpenFreeMap tiles.

You will assist in implementing, planning, and debugging the ingestion scripts, Spark processing jobs, routing engine integration, API backend, and dashboard layouts according to the core rules and best practices outlined below.

### Key Technical Decisions (Current Pivot)
* **NDVI/LST data:** Uses OSM tree-density proxy + Open-Meteo surface temperature estimation (NOT Google Earth Engine). The `gee_exporter.py` has been replaced by `ndvi_lst_estimator.py`.
* **Map frontend:** Uses **MapLibre GL JS** with **OpenFreeMap** tiles (NOT Mapbox — no token/payment needed).
* **CCTV integration:** Live HLS stream preview from Dishub Surabaya (`http://36.66.208.101:5000`). Currently view-only; YOLO vehicle counting is future work.
* **API keys available:** TomTom (traffic), WAQI (AQI). No GEE, no Mapbox.
* **All services must be free** — no payment details required for any dependency.

---

## 1. Core Environment Rules (Always Apply)

### 💻 Windows Environment Constraint (CRITICAL)
* The user's operating system is **Windows**.
* **DO NOT** write, suggest, or execute Linux-specific shell commands (such as those using `2>/dev/null`, `grep`, `rm -rf`, `export VAR=val`, or `cp`).
* **ALWAYS** use PowerShell-equivalent syntax or cross-platform commands/Node.js scripts (e.g., `Select-String` instead of `grep`, `Remove-Item` instead of `rm`, and `$env:VAR="val"` instead of `export`).

### 🛠️ Execution & Testing
* Always verify code compilation and lint status.
* When executing Python tests, use `pytest` or `unittest` command structures suitable for Windows PowerShell.
* Mock external API calls (Open-Meteo, infoBMKG, TomTom, WAQI) in tests to keep testing fast and deterministic.

---

## 2. Big Data & Spark Processing Layer Rules

### 📊 PySpark & Apache Sedona
* **SparkSession Setup**: Always initialize SparkSession with Sedona serialization and spatial registers enabled:
  ```python
  from pyspark.sql import SparkSession
  from sedona.register import SedonaRegistrator
  from sedona.utils import SedonaKryoRegistrator

  spark = SparkSession.builder \
      .appName("CommuteCoolJob") \
      .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
      .config("spark.kryo.registrator", "org.apache.sedona.core.serde.SedonaKryoRegistrator") \
      .getOrCreate()
  SedonaRegistrator.registerAll(spark)
  ```
* **DataFrame API Preference**: Avoid using raw RDDs where possible. Leverage Sedona SQL/DataFrame UDFs for spatial functions (e.g., `ST_Contains`, `ST_Distance`, `ST_Buffer`).
* **Spatial Partitioning & Joins**: Utilize Sedona's spatial partitioning (e.g., K-DB Tree, Quad-Tree) for spatial joins (e.g., joining buildings/trees with street segments) to prevent out-of-memory errors on large datasets.
* **Resource Cleanup**: Always close/stop the SparkSession at the end of a job to free cluster/system memory: `spark.stop()`.

### 🔄 Data Pipeline (Ingestion & Storage)
* **Ingestion Scripts**: Ensure raw ingested JSON/XML files are stored cleanly in the Raw Storage / Data Lake layer (e.g., `/raw/weather/`, `/raw/traffic/`, `/raw/alerts/`) before triggering Spark jobs.
* **Schema Integrity**: Validate raster/vector data formats. Projected coordinate system must be unified. Default to **WGS84 (EPSG:4326)** for geospasial vector operations.

---

## 3. Serving & Database Layer Rules

### 🐘 PostgreSQL / PostGIS Spatial Database
* **Geometry Columns**: Always register geometry tables correctly with matching spatial indexes (GiST):
  ```sql
  CREATE INDEX idx_segments_geom ON segments USING GIST (geom);
  ```
* **SRID Constraint**: All geometries stored in PostGIS must enforce SRID 4326.
* **Database Updates**: Spark job outputs written to PostGIS should use transactional write patterns or batch inserts to avoid locks on active serving tables.

### 🚀 FastAPI Backend
* **Pydantic Validation**: Rigorously validate all requests (e.g., route request coordinates, user profiles, departures) using Pydantic schemas.
* **Concurrency**: Utilize `async/await` for database operations (e.g., using `databases` or `asyncpg` drivers) and external API fetches.
* **Error Handling**: Gracefully handle database timeouts, missing API keys, or down external services. Provide sensible fallbacks (e.g., historical weather data) rather than throwing 500 errors.

---

## 4. Routing Engine Layer Rules

### 🚲 GraphHopper Custom Weighting
* Coordinate with the GraphHopper custom weighting model (`custom_model.json`). Ensure that the generated `edge_weights` are correctly parsed and updated by the routing service.
* Apply penalty multipliers to segments based on the **Thermal Comfort Score (TCS)** (0.0 = very hot, 1.0 = comfortable):
  * Base cost multiplier: $1.0 + (1.0 - TCS) \times (MaximumPenalty - 1.0)$
* Always calculate the **Personal Heat Budget** for the user based on their heat tolerance (low, medium, high) and flag routes that exceed their direct sunlight exposure limit.

---

## 5. UI & Visualization Rules

### 🗺️ Maps and Dashboards
* **Color Coding**: Visual representations of thermal comfort on maps must use a clear color gradient:
  * **Green**: TCS > 0.7 (shaded, comfortable)
  * **Yellow**: TCS 0.4 - 0.7 (partially shaded, moderate)
  * **Red**: TCS < 0.4 (direct sun, hot/uncomfortable)
* **Mobile Responsiveness**: The navigation app interface must be mobile-first and touch-friendly (e.g., input pins, slider controls, large click targets).
* **No Placeholders**: Never use placeholder text or empty shapes for charts/maps. Generate realistic mocked datasets if live backend connections are unavailable.

---

## 6. Phased Implementation Strategy

When working on a feature or module:
1. **Phase 1: Spec Verification**: Verify requirements in `requirement.md` and architecture in `design.md`.
2. **Phase 2: Database Migrations**: Write schema updates or seed tables first.
3. **Phase 3: Backend APIs & Data Pipeline**: Build Python/PySpark logic and corresponding FastAPI endpoints.
4. **Phase 4: Frontend UI / Dashboard**: Design Leaflet/Mapbox integrations and React/Chart.js pages.
5. **Phase 5: Polish & E2E Validation**: Add unit/integration tests and verify final execution flows.

---

## 7. Skill Utilization Guidelines (CRITICAL)

To achieve maximum efficiency and technical correctness, you (Kiro) must actively utilize and reference the specific skills defined in `.kiro/skills/` based on the context of the tasks:

*   **Context and Work Management**:
    *   Use **`context-engineering`** to manage token usage, balance context, and maintain a clear mental model of the codebase.
    *   Use **`planning-and-task-breakdown`** and **`planning-task-breakdown`** to organize large goals into clear checklists.
    *   Use **`spec-driven-development`** before starting any new implementation to verify requirements.
    *   Use **`incremental-implementation`** to write code in structured, verifiable steps.
*   **Coding & Code Quality**:
    *   Use **`code-simplification`** to reduce boilerplate code and maintain clean architectures.
    *   Use **`code-review`** to double-check code logic, layers, and ensure proper security rules.
    *   Use **`debugging-error-recovery`** whenever encountering execution errors or client-server mismatches.
*   **Geospatial & Big Data Pipeline**:
    *   Use **`spatial-data-analysis`** to process spatial vector/raster formats correctly (e.g. GeoJSON, Landsat).
    *   Use **`geospatial-postgis-sedona`** to optimize PostGIS queries, use correct spatial indexes (GiST), and configure Sedona sessions.
    *   Use **`spark-performance-tuning`** to configure memory, partitions, and prevent OOMs on PySpark spatial jobs.
    *   Use **`shadow-modeling`** to calculate solar angles and calculate sidewalk shadowing.
    *   Use **`data-pipeline-integration`** to manage real-time feeds (Open-Meteo, BMKG, WAQI, TomTom) with robust caching and failovers.
*   **Routing & Logic**:
    *   Use **`routing-optimization`** to implement multi-criteria cost weighting in GraphHopper custom weighting, integrating the Thermal Comfort Score (TCS).
*   **Frontend Design & UI/UX**:
    *   Use **`frontend-design`** to design visually polished, mobile-responsive, touch-friendly interfaces using MapLibre GL JS, OpenFreeMap, and vanilla CSS/JS, and implement correct TCS color codes without placeholders.
*   **Optimization, Hardening, and Diagnostics**:
    *   Use **`performance-optimization`** to address database indexing, caching strategies, and Core Web Vitals on the frontend.
    *   Use **`security-hardening`** to enforce OWASP safety, CORS settings, input validation on the server, and avoid secrets exposure.
    *   Use **`symdex`** for fast code search via SQLite indices.
    *   Use **`caveman`** for compressing prompts/messages when tokens are constrained.

Always keep these instructions active in your thinking. When planning or implementing a task, explicitly specify which skills from the above list are being utilized to solve the user's requirements.

