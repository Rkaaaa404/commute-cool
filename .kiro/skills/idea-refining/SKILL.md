---
name: idea-refining
description: Brainstorming and refining vague requirements into a clear, general web application concept. Focuses on identifying core problems, target audiences, constraints, tech stack options, architecture alternatives, and validation processes.
---

# General Idea Refinement and Brainstorming

## Overview

A structured brainstorming and refinement framework to convert vague ideas or raw feature requests into concrete, actionable web application proposals. Before drafting specifications or writing code, this process ensures the concept is well-formed, feasible, and optimized for general web architectures (monolith, microservices, SPA, SSR, serverless, etc.).

## When to Use

- Starting a new web application from scratch with ambiguous requirements.
- Exploring a new feature for an existing application that could be implemented in multiple ways.
- Deciding on a technology stack, database type, or architectural pattern.
- Aligning multiple stakeholders or developers on the core scope and goals of a project.

**When NOT to use:** When requirements are already fully specified and the tech stack is fixed — proceed directly to `spec-driven-development`.

---

## Refinement Process

### Phase 1: Diverge (Explore the Space)

Do not commit to a solution immediately. Ask expansive questions to understand the problem and explore the architectural options:

1. **Problem & Value**
   - What core problem does this solve?
   - Who are the primary users, and what is their context?
   - How is this problem solved currently (manual workarounds, competitors)?
   - What is the cost of NOT solving this problem?

2. **Architectural & Stack Options**
   - **Frontend**: SPA (React, Vue, Svelte, Angular) vs. SSR/SSG (Next.js, Nuxt.js, SvelteKit, Remix) vs. Traditional (Django/Laravel templates).
   - **Backend**: Monolith (Node.js, Go, Python, PHP, Ruby) vs. Serverless (AWS Lambda, Vercel Functions) vs. Microservices.
   - **Database**: Relational (PostgreSQL, MySQL) vs. NoSQL (MongoDB, DynamoDB) vs. Key-Value (Redis).
   - **Deployment**: Traditional VPS (DigitalOcean, AWS EC2), PaaS (Render, Heroku, Fly.io), Serverless/Static (Vercel, Netlify, Cloudflare Pages), or Containerized (Docker, Kubernetes).

3. **Constraints & Risks**
   - What are the timeline, budget, and resource constraints?
   - Are there specific performance, scaling, or regulatory requirements (e.g., GDPR, HIPAA)?
   - What could make this project fail technically or operationally?

---

### Phase 2: Converge (Define the Solution)

Narrow down the options and define a concrete, bounded proposal:

1. **The Proposal Summary**
   - **Problem Statement**: One sentence summarizing the issue.
   - **Target Audience**: Specific user personas or roles.
   - **Chosen Stack**: The specific frontend, backend, database, and hosting services selected, with rationale.
   - **Architecture Diagram**: A conceptual view of how components interact (frontend, APIs, databases, external services).

2. **Core Features (The MVP)**
   - List 3-5 must-have features that directly address the core problem.
   - Define clear "Out of Scope" items to prevent scope creep.

3. **Success Metrics**
   - How will we know if this succeeds? (e.g., page load under 1s, active users, successful conversions).

---

### Phase 3: Validation Checklist

Verify the viability of the proposal:

- [ ] **Problem Verification**: Is there actual evidence that users experience this problem?
- [ ] **Tech Feasibility**: Is the chosen stack aligned with the team's expertise and project timeline?
- [ ] **Complexity Check**: Have we chosen the simplest architecture that solves the problem? (Avoid over-engineering with microservices/K8s if a monolith suffices).
- [ ] **Security & Compliance**: Have we accounted for user data protection, auth requirements, and regulatory compliance?
- [ ] **Alternatives Documented**: At least two alternative approaches were considered and rejected with clear reasons.

---

## Output Template

Generate your refinement notes using the format below:

```markdown
# Brainstorming & Refinement: [Project/Feature Name]

## 1. Problem & Audience
- **Problem Statement**: [Define the core pain point]
- **Target Users**: [Who experiences this pain?]
- **Current Alternatives**: [How do they solve it today?]

## 2. Chosen Solution & Architecture
- **Core Concept**: [Briefly describe the solution]
- **Tech Stack**:
  - **Frontend**: [e.g., Next.js, React] - *Rationale:* [Why?]
  - **Backend**: [e.g., Express.js, NestJS, Go] - *Rationale:* [Why?]
  - **Database**: [e.g., PostgreSQL] - *Rationale:* [Why?]
  - **Hosting**: [e.g., Vercel + Render] - *Rationale:* [Why?]
- **Integration Flow**: [Describe how data flows, e.g., Client -> REST API -> DB]

## 3. Scope Bounding
### Must-Have (MVP)
- [ ] Feature 1
- [ ] Feature 2
- [ ] Feature 3

### Out of Scope (Future Phases)
- [ ] Excluded Feature A
- [ ] Excluded Feature B

## 4. Alternatives Considered
| Alternative Approach | Pros | Cons | Why Rejected |
|----------------------|------|------|--------------|
| [Approach A]         |      |      |              |
| [Approach B]         |      |      |              |

## 5. Next Steps
- [ ] Draft full system specification (use `spec-driven-development`)
- [ ] Plan task breakdown (use `planning-task-breakdown`)
```
