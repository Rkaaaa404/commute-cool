"""BMKG RSS Monitor - Parse weather alert feed from BMKG.

Monitors: https://www.bmkg.go.id/alerts/nowcast/id
Detects extreme weather warnings for Surabaya region.
No API key needed (public RSS feed).
"""

import json
import os
from datetime import datetime

import feedparser
import requests

from ingestion.config import BMKG_RSS_URL, ALERTS_DIR, SURABAYA_BBOX


def fetch_bmkg_alerts() -> list[dict]:
    """Fetch and parse BMKG weather alerts RSS feed."""
    print("[BMKG] Fetching weather alerts...")

    # BMKG nowcast page - try to get RSS/XML content
    # The nowcast endpoint returns weather warnings
    try:
        response = requests.get(BMKG_RSS_URL, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Error fetching BMKG RSS: {e}")
        return []

    # Parse as RSS feed
    feed = feedparser.parse(response.content)

    alerts = []
    for entry in feed.entries:
        alert = {
            "title": entry.get("title", ""),
            "description": entry.get("summary", entry.get("description", "")),
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "severity": _classify_severity(entry.get("title", "")),
            "timestamp": datetime.now().isoformat(),
        }

        # Check if alert is relevant to Surabaya area
        if _is_surabaya_relevant(alert):
            alert["relevant_to_surabaya"] = True
            alerts.append(alert)

    print(f"  Found {len(alerts)} Surabaya-relevant alerts")

    # Save to raw storage
    os.makedirs(ALERTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_path = os.path.join(ALERTS_DIR, f"alerts_{timestamp}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(alerts, f, indent=2, ensure_ascii=False)

    return alerts


def _classify_severity(title: str) -> str:
    """Classify alert severity from title keywords."""
    title_lower = title.lower()
    if any(w in title_lower for w in ["extreme", "ekstrem", "bahaya"]):
        return "extreme"
    elif any(w in title_lower for w in ["severe", "parah", "berat"]):
        return "severe"
    elif any(w in title_lower for w in ["moderate", "sedang", "waspada"]):
        return "moderate"
    return "minor"


def _is_surabaya_relevant(alert: dict) -> bool:
    """Check if alert mentions Surabaya or East Java."""
    text = f"{alert.get('title', '')} {alert.get('description', '')}".lower()
    keywords = ["surabaya", "jawa timur", "east java", "jatim", "gresik", "sidoarjo"]
    return any(kw in text for kw in keywords)


def get_active_alerts() -> list[dict]:
    """Read the most recent alerts file."""
    if not os.path.exists(ALERTS_DIR):
        return []

    files = sorted(
        [f for f in os.listdir(ALERTS_DIR) if f.startswith("alerts_")],
        reverse=True,
    )
    if not files:
        return []

    with open(os.path.join(ALERTS_DIR, files[0]), "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    alerts = fetch_bmkg_alerts()
    for a in alerts:
        print(f"  [{a['severity'].upper()}] {a['title']}")
