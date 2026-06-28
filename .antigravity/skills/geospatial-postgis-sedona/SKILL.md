---
name: geospatial-postgis-sedona
description: Ingestion, transformation, spatial join, and query optimization for vector and raster data using Apache Sedona (PySpark) and PostgreSQL/PostGIS.
---

# Geospatial Data Processing (PostGIS & Apache Sedona)

## Overview

COMMUTE-COOL relies heavily on geospasial datasets (pedestrian paths, buildings, trees, GEE rasters). Performing spatial operations on big data scales requires optimized queries, proper spatial indexing, and correct coordinate systems. This skill guides the agent in developing robust geospatial pipelines using PostGIS and Apache Sedona.

---

## 1. Coordinate Reference Systems (CRS)

* **Storage Default**: Always store and return final geometries in **WGS84 (EPSG:4326)** (latitude/longitude in degrees) for compatibility with Web Mapping APIs (Leaflet.js, Mapbox GL JS).
* **Metric Operations**: When performing calculations that require meters (e.g., buffer distances, building heights, shadow lengths, pedestrian speeds), project geometries to a metric coordinate system.
  * *For Surabaya case study:* Use **UTM Zone 49S (EPSG:32749)**.
* **Conversion in PostGIS**:
  ```sql
  -- Convert geometry to UTM Zone 49S to calculate distance in meters, then buffer by 2 meters, and project back to WGS84
  SELECT ST_Transform(ST_Buffer(ST_Transform(geom, 32749), 2.0), 4326) FROM segments;
  ```
* **Conversion in Sedona SQL**:
  ```python
  # Reproject geometry inside Sedona DataFrame
  df = spark.sql("""
      SELECT ST_Transform(geom, 'EPSG:4326', 'EPSG:32749') as geom_utm
      FROM segments_df
  """)
  ```

---

## 2. Spatial Indexing & Joins

### PostgreSQL / PostGIS Indexing
* Always index spatial tables using **GiST (Generalized Search Tree)**:
  ```sql
  CREATE INDEX idx_segments_geom ON segments USING GIST (geom);
  CREATE INDEX idx_buildings_geom ON buildings USING GIST (geom);
  CREATE INDEX idx_trees_geom ON trees USING GIST (geom);
  ```
* Regularly run `ANALYZE` after large batch inserts to update statistics for the spatial query planner.

### Apache Sedona Spatial Joins
* For heavy spatial joins (e.g., matching building shadows with street segment buffer zones), ensure Sedona's spatial partitioning is active to divide the data into spatial grids:
  ```python
  # Join segments with buildings using spatial intersection
  sedona_df = spark.sql("""
      SELECT s.segment_id, b.building_id
      FROM segments s, buildings b
      WHERE ST_Intersects(s.geom, b.geom)
  """)
  ```
* Keep partition counts aligned with data volume to avoid shuffling bottlenecks.

---

## 3. Shadow Projection Geometry

To project a shadow polygon from building or tree geometry:
1. Obtain the solar azimuth ($\theta$) and elevation ($\alpha$) for the location and timestamp.
2. Calculate shadow length: $L = \text{height} / \tan(\alpha)$.
3. Project coordinates of each polygon vertex in the direction of the shadow azimuth ($\theta + 180^\circ$):
   * $\Delta x = L \times \sin(\theta_{shadow})$
   * $\Delta y = L \times \cos(\theta_{shadow})$
4. Shift the original geometry using the delta values in the metric coordinate space (EPSG:32749) before converting back to EPSG:4326.

---

## 4. Verification & Testing

* **Intersection over Union (IoU) Validation**:
  Compare predicted shadow polygons with satellite/ground-truth imagery. Target $\text{IoU} \ge 80\%$:
  $$\text{IoU} = \frac{\text{Area}(\text{Shadow}_{\text{Model}} \cap \text{Shadow}_{\text{Real}})}{\text{Area}(\text{Shadow}_{\text{Model}} \cup \text{Shadow}_{\text{Real}})}$$
* **Unit Test Geometries**:
  Write unit tests with simple synthetic shapes (e.g., a square building of 10m height at the equator) to verify shadow calculations mathematically.
