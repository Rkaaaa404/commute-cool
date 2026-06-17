"""Spark Job 4: Traffic & AQI Aggregation per segment.

Geocodes raw traffic (TomTom) and AQI (WAQI) data to the nearest
street segment, producing per-segment congestion and air quality values.

Input: JSON files from data/raw/traffic/ and data/raw/aqi/ + segments (PostGIS)
Output: Internal aggregated data used by Job 3 (TCS calculation)
"""

import json
import os
from datetime import datetime

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import udf, col, lit
from pyspark.sql.types import FloatType, IntegerType, StructType, StructField, StringType, DoubleType

from sedona.register import SedonaRegistrator
from sedona.utils import SedonaKryoRegistrator

# --- Configuration ---
from spark_jobs.config import JDBC_URL, JDBC_PROPS, RAW_DATA_DIR


def create_spark_session() -> SparkSession:
    """Create SparkSession with Sedona."""
    spark = (
        SparkSession.builder
        .appName("CommuteCool_TrafficAQI")
        .master(os.getenv("SPARK_MASTER_URL", "local[*]"))
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config("spark.kryo.registrator", SedonaKryoRegistrator.getName)
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )
    SedonaRegistrator.registerAll(spark)
    return spark


def load_latest_traffic():
    """Read the most recent traffic data from raw storage."""
    traffic_dir = os.path.join(RAW_DATA_DIR, "traffic")
    if not os.path.exists(traffic_dir):
        return []

    files = sorted(
        [f for f in os.listdir(traffic_dir) if f.startswith("traffic_")],
        reverse=True,
    )
    if not files:
        return []

    with open(os.path.join(traffic_dir, files[0]), "r") as f:
        return json.load(f)


def load_latest_aqi() -> dict:
    """Read the most recent AQI data from raw storage."""
    aqi_dir = os.path.join(RAW_DATA_DIR, "aqi")
    if not os.path.exists(aqi_dir):
        return {"aqi": 50}

    files = sorted(
        [f for f in os.listdir(aqi_dir) if f.startswith("aqi_")],
        reverse=True,
    )
    if not files:
        return {"aqi": 50}

    with open(os.path.join(aqi_dir, files[0]), "r") as f:
        return json.load(f)


def aggregate_traffic_to_segments(spark: SparkSession) -> DataFrame:
    """Geocode traffic data points to nearest segments.

    For each traffic measurement point, find the nearest street segment
    and assign the congestion_ratio to that segment.
    Segments without nearby traffic data get a default moderate value.
    """
    print("  Loading traffic data...")
    traffic_data = load_latest_traffic()

    if not traffic_data:
        print("  No traffic data available, using defaults")
        # Return all segments with default congestion
        segments_df = (
            spark.read.jdbc(JDBC_URL, "segments", properties=JDBC_PROPS)
            .select("segment_id")
            .withColumn("congestion_ratio", lit(0.3))
        )
        return segments_df

    # Create DataFrame from traffic points
    traffic_schema = StructType([
        StructField("name", StringType(), True),
        StructField("lat", DoubleType(), True),
        StructField("lng", DoubleType(), True),
        StructField("congestion_ratio", DoubleType(), True),
    ])

    traffic_rows = [
        (d.get("name", ""), d.get("lat", 0), d.get("lng", 0), d.get("congestion_ratio", 0.3))
        for d in traffic_data
        if d.get("lat") and d.get("lng")
    ]

    traffic_df = spark.createDataFrame(traffic_rows, schema=traffic_schema)
    traffic_df.createOrReplaceTempView("traffic_points")

    # Load segments
    segments_df = spark.read.jdbc(JDBC_URL, "segments", properties=JDBC_PROPS)
    segments_df.createOrReplaceTempView("segments")

    # For each segment, find the nearest traffic point and assign its congestion
    # Using a cross join with distance filter (simplified approach)
    # In production, would use Sedona spatial join with KNN
    result_df = spark.sql("""
        SELECT
            s.segment_id,
            COALESCE(
                (SELECT t.congestion_ratio
                 FROM traffic_points t
                 ORDER BY ST_Distance(
                     ST_Point(t.lng, t.lat),
                     ST_Centroid(ST_GeomFromWKB(s.geom))
                 )
                 LIMIT 1),
                0.3
            ) as congestion_ratio
        FROM segments s
    """)

    return result_df


def aggregate_aqi_to_segments(spark: SparkSession) -> float:
    """Get city-wide AQI value.

    Since AQI stations in Surabaya are sparse, we apply a uniform
    city-wide AQI value to all segments (simplified approach).
    """
    aqi_data = load_latest_aqi()
    aqi_value = float(aqi_data.get("aqi", 50))
    print(f"  City-wide AQI: {aqi_value}")
    return aqi_value


def run():
    """Main entry point for Traffic & AQI Aggregation job."""
    print("=== Spark Job 4: Traffic & AQI Aggregation ===")
    spark = create_spark_session()

    try:
        traffic_df = aggregate_traffic_to_segments(spark)
        aqi_value = aggregate_aqi_to_segments(spark)

        # Add AQI as uniform column
        result_df = traffic_df.withColumn("aqi_value", lit(aqi_value))

        count = result_df.count()
        print(f"  Aggregated traffic+AQI for {count} segments")

        # Write to a staging table or pass directly to Job 3
        (
            result_df.write
            .mode("overwrite")
            .jdbc(JDBC_URL, "segment_traffic_aqi_staging", properties=JDBC_PROPS)
        )

        print("=== Traffic & AQI Aggregation Complete ===")
    finally:
        spark.stop()


if __name__ == "__main__":
    run()
