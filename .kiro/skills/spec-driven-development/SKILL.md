---
name: spec-driven-development
description: Writes comprehensive software design specifications before code implementation for general web applications. Use when starting a new project, feature, or major refactoring.
---

# Spec-Driven Development (General Web Apps)

## Overview

Write a software design specification (Product Requirement Document / Technical Design Doc) covering objectives, system requirements, data model, API design, UI architecture, security, testing strategy, and implementation plan before writing any code. A spec acts as a contract that aligns stakeholders, prevents scope creep, and establishes a clear path for development and validation.

## When to Use

- Starting a new project, microservice, or feature.
- Requirements are complex, multi-layered, or involve multiple system integrations.
- Collaborating with multiple developers or AI agents.
- Significant changes where the cost of rewrite is high.

**When NOT to use:** Simple bug fixes, minor UI tweaks, or documentation updates.

---

## Spec Template

Use the following template for all specifications:

```markdown
# Spec: [Feature/Project Name]

## 1. Objective & Success Criteria
- **Context**: Why are we building this? Who benefits?
- **Goals**: What does success look like? (List 1-3 measurable goals).

## 2. Requirements
### Must-Have (MVP)
- [ ] Requirement 1
- [ ] Requirement 2

### Nice-to-Have (Future)
- [ ] Requirement A

### Out of Scope
- [ ] Specifically excluded features or constraints to prevent scope creep.

## 3. Technology & Architecture
- **Tech Stack**: [Frontend, Backend, Database, Cache, Message Queue, etc.]
- **Architecture Style**: [Monolith, Microservice, Serverless, Event-Driven]
- **System Diagram**: [Describe components and how they communicate]

## 4. Data Model (Schema)
Define database schemas, tables, collections, columns, types, indexes, and relationships:
- **Table/Collection Name**: `users`
  - `id`: UUID (Primary Key)
  - `email`: VARCHAR(255) (Unique, Indexed)
  - `password_hash`: VARCHAR(255)
  - `created_at`: TIMESTAMP
- **Relationships**: One-to-Many between `users` and `posts`.

## 5. API Design
Define the API endpoints, methods, request bodies, and responses:
- **Endpoint**: `POST /api/v1/posts`
  - **Description**: Create a new post.
  - **Headers**: `Authorization: Bearer <token>`
  - **Request Body**:
    ```json
    {
      "title": "String",
      "content": "String"
    }
    ```
  - **Responses**:
    - `201 Created`: Post object with ID.
    - `400 Bad Request`: Validation errors.
    - `401 Unauthorized`: Missing or invalid token.

## 6. UI/UX Design & Component Architecture
- **User Flow**: [Step-by-step path the user takes]
- **Component Breakdown**: [List main components and their state inputs/outputs]
- **Responsive Layout**: [Behavior on Mobile, Tablet, Desktop]
- **Accessibility (a11y)**: [Keyboard navigation, ARIA roles, color contrast]

## 7. Security Considerations
- **Authentication**: [Session-based, JWT, OAuth]
- **Authorization**: [RBAC, ABAC, Row-Level Security]
- **Data Protection**: [Input validation schemas, output sanitization, CSRF tokens, CORS setup]

## 8. Testing Strategy
- **Unit Tests**: [What logic or utility functions to test]
- **Integration Tests**: [API endpoint tests, database queries]
- **End-to-End (E2E) Tests**: [Critical user journeys, e.g., register -> login -> create post]

## 9. Implementation Plan (Phased)
- **Phase 0: Environment & Boilerplate Setup** (config, database init)
- **Phase 1: Database Migration & Schema Creation**
- **Phase 2: Backend APIs & Auth Integration**
- **Phase 3: Frontend Layout & Components**
- **Phase 4: State Management & API Integration**
- **Phase 5: Automated Testing & Validation**
- **Phase 6: Deployment & Verification**

## 10. Boundaries & Rules
### Always
- Use static analysis (linting, formatting, type checking) before committing.
- Run tests after every change.
- Validate all inputs on both client and server side.

### Ask First
- Changing database schemas after implementation starts.
- Adding third-party libraries/dependencies.

### Never
- Hardcode secrets, API keys, or credentials.
- Deploy without running database migrations first.
```

---

## The SDD Process

1. **Information Gathering**: Collect requirements and clarify assumptions.
2. **Drafting the Spec**: Fill out the template above. Focus on edge cases and error handling, not just the happy path.
3. **Review**: Share the spec with peers, stakeholders, or users to gather feedback.
4. **Approval**: Get confirmation on the spec before writing a single line of code.
5. **Implementation**: Treat the spec as the source of truth. Tick off requirements as you build and test.
6. **Verify**: Ensure all "Must-Have" checkmarks are green and covered by automated tests.
