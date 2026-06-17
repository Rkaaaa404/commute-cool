"""Alert Rerouter - Block segments affected by active weather alerts.

Checks BMKG weather alerts and marks affected segments as impassable
or heavily penalized. Satisfies requirement F-11.
"""

from typing import Optional

import psycopg2

from ingestion.config import DATABASE_URL


def get_blocked_segments() -> list[int]:
    """Get segment IDs that fall within active weather alert areas.

    Returns:
        List of segment_ids that should be blocked or heavily penalized.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Find segments that intersect with active weather alert polygons
        cur.execute("""
            SELECT DISTINCT s.segment_id
            FROM segments s
            JOIN weather_alerts wa ON ST_Intersects(s.geom, wa.affected_area)
            WHERE wa.is_active = TRUE
              AND (wa.expires_at IS NULL OR wa.expires_at > NOW())
              AND wa.severity IN ('severe', 'extreme')
        """)

        blocked = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()

        return blocked

    except Exception as e:
        print(f"[AlertRerouter] Error checking alerts: {e}")
        return []


def is_segment_blocked(segment_id: int) -> bool:
    """Check if a specific segment is blocked by weather alert."""
    blocked = get_blocked_segments()
    return segment_id in blocked


def get_active_alert_summary() -> Optional[dict]:
    """Get summary of active weather alerts for Surabaya."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute("""
            SELECT title, severity, description, issued_at, expires_at
            FROM weather_alerts
            WHERE is_active = TRUE
              AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY severity DESC, issued_at DESC
            LIMIT 5
        """)

        alerts = []
        for row in cur.fetchall():
            alerts.append({
                "title": row[0],
                "severity": row[1],
                "description": row[2],
                "issued_at": str(row[3]) if row[3] else None,
                "expires_at": str(row[4]) if row[4] else None,
            })

        cur.close()
        conn.close()

        if not alerts:
            return None

        return {
            "count": len(alerts),
            "most_severe": alerts[0]["severity"],
            "alerts": alerts,
        }

    except Exception as e:
        print(f"[AlertRerouter] Error: {e}")
        return None
