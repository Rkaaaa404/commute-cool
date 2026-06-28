---
name: code-simplification
description: Refactors complex code to be simpler, cleaner, and more readable. Use to reduce cognitive load and remove duplicate logic.
---

# Code Simplification

## Overview
This skill focuses on simplifying complex implementation structures. It aims to reduce cognitive load, improve readability, and eliminate boilerplate or duplicated code, especially when dealing with complex data transformation pipelines.

## When to Use
- When a function or module has high cyclomatic complexity (too many nested loops/conditionals).
- When resolving redundant code blocks or refactoring utility helpers.
- When optimizing long data formatting routines.

## Instructions
1. Break down large functions into smaller, single-responsibility helpers.
2. Replace nested conditions with early exit guard clauses.
3. Keep logic clean and document why non-obvious optimizations are implemented.
