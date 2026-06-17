"""Spark Job 3: Thermal Comfort Score Calculation.

Joins all data layers (raster scores, shadow ratios, weather, AQI, traffic)
and computes the composite TCS per street segment.

Input: segment_raster_scores, segment_shadows, weather JSON, AQI JSON, traffic JSON
Output: thermal_comfort_scores table
"""

import json
import os
from datetime import datetime, date

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import udf, col, lit, coalesce, current_timestamp
from pyspark.sql.types import FloatType

from sedona.register import SedonaRegistrator
from sedona.utils import SedonaKryoRegistrator

from spark_jobs.utils.normalization import (
    normalize_shade,
    normalize_temperature,
    normalize_aqi,
    normalize_traffic,
    normalize_surface,
    compute_tcs,
)

# --- Configuration ---
from spark_jobs.config import JDBC_URL, JDBC_PROPS, RAW_DATA_DIR


def create_spark_session() -> SparkSession:
    """Create SparkSession with Sedona."""
    spark = (
        SparkSession.builder
        .appName("CommuteCool_ThermalComfort")
        .master(os.getenv("SPARK_MASTER_URL", "local[*]"))
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config("spark.kryo.registrator", SedonaKryoRegistrator.getName)
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )
    SedonaRegistrator.registerAll(spark)
    return spark


def load_segment_base(spark: SparkSession) -> DataFrame:
    """Load segments with surface info."""
    return (
        spark.read.jdbc(JDBC_URL, "segments", properties=JDBC_PROPS)
        .select("segment_id", "surface_type", "smoothness")
    )


def load_raster_scores(spark: SparkSession) -> DataFrame:
    """Load latest NDVI/LST scores per segment."""
    query = """
    (SELECT DISTINCT ON (segment_id)
        segment_id, avg_ndvi, avg_lst
    FROM segment_raster_scores
    ORDER BY segment_id, computed_at DESC) as latest_raster
    """
    return spark.read.jdbc(JDBC_URL, query, properties=JDBC_PROPS)


def load_shadow_scores(spark: SparkSession, hour: int) -> DataFrame:
    """Load shadow ratios for specific hour."""
    query = f"""
    (SELECT DISTINCT ON (segment_id)
        segment_id, shade_ratio
    FROM segment_shadows
    WHERE hour_of_day = {hour}
    ORDER BY segment_id, computed_at DESC) as latest_shadow
    """
    return spark.read.jdbc(JDBC_URL, query, properties=JDBC_PROPS)


def get_current_weather() -> dict:
    """Read latest weather data from raw storage."""
    weather_dir = os.path.join(RAW_DATA_DIR, "weather")
    if not os.path.exists(weather_dir):
        return {"apparent_temperature": 33.0, "relative_humidity_2m": 70.0}

    files = sorted(
        [f for f in os.listdir(weather_dir) if f.startswith("weather_")],
        reverse=True,
    )
    if not files:
        return {"apparent_temperature": 33.0, "relative_humidity_2m": 70.0}

    with open(os.path.join(weather_dir, files[0]), "r") as f:
        data = json.load(f)

    current = data.get("current", {})
    return {
        "apparent_temperature": current.get("apparent_temperature", 33.0),
        "temperature_2m": current.get("temperature_2m", 32.0),
        "relative_humidity_2m": current.get("relative_humidity_2m", 70.0),
        "direct_radiation": current.get("direct_radiation", 500.0),
    }


def get_current_aqi() -> float:
    """Read latest AQI value from raw storage."""
    aqi_dir = os.path.join(RAW_DATA_DIR, "aqi")
    if not os.path.exists(aqi_dir):
        return 50.0  # default moderate

    files = sorted(
        [f for f in os.listdir(aqi_dir) if f.startswith("aqi_")],
        reverse=True,
    )
    if not files:
        return 50.0

    with open(os.path.join(aqi_dir, files[0]), "r") as f:
        data = json.load(f)

    return float(data.get("aqi", 50.0))


