-- ============================================================
-- COMMUTE-COOL Database Schema Initialization
-- PostgreSQL + PostGIS
-- ============================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgrouting;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TABEL INTI: Segmen Jalan Pedestrian
-- ============================================================
CREATE TABLE segments (
    segment_id      SERIAL PRIMARY KEY,
    osm_way_id      BIGINT,
    name            VARCHAR(255),
    geom            GEOMETRY(LineString, 4326) NOT NULL,
    length_m        DOUBLE PRECISION,
    highway_type    VARCHAR(50),
    surface_type    VARCHAR(50),
    smoothness      VARCHAR(50),
    sidewalk_width  DOUBLE PRECISION,
    has_shade_tree  BOOLEAN DEFAULT FALSE,
    source          INTEGER,
    target          INTEGER,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_segments_geom ON segments USING GIST (geom);
CREATE INDEX idx_segments_highway ON segments (highway_type);
CREATE INDEX idx_segments_source ON segments (source);
CREATE INDEX idx_segments_target ON segments (target);

-- ============================================================
-- TABEL: Bangunan (untuk shadow modeling)
-- ============================================================
CREATE TABLE buildings (
    building_id     SERIAL PRIMARY KEY,
    osm_id          BIGINT,
    geom            GEOMETRY(Polygon, 4326) NOT NULL,
    height_m        DOUBLE PRECISION,
    levels          INTEGER
);

CREATE INDEX idx_buildings_geom ON buildings USING GIST (geom);

-- ============================================================
-- TABEL: Pohon (untuk shadow modeling)
-- ============================================================
CREATE TABLE trees (
    tree_id         SERIAL PRIMARY KEY,
    osm_id          BIGINT,
    geom            GEOMETRY(Point, 4326) NOT NULL,
    height_m        DOUBLE PRECISION DEFAULT 8.0,
    crown_radius_m  DOUBLE PRECISION DEFAULT 4.0
);

CREATE INDEX idx_trees_geom ON trees USING GIST (geom);

-- ============================================================
-- TABEL: Titik Transit Transportasi Publik
-- ============================================================
CREATE TABLE transit_stops (
    stop_id         SERIAL PRIMARY KEY,
    name            VARCHAR(255),
    geom            GEOMETRY(Point, 4326) NOT NULL,
    stop_type       VARCHAR(50),
    operator        VARCHAR(100),
    route_name      VARCHAR(255)
);

CREATE INDEX idx_transit_geom ON transit_stops USING GIST (geom);

-- ============================================================
-- TABEL: Skor NDVI & LST per Segmen (hasil Spark Job 1)
-- ============================================================
CREATE TABLE segment_raster_scores (
    id              SERIAL PRIMARY KEY,
    segment_id      INTEGER REFERENCES segments(segment_id),
    avg_ndvi        DOUBLE PRECISION,
    avg_lst         DOUBLE PRECISION,
    computed_at     DATE NOT NULL,
    UNIQUE(segment_id, computed_at)
);

CREATE INDEX idx_raster_segment ON segment_raster_scores (segment_id);

-- ============================================================
-- TABEL: Rasio Bayangan per Segmen per Waktu (hasil Spark Job 2)
-- ============================================================
CREATE TABLE segment_shadows (
    id              SERIAL PRIMARY KEY,
    segment_id      INTEGER REFERENCES segments(segment_id),
    hour_of_day     SMALLINT NOT NULL,
    shade_ratio     DOUBLE PRECISION,
    computed_at     DATE NOT NULL,
    UNIQUE(segment_id, hour_of_day, computed_at)
);

CREATE INDEX idx_shadows_segment_hour ON segment_shadows (segment_id, hour_of_day);

-- ============================================================
-- TABEL: Thermal Comfort Score per Segmen (hasil Spark Job 3)
-- ============================================================
CREATE TABLE thermal_comfort_scores (
    id              SERIAL PRIMARY KEY,
    segment_id      INTEGER REFERENCES segments(segment_id),
    tcs_value       DOUBLE PRECISION NOT NULL,
    apparent_temp   DOUBLE PRECISION,
    shade_ratio     DOUBLE PRECISION,
    aqi_value       DOUBLE PRECISION,
    traffic_level   DOUBLE PRECISION,
    computed_at     TIMESTAMP NOT NULL,
    UNIQUE(segment_id, computed_at)
);

CREATE INDEX idx_tcs_segment_time ON thermal_comfort_scores (segment_id, computed_at DESC);

-- ============================================================
-- TABEL: Bobot Routing per Edge (hasil Spark Job 5)
-- ============================================================
CREATE TABLE edge_weights (
    id              SERIAL PRIMARY KEY,
    segment_id      INTEGER REFERENCES segments(segment_id),
    base_cost       DOUBLE PRECISION,
    thermal_penalty DOUBLE PRECISION,
    total_cost      DOUBLE PRECISION,
    valid_from      TIMESTAMP NOT NULL,
    valid_until     TIMESTAMP NOT NULL
);

CREATE INDEX idx_edge_weights_segment ON edge_weights (segment_id);
CREATE INDEX idx_edge_weights_validity ON edge_weights (valid_from, valid_until);

-- ============================================================
-- TABEL: Profil Pengguna (Personal Heat Budget)
-- ============================================================
CREATE TABLE user_profiles (
    user_id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    heat_tolerance      VARCHAR(20) NOT NULL DEFAULT 'medium',
    max_sun_exposure_min INTEGER DEFAULT 15,
    age_group           VARCHAR(20),
    created_at          TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- TABEL: Log Peringatan Cuaca (dari RSS BMKG)
-- ============================================================
CREATE TABLE weather_alerts (
    alert_id        SERIAL PRIMARY KEY,
    title           TEXT,
    description     TEXT,
    severity        VARCHAR(20),
    affected_area   GEOMETRY(Polygon, 4326),
    issued_at       TIMESTAMP,
    expires_at      TIMESTAMP,
    is_active       BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_alerts_active ON weather_alerts (is_active) WHERE is_active = TRUE;
CREATE INDEX idx_alerts_area ON weather_alerts USING GIST (affected_area);

-- ============================================================
-- TABEL: CCTV Cameras (Dishub Surabaya)
-- ============================================================
CREATE TABLE cctv_cameras (
    cctv_id         SERIAL PRIMARY KEY,
    dishub_id       VARCHAR(50),          -- ID dari sistem Dishub (e.g. "cctv_149")
    name            VARCHAR(255) NOT NULL, -- Nama lokasi (e.g. "Jl. Basuki Rahmat - Tunjungan")
    geom            GEOMETRY(Point, 4326) NOT NULL,
    stream_url      TEXT NOT NULL,         -- HLS stream URL
    is_active       BOOLEAN DEFAULT TRUE,
    nearest_segment INTEGER REFERENCES segments(segment_id),
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_cctv_geom ON cctv_cameras USING GIST (geom);
CREATE INDEX idx_cctv_active ON cctv_cameras (is_active) WHERE is_active = TRUE;


-- ============================================================
-- pgRouting: Network Topology Builder
-- Run after segments are loaded to build routing graph
-- ============================================================
CREATE OR REPLACE FUNCTION build_routing_topology() RETURNS void AS $$
BEGIN
    -- Create topology (nodes at segment endpoints)
    PERFORM pgr_createTopology(
        'segments',
        0.0001,          -- tolerance (~11m for snapping endpoints)
        'geom',
        'segment_id',
        'source',
        'target'
    );

    -- Analyze topology for connectivity
    PERFORM pgr_analyzeGraph('segments', 0.0001, 'geom', 'segment_id');

    RAISE NOTICE 'Routing topology built successfully';
END;
$$ LANGUAGE plpgsql;
