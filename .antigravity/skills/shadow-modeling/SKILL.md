---
name: shadow-modeling
description: Calculates solar positioning and projects building/tree shadows. Use when implementing dynamic shade mapping.
---

# Shadow Modeling

## Overview
This skill implements physical modeling of shadows cast by buildings and trees onto sidewalks. It calculates solar elevation and azimuth angles based on geographic coordinates, date, and local time.

## When to Use
- When writing routines to determine actual shade levels on pedestrian routes.
- When computing dynamic comfort metrics for smart city mapping.

## Instructions
1. Use standard astronomical algorithms to compute solar position (elevation/azimuth).
2. Construct shadow projection polygons using building heights and solar vector.
3. Intersect projected shadow polygons with pedestrian path geometry to calculate actual shaded segments.
