---
name: spatial-data-analysis
description: Parses, transforms, and analyzes geospatial vector and raster data. Use when handling GeoJSON, OSM tags, and GeoTIFFs.
---

# Spatial Data Analysis

## Overview
This skill helps ingest, transform, and analyze geospatial datasets (GeoJSON, Shapefiles, Sentinel/Landsat rasters). It is critical for calculating NDVI indices, Land Surface Temperature (LST), and mapping sidewalks/vegetation.

## When to Use
- When parsing OSM Overpass API responses (nodes, ways, relations).
- When processing NDVI/LST layers from Google Earth Engine.
- When performing spatial queries (e.g., finding the nearest bus stops or building coordinates).

## Instructions
1. Handle geometry objects (polygons, lines, points) using standard tools (e.g., PostGIS, Turf.js, Shapely).
2. Validate Coordinate Reference Systems (CRS) and ensure consistent projections (e.g., EPSG:4326/WGS84).
3. Implement fallback values for missing attributes (e.g., unlabelled sidewalk width/surface).
