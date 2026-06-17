"""Configuration for COMMUTE-COOL ingestion layer."""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Surabaya Bounding Box (EPSG:4326) ---
SURABAYA_BBOX = {
    "south": -7.35,
    "west": 112.60,
    "north": -7.20,
    "east": 112.85,
}

# --- Data Lake Paths ---
RAW_DATA_DIR = os.getenv("RAW_DATA_DIR", "./data/raw")
RASTER_DIR = f"{RAW_DATA_DIR}/raster"
OSM_DIR = f"{RAW_DATA_DIR}/osm"
WEATHER_DIR = f"{RAW_DATA_DIR}/weather"
TRAFFIC_DIR = f"{RAW_DATA_DIR}/traffic"
AQI_DIR = f"{RAW_DATA_DIR}/aqi"
ALERTS_DIR = f"{RAW_DATA_DIR}/alerts"
TRANSIT_DIR = f"{RAW_DATA_DIR}/transit"

# --- API Keys & Endpoints ---
OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
BMKG_RSS_URL = "https://www.bmkg.go.id/alerts/nowcast/id"
WAQI_API_TOKEN = os.getenv("WAQI_API_TOKEN", "")
WAQI_BASE_URL = "https://api.waqi.info/feed"
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY", "")
TOMTOM_BASE_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"

# --- Overpass API ---
OVERPASS_API_URL = "https://maps.mail.ru/osm/tools/overpass/api/interpreter"

# --- Database ---
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://cc_user:cc_dev_pass@localhost:5432/commute_cool"
)

# --- Surabaya Center Coordinates (for weather queries) ---
SURABAYA_LAT = -7.2575
SURABAYA_LNG = 112.7521
