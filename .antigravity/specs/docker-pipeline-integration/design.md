# Design Document: Docker Pipeline Integration

## Overview

Fitur **Docker Pipeline Integration** mengonsolidasikan seluruh stack COMMUTE-COOL ke dalam satu orkestrasi Docker Compose (`docker compose up --build`) yang menjalankan 4 services: PostgreSQL/PostGIS, Apache Spark pipeline (one-shot), FastAPI backend, dan Nginx frontend. Seluruh data berasal dari pemrosesan real API + Spark jobs (bukan dummy seed). Fallback ke PostgreSQL langsung disediakan jika Spark gagal.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Docker Compose Network                           │
│                                                                          │
│  ┌─────────────────────┐     ┌──────────────────────────────────────┐   │
│  │   frontend (Nginx)  │     │        spark-pipeline                │   │
│  │   Port: 3000→80     │     │   (one-shot, exit after pipeline)    │   │
│  │                     │     │                                      │   │
│  │  / → navigation/    │     │  Step 1: Ingest APIs (WAQI/TomTom)  │   │
│  │  /dashboard → dash/ │     │  Step 2: Load OSM GeoJSON → PostGIS │   │
│  │  /api/ → proxy→api  │     │  Step 3-7: Spark Jobs 1-5           │   │
│  └─────────┬───────────┘     └──────────────────┬───────────────────┘   │
│            │                                     │                       │
│            ▼                                     │ JDBC write             │
│  ┌─────────────────────┐                        ▼                       │
│  │   api (FastAPI)     │     ┌──────────────────────────────────────┐   │
│  │   Port: 8000        │────→│       postgres (PostGIS)             │   │
│  │   asyncpg pool      │     │       Port: 5432                     │   │
│  └─────────────────────┘     └──────────────────────────────────────┘   │
│                                                                          │
│  Volumes: pgdata (persistent DB), spark_data (raw data cache)           │
└──────────────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### Docker Compose Services

| Service | Image | Port | Depends On | Behavior |
|---------|-------|------|-----------|----------|
| `postgres` | postgis/postgis:15-3.3 | 5432 | - | Persistent, auto-init schema |
| `spark-pipeline` | Dockerfile.spark | - | postgres (healthy) | One-shot: runs pipeline then exits |
| `api` | Dockerfile.api | 8000 | postgres (healthy) | Long-running, restart unless-stopped |
| `frontend` | nginx:alpine | 3000→80 | api | Long-running, restart unless-stopped |

### Spark Pipeline Steps (run_pipeline.py)

```
wait_for_db(30 retries × 2s)
  → Step 1: Ingest APIs (Open-Meteo, WAQI, TomTom) → data/raw/
  → Step 2: Load OSM GeoJSON → PostGIS (segments, buildings, trees)
  → Step 3: Spark Job 1 (NDVI/LST) [fallback: ndvi_lst_estimator.py]
  → Step 4: Spark Job 2 (Shadow) [fallback: PostGIS proximity]
  → Step 5: Spark Job 4 (Traffic/AQI) [no fallback needed]
  → Step 6: Spark Job 3 (TCS) [fallback: PostgreSQL computation]
  → Step 7: Spark Job 5 (Weights) [fallback: PostgreSQL computation]
  → Exit 0
```

### API Endpoints (FastAPI + asyncpg)

| Endpoint | Interface | PostGIS Query Strategy |
|----------|-----------|------------------------|
| `POST /api/route` | origin, destination, user_profile → 2 routes | Bounding box corridor → JOIN TCS + weights |
| `GET /api/segments/thermal` | → GeoJSON segments + TCS | INNER JOIN latest TCS, LIMIT 2000 |
| `GET /api/dashboard/uhi` | → hotspots + summary | Filter TCS < 0.5, LIMIT 100 |
| `GET /api/dashboard/priority-corridors` | → ranked corridors | TCS < 0.55 + ST_DWithin(transit) |
| `GET /api/dashboard/walkability` | → transit accessibility stats | COUNT stops with TCS > 0.5 within 750m |
| `GET /api/cctv/nearby` | lat, lng, radius → cameras | ST_DWithin + ORDER BY distance |

### Frontend Layers

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Navigation map | MapLibre GL JS + OpenFreeMap Liberty | 3D buildings, route display |
| Thermal heatmap | MapLibre dual-layer (glow + crisp) | City-wide TCS visualization |
| Route panel | Vanilla JS | Comparison cards with TCS metrics |
| CCTV modal | HLS.js | Live stream preview |
| Dashboard | Chart.js + MapLibre | Government analytics (5 tabs) |

### Nginx Proxy Configuration

```
/              → /usr/share/nginx/html/navigation/ (try_files)
/dashboard     → alias /usr/share/nginx/html/dashboard/
/api/          → proxy_pass http://api:8000/api/
/health        → proxy_pass http://api:8000/health
```

## Data Models

### PostGIS Tables (written by Spark Pipeline)

