"""Score Normalization Helpers.

Normalizes raw environmental values into 0.0-1.0 comfort scores
for use in the Thermal Comfort Score formula.
"""


def normalize_shade(shade_ratio: float, ndvi: float) -> float:
    """Shade comfort score. Higher shade = more comfortable.

    Args:
        shade_ratio: 0.0-1.0 from shadow model.
        ndvi: 0.0-1.0 from satellite imagery.

    Returns:
        Normalized score 0.0-1.0.
    """
    # NDVI contribution capped (values > 0.5 are dense vegetation)
    ndvi_component = min(ndvi * 2.0, 1.0)
    combined = 0.7 * shade_ratio + 0.3 * ndvi_component
    return max(0.0, min(1.0, combined))


def normalize_temperature(apparent_temp: float, lst: float) -> float:
    """Temperature comfort score. Lower temp = more comfortable.

    Range calibrated for Surabaya: 28C (comfortable) to 45C (extreme).

    Args:
        apparent_temp: Apparent temperature in Celsius.
        lst: Land Surface Temperature in Celsius.

    Returns:
        Normalized score 0.0-1.0 (1.0 = comfortable, 0.0 = extreme heat).
    """
    TEMP_MIN = 28.0  # comfortable threshold
    TEMP_MAX = 45.0  # extreme heat threshold

    temp_combined = 0.6 * apparent_temp + 0.4 * lst
    score = 1.0 - (temp_combined - TEMP_MIN) / (TEMP_MAX - TEMP_MIN)
    return max(0.0, min(1.0, score))


def normalize_aqi(aqi_value: float) -> float:
    """Air quality comfort score. Lower AQI = more comfortable.

    AQI scale: 0-50 Good, 51-100 Moderate, 101-150 Unhealthy for Sensitive,
    151+ Unhealthy.

    Args:
        aqi_value: AQI index value (0-500+).

    Returns:
        Normalized score 0.0-1.0.
    """
    AQI_MAX = 150.0  # Beyond this = 0.0 comfort
    score = 1.0 - (aqi_value / AQI_MAX)
    return max(0.0, min(1.0, score))


def normalize_traffic(congestion_ratio: float) -> float:
    """Traffic comfort score. Less congestion = more comfortable.

    Congestion affects pedestrians via noise, exhaust fumes, and danger.

    Args:
        congestion_ratio: 0.0-1.0 (0=free flow, 1=complete gridlock).

    Returns:
        Normalized score 0.0-1.0.
    """
    return max(0.0, min(1.0, 1.0 - congestion_ratio))


def normalize_surface(surface_type: str, smoothness: str) -> float:
    """Surface quality comfort score.

    Args:
        surface_type: OSM surface tag value.
        smoothness: OSM smoothness tag value.

    Returns:
        Normalized score 0.0-1.0.
    """
    surface_scores = {
        "asphalt": 0.9,
        "paving_stones": 0.85,
        "concrete": 0.8,
        "concrete:plates": 0.75,
        "sett": 0.7,
        "compacted": 0.6,
        "fine_gravel": 0.5,
        "gravel": 0.4,
        "unpaved": 0.3,
        "ground": 0.3,
        "dirt": 0.2,
        "sand": 0.2,
        "grass": 0.4,
    }

    smoothness_scores = {
        "excellent": 1.0,
        "good": 0.8,
        "intermediate": 0.6,
        "bad": 0.3,
        "very_bad": 0.1,
        "horrible": 0.05,
    }

    s = surface_scores.get(surface_type, 0.5) if surface_type else 0.5
    sm = smoothness_scores.get(smoothness, 0.5) if smoothness else 0.5
    return 0.5 * s + 0.5 * sm


def compute_tcs(
    shade_score: float,
    temp_score: float,
    aqi_score: float,
    traffic_score: float,
    surface_score: float,
) -> float:
    """Compute final Thermal Comfort Score.

    Weighted combination of all sub-scores.

    Args:
        shade_score: Normalized shade comfort (0-1).
        temp_score: Normalized temperature comfort (0-1).
        aqi_score: Normalized AQI comfort (0-1).
        traffic_score: Normalized traffic comfort (0-1).
        surface_score: Normalized surface comfort (0-1).

    Returns:
        TCS value 0.0 (extremely uncomfortable) to 1.0 (very comfortable).
    """
    W_SHADE = 0.35
    W_TEMP = 0.30
    W_AQI = 0.15
    W_TRAFFIC = 0.10
    W_SURFACE = 0.10

    tcs = (
        W_SHADE * shade_score
        + W_TEMP * temp_score
        + W_AQI * aqi_score
        + W_TRAFFIC * traffic_score
        + W_SURFACE * surface_score
    )
    return max(0.0, min(1.0, tcs))
