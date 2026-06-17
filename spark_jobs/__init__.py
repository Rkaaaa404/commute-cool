"""COMMUTE-COOL Spark Processing Jobs.

Batch and micro-batch jobs for geospatial Big Data processing:
- Job 1: Raster Segmentation (NDVI/LST per street segment)
- Job 2: Dynamic Shadow Modeling (shade ratio per segment per hour)
- Job 3: Thermal Comfort Score calculation
- Job 4: Traffic & AQI aggregation per segment
- Job 5: Graph Weight Export for routing engine
"""
