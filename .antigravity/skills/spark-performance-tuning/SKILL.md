---
name: spark-performance-tuning
description: Performance optimization, memory management, partitioning, and caching strategies for PySpark and Apache Sedona big data pipelines.
---

# Spark Performance Tuning and Optimization

## Overview

COMMUTE-COOL processes heavy datasets like Landsat 8 rasters (LST, NDVI) and OpenStreetMap vector layers (roads, buildings, trees). Unoptimized Spark jobs can lead to memory overhead, data skewness, high execution times, and out-of-memory (OOM) errors. This skill details strategies for optimizing PySpark and Apache Sedona execution.

---

## 1. Serialization & Memory Management

* **Kryo Serializer**: Always use Kryo serialization for Sedona, as it is 10x faster and more compact than standard Java serialization:
  ```python
  spark = SparkSession.builder \
      .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
      .config("spark.kryo.registrator", "org.apache.sedona.core.serde.SedonaKryoRegistrator") \
      .getOrCreate()
  ```
* **Memory Allocation**: Configure executor and driver memory ratios. Balance executor cores and memory to prevent garbage collection bottlenecks:
  ```properties
  spark.executor.memory = 4g
  spark.driver.memory = 2g
  spark.executor.cores = 2
  ```

---

## 2. Partitioning & Parallelism

* **Default Parallelism**: Match the number of partitions to $2 \times \text{total executor cores}$ in the cluster (or CPU threads on local development setups).
  ```python
  # Set default shuffle partitions for DataFrame joins and aggregations
  spark.conf.set("spark.sql.shuffle.partitions", "8")  # Align with system/cluster threads
  ```
* **Spatial Partitioning in Sedona**:
  When performing spatial joins, partitioning by spatial boundaries prevents full cartesian product lookups. Use K-DB Tree or Quad-Tree partitioning:
  ```python
  # Partition street segments and building boundaries spatially
  segments_df.spatialPartitioning(GridType.QUADTREE)
  buildings_df.spatialPartitioning(segments_df.getPartitioner())
  ```

---

## 3. Caching & Persistence

* **When to Cache**: Cache DataFrames that are reused multiple times in downstream transformations (e.g., street segments after cleaning, building geometries before shadow projection).
* **Storage Level**: Default to `MEMORY_AND_DISK` to avoid recomputation if executor memory is full.
* **Unpersist**: Always release cached DataFrames once they are no longer needed:
  ```python
  # Cache
  clean_segments_df.persist(StorageLevel.MEMORY_AND_DISK)
  
  # Perform calculations...
  
  # Unpersist at the end of execution
  clean_segments_df.unpersist()
  ```

---

## 4. Avoiding Skewness and Shuffling

* **Broadcast Joins**: If joining a large spatial dataset (e.g., street segments) with a small dataset (e.g., weather coordinates or AQI values), broadcast the smaller dataset to eliminate shuffling across the cluster:
  ```python
  from pyspark.sql.functions import broadcast
  
  # Broadcast smaller lookup table
  joined_df = segments_df.join(broadcast(weather_lookup_df), "region_id")
  ```
* **Minimize UDFs**: Avoid raw Python User-Defined Functions (UDFs) inside Spark SQL queries where Sedona native SQL functions exist. Python UDFs force serialization and transfer of data between JVM and Python processes, causing huge overheads.
