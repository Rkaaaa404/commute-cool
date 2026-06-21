---
name: code-review
description: Comprehensive quality control checklist for peer and self code reviews, focusing on security, performance, accessibility, architecture, and maintainability.
---

# Code Review Guidelines (General Web Apps)

## Overview

A guide to performing high-quality code reviews. This checklist ensures that any code merged into the main codebase is secure, performant, readable, accessible, and thoroughly tested.

---

## Code Review Checklist

### 1. Architectural Alignment
- Does the code follow the design specified in the `spec-driven-development` document?
- Does it place logic in the correct layer? (e.g., business logic on the backend, layout/presentation on the frontend).
- Does it reuse existing functions, utilities, and UI components rather than duplicating them?

### 2. Security (Critical)
- **Authentication & Authorization**: Are API endpoints gated by auth checks? Are users permitted to edit/view only their own records (row-level security, ACLs)?
- **Input Validation**: Is all user input validated on both client (UX) and server (Security)?
- **OWASP Protection**: Is the code safe from SQL Injection (using parameterized queries/ORMs), Cross-Site Scripting (XSS), and Cross-Site Request Forgery (CSRF)?
- **Secrets Management**: Are there any hardcoded passwords, keys, or tokens? (Verify `.env` keys aren't committed).

### 3. Performance
- **Database Queries**: Are queries optimized? Are indexes used correctly? Are there any N+1 query patterns?
- **Network Payloads**: Are responses compressed, paginated, and returning only the fields required by the UI?
- **Bundle Size**: Are we importing large libraries unnecessarily? (Use code splitting or dynamic imports for heavy components).
- **Caching**: Are cache headers (`Cache-Control`) set correctly for static and dynamic assets?

### 4. Accessibility (a11y) & UX
- **Semantic HTML**: Are elements like `<button>`, `<nav>`, `<main>`, and `<article>` used instead of plain `<div>`s?
- **Keyboard Navigation**: Can all interactive elements be reached and operated using the `Tab` and `Enter`/`Space` keys?
- **ARIA Attributes**: Are `aria-label`, `aria-expanded`, and other attributes set correctly for custom UI elements?
- **Contrast & Text**: Does the design meet WCAG AA contrast standards? Are font sizes readable on mobile viewports?

### 5. Readability & Maintainability
- **Naming**: Are variables, functions, and classes named descriptively and consistently?
- **DRY (Don't Repeat Yourself)**: Is duplicate code refactored into reusable services, custom hooks, or utility helper files?
- **Complexity**: Are large functions broken into smaller, single-purpose functions?
- **Comments**: Are comments describing *why* something is done (intent, edge-case reasons) rather than *what* the code does (which should be clear from reading it)?

### 6. Testing Coverage
- **API Tests**: Are new API routes covered by integration tests checking success and error states (400, 401, 403, 404)?
- **Component Tests**: Are UI components tested for interactive logic, rendering variations, and error states?
- **E2E Tests**: Are core user flows tested in a real browser environment?

---

## Feedback Standards

- **Empathy & Constructiveness**: Frame feedback around the code, not the developer. (e.g., "This function could be simplified" rather than "You wrote this function poorly").
- **Categorize Severity**:
  - `[BLOCKER]`: Security risks, build breaks, data loss bugs, or severe architectural divergence.
  - `[SHOULD]`: Performance improvements, code style alignment, test coverage improvements.
  - `[NIT]`: Minor styling tweaks, alternative naming choices, optional refactoring.
- **Explain the "Why"**: Don't just say "change this." Explain the benefit (e.g., "Moving this filter to the database query instead of in-memory Javascript will speed up page loading when records exceed 1,000").
