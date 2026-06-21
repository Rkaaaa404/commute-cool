---
name: graphify
description: Codebase dependency and structural graph analyzer. Use to map file dependencies, import paths, and module hierarchies.
---

# Graphify

## Overview
Graphify parses codebase folder structures, schemas, and media files to build a queryable knowledge graph. By analyzing AST structures (via tree-sitter or parser rules), it allows the agent to navigate code bases structurally, tracing relationships between files, imports, and modules.

## When to Use
- When entering a new or unfamiliar codebase to understand its architecture.
- When checking which files will be affected by refactoring a specific module.
- When mapping imports and dependency chains.

## Instructions
1. Build or query the dependency graph of the target directory.
2. Identify core modules and high-degree nodes (frequently imported files).
3. Validate that new imports do not introduce circular dependencies.
