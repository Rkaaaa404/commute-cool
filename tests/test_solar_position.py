"""Unit tests for solar position calculator."""

from datetime import datetime
from spark_jobs.utils.solar_position import (
    get_solar_position,
    get_surabaya_solar_position,
    _simplified_solar_position,
)

# Surabaya coordinates
LAT = -7.2575
LNG = 112.7521


def test_midday_elevation_tropical():
    """At tropical latitude, midday sun should be high (>60 degrees)."""
    dt = datetime(2026, 6, 15, 12, 0, 0)
    pos = _simplified_solar_position(LAT, LNG, dt)
    assert pos.elevation > 50.0, f"Expected >50, got {pos.elevation}"
    assert pos.elevation < 90.0


def test_early_morning_low_elevation():
    """At 6 AM, sun should be near horizon."""
    dt = datetime(2026, 6, 15, 6, 0, 0)
    pos = _simplified_solar_position(LAT, LNG, dt)
    assert pos.elevation < 30.0, f"Expected <30, got {pos.elevation}"
    assert pos.elevation >= 0.0


def test_night_time_zero_elevation():
    """At midnight, sun should be below horizon."""
    dt = datetime(2026, 6, 15, 0, 0, 0)
    pos = _simplified_solar_position(LAT, LNG, dt)
    assert pos.elevation <= 0.0


def test_azimuth_range():
    """Azimuth should be 0-360 degrees."""
    dt = datetime(2026, 6, 15, 10, 0, 0)
    pos = _simplified_solar_position(LAT, LNG, dt)
    assert 0.0 <= pos.azimuth <= 360.0


def test_surabaya_convenience_function():
    """Test the Surabaya-specific convenience function."""
    dt = datetime(2026, 6, 15, 12, 0, 0)
    pos = get_surabaya_solar_position(dt)
    assert pos.elevation > 0
    assert 0 <= pos.azimuth <= 360


def test_zenith_complement():
    """Zenith should be 90 - elevation."""
    dt = datetime(2026, 6, 15, 12, 0, 0)
    pos = _simplified_solar_position(LAT, LNG, dt)
    assert abs(pos.zenith - (90.0 - pos.elevation)) < 0.01
