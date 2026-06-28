---
name: llm-council
description: Simulates a multi-perspective deliberation (council of experts) to critique, refine, and validate complex technical designs, architectures, and bug diagnostics.
---

# LLM Council

## Overview
The LLM Council skill improves the reliability and depth of reasoning by replacing single-model intuition with structured peer deliberation. By simulating virtual, specialized expert personas, the agent pressure-tests its own ideas, identifies hidden edge cases, and synthesizes a more balanced, robust solution.

## When to Use
- **Complex Architecture Design**: Designing new services, database schemas, or routing engines.
- **High-Risk/Ambiguous Bugs**: When diagnosing root causes that are difficult to trace or reproduce.
- **Critical Code Refactoring**: Modifying core APIs or shared utilities where regressions could break existing services.
- **Deliberating Trade-offs**: When choosing between multiple design directions (e.g., performance vs. complexity).

## Instructions
1. **Initialize the Council**: Identify the issue/decision and select a subset of virtual expert personas:
   - **The Lead Architect**: Evaluates structural consistency, scalability, and design patterns.
   - **The Security & Stability Guard**: Identifies security risks (e.g., SQLi, CORS, data leakage), concurrency bottlenecks, and error-handling gaps.
   - **The Pragmatic Builder**: Advocates for simplicity, reuse of existing code, and minimizing overhead.
2. **Deliberate**: Present the proposed approach or bug analysis. Simulate feedback and critiques from each persona, focusing on their specific domain of expertise.
3. **Synthesize**: Act as the Moderator (Antigravity) to consolidate the feedback, resolve conflicts, and output a refined, optimal implementation plan or solution.
