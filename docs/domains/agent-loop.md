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
              AgentState           ▼           (agentloop-state.jsonc)
         ┌────────────────────────────────────────────────────┐
         │                                                    │
         │  ┌───────────────────┐                             │
         └─▶│    AGENT NODE     │◀────────────────────────┐   │
            │ [LLM → AIMessage] │                         │   │
            └────────┬──────────┘                         │   │
                     │     (agentloop-messages.jsonc)     │   │
           ┌─────────┴─────────┐                          │   │
           │   Tool calls?     │                          │   │
           └─────────┬─────────┘                          │   │
              YES    │    NO                              │   │
          ┌──────────┴──────────┐                         │   │
          ▼                     ▼                         │   │
 ┌──────────────┐     ┌───────────────────┐               │   │
 │  TOOLS NODE  │     │  EVALUATOR NODE   │               │   │
 │[→ToolMessage]│     │ [→ Evaluation]    │               │   │
 └──────┬───────┘     └────────┬──────────┘               │   │
        │                      │                          │   │
        │                      ▼                          │   │
        │             ┌───────────────────┐               │   │
        │             │   RANKER NODE     │               │   │
        │             │   [→ Ranking]     │               │   │
        │             └────────┬──────────┘               │   │
        │                      │                          │   │
        │                      ▼                          │   │
        │             ┌───────────────────┐               │   │
        │             │   DECIDER NODE    │               │   │
        │             │   [logic only]    │               │   │
        │             └────────┬──────────┘               │   │
        │                      │                          │   │
        │           ┌──────────┴──────────┐               │   │
        │           │  Complete response? │               │   │
        │           │  or at max iter?    │               │   │
        │           └──────────┬──────────┘               │   │
        │                YES   │   NO                     │   │
        │              ┌───────┴───────┐                  │   │
        │              ▼               └──────────────────┘   │
        │         ┌─────────┐              (iterate)          │
        │         │   END   │                                 │
        │         └────┬────┘                                 │
        │              │                                      │
        └──────────────┼──────────────────────────────────────┘
                       │  (process tool results)
                       ▼
              langgraph-checkpoint.jsonc  (persisted state)
              weave-call.jsonc            (traced operations)
```

## LLM Calls Per Request

| Scenario            | Agent | Evaluator | Ranker | Decider |  Total  |
|---------------------|--------|--------|--------- |-------------------|
| Simple (early exit) |   1    |     1  |      1   |    0    | **3**   |
| With tools (1 iter) |   1+   |     1  |      1   |    0    | **3+**  |
| Max iterations  (5) |   5    |     5  |      5   |    1    | **16**  |

## Domain Concepts

- **AgentState** (`agentloop-state.jsonc`): Typed Pydantic state (task, messages, evaluations, rankings, response).
- **Messages** (`agentloop-messages.jsonc`): HumanMessage, AIMessage, ToolMessage from LangChain.
- **Evaluation**: Assessor output stored in `AgentState.evaluations[]`.
- **Ranking**: Comparative analysis stored in `AgentState.rankings[]`.
- **Early Termination**: Decider exits if agent provides complete response (≥10 chars, no tools).

## Thread Continuity

LangGraph and Weave use **ID-based grouping** (no explicit container objects).

**Terminology**: Weave `call` = LangGraph `step` (see `metadata.step` in checkpoint)

```
thread_id: "thread-abc123"            trace_id: "trace-xyz789"
    │                                     │
    ├── Step 1 (checkpoint)               ├── Call/Step 1 (agent_node)
    ├── Step 2 (checkpoint)               ├── Call/Step 2 (tools_node)
    └── Step 3 (latest)                   └── Call/Step 3 (evaluator_node)
```

- **LangGraph**: `thread_id` groups checkpoints, each with `metadata.step`
- **Weave**: `trace_id` groups calls (steps), root has `parent_id: null`

See `docs/api-contracts/json-examples/README.md#id-based-grouping` for details.
