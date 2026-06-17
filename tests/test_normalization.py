"""Unit tests for normalization utility functions."""

from spark_jobs.utils.normalization import (
    normalize_shade,
    normalize_temperature,
    normalize_aqi,
    normalize_traffic,
    normalize_surface,
    compute_tcs,
)


def test_normalize_shade_full():
    """Full shade should give score close to 1.0."""
    score = normalize_shade(1.0, 0.8)
    assert 0.9 <= score <= 1.0


def test_normalize_shade_none():
    """No shade should give low score."""
    score = normalize_shade(0.0, 0.0)
    assert score == 0.0


def test_normalize_shade_bounds():
    """Output should always be 0-1."""
    for shade in [0.0, 0.25, 0.5, 0.75, 1.0]:
        for ndvi in [0.0, 0.3, 0.6, 1.0]:
            score = normalize_shade(shade, ndvi)
            assert 0.0 <= score <= 1.0


def test_normalize_temperature_comfortable():
    """28C should be max comfort."""
    score = normalize_temperature(28.0, 28.0)
    assert score == 1.0


def test_normalize_temperature_extreme():
    """45C should be zero comfort."""
    score = normalize_temperature(45.0, 45.0)
    assert score == 0.0


def test_normalize_temperature_typical_surabaya():
    """Typical Surabaya 33-35C should be moderate."""
    score = normalize_temperature(34.0, 36.0)
    assert 0.2 <= score <= 0.65


def test_normalize_aqi_good():
    """AQI 0-50 should be high comfort."""
    score = normalize_aqi(25.0)
    assert score > 0.8


def test_normalize_aqi_unhealthy():
    """AQI 150+ should be zero comfort."""
    score = normalize_aqi(150.0)
    assert score == 0.0


def test_normalize_traffic_free_flow():
    """No congestion = comfortable."""
    score = normalize_traffic(0.0)
    assert score == 1.0


def test_normalize_traffic_gridlock():
    """Full congestion = uncomfortable."""
    score = normalize_traffic(1.0)
    assert score == 0.0


def test_normalize_surface_asphalt_good():
    """Good asphalt should score high."""
    score = normalize_surface("asphalt", "good")
    assert score > 0.8


def test_normalize_surface_unpaved_bad():
    """Unpaved + bad smoothness should score low."""
    score = normalize_surface("unpaved", "bad")
    assert score < 0.4


def test_compute_tcs_all_perfect():
    """All perfect sub-scores should give TCS = 1.0."""
    tcs = compute_tcs(1.0, 1.0, 1.0, 1.0, 1.0)
    assert abs(tcs - 1.0) < 1e-9


def test_compute_tcs_all_worst():
    """All zero sub-scores should give TCS = 0.0."""
    tcs = compute_tcs(0.0, 0.0, 0.0, 0.0, 0.0)
    assert tcs == 0.0


def test_compute_tcs_bounds():
    """TCS should always be 0-1."""
    import random
    random.seed(42)
    for _ in range(100):
        scores = [random.random() for _ in range(5)]
        tcs = compute_tcs(*scores)
        assert 0.0 <= tcs <= 1.0


def test_compute_tcs_weights_sum_to_one():
    """Verify weight proportions are correct."""
    # If all sub-scores are equal, TCS should equal that value
    tcs = compute_tcs(0.5, 0.5, 0.5, 0.5, 0.5)
    assert abs(tcs - 0.5) < 0.001
