---
name: symdex
description: Symbolic indexing and navigation engine for codebases. Use when locating classes, functions, routes, and call trees across the project.
---

# SymDex (Symbolic Indexing)

## Overview
SymDex provides symbolic indexing and quick navigation capabilities for the codebase. Instead of performing text-heavy file content searches or running greps across the repository, this skill queries a repository-local SQLite oracle to retrieve classes, functions, structs, variables, call trees, and callers/callees.

## When to Use
- When searching for specific classes, functions, methods, or structs by name.
- When tracing function call hierarchies (who calls this function, or what functions does this call).
- When trying to understand the API routing or entry points of a service.

## Instructions
1. Query the symbol database first before reading full files.
2. Locate the specific file containing the symbol definition.
3. Examine the call graph to trace input/output data flow through function parameters.
