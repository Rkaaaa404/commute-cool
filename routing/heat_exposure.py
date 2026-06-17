"""Heat Exposure Calculator.

Calculates total sun exposure time and accumulated heat for a route.
Satisfies requirement F-10.
"""


WALKING_SPEED_M_PER_MIN = 80.0  # Average walking speed: 80m/min (~4.8 km/h)


def calculate_heat_exposure(segments: list[dict], hour: int = 12) -> dict:
    """Calculate total heat exposure for a route.

    Args:
        segments: List of segment dicts with 'length_m' and 'shade_ratio'.
        hour: Hour of day (affects shadow calculation).

    Returns:
        Dict with:
        - total_sun_minutes: Minutes walking in direct sunlight.
        - total_shade_minutes: Minutes walking in shade.
        - total_walk_minutes: Total walking time.
        - avg_shade_ratio: Average shade ratio across route.
        - exposure_segments: Per-segment breakdown.
    """
    total_sun_minutes = 0.0
    total_shade_minutes = 0.0
    total_walk_minutes = 0.0
    exposure_details = []

    for seg in segments:
        length_m = seg.get("length_m", 0)
        shade_ratio = seg.get("shade_ratio", 0.2)

        if length_m <= 0:
            continue

        walk_time_min = length_m / WALKING_SPEED_M_PER_MIN
        sun_time = walk_time_min * (1.0 - shade_ratio)
        shade_time = walk_time_min * shade_ratio

        total_sun_minutes += sun_time
        total_shade_minutes += shade_time
        total_walk_minutes += walk_time_min

        exposure_details.append({
            "segment_id": seg.get("segment_id"),
            "walk_time_min": round(walk_time_min, 2),
            "sun_exposure_min": round(sun_time, 2),
            "shade_ratio": shade_ratio,
        })

    avg_shade = (
        total_shade_minutes / total_walk_minutes if total_walk_minutes > 0 else 0
    )

    return {
        "total_sun_minutes": round(total_sun_minutes, 1),
        "total_shade_minutes": round(total_shade_minutes, 1),
        "total_walk_minutes": round(total_walk_minutes, 1),
        "avg_shade_ratio": round(avg_shade, 3),
        "exposure_segments": exposure_details,
    }