def get_avg_traffic() -> float:
    """Read average traffic congestion from raw storage."""
    traffic_dir = os.path.join(RAW_DATA_DIR, "traffic")
    if not os.path.exists(traffic_dir):
        return 0.3  # default moderate

    files = sorted(
        [f for f in os.listdir(traffic_dir) if f.startswith("traffic_")],
        reverse=True,
    )
    if not files:
        return 0.3

    with open(os.path.join(traffic_dir, files[0]), "r") as f:
        data = json.load(f)

    if isinstance(data, list) and data:
        ratios = [d.get("congestion_ratio", 0.3) for d in data if d.get("congestion_ratio")]
        return sum(ratios) / len(ratios) if ratios else 0.3

    return 0.3


def compute_thermal_comfort(spark: SparkSession, hour: int = None):
    """Compute TCS for all segments."""
    if hour is None:
        hour = datetime.now().hour

    print(f"  Loading data layers...")
    segments_df = load_segment_base(spark)
    raster_df = load_raster_scores(spark)
    shadow_df = load_shadow_scores(spark, hour)

    # Get environmental conditions
    weather = get_current_weather()
    aqi_value = get_current_aqi()
    traffic_ratio = get_avg_traffic()

    apparent_temp = weather["apparent_temperature"]

    print(f"  Weather: apparent_temp={apparent_temp}C, AQI={aqi_value}, traffic={traffic_ratio:.2f}")

    # Join all layers
    joined_df = (
        segments_df
        .join(raster_df, "segment_id", "left")
        .join(shadow_df, "segment_id", "left")
    )

    # Broadcast environmental constants
    b_apparent_temp = apparent_temp
    b_aqi = aqi_value
    b_traffic = traffic_ratio

    @udf(FloatType())
    def calc_tcs(shade_ratio, avg_ndvi, avg_lst, surface_type, smoothness):
        """Calculate TCS for a single segment."""
        # Handle nulls with defaults
        _shade = float(shade_ratio) if shade_ratio is not None else 0.2
        _ndvi = float(avg_ndvi) if avg_ndvi is not None else 0.3
        _lst = float(avg_lst) if avg_lst is not None else 35.0
        _surface = surface_type if surface_type else "asphalt"
        _smooth = smoothness if smoothness else "good"

        shade_score = normalize_shade(_shade, _ndvi)
        temp_score = normalize_temperature(b_apparent_temp, _lst)
        aqi_score = normalize_aqi(b_aqi)
        traffic_score = normalize_traffic(b_traffic)
        surface_score = normalize_surface(_surface, _smooth)

        return float(compute_tcs(shade_score, temp_score, aqi_score, traffic_score, surface_score))

    # Compute TCS
    result_df = joined_df.withColumn(
        "tcs_value",
        calc_tcs(
            col("shade_ratio"),
            col("avg_ndvi"),
            col("avg_lst"),
            col("surface_type"),
            col("smoothness"),
        )
    ).select(
        col("segment_id"),
        col("tcs_value"),
        lit(apparent_temp).alias("apparent_temp"),
        coalesce(col("shade_ratio"), lit(0.2)).alias("shade_ratio"),
        lit(aqi_value).alias("aqi_value"),
        lit(traffic_ratio).alias("traffic_level"),
        current_timestamp().alias("computed_at"),
    )

    return result_df


def write_results(df: DataFrame):
    """Write TCS results to PostGIS."""
    (
        df.write
        .mode("append")
        .jdbc(JDBC_URL, "thermal_comfort_scores", properties=JDBC_PROPS)
    )


def run(hour: int = None):
    """Main entry point for Thermal Comfort Score job."""
    if hour is None:
        hour = datetime.now().hour

    print(f"=== Spark Job 3: Thermal Comfort Score (hour={hour}) ===")
    spark = create_spark_session()

    try:
        result_df = compute_thermal_comfort(spark, hour)
        count = result_df.count()
        print(f"  Computed TCS for {count} segments")

        write_results(result_df)
        print("=== Thermal Comfort Score Complete ===")
    finally:
        spark.stop()


if __name__ == "__main__":
    run()
