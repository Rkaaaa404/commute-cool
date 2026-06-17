"""SQLAlchemy + GeoAlchemy2 ORM models for COMMUTE-COOL."""

from datetime import datetime, date
from uuid import uuid4

from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Boolean, DateTime, Date,
    SmallInteger, Text, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from geoalchemy2 import Geometry

Base = declarative_base()


class Segment(Base):
    """Pedestrian street segment."""
    __tablename__ = "segments"

    segment_id = Column(Integer, primary_key=True, autoincrement=True)
    osm_way_id = Column(BigInteger)
    name = Column(String(255))
    geom = Column(Geometry("LINESTRING", srid=4326), nullable=False)
    length_m = Column(Float)
    highway_type = Column(String(50))
    surface_type = Column(String(50))
    smoothness = Column(String(50))
    sidewalk_width = Column(Float)
    has_shade_tree = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    raster_scores = relationship("SegmentRasterScore", back_populates="segment")
    shadows = relationship("SegmentShadow", back_populates="segment")
    thermal_scores = relationship("ThermalComfortScore", back_populates="segment")
    edge_weights = relationship("EdgeWeight", back_populates="segment")


class Building(Base):
    """Building footprint for shadow modeling."""
    __tablename__ = "buildings"

    building_id = Column(Integer, primary_key=True, autoincrement=True)
    osm_id = Column(BigInteger)
    geom = Column(Geometry("POLYGON", srid=4326), nullable=False)
    height_m = Column(Float)
    levels = Column(Integer)


class Tree(Base):
    """Tree point for shadow modeling."""
    __tablename__ = "trees"

    tree_id = Column(Integer, primary_key=True, autoincrement=True)
    osm_id = Column(BigInteger)
    geom = Column(Geometry("POINT", srid=4326), nullable=False)
    height_m = Column(Float, default=8.0)
    crown_radius_m = Column(Float, default=4.0)


class TransitStop(Base):
    """Public transit stop/station."""
    __tablename__ = "transit_stops"

    stop_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255))
    geom = Column(Geometry("POINT", srid=4326), nullable=False)
    stop_type = Column(String(50))
    operator = Column(String(100))
    route_name = Column(String(255))


class SegmentRasterScore(Base):
    """NDVI & LST scores per segment from satellite imagery (Spark Job 1)."""
    __tablename__ = "segment_raster_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    segment_id = Column(Integer, ForeignKey("segments.segment_id"))
    avg_ndvi = Column(Float)
    avg_lst = Column(Float)
    computed_at = Column(Date, nullable=False)

    segment = relationship("Segment", back_populates="raster_scores")

    __table_args__ = (
        UniqueConstraint("segment_id", "computed_at"),
    )


class SegmentShadow(Base):
    """Shadow ratio per segment per hour (Spark Job 2)."""
    __tablename__ = "segment_shadows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    segment_id = Column(Integer, ForeignKey("segments.segment_id"))
    hour_of_day = Column(SmallInteger, nullable=False)
    shade_ratio = Column(Float)
    computed_at = Column(Date, nullable=False)

    segment = relationship("Segment", back_populates="shadows")

    __table_args__ = (
        UniqueConstraint("segment_id", "hour_of_day", "computed_at"),
    )


class ThermalComfortScore(Base):
    """Composite Thermal Comfort Score per segment (Spark Job 3)."""
    __tablename__ = "thermal_comfort_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    segment_id = Column(Integer, ForeignKey("segments.segment_id"))
    tcs_value = Column(Float, nullable=False)
    apparent_temp = Column(Float)
    shade_ratio = Column(Float)
    aqi_value = Column(Float)
    traffic_level = Column(Float)
    computed_at = Column(DateTime, nullable=False)

    segment = relationship("Segment", back_populates="thermal_scores")

    __table_args__ = (
        UniqueConstraint("segment_id", "computed_at"),
    )


class EdgeWeight(Base):
    """Routing weights per segment edge (Spark Job 5)."""
    __tablename__ = "edge_weights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    segment_id = Column(Integer, ForeignKey("segments.segment_id"))
    base_cost = Column(Float)
    thermal_penalty = Column(Float)
    total_cost = Column(Float)
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=False)

    segment = relationship("Segment", back_populates="edge_weights")


class UserProfile(Base):
    """User heat tolerance profile for Personal Heat Budget."""
    __tablename__ = "user_profiles"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    heat_tolerance = Column(String(20), nullable=False, default="medium")
    max_sun_exposure_min = Column(Integer, default=15)
    age_group = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)


class WeatherAlert(Base):
    """Active weather alerts from BMKG RSS."""
    __tablename__ = "weather_alerts"

    alert_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text)
    description = Column(Text)
    severity = Column(String(20))
    affected_area = Column(Geometry("POLYGON", srid=4326))
    issued_at = Column(DateTime)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
