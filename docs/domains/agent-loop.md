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

## Graph Flow

```
                         ┌─────────┐
                         │  START  │
                         └────┬────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │    AGENT NODE     │ ←──────────────────┐
                    │    [LLM call]     │                    │
                    └────────┬──────────┘                    │
                             │                               │
                   ┌─────────┴─────────┐                     │
                   │   Tool calls?     │                     │
                   └─────────┬─────────┘                     │
                      YES    │    NO                         │
                  ┌──────────┴──────────┐                    │
                  ▼                     ▼                    │
         ┌──────────────┐     ┌───────────────────┐          │
         │  TOOLS NODE  │     │  EVALUATOR NODE   │          │
         │  [execute]   │     │  [LLM call]       │          │
         └──────┬───────┘     └────────┬──────────┘          │
                │                      │                     │
                │                      ▼                     │
                │             ┌───────────────────┐          │
                │             │   RANKER NODE     │          │
                │             │   [LLM call]      │          │
                │             └────────┬──────────┘          │
                │                      │                     │
                │                      ▼                     │
                │             ┌───────────────────┐          │
                │             │   DECIDER NODE    │          │
                │             │   [logic only]    │          │
                │             └────────┬──────────┘          │
                │                      │                     │
                │           ┌──────────┴──────────┐          │
                │           │  Complete response? │          │
                │           │  or at max iter?    │          │
                │           └──────────┬──────────┘          │
                │                YES   │   NO                │
                │              ┌───────┴───────┐             │
                │              ▼               └─────────────┘
                │         ┌─────────┐
                └────────▶│   END   │
                          └─────────┘
```

## LLM Calls Per Request

| Scenario | Agent | Evaluator | Ranker | Decider | Total |
|----------|-------|-----------|--------|---------|-------|
| Simple (early exit) | 1 | 1 | 1 | 0 | **3** |
| With tools (1 iter) | 1+ | 1 | 1 | 0 | **3+** |
| Max iterations (5) | 5 | 5 | 5 | 1 | **16** |

## Domain Concepts

- **AgentState**: Typed Pydantic state (task, messages, evaluations, rankings, response).
- **Early Termination**: Decider exits if agent provides complete response (≥10 chars, no tools).
- **Observation**: Result of tool execution, stored as ToolMessage.
- **Evaluation**: Assessor output analyzing progress, quality, efficiency.
- **Ranking**: Comparative analysis across iterations.

## Thread Continuity

LangGraph uses `thread_id` in the `configurable` config for thread persistence.
This allows returning to prior state for the same conversation.

**Source:** https://langchain-ai.github.io/langgraph/concepts/persistence/
