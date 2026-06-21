---
name: debugging-error-recovery
description: A systematic methodology for diagnosing, isolating, and fixing bugs across frontend, backend, database, and network layers of general web applications.
---

# Debugging and Error Recovery

## Overview

A structured, logical process for resolving software bugs. Rather than trying arbitrary fixes (guessing), this guide outlines how to observe symptoms, reproduce issues, isolate the root cause, apply durable fixes, and prevent regressions.

---

## The 6-Step Debugging Cycle

```
[1. Observe] ──> [2. Reproduce] ──> [3. Isolate]
                                         │
[6. Document] <── [5. Verify] <── [4. Fix]
```

### 1. Observe & Document the Symptom
- Collect the exact error messages, stack traces, and screenshots.
- Check user reports: What were they doing? What did they expect? What actually happened?
- Capture context: Browser version, operating system, API payload, user session details.

### 2. Reproduce the Issue
- Write a failing test (unit, integration, or E2E) that reliably triggers the error.
- If a test isn't possible, write a step-by-step manual script to trigger it in the local environment.
- *If you cannot reproduce the bug, you cannot verify if a fix actually works.*

### 3. Isolate the Root Cause
Narrow down where the failure occurs:
- **Client (Frontend)**: Check browser devtools Console, React/Vue DevTools, local state, or UI styling issues.
- **Network**: Check the Network tab in DevTools. What is the request URL, headers, and request body? What is the response status code and JSON payload?
- **Server (Backend)**: Look at backend logs, trace IDs, environment variables, or application exceptions.
- **Database**: Check slow query logs, database constraints, lock conditions, or connection pool statistics.

### 4. Apply a Durable Fix
- Address the root cause, not just the symptom.
-   *Symptom fix:* `if (data === null) return ""` (might just hide a deeper DB fetching issue).
-   *Root cause fix:* Resolve the database query that was returning `null` incorrectly.
- Follow existing architecture patterns and code styles.

### 5. Verify the Fix
- Run the reproduction script or automated test created in Step 2.
- Run the full project test suite to ensure no regressions were introduced.
- Verify in multiple browsers or responsive layouts if it was a frontend issue.

### 6. Document & Prevent
- Keep the regression test in the code repository to prevent the bug from coming back.
- If the bug was caused by a configuration or environment issue, update `.env.example` or documentation.

---

## Troubleshooting Guide by Layer

### Frontend Issues (React, Vue, etc.)
- **State Issues**: Use React/Vue devtools to track state mutations over time. Check if parent re-renders are causing state resets.
- **CORS Errors**: Check if the backend is configured to accept requests from the frontend origin. Ensure you are using relative URLs if using a proxy, or check headers like `Access-Control-Allow-Origin`.
- **Hydration Mismatches**: In SSR frameworks, check if browser-only objects (like `window` or `document`) are accessed during initial server render.

### Backend Issues (Express, Go, Fastify, Django)
- **Unhanded Exceptions**: Ensure global error-handling middleware is catching errors and returning structured JSON responses.
- **Auth Failures**: Decode JWT tokens using tools like `jwt.io` to check if permissions (claims) or expiration times are correct.
- **Environment Variables**: Verify that variables are loaded correctly (`process.env` or equivalent) and match the required format.

### Database Issues (PostgreSQL, MySQL, MongoDB)
- **N+1 Query Problems**: Check logs to see if a loop is querying the database repeatedly. Resolve by using joins, eager loading, or aggregation queries.
- **Timeout/Pool Exhaustion**: Check if database connections are being closed correctly after queries finish.
- **Data Validation**: Ensure DB schema constraints (e.g., `NOT NULL`, `FOREIGN KEY`, `UNIQUE`) match backend validation schemas.
