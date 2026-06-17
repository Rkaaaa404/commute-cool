"""Weather Collector - Fetch weather data from Open-Meteo for Surabaya.

Collects: temperature_2m, relative_humidity_2m, wind_speed_10m,
direct_radiation, apparent_temperature.

No API key needed for Open-Meteo (free, open-source).
"""
from __future__ import annotations

import json
import os
from datetime import datetime

import requests

from ingestion.config import (
    OPEN_METEO_BASE_URL,
    SURABAYA_LAT,
    SURABAYA_LNG,
    WEATHER_DIR,
)


def fetch_current_weather() -> dict:
    """Fetch current weather conditions for Surabaya from Open-Meteo."""
    print("[Weather] Fetching current weather from Open-Meteo...")

    params = {
        "latitude": SURABAYA_LAT,
        "longitude": SURABAYA_LNG,
        "current": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "wind_speed_10m",
            "wind_direction_10m",
            "direct_radiation",
            "diffuse_radiation",
            "cloud_cover",
        ]),
        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "wind_speed_10m",
            "direct_radiation",
            "cloud_cover",
        ]),
        "timezone": "Asia/Jakarta",
        "forecast_days": 1,
    }

    response = requests.get(OPEN_METEO_BASE_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    print(f"  Temperature: {data['current']['temperature_2m']}C")
    print(f"  Apparent: {data['current']['apparent_temperature']}C")
    print(f"  Humidity: {data['current']['relative_humidity_2m']}%")
    print(f"  Radiation: {data['current']['direct_radiation']} W/m2")

    # Save to raw storage
    os.makedirs(WEATHER_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    output_path = os.path.join(WEATHER_DIR, f"weather_{timestamp}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"  Saved to: {output_path}")
    return data


def get_latest_weather() -> dict | None:
    """Read the most recent weather file from raw storage."""
    if not os.path.exists(WEATHER_DIR):
        return None

    files = sorted(
        [f for f in os.listdir(WEATHER_DIR) if f.startswith("weather_")],
        reverse=True,
    )
    if not files:
        return None

    with open(os.path.join(WEATHER_DIR, files[0]), "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    fetch_current_weather()
