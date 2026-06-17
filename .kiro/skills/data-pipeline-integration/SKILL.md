---
name: data-pipeline-integration
description: Sets up data pipelines for live external APIs and RSS feeds. Use when connecting weather data, traffic, and emergency alerts.
---

# Data Pipeline Integration

## Overview
This skill coordinates fetching, parsing, and cleaning data from external real-time sources (Open-Meteo, BMKG RSS feeds, AQI portals, traffic streams). It ensures data resilience via caching and graceful failover configurations.

## When to Use
- When setting up cron jobs or hooks to sync weather and AQI info.
- When parsing raw XML alerts from BMKG feeds for dynamic rerouting.

## Instructions
1. Implement robust error-handling, timeouts, and retries for all third-party API calls.
2. Cache response data (e.g., weather updates every 1 hour) to minimize external network dependencies and latency.
3. Ensure fallback to historic/climatological defaults if external APIs fail.
