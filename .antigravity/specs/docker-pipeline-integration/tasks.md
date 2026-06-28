# Implementation Plan: Docker Pipeline Integration

## Overview

Plan implementasi fitur Docker Pipeline Integration untuk COMMUTE-COOL. Mengonsolidasikan seluruh stack ke Docker Compose (4 services), real data pipeline via Spark, asyncpg API, dan thermal heatmap overlay.

## Tasks

- [x] 1. Rewrite `docker-compose.yml` — 4 services (postgres, spark-pipeline, api, frontend) dengan healthcheck, named volumes, port mapping, dan environment variables
  - *Files:* `docker-compose.yml`

- [x] 2. Buat `Dockerfile.spark` — Spark 3.5 base image, pre-download PostgreSQL JDBC + Sedona + DataSketches JARs, copy spark_jobs/ + ingestion/ + data/
  - *Files:* `Dockerfile.spark`

- [x] 3. Buat `Dockerfile.api` — python:3.11-slim, install requirements-docker.txt, copy api/ + routing/, run uvicorn
  - *Files:* `Dockerfile.api`

- [x] 4. Buat `nginx.conf` — serve navigation at /, dashboard at /dashboard, proxy /api/ ke api:8000
  - *Files:* `nginx.conf`

- [x] 5. Buat `.dockerignore` — exclude .git, .venv, __pycache__, *.md, frontend, notebooks, docs
  - *Files:* `.dockerignore`

- [x] 6. Split requirements — `requirements-docker.txt` (API deps tanpa PySpark) + `requirements-spark.txt` (Spark deps)
  - *Files:* `requirements-docker.txt`, `requirements-spark.txt`

- [x] 7. Buat `spark_jobs/config.py` — parse DATABASE_URL env var ke JDBC_URL + JDBC_PROPS untuk semua Spark jobs
  - *Files:* `spark_jobs/config.py`

- [x] 8. Buat `spark_jobs/run_pipeline.py` — orchestrator: wait_for_db → 7 steps (ingest, load OSM, 5 Spark jobs) dengan fallback PostgreSQL per step
  - *Files:* `spark_jobs/run_pipeline.py`

- [x] 9. Update `job_raster_segment.py` — gunakan shared config, local[*] mode, Sedona spatial join tree density + LST correction
  - *Files:* `spark_jobs/job_raster_segment.py`

- [x] 10. Update `job_shadow_model.py` — gunakan shared config, solar position pvlib, shade ratio per jam 6-17 WIB
  - *Files:* `spark_jobs/job_shadow_model.py`

- [x] 11. Update `job_traffic_aqi.py` — gunakan shared config, geocode traffic ke nearest segment, uniform AQI
  - *Files:* `spark_jobs/job_traffic_aqi.py`

- [x] 12. Update `job_thermal_comfort.py` — gunakan shared config, join all layers, formula TCS (0.35×shade + 0.30×temp + 0.15×aqi + 0.10×traffic + 0.10×surface)
  - *Files:* `spark_jobs/job_thermal_comfort.py`

- [x] 13. Update `job_graph_weight.py` — gunakan shared config, penalty formula total_cost = base × (1 + (1-TCS) × 2), write DB + JSON
  - *Files:* `spark_jobs/job_graph_weight.py`

- [x] 14. Buat `api/db.py` — asyncpg connection pool (min=2, max=10, timeout=30s) dengan lifespan init/close
  - *Files:* `api/db.py`

- [x] 15. Update `api/main.py` — lifespan pool management, CORS middleware, include 3 routers (navigation, dashboard, cctv)
  - *Files:* `api/main.py`

- [x] 16. Rewrite `api/routes/navigation.py` — POST /api/route (corridor query, 2 routes) + GET /api/segments/thermal (heatmap, max 2000)
  - *Files:* `api/routes/navigation.py`

- [x] 17. Rewrite `api/routes/dashboard.py` — 3 endpoints (uhi, priority-corridors, walkability) dengan real PostGIS queries
  - *Files:* `api/routes/dashboard.py`

- [x] 18. Rewrite `api/routes/cctv.py` — GET /api/cctv/nearby spatial query (ST_DWithin) + GET /api/cctv/{id}/info
  - *Files:* `api/routes/cctv.py`

- [x] 19. Implementasi thermal heatmap di `map.js` — loadThermalHeatmap() on map load, dual-layer (glow + crisp), color gradient, click popup, zoom-dependent width
  - *Files:* `frontend/navigation/map.js`

- [x] 20. Tambah heatmap toggle di `index.html` — checkbox di legend panel, default checked
  - *Files:* `frontend/navigation/index.html`, `frontend/navigation/map.js`

- [x] 21. Update `dashboard.js` — relative API URL via nginx proxy (/api/ bukan localhost:8000)
  - *Files:* `frontend/dashboard/dashboard.js`

- [x] 22. Hapus MinIO dari docker-compose dan hapus seed_tcs.sql
  - *Files:* `docker-compose.yml`

- [x] 23. Update `README.md` — Docker Compose quick start, arsitektur baru, endpoints, fallback explanation
  - *Files:* `README.md`

## Task Dependency Graph

```json
{
  "waves": [
    [1, 5, 6],
    [2, 3, 4],
    [7, 14],
    [9, 10, 11, 12, 13, 15],
    [8, 16, 17, 18],
    [19, 20, 21, 22],
    [23]
  ]
}
```

## Notes

- Semua 23 tasks sudah diimplementasi. Tidak ada task pending.
- Spark jobs menjalankan dalam mode `local[*]` (single machine, multi-thread) — cukup untuk data kota Surabaya (~15k segments).
- Fallback mechanism memastikan API selalu memiliki data untuk disajikan, bahkan jika Spark cluster gagal.
- Frontend tidak memerlukan build step — semua vanilla JS, langsung di-serve oleh Nginx.
