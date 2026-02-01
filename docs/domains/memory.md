---
title: "Memory domain"
usage: "Defines memory categories and persistence boundaries"
sources:
  - https://docs.wandb.ai/weave/guides/tracking/objects
  - https://langchain-ai.github.io/langgraph/concepts/persistence/
---

# Memory Domain

See `AGENTS.md` ([WV1a-d], [LG1a-d], [FS1b]).

## Memory Flow

```
┌───────────────────────────────────────────────────────────────────────┐
│                         Memory Pipeline                               │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                      Runtime Sources                             │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐  │ │
│  │  │ Messages       │  │ ToolMessage    │  │ Evaluation         │  │ │
│  │  │ (agentloop-    │  │ (agentloop-    │  │ (agentloop-        │  │ │
│  │  │  messages)     │  │  messages)     │  │  state.evaluations)│  │ │
│  │  └───────┬────────┘  └───────┬────────┘  └─────────┬──────────┘  │ │
│  └──────────┼───────────────────┼─────────────────────┼─────────────┘ │
│             │                   │                     │               │
│             └───────────────────┼─────────────────────┘               │
│                                 ▼                                     │
│           ┌─────────────────────────────────────────────────┐         │
│           │            Memory Categorization                │         │
│           │                                                 │         │
│           │  ┌────────────────────────────────────────────┐ │         │
│           │  │ ConversationMemory → langgraph-checkpoint  │ │         │
│           │  │ PatternMemory      → agentloop-memory      │ │         │
│           │  │                      (pattern_entry)       │ │         │
│           │  │ RankingMemory      → agentloop-memory      │ │         │
│           │  │                      (ranking_entry)       │ │         │
│           │  │ PreferenceMemory   → weave-object          │ │         │
│           │  └────────────────────────────────────────────┘ │         │
│           └─────────────────────┬───────────────────────────┘         │
│                                 │                                     │
│        ┌────────────────────────┼─────────────────────────┐           │
│        ▼                        ▼                         ▼           │
│  ┌─────────────────┐    ┌─────────────────┐    ┌────────────────────┐ │
│  │agentloop-memory │    │ weave-object    │    │langgraph-memory    │ │
│  │.jsonc (primary) │    │ .jsonc          │    │-item.jsonc         │ │
│  └─────────────────┘    └─────────────────┘    └────────────────────┘ │
└───────────────────────────────────────────────────────────────────────┘
```

## Purpose

Memory captures conversation history, learned preferences, patterns, and rankings.
We persist canonical memory to local JSON/JSONL (`agentloop-memory.jsonc`) and
mirror key structures as Weave objects for versioned tracking.

## Memory Categories

- **ConversationMemory** → `langgraph-checkpoint.jsonc`: Messages and observations per thread.
  - Persisted via LangGraph checkpointer (default: `InMemorySaver`, ephemeral).
  - For durable persistence, inject `SqliteSaver` or `PostgresSaver` into `AgentLoop`.
- **PatternMemory** → `agentloop-memory.jsonc` (`pattern_entry`): Learned prompt patterns.
- **RankingMemory** → `agentloop-memory.jsonc` (`ranking_entry`): Evaluator rankings.
- **PreferenceMemory** → `weave-object.jsonc`: User preferences and constraints.

## Storage Boundaries

All storage uses **ID-based grouping** (no explicit container objects):

```
thread_id: "thread-abc123"         namespace: ["user-123", "patterns"]
    │                                  │
    ├── Checkpoint (conversation)      ├── langgraph-memory-item (pattern A)
    └── Checkpoint (latest)            └── langgraph-memory-item (pattern B)
```

- **Local JSON** (`agentloop-memory.jsonc`): Canonical persistence for MVP.
- **Weave Objects** (`weave-object.jsonc`): Versioned records, grouped by `ref`.
- **LangGraph MemoryStore** (`langgraph-memory-item.jsonc`): Grouped by `namespace[]`.

See `docs/api-contracts/json-examples/README.md#id-based-grouping` for details.
