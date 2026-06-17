---
name: leanctx
description: Context intelligence and token pruning manager. Use to clean up agent memory, exclude irrelevant files, and compress log/terminal outputs.
---

# LeanCTX (Lean Context Manager)

## Overview
LeanCTX ensures token efficiency and context clarity by managing what the AI agent reads, remembers, and saves. It helps prevent context bloat, reduces API costs, and avoids reasoning degradation during long coding sessions by filtering out noise, raw logs, and unneeded file contents.

## When to Use
- When the conversation history becomes very long and token usage is high.
- Before opening multiple large files that contain irrelevant utility functions or boilerplate.
- When terminal commands produce verbose outputs that need to be pruned.

## Instructions
1. Prioritize reading specific line ranges of files rather than entire files.
2. Regularly summarize the session goals and remove resolved subtasks from memory.
3. Exclude logs, lockfiles, and build directories from search paths.
