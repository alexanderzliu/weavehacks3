---
title: "Agent loop domain"
usage: "Core domain definition for loop orchestration and states"
sources:
  - https://docs.langchain.com/oss/python/langgraph/graph-api
  - https://langchain-ai.github.io/langgraph/concepts/persistence/
  - https://docs.wandb.ai/weave/guides/tracking/ops
---

# Agent Loop Domain

See `AGENTS.md` ([AR1a-e], [LG1a-d], [WV1a-d]).

## Purpose

The agent loop coordinates observe → decide → act → evaluate → rank → select → finalize
using a LangGraph `StateGraph` with typed state and checkpointed threads.
Each node is traced with `@weave.op()` for observability.

**Sources:**
- https://docs.langchain.com/oss/python/langgraph/graph-api
- https://langchain-ai.github.io/langgraph/concepts/persistence/
- https://docs.wandb.ai/weave/guides/tracking/ops

## Domain Concepts

- **LoopState**: Typed state passed between nodes (task, messages, observations, decision, response).
- **Decision**: Either tool call, evaluation request, or final response.
- **Observation**: Result of tool execution or evaluator output.
- **Run**: One full loop execution with a `run_id` and optional `thread_id`.

## Thread Continuity

LangGraph uses `thread_id` in the `configurable` config for thread persistence.
This allows returning to prior state for the same conversation.

**Source:** https://langchain-ai.github.io/langgraph/concepts/persistence/
