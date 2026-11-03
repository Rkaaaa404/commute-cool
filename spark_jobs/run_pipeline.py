"""COMMUTE-COOL Full Data Pipeline Orchestrator.

Runs the complete Big Data pipeline in sequence:
1. Ingestion: Fetch real data from APIs (Open-Meteo, TomTom, WAQI)
2. OSM Load: Load GeoJSON → PostGIS (segments, buildings, trees)
3. Spark Job 1: NDVI/LST Raster Segmentation
4. Spark Job 2: Dynamic Shadow Modeling
5. Spark Job 4: Traffic & AQI Aggregation
6. Spark Job 3: Thermal Comfort Score (depends on 1, 2, 4)
7. Spark Job 5: Graph Weight Export (depends on 3)

All Spark jobs run in LOCAL mode (no cluster needed for city-scale data).

Usage:
    python -m spark_jobs.run_pipeline                # full pipeline
    python -m spark_jobs.run_pipeline --skip-ingest  # Spark jobs only (reuse data already in DB/HDFS)
"""

import argparse
import os
import sys
import time
import traceback
from datetime import datetime

# Ensure project root is in path
sys.path.insert(0, "/app")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def wait_for_db(max_retries=30, delay=2):
    """Wait until PostgreSQL is accepting connections."""
    import psycopg2
    db_url = os.getenv("DATABASE_URL", "postgresql://cc_user:cc_dev_pass@postgres:5432/commute_cool")

    for i in range(max_retries):
        try:
            conn = psycopg2.connect(db_url)
            conn.close()
            print(f"[Pipeline] Database ready (attempt {i+1})")
            return True
        except Exception:
            if i < max_retries - 1:
                time.sleep(delay)
            else:
                print("[Pipeline] ERROR: Database not available after retries")
                return False
    return False


def step_1_ingest_apis():
    """Fetch current data from external APIs."""
    print("\n" + "=" * 60)
    print("STEP 1: Ingestion - Fetch Real API Data")
    print("=" * 60)

    # Weather (Open-Meteo - no API key needed)
    try:
        from ingestion.weather_collector import fetch_current_weather
        weather = fetch_current_weather()
        print(f"  ✓ Weather: {weather['current']['temperature_2m']}°C")
    except Exception as e:
        print(f"  ✗ Weather fetch failed: {e}")

    # AQI (WAQI)
    try:
        from ingestion.aqi_collector import fetch_aqi
        aqi = fetch_aqi()
        if aqi:
            print(f"  ✓ AQI: {aqi.get('aqi', 'N/A')}")
        else:
            print("  ⚠ AQI: No API token, using defaults")
    except Exception as e:
        print(f"  ✗ AQI fetch failed: {e}")

    # Traffic (TomTom)
    try:
        from ingestion.traffic_collector import fetch_all_traffic
        traffic = fetch_all_traffic()
        print(f"  ✓ Traffic: {len(traffic)} measurement points")
    except Exception as e:
        print(f"  ✗ Traffic fetch failed: {e}")

    # OSM Data (footways, buildings, trees)
    try:
        from ingestion.osm_fetcher import fetch_all
        osm_paths = fetch_all()
        print(f"  ✓ OSM Data: downloaded to {list(osm_paths.values())}")
    except Exception as e:
        print(f"  ✗ OSM fetch failed: {e}")



def upload_to_hdfs_bronze():
    """Upload ingested raw local files to HDFS Bronze layer using PySpark."""
    print("\n" + "=" * 60)
    print("STEP 1.5: Upload Raw Data to HDFS Bronze Layer")
    print("=" * 60)

    from pyspark.sql import SparkSession
    from spark_jobs.config import BRONZE_DIR, RAW_DATA_DIR

    spark = SparkSession.builder.appName("CommuteCool_HDFSUploader").master(os.getenv("SPARK_MASTER_URL", "local[*]")).getOrCreate()

    try:
        categories = ["weather", "aqi", "traffic"]
        for cat in categories:
            local_path = os.path.join(RAW_DATA_DIR, cat)
            hdfs_path = f"{BRONZE_DIR}/{cat}"
            if os.path.exists(local_path) and os.listdir(local_path):
                print(f"  Uploading local {local_path} to HDFS {hdfs_path}...")
                df = spark.read.text(f"file://{os.path.abspath(local_path)}/*.json")
                df.write.mode("overwrite").text(hdfs_path)
                print(f"    ✓ Uploaded {cat} successfully")
            else:
                print(f"  ⚠ No local data found for category: {cat}")
    except Exception as e:
        print(f"  ✗ HDFS Bronze upload failed: {e}")
    finally:
        spark.stop()


