"""Spark Job 1: Raster Segmentation (NDVI/LST per street segment).

This job computes proxy NDVI and LST values for each street segment
using tree density (from OSM) and surface temperature estimation.

In production, this would process actual GeoTIFF rasters from
Sentinel-2 (NDVI) and Landsat-8 (LST) via zonal statistics.
For this prototype, we use OSM-based proxy estimation processed
through Spark for distributed computation at scale.

Input: segments table, trees table, buildings table (PostGIS)
Output: segment_raster_scores table
"""

import os
from datetime import date

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import udf, col, lit, count, avg, coalesce
from pyspark.sql.types import FloatType

from sedona.register import SedonaRegistrator
from sedona.utils import SedonaKryoRegistrator

# --- Configuration ---
from spark_jobs.config import JDBC_URL, JDBC_PROPS

# NDVI estimation parameters
MAX_TREES_FOR_MAX_NDVI = 10
NDVI_MIN = 0.10
NDVI_MAX = 0.72

# LST estimation parameters (surface correction from air temp)
SURFACE_TEMP_CORRECTION = {
    "asphalt": 8.0,
    "concrete": 6.0,
    "paving_stones": 4.0,
    "compacted": 3.0,
    "gravel": 2.0,
    "grass": -2.0,
    "unpaved": 2.0,
}
DEFAULT_CORRECTION = 4.0
DEFAULT_AIR_TEMP = 32.0


def create_spark_session() -> SparkSession:
    """Create SparkSession with Sedona for geospatial ops."""
    spark = (
        SparkSession.builder
        .appName("CommuteCool_RasterSegment")
        .master(os.getenv("SPARK_MASTER_URL", "local[*]"))
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config("spark.kryo.registrator", SedonaKryoRegistrator.getName)
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )
    SedonaRegistrator.registerAll(spark)
    return spark


def compute_ndvi_proxy(spark: SparkSession) -> DataFrame:
    """Compute NDVI proxy based on tree density near each segment.

    Uses Sedona spatial join to count trees within 30m buffer of each segment.
    More trees = higher NDVI proxy (validated correlation r>0.7 in urban studies).
    """
    print("  Computing NDVI proxy from tree density...")

    # Load data from PostGIS
    segments_df = spark.read.jdbc(JDBC_URL, "segments", properties=JDBC_PROPS)
    trees_df = spark.read.jdbc(JDBC_URL, "trees", properties=JDBC_PROPS)

    # Register as temp views for Sedona SQL
    segments_df.createOrReplaceTempView("segments")
    trees_df.createOrReplaceTempView("trees")

    # Spatial join: count trees within ~30m (0.0003 degrees) of each segment
    tree_count_df = spark.sql("""
        SELECT
            s.segment_id,
            COUNT(t.tree_id) as tree_count
        FROM segments s
        LEFT JOIN trees t
            ON ST_DWithin(
                ST_GeomFromWKB(s.geom),
                ST_GeomFromWKB(t.geom),
                0.0003
            )
        GROUP BY s.segment_id
    """)

    # Calculate NDVI proxy
    @udf(FloatType())
    def calc_ndvi_proxy(tree_count):
        if tree_count is None:
            tree_count = 0
        ratio = min(tree_count / MAX_TREES_FOR_MAX_NDVI, 1.0)
        return float(NDVI_MIN + ratio * (NDVI_MAX - NDVI_MIN))

    ndvi_df = tree_count_df.withColumn(
        "avg_ndvi", calc_ndvi_proxy(col("tree_count"))
    ).select("segment_id", "avg_ndvi")

    return ndvi_df


def compute_lst_proxy(spark: SparkSession, air_temp: float = DEFAULT_AIR_TEMP) -> DataFrame:
    """Compute LST proxy based on surface material type.

    Different materials absorb/emit heat differently:
    - Asphalt: +8C above air temperature
    - Concrete: +6C
    - Grass: -2C (evapotranspiration cooling)
    """
    print(f"  Computing LST proxy (air temp: {air_temp}C)...")

    segments_df = (
        spark.read.jdbc(JDBC_URL, "segments", properties=JDBC_PROPS)
        .select("segment_id", "surface_type")
    )

    @udf(FloatType())
    def calc_lst(surface_type):
        if surface_type is None:
            correction = DEFAULT_CORRECTION
        else:
            correction = SURFACE_TEMP_CORRECTION.get(surface_type, DEFAULT_CORRECTION)
        return float(air_temp + correction)

    lst_df = segments_df.withColumn(
        "avg_lst", calc_lst(col("surface_type"))
    ).select("segment_id", "avg_lst")

    return lst_df


def run(air_temp: float = None):
    """Main entry point for Raster Segmentation job."""
    if air_temp is None:
        air_temp = DEFAULT_AIR_TEMP

    today = date.today()
    print(f"=== Spark Job 1: Raster Segmentation ({today}) ===")
    print(f"  Mode: OSM proxy estimation (tree density + surface material)")

    spark = create_spark_session()

    try:
        # Compute NDVI and LST proxies
        ndvi_df = compute_ndvi_proxy(spark)
        lst_df = compute_lst_proxy(spark, air_temp)

        # Join NDVI and LST
        result_df = (
            ndvi_df
            .join(lst_df, "segment_id", "outer")
            .withColumn("computed_at", lit(str(today)))
        )

        row_count = result_df.count()
        print(f"  Computed raster scores for {row_count} segments")

        # Write to HDFS Gold (Parquet)
        from spark_jobs.config import GOLD_DIR
        gold_path = f"{GOLD_DIR}/segment_raster_scores"
        print(f"  Writing raster scores to HDFS Gold Parquet: {gold_path}")
        result_df.write.mode("overwrite").parquet(gold_path)

        # Write to PostGIS (Serving Layer)
        print("  Writing raster scores to PostgreSQL...")
        (
            result_df.write
            .mode("overwrite")
            .jdbc(JDBC_URL, "segment_raster_scores", properties=JDBC_PROPS)
        )

        print("=== Raster Segmentation Complete ===")

    finally:
        spark.stop()


if __name__ == "__main__":
    run()
