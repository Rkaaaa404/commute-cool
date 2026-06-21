"""Spark Job 6: AI/ML Predictive Simulations (Decision Tree / Linear Regression).

Uses PySpark MLlib to train a predictive model on segment environmental features
(NDVI, LST, shade ratio, traffic, AQI) to predict the Thermal Comfort Score (TCS).
Runs scenario simulations for urban planners:
1. Green Scenario: Increase tree canopy/NDVI (+0.25)
2. Cool Pavement Scenario: Reduce surface temperature (-3.5C)
Saves predictions to PostgreSQL serving layer for dashboard analysis.
"""
from __future__ import annotations

import os
from datetime import datetime

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, lit, current_timestamp, when
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import DecisionTreeRegressor, LinearRegression

# --- Configuration ---
from spark_jobs.config import JDBC_URL, JDBC_PROPS, GOLD_DIR


def create_spark_session() -> SparkSession:
    """Create SparkSession with MLlib support."""
    return (
        SparkSession.builder
        .appName("CommuteCool_MLPredictor")
        .master(os.getenv("SPARK_MASTER_URL", "local[*]"))
        .config("spark.driver.memory", "2g")
        .getOrCreate()
    )


def load_dataset(spark: SparkSession) -> DataFrame:
    """Load latest scores from HDFS Gold (or PostGIS fallbacks) and assemble dataset."""
    print("  Loading layers for ML training...")
    
    # 1. Base segments
    segments_df = (
        spark.read.jdbc(JDBC_URL, "segments", properties=JDBC_PROPS)
        .select("segment_id")
    )
    
    # 2. Raster scores (NDVI/LST)
    try:
        raster_df = spark.read.parquet(f"{GOLD_DIR}/segment_raster_scores").select("segment_id", "avg_ndvi", "avg_lst")
    except Exception:
        raster_df = spark.read.jdbc(JDBC_URL, "segment_raster_scores", properties=JDBC_PROPS).select("segment_id", "avg_ndvi", "avg_lst")
        
    # 3. Shadows (Average shade ratio)
    try:
        shadow_df = spark.read.parquet(f"{GOLD_DIR}/segment_shadows").groupBy("segment_id").avg("shade_ratio").withColumnRenamed("avg(shade_ratio)", "avg_shade")
    except Exception:
        shadow_df = spark.read.jdbc(JDBC_URL, "segment_shadows", properties=JDBC_PROPS).groupBy("segment_id").avg("shade_ratio").withColumnRenamed("avg(shade_ratio)", "avg_shade")
        
    # 4. Traffic/AQI
    try:
        traffic_aqi_df = spark.read.parquet(f"{GOLD_DIR}/segment_traffic_aqi").select("segment_id", "congestion_ratio", "aqi_value")
    except Exception:
        traffic_aqi_df = spark.read.jdbc(JDBC_URL, "segments", properties=JDBC_PROPS).select("segment_id").withColumn("congestion_ratio", lit(0.3)).withColumn("aqi_value", lit(50.0))
        
    # 5. TCS Target values (actual values)
    try:
        tcs_df = spark.read.parquet(f"{GOLD_DIR}/thermal_comfort_scores").select("segment_id", "tcs_value")
    except Exception:
        tcs_df = spark.read.jdbc(JDBC_URL, "thermal_comfort_scores", properties=JDBC_PROPS).select("segment_id", "tcs_value")

    # Join dataset
    dataset_df = (
        segments_df
        .join(raster_df, "segment_id", "inner")
        .join(shadow_df, "segment_id", "inner")
        .join(traffic_aqi_df, "segment_id", "inner")
        .join(tcs_df, "segment_id", "inner")
    )
    
    # Fill defaults for nulls
    return dataset_df.na.fill({
        "avg_ndvi": 0.3,
        "avg_lst": 35.0,
        "avg_shade": 0.2,
        "congestion_ratio": 0.3,
        "aqi_value": 50.0,
        "tcs_value": 0.5
    })


def train_and_simulate():
    """Train ML model, perform simulations, and write to PostgreSQL."""
    print("=== Spark Job 6: AI/ML Predictive Simulations ===")
    spark = create_spark_session()
    
    try:
        dataset_df = load_dataset(spark)
        
        row_count = dataset_df.count()
        if row_count == 0:
            print("  [Error] No training data available in Gold layer/PostGIS. Run ingestion & Spark pipeline first.")
            return
            
        print(f"  Total records for ML modeling: {row_count} segments")
        
        # Define features and assemble vectors
        feature_cols = ["avg_ndvi", "avg_lst", "avg_shade", "congestion_ratio", "aqi_value"]
        assembler = VectorAssembler(inputCols=feature_cols, outputCol="features")
        vector_df = assembler.transform(dataset_df)
        
        # Train Decision Tree model (explains target TCS)
        print("  Training Decision Tree Regressor Model...")
        dt = DecisionTreeRegressor(featuresCol="features", labelCol="tcs_value", maxDepth=5)
        model = dt.fit(vector_df)
        
        # Show feature importances
        importances = model.featureImportances
        print("  Model Training Complete.")
        for col_name, imp_val in zip(feature_cols, importances):
            print(f"    Importance - {col_name}: {imp_val:.4f}")
            
        # --- Simulate Scenario 1: Green Scenario (Urban Afforestation) ---
        # What if we increase NDVI tree density by +0.25 (capped at 0.75 max)?
        print("  Simulating Scenario 1: Green City (NDVI +0.25)...")
        green_sim_df = dataset_df.withColumn(
            "avg_ndvi", 
            when(col("avg_ndvi") + 0.25 > 0.72, 0.72).otherwise(col("avg_ndvi") + 0.25)
        )
        green_vector_df = assembler.transform(green_sim_df)
        green_pred_df = model.transform(green_vector_df).withColumnRenamed("prediction", "predicted_tcs_green")
        
        # --- Simulate Scenario 2: Cool Pavement Scenario (Albedo change) ---
        # What if we replace asphalt with cool pavement, reducing LST surface temp by -3.5C?
        print("  Simulating Scenario 2: Cool Pavement (LST -3.5°C)...")
        cool_sim_df = dataset_df.withColumn(
            "avg_lst", 
            when(col("avg_lst") - 3.5 < 28.0, 28.0).otherwise(col("avg_lst") - 3.5)
        )
        cool_vector_df = assembler.transform(cool_sim_df)
        cool_pred_df = model.transform(cool_vector_df).withColumnRenamed("prediction", "predicted_tcs_cool")
        
        # Combine simulations
        simulations_final_df = (
            dataset_df.select(col("segment_id"), col("tcs_value").alias("current_tcs"))
            .join(green_pred_df.select("segment_id", "predicted_tcs_green"), "segment_id", "inner")
            .join(cool_pred_df.select("segment_id", "predicted_tcs_cool"), "segment_id", "inner")
            .withColumn("tcs_improvement_green", col("predicted_tcs_green") - col("current_tcs"))
            .withColumn("tcs_improvement_cool", col("predicted_tcs_cool") - col("current_tcs"))
            .withColumn("simulated_at", current_timestamp())
        )
        
        # Write to PostGIS
        print("  Writing simulation predictions to PostgreSQL...")
        (
            simulations_final_df.write
            .mode("overwrite")
            .jdbc(JDBC_URL, "tcs_simulations", properties=JDBC_PROPS)
        )
        
        print(f"  ✓ Successfully simulated and saved {simulations_final_df.count()} records.")
        print("=== AI/ML Simulations Complete ===")
        
    finally:
        spark.stop()


if __name__ == "__main__":
    train_and_simulate()