def step_2_load_osm():
    """Load OSM GeoJSON data into PostGIS."""
    print("\n" + "=" * 60)
    print("STEP 2: Load OSM Data to PostGIS")
    print("=" * 60)

    from ingestion.osm_loader import load_all
    load_all()

    # Build pgRouting topology
    print("  Building routing topology (pgRouting)...")
    try:
        import psycopg2
        db_url = os.getenv("DATABASE_URL", "postgresql://cc_user:cc_dev_pass@postgres:5432/commute_cool")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute("SELECT build_routing_topology();")
        conn.commit()
        # Check how many nodes were created in the noded network
        cur.execute("SELECT COUNT(*) FROM segments_noded_vertices_pgr")
        node_count = cur.fetchone()[0]
        print(f"  Topology built: {node_count} nodes")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"  Topology build failed: {e}")
        print("  Routing will fall back to nearest-segment approach")


def step_3_ndvi_lst():
    """Run NDVI/LST estimation (can use API-based estimator for speed, or Spark job)."""
    print("\n" + "=" * 60)
    print("STEP 3: Spark Job 1 - NDVI/LST Raster Segmentation")
    print("=" * 60)

    try:
        from spark_jobs.job_raster_segment import run
        run()
    except Exception as e:
        print(f"  Spark Job 1 failed: {e}")
        print("  Falling back to API-based NDVI/LST estimator...")
        traceback.print_exc()
        # Fallback: use the lightweight estimator (still uses real Open-Meteo data)
        from ingestion.ndvi_lst_estimator import estimate_all
        estimate_all()


def step_4_shadow_model():
    """Run shadow modeling Spark job."""
    print("\n" + "=" * 60)
    print("STEP 4: Spark Job 2 - Dynamic Shadow Modeling")
    print("=" * 60)

    try:
        from spark_jobs.job_shadow_model import run
        run()
    except Exception as e:
        print(f"  Spark Job 2 failed: {e}")
        traceback.print_exc()
        print("  Falling back to simplified shadow estimation...")
        _fallback_shadow_estimation()


def _fallback_shadow_estimation():
    """Lightweight shadow estimation without full Spark job.

    Uses PostGIS directly to estimate shade from building/tree proximity.
    """
    import psycopg2
    db_url = os.getenv("DATABASE_URL", "postgresql://cc_user:cc_dev_pass@postgres:5432/commute_cool")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    current_hour = datetime.now().hour
    today = datetime.now().date()

    # Solar elevation approximation for Surabaya
    # Peak at noon (~75°), low morning/evening (~15°)
    if 6 <= current_hour <= 17:
        from spark_jobs.utils.solar_position import get_surabaya_solar_position
        solar = get_surabaya_solar_position(datetime.now())
        elevation = max(solar.elevation, 5.0)
    else:
        elevation = 0

    print(f"  Current hour: {current_hour}, solar elevation: {elevation:.1f}°")

    # Compute shade ratio for current hour based on nearby buildings/trees
    cur.execute("""
        INSERT INTO segment_shadows (segment_id, hour_of_day, shade_ratio, computed_at)
        SELECT
            s.segment_id,
            %s as hour_of_day,
            LEAST(1.0, GREATEST(0.0,
                COALESCE(
                    (SELECT COUNT(*) * LEAST(1.0, AVG(COALESCE(b.height_m, 10.0)) / %s)
                     FROM buildings b
                     WHERE ST_DWithin(b.geom, s.geom, 0.0004)) * 0.15,
                0) +
                COALESCE(
                    (SELECT COUNT(*) * 0.06
                     FROM trees t
                     WHERE ST_DWithin(t.geom, s.geom, 0.0003)),
                0)
            )) as shade_ratio,
            %s as computed_at
        FROM segments s
        ON CONFLICT (segment_id, hour_of_day, computed_at) DO UPDATE
            SET shade_ratio = EXCLUDED.shade_ratio
    """, (current_hour, max(1, elevation * 0.15), today))

    conn.commit()
    print(f"  Computed shadow estimates for {cur.rowcount} segments")
    cur.close()
    conn.close()


def step_5_traffic_aqi():
    """Run traffic & AQI aggregation Spark job."""
    print("\n" + "=" * 60)
    print("STEP 5: Spark Job 4 - Traffic & AQI Aggregation")
    print("=" * 60)

    try:
        from spark_jobs.job_traffic_aqi import run
        run()
    except Exception as e:
        print(f"  Spark Job 4 failed: {e}")
        traceback.print_exc()
        print("  Traffic/AQI data will use raw JSON values in TCS calculation")


def step_6_thermal_comfort():
    """Run Thermal Comfort Score calculation."""
    print("\n" + "=" * 60)
    print("STEP 6: Spark Job 3 - Thermal Comfort Score")
    print("=" * 60)

    try:
        from spark_jobs.job_thermal_comfort import run
        run()
    except Exception as e:
        print(f"  Spark Job 3 failed: {e}")
        traceback.print_exc()
        print("  Falling back to lightweight TCS computation...")
        _fallback_tcs_computation()


