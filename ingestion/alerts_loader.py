"""BMKG Alerts Loader - Load raw weather alerts JSON into PostgreSQL.

Reads alerts from Bronze layer (JSON files) and syncs them to the weather_alerts table
with PostGIS spatial geometries for the Surabaya bounding box.
"""

import json
import os
import psycopg2
from datetime import datetime, timedelta

from ingestion.config import ALERTS_DIR, DATABASE_URL


def load_alerts_to_db():
    """Load the latest weather alerts from JSON files into the database."""
    print("[AlertsLoader] Loading weather alerts to PostgreSQL...")

    if not os.path.exists(ALERTS_DIR):
        print("  Alerts directory does not exist yet.")
        return

    files = sorted(
        [f for f in os.listdir(ALERTS_DIR) if f.startswith("alerts_")],
        reverse=True,
    )
    if not files:
        print("  No raw weather alert files found.")
        return

    latest_file = os.path.join(ALERTS_DIR, files[0])
    print(f"  Reading alerts from: {latest_file}")

    with open(latest_file, "r", encoding="utf-8") as f:
        alerts = json.load(f)

    if not alerts:
        print("  No active alerts found in the file.")
        return

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Mark all old alerts as inactive
        cur.execute("UPDATE weather_alerts SET is_active = FALSE WHERE is_active = TRUE;")

        inserted = 0
        for alert in alerts:
            title = alert.get("title", "")
            description = alert.get("description", "")
            severity = alert.get("severity", "minor")

            # Parse published time or fallback to now
            published_str = alert.get("published", "")
            try:
                # Common RSS date format parser placeholder or parse string
                # e.g. "Sat, 20 Jun 2026 12:00:00 GMT"
                issued_at = datetime.now()
            except Exception:
                issued_at = datetime.now()

            # Set expiration to 3 hours after issue for nowcasts
            expires_at = issued_at + timedelta(hours=3)

            # Insert alert and assign Surabaya BBox as affected area
            # Surabaya coordinates: south: -7.35, west: 112.60, north: -7.20, east: 112.85
            cur.execute("""
                INSERT INTO weather_alerts 
                    (title, description, severity, affected_area, issued_at, expires_at, is_active)
                VALUES (
                    %s, %s, %s,
                    ST_SetSRID(ST_MakeEnvelope(112.60, -7.35, 112.85, -7.20), 4326),
                    %s, %s, TRUE
                )
            """, (title, description, severity, issued_at, expires_at))
            inserted += 1

        conn.commit()
        cur.close()
        print(f"  ✓ Successfully loaded {inserted} active alerts into PostgreSQL.")

    except Exception as e:
        print(f"  ✗ Error loading weather alerts: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    load_alerts_to_db()
