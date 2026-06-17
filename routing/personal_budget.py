"""Personal Heat Budget Filter.

Validates whether a route's sun exposure is within the user's tolerance.
Satisfies requirement F-07.
"""

# Maximum sun exposure minutes by tolerance level
HEAT_BUDGET_LIMITS = {
    "low": 10,     # Elderly, children, heat-sensitive individuals
    "medium": 20,  # Average adult
    "high": 35,    # Physically active / heat-adapted individuals
}


def check_heat_budget(total_sun_minutes: float, heat_tolerance: str = "medium") -> dict:
    """Check if route sun exposure is within user's heat budget.

    Args:
        total_sun_minutes: Total minutes of direct sun exposure on route.
        heat_tolerance: User tolerance level (low/medium/high).

    Returns:
        Dict with budget status and details.
    """
    budget_limit = HEAT_BUDGET_LIMITS.get(heat_tolerance, 20)
    within_budget = total_sun_minutes <= budget_limit
    remaining = budget_limit - total_sun_minutes

    return {
        "within_budget": within_budget,
        "total_sun_exposure_min": round(total_sun_minutes, 1),
        "budget_limit_min": budget_limit,
        "budget_remaining_min": round(remaining, 1),
        "heat_tolerance": heat_tolerance,
        "warning": None if within_budget else (
            f"Route exceeds heat budget by {abs(remaining):.1f} minutes. "
            f"Consider the shaded route alternative."
        ),
    }


def get_recommended_route(
    shortest_sun_min: float,
    comfortable_sun_min: float,
    heat_tolerance: str = "medium",
) -> str:
    """Recommend which route the user should take.

    Args:
        shortest_sun_min: Sun exposure on shortest route.
        comfortable_sun_min: Sun exposure on comfortable route.
        heat_tolerance: User's tolerance level.

    Returns:
        "shortest" or "most_comfortable"
    """
    budget_limit = HEAT_BUDGET_LIMITS.get(heat_tolerance, 20)

    # If shortest is within budget, recommend it (faster)
    if shortest_sun_min <= budget_limit:
        return "shortest"

    # If comfortable is within budget, recommend it
    if comfortable_sun_min <= budget_limit:
        return "most_comfortable"

    # Both exceed budget - still recommend comfortable (less exposure)
    return "most_comfortable"
