---
name: planning-task-breakdown
description: Decomposes high-level specifications and PRDs into structured, sequential, and testable tasks for general web applications.
---

# Planning and Task Breakdown

## Overview

A structured methodology to decompose a software design specification into a list of clear, bite-sized tasks. Proper breakdown ensures incremental progress, reduces merge conflicts, simplifies code reviews, and makes it easy to write targeted tests.

## When to Use

- After a specification (from `spec-driven-development`) is approved and before writing code.
- Implementing features that touch multiple layers (database, API, frontend UI, state).
- Dividing work among multiple developers or planning developer sprints.

---

## Decomposition Strategy

Break down the development process into logical phases, ensuring that each task has:
1. **Description**: What needs to be done.
2. **Dependencies**: What must be completed first.
3. **Acceptance Criteria**: How to verify the task is complete (both manual and automated).

### Phase 0: Setup & Foundation
- Setup local environments, configuration files, and install dependencies.
- Verify docker environments, linting rules, and formatting configurations.
- Verify basic boilerplate builds without errors.

### Phase 1: Database & Data Access Layer
- Write database migrations (SQL files, schema definitions, ORM migrations).
- Seed initial data or test fixtures.
- Write repository methods or database queries (SQL/ORM) to fetch and mutate data.
- **Verification**: Run unit tests on database queries or inspect schema directly.

### Phase 2: Core Backend Services & APIs
- Create controller/service layer for business logic.
- Create API endpoints (REST routes, GraphQL resolvers, or gRPC methods).
- Add input validation schemas (e.g., Zod, Yup, Joi) and authentication/authorization middleware.
- **Verification**: Write integration tests targeting API endpoints using mock DB or test database.

### Phase 3: Frontend Layout & UI Components
- Build static, presentation-only UI components (React/Vue/Svelte components).
- Ensure styling (CSS/Tailwind), layouts, and responsiveness match designs.
- Check accessibility (keyboard navigation, semantic HTML, ARIA tags).
- **Verification**: Storybook review or visual testing.

### Phase 4: State Management & Frontend Integration
- Set up global state, store, context, or react-query hooks.
- Bind API request/response hooks to the frontend components.
- Implement error handling, loading states, and notification messages.
- **Verification**: Manual end-to-end user flow tests in local browser.

### Phase 5: Testing, Hardening & Polishing
- Write End-to-End (E2E) tests covering key user journeys.
- Verify error handling and validation edges.
- Polish animations, page transitions, and loading skeletons.
- **Verification**: Green E2E test suite.

---

## Task List Template

Organize the execution plan using the following format:

```markdown
# Execution Plan: [Feature/Project Name]

## Phase 0: Prep & Foundation
- [ ] Task 0.1: Initialize environment configs and verify build.
  - *Acceptance Criteria:* `npm run build` succeeds.
  - *Files:* `.env.example`, `package.json`

## Phase 1: Database
- [ ] Task 1.1: Create database migrations for [tables/collections].
  - *Acceptance Criteria:* Migration runs successfully and database schema matches spec.
  - *Files:* `migrations/xxxx_create_tables.sql`
- [ ] Task 1.2: Seed database with test data.
  - *Acceptance Criteria:* Querying tables returns expected records.
  - *Files:* `seeds/test_data.js`

## Phase 2: Backend APIs
- [ ] Task 2.1: Implement API endpoint [Endpoint Path] with validation.
  - *Acceptance Criteria:* Request returns correct status codes (200/201/400/401/403/500) and response formats.
  - *Files:* `controllers/postController.ts`, `routes/postRoutes.ts`
- [ ] Task 2.2: Add integration tests for [Endpoint Path].
  - *Acceptance Criteria:* Running `npm run test:api` passes.
  - *Files:* `tests/api/post.test.ts`

## Phase 3: Frontend UI Components
- [ ] Task 3.1: Create static UI components for [Views].
  - *Acceptance Criteria:* Matches mockups, responsive, accessible (no contrast errors).
  - *Files:* `components/PostCard.tsx`, `components/PostList.tsx`

## Phase 4: Frontend Integration
- [ ] Task 4.1: Bind [API Endpoints] to frontend components.
  - *Acceptance Criteria:* Page loads dynamic data from database; forms successfully submit data.
  - *Files:* `hooks/usePosts.ts`, `pages/posts.tsx`

## Phase 5: E2E Tests & Polish
- [ ] Task 5.1: Write Playwright/Cypress tests for [User Flow].
  - *Acceptance Criteria:* Automated test completes registration -> login -> create post flow successfully.
  - *Files:* `tests/e2e/posts.spec.ts`
```

---

## Common Planning Pitfalls

- **Creating too-large tasks**: "Build the frontend" is not a task; it's a project. Break it down to specific pages or components.
- **Neglecting dependency order**: Trying to integrate APIs before database migrations are done. Always follow the bottom-up approach (Database -> API -> UI -> Integration).
- **Ignoring testing time**: Writing tests should be embedded in each phase, not left as a single task at the very end.
