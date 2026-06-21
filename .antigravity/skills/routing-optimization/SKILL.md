---
name: routing-optimization
description: Customizes routing engine costs and penalties. Use when integrating thermal comfort scores into pathfinding.
---

# Routing Optimization

## Overview
This skill modifies open-source routing algorithms (like Dijkstra, A*, or contraction hierarchies) to incorporate multi-criteria cost weighting. It applies penalties for thermal discomfort (heat budget, direct sunlight exposure) alongside traditional distance/time metrics.

## When to Use
- When configuring GraphHopper or Valhalla custom profiles.
- When calculating shortest route vs. coolest/most comfortable route options.

## Instructions
1. Formulate a balanced cost function combining segment length, walking speed, and thermal comfort score.
2. Implement routing engine constraints, ensuring that segments violating absolute heat limits are blocked or heavily penalized.
3. Validate routing output to ensure path continuity and reasonable execution times (<3 seconds).
