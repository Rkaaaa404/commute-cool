"""Spark Job 5: Graph Weight Export.

Transforms Thermal Comfort Scores into routing edge weights (penalties)
for the GraphHopper routing engine.

Input: thermal_comfort_scores table
Output: edge_weights table + JSON export file
"""

import json
import os
from datetime import datetime, timedelta

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import udf, col, lit, current_timestamp
from pyspark.sql.types import FloatType

from sedona.register import SedonaRegistrator
from sedona.utils import SedonaKryoRegistrator

# --- Configuration ---
from spark_jobs.config import JDBC_URL, JDBC_PROPS

MAX_PENALTY_MULTIPLIER = 3.0  # Max penalty: 3x base cost for TCS=0
WEIGHT_VALIDITY_HOURS = 1  # Weights valid for 1 hour

OUTPUT_DIR = os.getenv("GRAPH_WEIGHT_DIR", "./data/routing_weights")


def create_spark_session() -> SparkSession:
    """Create SparkSession."""
    spark = (
        SparkSession.builder
        .appName("CommuteCool_GraphWeight")
        .master(os.getenv("SPARK_MASTER_URL", "local[*]"))
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config("spark.kryo.registrator", SedonaKryoRegistrator.getName)
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )
    SedonaRegistrator.registerAll(spark)
    return spark


def load_latest_tcs(spark: SparkSession) -> DataFrame:
    """Load most recent TCS per segment."""
    query = """
    (SELECT DISTINCT ON (segment_id)
        segment_id, tcs_value
    FROM thermal_comfort_scores
    ORDER BY segment_id, computed_at DESC) as latest_tcs
    """
    return spark.read.jdbc(JDBC_URL, query, properties=JDBC_PROPS)


def load_segment_lengths(spark: SparkSession) -> DataFrame:
    """Load segment base costs (length-based)."""
    return (
        spark.read.jdbc(JDBC_URL, "segments", properties=JDBC_PROPS)
        .select("segment_id", "length_m")
    )


def compute_edge_weights(spark: SparkSession) -> DataFrame:
    """Compute routing weights from TCS values."""
    tcs_df = load_latest_tcs(spark)
    segments_df = load_segment_lengths(spark)

    joined_df = segments_df.join(tcs_df, "segment_id", "left")

    now = datetime.utcnow()
    valid_from = now
    valid_until = now + timedelta(hours=WEIGHT_VALIDITY_HOURS)

    @udf(FloatType())
    def calc_base_cost(length_m):
        """Base cost = walking time in seconds (80m/min = 1.33m/s)."""
        if length_m is None or length_m <= 0:
            return 0.0
        return float(length_m / 1.33)

    @udf(FloatType())
    def calc_thermal_penalty(tcs_value, base_cost):
        """Thermal penalty based on TCS.

        TCS=1.0 → multiplier=1.0 (no penalty)
        TCS=0.0 → multiplier=3.0 (max penalty)
        """
        if tcs_value is None:
            tcs_value = 0.5  # default moderate
        if base_cost is None or base_cost <= 0:
            return 0.0

        multiplier = 1.0 + (1.0 - tcs_value) * (MAX_PENALTY_MULTIPLIER - 1.0)
        penalty = base_cost * (multiplier - 1.0)
        return float(penalty)

    result_df = joined_df.withColumn(
        "base_cost", calc_base_cost(col("length_m"))
    ).withColumn(
        "thermal_penalty", calc_thermal_penalty(col("tcs_value"), col("base_cost"))
    ).withColumn(
        "total_cost", col("base_cost") + col("thermal_penalty")
    ).select(
        col("segment_id"),
        col("base_cost"),
        col("thermal_penalty"),
        col("total_cost"),
        lit(str(valid_from)).alias("valid_from"),
        lit(str(valid_until)).alias("valid_until"),
    )

    return result_df


def write_to_db(df: DataFrame):
    """Write edge weights to PostGIS."""
    (
        df.write
        .mode("overwrite")  # Replace old weights
        .jdbc(JDBC_URL, "edge_weights", properties=JDBC_PROPS)
    )


def export_to_json(df: DataFrame):
    """Export edge weights as JSON for GraphHopper custom model."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Collect to driver (acceptable for city-scale data)
    rows = df.collect()

    weights = {}
    for row in rows:
        weights[str(row["segment_id"])] = {
            "base_cost": row["base_cost"],
            "thermal_penalty": row["thermal_penalty"],
            "total_cost": row["total_cost"],
        }

    output_path = os.path.join(OUTPUT_DIR, "edge_weights.json")
    with open(output_path, "w") as f:
        json.dump(weights, f)

    print(f"  Exported {len(weights)} edge weights to {output_path}")
    return output_path


def run():
    """Main entry point for Graph Weight Export job."""
    print("=== Spark Job 5: Graph Weight Export ===")
    spark = create_spark_session()

    try:
        result_df = compute_edge_weights(spark)
        count = result_df.count()
        print(f"  Computed weights for {count} edges")

        write_to_db(result_df)
        print("  Written to edge_weights table")

        export_to_json(result_df)
        print("=== Graph Weight Export Complete ===")
    finally:
        spark.stop()


if __name__ == "__main__":
    run()
