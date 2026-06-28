---
name: caveman
description: Semantic prompt and communication compression. Use to strip linguistic filler, articles, and pleasantries to minimize token usage.
---

# Caveman Compression

## Overview
Caveman Compression is a token-reduction technique that strips out predictable linguistic elements, filler words, passive voice, and pleasantries. It uses a terse, direct, keyword-focused syntax to preserve technical precision while saving up to 75% of context window space.

## When to Use
- When writing compact instructions or prompts.
- When summarizing terminal logs, error traces, or diff outputs.
- When communicating concise status updates in high-density contexts.

## Instructions
1. Remove articles (the, a, an), pronouns, auxiliary verbs, and pleasantries.
2. Use short, imperative sentences or bullet points.
3. Focus entirely on technical facts, command names, error messages, and variables.
