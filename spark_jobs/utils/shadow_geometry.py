"""Shadow Geometry Projection Functions.

Projects shadow polygons from buildings and trees based on solar position.
Used by Spark Job 2 (Shadow Modeling).
"""

import math
from typing import Optional

import numpy as np
from shapely.geometry import Polygon, Point, LineString, MultiPolygon
from shapely.affinity import translate
from shapely.ops import unary_union


def compute_shadow_length(obj_height: float, solar_elevation: float) -> float:
    """Calculate shadow length from object height and sun elevation.

    Args:
        obj_height: Height of object in meters.
        solar_elevation: Sun elevation angle in degrees above horizon.

    Returns:
        Shadow length in meters. Returns 0 if sun is at/below horizon.
    """
    if solar_elevation <= 0:
        return 0.0
    if solar_elevation >= 90:
        return 0.0  # Sun directly overhead, no shadow

    return obj_height / math.tan(math.radians(solar_elevation))


def compute_shadow_direction(solar_azimuth: float) -> float:
    """Shadow direction is opposite to sun azimuth.

    Args:
        solar_azimuth: Sun azimuth in degrees clockwise from North.

    Returns:
        Shadow direction in degrees clockwise from North.
    """
    return (solar_azimuth + 180.0) % 360.0


def _direction_to_dx_dy(direction_degrees: float, distance_m: float, latitude: float):
    """Convert direction and distance to dx/dy in degrees.

    Approximate conversion for small distances near equator.
    At Surabaya latitude (~7 S), 1 degree lat ~ 111km, 1 degree lng ~ 110km.
    """
    meters_per_deg_lat = 111320.0
    meters_per_deg_lng = 111320.0 * math.cos(math.radians(latitude))

    # Convert direction from North-clockwise to standard math angle
    angle_rad = math.radians(90.0 - direction_degrees)

    dx_m = distance_m * math.cos(angle_rad)
    dy_m = distance_m * math.sin(angle_rad)

    dx_deg = dx_m / meters_per_deg_lng
    dy_deg = dy_m / meters_per_deg_lat

    return dx_deg, dy_deg


def project_building_shadow(
    building_polygon: Polygon,
    building_height: float,
    solar_elevation: float,
    solar_azimuth: float,
    latitude: float = -7.2575,
) -> Optional[Polygon]:
    """Project shadow polygon from a building.

    The shadow is formed by translating the building footprint in the
    shadow direction by the shadow length.

    Args:
        building_polygon: Shapely Polygon of building footprint.
        building_height: Building height in meters.
        solar_elevation: Sun elevation in degrees.
        solar_azimuth: Sun azimuth in degrees from North.
        latitude: Latitude for degree-to-meter conversion.

    Returns:
        Shadow polygon (Shapely Polygon) or None if no shadow.
    """
    shadow_length = compute_shadow_length(building_height, solar_elevation)
    if shadow_length <= 0:
        return None

    shadow_dir = compute_shadow_direction(solar_azimuth)
    dx_deg, dy_deg = _direction_to_dx_dy(shadow_dir, shadow_length, latitude)

    # Create shadow by combining original footprint with translated footprint
    translated = translate(building_polygon, xoff=dx_deg, yoff=dy_deg)

    # The actual shadow is the convex hull of original + translated
    # (simplified approach; more accurate would be vertex-by-vertex extrusion)
    shadow = unary_union([building_polygon, translated]).convex_hull

    return shadow


def project_tree_shadow(
    tree_point: Point,
    tree_height: float,
    crown_radius: float,
    solar_elevation: float,
    solar_azimuth: float,
    latitude: float = -7.2575,
) -> Optional[Polygon]:
    """Project shadow from a tree (approximated as ellipse).

    Args:
        tree_point: Shapely Point of tree location.
        tree_height: Tree height in meters.
        crown_radius: Crown radius in meters.
        solar_elevation: Sun elevation in degrees.
        solar_azimuth: Sun azimuth in degrees.
        latitude: Latitude for conversion.

    Returns:
        Shadow polygon (ellipse) or None.
    """
    shadow_length = compute_shadow_length(tree_height, solar_elevation)
    if shadow_length <= 0:
        return None

    shadow_dir = compute_shadow_direction(solar_azimuth)
    dx_deg, dy_deg = _direction_to_dx_dy(shadow_dir, shadow_length, latitude)

    # Shadow center is offset from tree position
    shadow_center_x = tree_point.x + dx_deg / 2.0
    shadow_center_y = tree_point.y + dy_deg / 2.0

    # Convert crown radius to degrees
    meters_per_deg_lng = 111320.0 * math.cos(math.radians(latitude))
    meters_per_deg_lat = 111320.0
    radius_x = crown_radius / meters_per_deg_lng
    radius_y = crown_radius / meters_per_deg_lat

    # Create ellipse (approximation of tree shadow)
    # Major axis along shadow direction, minor axis = crown diameter
    shadow_half_length = abs(dx_deg) / 2.0 + radius_x
    shadow_half_width = radius_y

    # Generate ellipse points
    angles = np.linspace(0, 2 * math.pi, 32)
    ellipse_x = shadow_center_x + shadow_half_length * np.cos(angles)
    ellipse_y = shadow_center_y + shadow_half_width * np.sin(angles)

    coords = list(zip(ellipse_x, ellipse_y))
    if len(coords) >= 4:
        return Polygon(coords)

    return None


def compute_segment_shade_ratio(
    segment_geom: LineString,
    shadow_polygons,
    buffer_m: float = 2.0,
    latitude: float = -7.2575,
) -> float:
    """Calculate what proportion of a street segment is shaded.

    Args:
        segment_geom: LineString geometry of the segment.
        shadow_polygons: List of shadow Polygon geometries.
        buffer_m: Buffer around segment (approximate sidewalk width).
        latitude: Latitude for degree conversion.

    Returns:
        Shade ratio (0.0 to 1.0).
    """
    if not shadow_polygons:
        return 0.0

    # Buffer segment to represent sidewalk area
    meters_per_deg = 111320.0 * math.cos(math.radians(latitude))
    buffer_deg = buffer_m / meters_per_deg

    segment_area = segment_geom.buffer(buffer_deg)
    total_area = segment_area.area

    if total_area <= 0:
        return 0.0

    # Union all shadows and intersect with segment area
    all_shadows = unary_union([s for s in shadow_polygons if s is not None])
    shaded_area = segment_area.intersection(all_shadows).area

    shade_ratio = min(1.0, shaded_area / total_area)
    return shade_ratio