def _fallback_tcs_computation():
    """Lightweight TCS computation using PostGIS + raw API data.

    Same formula as Spark job but executed directly in PostgreSQL.
    """
    import psycopg2
    import json

    db_url = os.getenv("DATABASE_URL", "postgresql://cc_user:cc_dev_pass@postgres:5432/commute_cool")
    raw_dir = os.getenv("RAW_DATA_DIR", "./data/raw")

    # Load latest weather
    weather_dir = os.path.join(raw_dir, "weather")
    apparent_temp = 33.0
    if os.path.exists(weather_dir):
        files = sorted([f for f in os.listdir(weather_dir) if f.startswith("weather_")], reverse=True)
        if files:
            with open(os.path.join(weather_dir, files[0])) as f:
                data = json.load(f)
            apparent_temp = data.get("current", {}).get("apparent_temperature", 33.0)

    # Load latest AQI
    aqi_dir = os.path.join(raw_dir, "aqi")
    aqi_value = 50.0
    if os.path.exists(aqi_dir):
        files = sorted([f for f in os.listdir(aqi_dir) if f.startswith("aqi_")], reverse=True)
        if files:
            with open(os.path.join(aqi_dir, files[0])) as f:
                data = json.load(f)
            aqi_value = float(data.get("aqi", 50.0))

    # Load latest traffic
    traffic_dir = os.path.join(raw_dir, "traffic")
    traffic_ratio = 0.3
    if os.path.exists(traffic_dir):
        files = sorted([f for f in os.listdir(traffic_dir) if f.startswith("traffic_")], reverse=True)
        if files:
            with open(os.path.join(traffic_dir, files[0])) as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                ratios = [d.get("congestion_ratio", 0.3) for d in data if d.get("congestion_ratio")]
                traffic_ratio = sum(ratios) / len(ratios) if ratios else 0.3

    print(f"  Data: apparent_temp={apparent_temp}°C, AQI={aqi_value}, traffic={traffic_ratio:.2f}")

    # Normalize scores
    aqi_score = max(0.0, min(1.0, 1.0 - (aqi_value / 150.0)))
    traffic_score = max(0.0, min(1.0, 1.0 - traffic_ratio))
    temp_min, temp_max = 28.0, 45.0

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    current_hour = datetime.now().hour

    cur.execute("""
        INSERT INTO thermal_comfort_scores
            (segment_id, tcs_value, apparent_temp, shade_ratio, aqi_value, traffic_level, computed_at)
        SELECT
            s.segment_id,
            -- TCS = 0.35*shade + 0.30*temp + 0.15*aqi + 0.10*traffic + 0.10*surface
            LEAST(1.0, GREATEST(0.0,
                0.35 * (0.7 * COALESCE(sh.shade_ratio, 0.15) + 0.3 * LEAST(COALESCE(rs.avg_ndvi, 0.15) * 2.0, 1.0))
                + 0.30 * (1.0 - ((%s + 0.4 * COALESCE(rs.avg_lst, 35.0) - 0.4 * %s) - %s) / (%s - %s))
                + 0.15 * %s
                + 0.10 * %s
                + 0.10 * 0.5
            )),
            %s,
            COALESCE(sh.shade_ratio, 0.15),
            %s,
            %s,
            NOW()
        FROM segments s
        LEFT JOIN LATERAL (
            SELECT shade_ratio FROM segment_shadows
            WHERE segment_id = s.segment_id AND hour_of_day = %s
            ORDER BY computed_at DESC LIMIT 1
        ) sh ON true
        LEFT JOIN LATERAL (
            SELECT avg_ndvi, avg_lst FROM segment_raster_scores
            WHERE segment_id = s.segment_id
            ORDER BY computed_at DESC LIMIT 1
        ) rs ON true
        ON CONFLICT (segment_id, computed_at) DO NOTHING
    """, (
        apparent_temp, apparent_temp, temp_min, temp_max, temp_min,
        aqi_score, traffic_score,
        apparent_temp, aqi_value, traffic_ratio,
        current_hour,
    ))

    conn.commit()
    print(f"  Computed TCS for {cur.rowcount} segments")
    cur.close()
    conn.close()


def step_7_graph_weights():
    """Run Graph Weight Export."""
    print("\n" + "=" * 60)
    print("STEP 7: Spark Job 5 - Graph Weight Export")
    print("=" * 60)

    try:
        from spark_jobs.job_graph_weight import run
        run()
    except Exception as e:
        print(f"  Spark Job 5 failed: {e}")
        traceback.print_exc()
        print("  Falling back to direct weight computation...")
        _fallback_edge_weights()


