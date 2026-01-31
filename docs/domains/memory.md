---
title: "Memory domain"
usage: "Defines memory categories and persistence boundaries"
sources:
  - https://docs.wandb.ai/weave/guides/tracking/objects
  - https://langchain-ai.github.io/langgraph/concepts/persistence/
---

# Memory Domain

See `AGENTS.md` ([WV1a-d], [LG1a-d], [FS1b]).

## Purpose

Memory captures conversation history, learned preferences, patterns, and rankings.
We persist canonical memory to local JSON/JSONL and mirror key structures
as Weave objects for versioned tracking and evaluation reuse.

**Sources:**
- https://docs.wandb.ai/weave/guides/tracking/objects
- https://langchain-ai.github.io/langgraph/concepts/persistence/

## Memory Categories

- **ConversationMemory**: Messages and tool observations per thread.
- **PatternMemory**: Learned prompt patterns and effectiveness scores.
- **RankingMemory**: Evaluator rankings and rationale.
- **PreferenceMemory**: User preferences and constraints.

## Storage Boundaries

- **Weave Objects**: Versioned records for cross-run analysis and evaluation.
- **LangGraph Memory Store**: Optional cross-thread retrieval inside the graph.
- **Local JSON/JSONL**: Canonical persistence for MVP file-system storage.
