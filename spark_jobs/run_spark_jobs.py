"""Run Spark Jobs only, skipping raw ingestion and OSM loading."""

import os
import sys
import time
from datetime import datetime

# Ensure project root is in path
sys.path.insert(0, "/app")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    start_time = time.time()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║   COMMUTE-COOL Spark Jobs runner                           ║")
    print("║   Running Jobs 1, 2, 4, 3, 5, 6 in sequence                ║")
    print("╚════════════════════════════════════════════════════════════╝")

    from spark_jobs.job_raster_segment import run as run_raster
    from spark_jobs.job_shadow_model import run as run_shadow
    from spark_jobs.job_traffic_aqi import run as run_traffic
    from spark_jobs.job_thermal_comfort import run as run_thermal
    from spark_jobs.job_graph_weight import run as run_weights
    from spark_jobs.job_tcs_predictor import train_and_simulate as run_simulations

    print("\n>>> Running Job 1: Raster Segmentation")
    run_raster()

    print("\n>>> Running Job 2: Dynamic Shadow Modeling")
    run_shadow()

    print("\n>>> Running Job 4: Traffic & AQI Aggregation")
    run_traffic()

    print("\n>>> Running Job 3: Thermal Comfort Score")
    run_thermal()

    print("\n>>> Running Job 5: Graph Weight Export")
    run_weights()

    print("\n>>> Running Job 6: AI/ML Predictive Simulations")
    run_simulations()

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"✓ Spark Jobs complete in {elapsed:.1f}s")
    print("=" * 60)

if __name__ == "__main__":
    main()