| Table | Written By | Key Columns |
|-------|-----------|-------------|
| `segments` | OSM Loader | segment_id, geom(LineString,4326), surface_type, length_m |
| `buildings` | OSM Loader | building_id, geom(Polygon,4326), height_m |
| `trees` | OSM Loader | tree_id, geom(Point,4326), height_m, crown_radius_m |
| `segment_raster_scores` | Spark Job 1 | segment_id, avg_ndvi, avg_lst, computed_at |
| `segment_shadows` | Spark Job 2 | segment_id, hour_of_day, shade_ratio, computed_at |
| `thermal_comfort_scores` | Spark Job 3 | segment_id, tcs_value, apparent_temp, shade_ratio, aqi_value, traffic_level, computed_at |
| `edge_weights` | Spark Job 5 | segment_id, base_cost, thermal_penalty, total_cost, valid_from, valid_until |
| `transit_stops` | Seed SQL | stop_id, geom(Point,4326), stop_type, operator |
| `cctv_cameras` | CCTV Registry | dishub_id, geom(Point,4326), name, stream_url, is_active |

### Environment Variables

| Variable | Used By | Format |
|----------|---------|--------|
| `DATABASE_URL` | spark-pipeline, api | `postgresql://cc_user:cc_dev_pass@postgres:5432/commute_cool` |
| `ASYNC_DATABASE_URL` | api | `postgresql+asyncpg://cc_user:cc_dev_pass@postgres:5432/commute_cool` |
| `TOMTOM_API_KEY` | spark-pipeline | API key string |
| `WAQI_API_TOKEN` | spark-pipeline | API token string |
| `RAW_DATA_DIR` | spark-pipeline | `/app/data/raw` |
| `SPARK_MASTER_URL` | spark-pipeline | `local[*]` |

### API Request/Response Schema (key models)

**Route Request:**
```json
{ "origin": {"lat": -7.27, "lng": 112.74},
  "destination": {"lat": -7.26, "lng": 112.75},
  "user_profile": {"heat_tolerance": "low"} }
```

**Route Response:** 2 routes (shortest + most_comfortable) each with distance_m, duration_min, sun_exposure_min, avg_tcs, within_heat_budget, geometry (GeoJSON), segments (per-segment TCS).

**Thermal Segments Response:** Array of `{segment_id, tcs_value, geometry}` (max 2000).

## Correctness Properties

### Property 1: Data Integrity
All geometries stored with SRID 4326. GiST indexes on all geometry columns ensure spatial query correctness. Segments, buildings, and trees tables enforce NOT NULL on geom columns.
**Validates: Requirements 2.4, 3.1**

### Property 2: TCS Range
TCS output always clamped to [0.0, 1.0] via `LEAST(1.0, GREATEST(0.0, ...))` in both Spark jobs and PostgreSQL fallback. No NaN or NULL values written to tcs_value column.
**Validates: Requirements 3.4, 4.2**

### Property 3: Fallback Equivalence
Fallback path produces identical table schema (same columns, same types, same constraints) and valid TCS values within [0.0, 1.0] as Spark primary path. API layer is agnostic to which path produced the data.
**Validates: Requirements 4.1, 4.2**

### Property 4: Idempotent Pipeline
Re-running pipeline does not corrupt data. OSM load uses ON CONFLICT DO NOTHING. Edge weights use mode overwrite. TCS uses UNIQUE constraint (segment_id, computed_at).
**Validates: Requirements 10.3, 10.4**

### Property 5: Dependency Order
Spark Job 3 (TCS) only runs after Jobs 1, 2, and 4 complete. Job 5 (Weights) only runs after Job 3. Enforced by sequential execution in run_pipeline.py.
**Validates: Requirements 3.6, 3.7**

## Error Handling

| Component | Error Type | Handling Strategy |
|-----------|-----------|-------------------|
| Spark Pipeline | API timeout (30s) | Log warning, use last available raw data |
| Spark Pipeline | Sedona JAR error | Catch exception, run PostgreSQL fallback |
| Spark Pipeline | DB unavailable | Retry 30×2s, then exit(1) |
| API | DB pool exhausted | Return HTTP 503 with descriptive message |
| API | Query timeout (30s) | asyncpg raises, caught → HTTP 503 |
| API | Coordinates out of bounds | Validate → HTTP 400 "outside Surabaya area" |
| Frontend | API unavailable | Show map without heatmap, log to console |
| Frontend | Route API fails | Display demo/fallback route data |

## Testing Strategy

| Layer | Test Type | Tool | Files |
|-------|-----------|------|-------|
| Spark utils | Unit test | pytest | `tests/test_normalization.py` (16 tests), `tests/test_solar_position.py` (6 tests) |
| Shadow model | Validation | Custom script | `validation/validate_shadow.py` (IoU check) |
| TCS accuracy | Validation | Custom script | `validation/validate_thermal.py` (MAE check) |
| API endpoints | Integration | pytest + httpx | `tests/test_e2e.py` |
| Full stack | E2E | docker compose up → verify endpoints | Manual / CI script |

**Verification after `docker compose up --build`:**
```sql
SELECT COUNT(*) FROM thermal_comfort_scores;  -- Should be > 0
SELECT COUNT(*) FROM edge_weights;            -- Should be > 0
SELECT COUNT(*) FROM segments;                -- Should be > 1000
```
