"""Solar Position Calculator.

Computes sun elevation and azimuth angles for a given location and time.
Used by shadow modeling to determine shadow direction and length.

Uses pvlib for accurate solar position calculation.
"""

from datetime import datetime
from typing import NamedTuple

import numpy as np

try:
    import pvlib
    PVLIB_AVAILABLE = True
except ImportError:
    PVLIB_AVAILABLE = False


class SolarPosition(NamedTuple):
    """Solar position angles."""
    elevation: float  # degrees above horizon (0-90)
    azimuth: float    # degrees clockwise from North (0-360)
    zenith: float     # degrees from vertical (0=directly overhead)


def get_solar_position(latitude: float, longitude: float, dt: datetime) -> SolarPosition:
    """Calculate solar elevation and azimuth for given location and time.

    Args:
        latitude: Latitude in degrees (negative for south).
        longitude: Longitude in degrees.
        dt: Datetime object (should be timezone-aware or assumed UTC+7 for Surabaya).

    Returns:
        SolarPosition with elevation, azimuth, and zenith angles.
    """
    if PVLIB_AVAILABLE:
        return _pvlib_solar_position(latitude, longitude, dt)
    else:
        return _simplified_solar_position(latitude, longitude, dt)


def _pvlib_solar_position(lat: float, lng: float, dt: datetime) -> SolarPosition:
    """Accurate solar position using pvlib library."""
    import pandas as pd

    # Ensure timezone (assume WIB = UTC+7 if naive)
    if dt.tzinfo is None:
        import pytz
        dt = pytz.timezone("Asia/Jakarta").localize(dt)

    times = pd.DatetimeIndex([dt])
    solpos = pvlib.solarposition.get_solarposition(times, lat, lng)

    elevation = float(solpos["apparent_elevation"].iloc[0])
    azimuth = float(solpos["azimuth"].iloc[0])
    zenith = float(solpos["apparent_zenith"].iloc[0])

    return SolarPosition(elevation=elevation, azimuth=azimuth, zenith=zenith)


def _simplified_solar_position(lat: float, lng: float, dt: datetime) -> SolarPosition:
    """Simplified solar position calculation (fallback without pvlib).

    Uses basic astronomical formulas. Accuracy: ~1 degree for tropical regions.
    """
    # Day of year
    day_of_year = dt.timetuple().tm_yday

    # Solar declination (Cooper's equation)
    declination = 23.45 * np.sin(np.radians((360 / 365) * (day_of_year - 81)))

    # Hour angle (15 degrees per hour from solar noon)
    # Approximate solar noon based on longitude (Surabaya ~112.75E, timezone UTC+7)
    solar_noon_offset = (lng - 105.0) / 15.0  # hours from timezone meridian
    hour = dt.hour + dt.minute / 60.0
    solar_time = hour + solar_noon_offset
    hour_angle = 15.0 * (solar_time - 12.0)

    # Convert to radians
    lat_rad = np.radians(lat)
    dec_rad = np.radians(declination)
    ha_rad = np.radians(hour_angle)

    # Solar elevation
    sin_elevation = (
        np.sin(lat_rad) * np.sin(dec_rad)
        + np.cos(lat_rad) * np.cos(dec_rad) * np.cos(ha_rad)
    )
    elevation = np.degrees(np.arcsin(np.clip(sin_elevation, -1, 1)))

    # Solar azimuth
    cos_azimuth = (
        (np.sin(dec_rad) - np.sin(lat_rad) * sin_elevation)
        / (np.cos(lat_rad) * np.cos(np.radians(elevation)) + 1e-10)
    )
    azimuth = np.degrees(np.arccos(np.clip(cos_azimuth, -1, 1)))
    if hour_angle > 0:
        azimuth = 360.0 - azimuth

    zenith = 90.0 - elevation

    return SolarPosition(
        elevation=max(0.0, elevation),
        azimuth=azimuth % 360.0,
        zenith=zenith,
    )


# --- Convenience for Surabaya ---

SURABAYA_LAT = -7.2575
SURABAYA_LNG = 112.7521


def get_surabaya_solar_position(dt: datetime) -> SolarPosition:
    """Get solar position for Surabaya at given time."""
    return get_solar_position(SURABAYA_LAT, SURABAYA_LNG, dt)