def _fallback_edge_weights():
    """Compute edge weights directly in PostgreSQL."""
    import psycopg2
    db_url = os.getenv("DATABASE_URL", "postgresql://cc_user:cc_dev_pass@postgres:5432/commute_cool")

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO edge_weights (segment_id, base_cost, thermal_penalty, total_cost, valid_from, valid_until)
        SELECT
            s.segment_id,
            COALESCE(s.length_m, 50.0) / 1.33 as base_cost,  -- walking speed 1.33 m/s
            (COALESCE(s.length_m, 50.0) / 1.33) * (1.0 - COALESCE(tcs.tcs_value, 0.5)) * 2.0 as thermal_penalty,
            (COALESCE(s.length_m, 50.0) / 1.33) * (1.0 + (1.0 - COALESCE(tcs.tcs_value, 0.5)) * 2.0) as total_cost,
            NOW() as valid_from,
            NOW() + INTERVAL '1 hour' as valid_until
        FROM segments s
        LEFT JOIN LATERAL (
            SELECT tcs_value FROM thermal_comfort_scores
            WHERE segment_id = s.segment_id
            ORDER BY computed_at DESC LIMIT 1
        ) tcs ON true
        ON CONFLICT DO NOTHING
    """)

    conn.commit()
    print(f"  Computed edge weights for {cur.rowcount} segments")
    cur.close()
    conn.close()


def step_8_ai_simulations():
    """Run AI/ML Predictive Simulations."""
    print("\n" + "=" * 60)
    print("STEP 8: Spark Job 6 - AI/ML Predictive Simulations")
    print("=" * 60)

    try:
        from spark_jobs.job_tcs_predictor import train_and_simulate
        train_and_simulate()
    except Exception as e:
        print(f"  Spark Job 6 failed: {e}")
        traceback.print_exc()
        print("  Falling back to direct simulation estimation...")
        _fallback_ai_simulations()


def _fallback_ai_simulations():
    """Compute AI simulations directly in PostgreSQL (fallback)."""
    import psycopg2
    db_url = os.getenv("DATABASE_URL", "postgresql://cc_user:cc_dev_pass@postgres:5432/commute_cool")

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO tcs_simulations 
            (segment_id, current_tcs, predicted_tcs_green, predicted_tcs_cool, tcs_improvement_green, tcs_improvement_cool)
        SELECT
            t.segment_id,
            t.tcs_value as current_tcs,
            LEAST(1.0, t.tcs_value + 0.12) as predicted_tcs_green,
            LEAST(1.0, t.tcs_value + 0.08) as predicted_tcs_cool,
            LEAST(1.0, t.tcs_value + 0.12) - t.tcs_value as tcs_improvement_green,
            LEAST(1.0, t.tcs_value + 0.08) - t.tcs_value as tcs_improvement_cool
        FROM (
            SELECT DISTINCT ON (segment_id) segment_id, tcs_value
            FROM thermal_comfort_scores
            ORDER BY segment_id, computed_at DESC
        ) t
    """)

    conn.commit()
    print(f"  Computed fallback simulations for {cur.rowcount} segments")
    cur.close()
    conn.close()


def main():
    """Run the full COMMUTE-COOL data pipeline."""
    parser = argparse.ArgumentParser(description="COMMUTE-COOL data pipeline")
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Skip API ingestion, HDFS bronze upload and OSM load; run Spark jobs only",
    )
    args = parser.parse_args()

    start_time = time.time()

    print("╔════════════════════════════════════════════════════════════╗")
    print("║   COMMUTE-COOL Big Data Pipeline                         ║")
    print("║   Apache Spark (Local Mode) + PostGIS + Real APIs        ║")
    print(f"║   {datetime.now().strftime('%Y-%m-%d %H:%M:%S WIB')}                            ║")
    print("╚════════════════════════════════════════════════════════════╝")

    # Wait for DB
    if not wait_for_db():
        sys.exit(1)

    # Run pipeline steps
    if args.skip_ingest:
        print("[Pipeline] --skip-ingest: skipping ingestion, HDFS bronze upload and OSM load")
    else:
        step_1_ingest_apis()
        upload_to_hdfs_bronze()
        step_2_load_osm()
    step_3_ndvi_lst()
    step_4_shadow_model()
    step_5_traffic_aqi()
    step_6_thermal_comfort()
    step_7_graph_weights()
    step_8_ai_simulations()

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"✓ Pipeline complete in {elapsed:.1f}s")
    print("=" * 60)

    # Explicitly exit so that the JVM daemon process doesn't keep the
    # container alive and inadvertently restart the pipeline in a loop.
    sys.exit(0)


if __name__ == "__main__":
    main()
