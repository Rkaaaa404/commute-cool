---
name: performance-optimization
description: Guidelines for optimizing full-stack web applications to improve speed, user experience, database query times, and frontend Core Web Vitals.
---

# Performance Optimization (General Web Apps)

## Overview

Performance is a key feature of any web application. Faster applications see higher engagement, conversion rates, and better search rankings. This skill outlines techniques to optimize performance across the frontend, API, database, and infrastructure layers.

---

## 1. Frontend Performance & Core Web Vitals

- **LCP (Largest Contentful Paint)**: Measure when the main content of a page is rendered.
  - Optimize images: Use modern formats (WebP, AVIF), size images appropriately, and lazy-load below-the-fold assets.
  - Preload critical fonts, stylesheets, and hero images.
- **FID / INP (First Input Delay / Interaction to Next Paint)**: Measure page responsiveness to user inputs.
  - Keep main-thread tasks short. Break long JS executions into smaller chunks.
  - Use code-splitting and dynamic imports (`import()`) to load heavy components only when needed.
- **CLS (Cumulative Layout Shift)**: Measure visual stability.
  - Always specify width and height dimensions for images and video containers.
  - Use loading skeletons or reserve spaces for dynamically injected content to prevent elements from shifting.

---

## 2. API & Network Optimization

- **Payload Minimization**: Return only the data fields required by the frontend client. Avoid fetching or sending large, unused nested JSON arrays.
- **Pagination**: Implement cursor-based or offset-based pagination on list endpoints. Avoid returning infinite records in a single request.
- **Compression**: Ensure the server compresses HTTP payloads using GZIP or Brotli.
- **Request Batched/Parallelization**: Use `Promise.all()` (in Node.js) or parallel worker threads to fetch independent data sources concurrently rather than sequentially.

---

## 3. Database Query & Schema Optimization

- **Indexing**: Create indexes on fields frequently used in `WHERE`, `JOIN`, `ORDER BY`, or `GROUP BY` clauses (e.g., `user_id`, `created_at`, `status`). Avoid over-indexing, as it slows down write operations.
- **Query Analysis**: Use database tools (like PostgreSQL `EXPLAIN ANALYZE` or MySQL `EXPLAIN`) to inspect query execution plans and find slow table scans.
- **Connection Pooling**: Use connection pool managers (e.g., PgBouncer) to recycle database connections instead of opening/closing a connection per request.
- **Avoid N+1 Queries**: Eager-load or join related tables instead of executing database queries inside loops.

---

## 4. Caching Strategies

- **Browser Caching**: Set appropriate `Cache-Control` headers for static assets (e.g., `Cache-Control: public, max-age=31536000, immutable`).
- **CDN (Content Delivery Network)**: Distribute static assets and API responses globally using a CDN (e.g., Cloudflare, AWS CloudFront, Fastly).
- **Server Caching**: Store highly read, rarely mutated data (like configurations, lookup tables, user session metadata) in in-memory key-value databases like Redis.
- **Cache Invalidation**: Choose proper eviction policies (e.g., LRU) and invalidation strategies (e.g., cache-aside, write-through) to prevent serving stale data.
