# JSON Schema Examples

This directory contains canonical JSON schema examples for all object types used in agent-loop.

## Naming Convention

| Prefix | Source | Description |
|--------|--------|-------------|
| `weave-*.jsonc` | W&B Weave | Objects defined by Weave SDK |
| `langgraph-*.jsonc` | LangGraph | Objects defined by LangGraph SDK |
| `agentloop-*.jsonc` | agent-loop | Objects defined by this library (may reference default objects) |

## Weave Objects

| File | Description | Source |
|------|-------------|--------|
| `weave-object.jsonc` | Generic versioned object | [Weave Objects](https://docs.wandb.ai/weave/guides/tracking/objects) |
| `weave-dataset.jsonc` | Evaluation dataset | [Weave Datasets](https://docs.wandb.ai/weave/guides/core-types/datasets) |
| `weave-evaluation.jsonc` | Evaluation run | [Weave Evaluations](https://docs.wandb.ai/weave/guides/core-types/evaluations) |
| `weave-call.jsonc` | Traced operation | [Weave Ops](https://docs.wandb.ai/weave/guides/tracking/ops) |
| `weave-model.jsonc` | Versioned model | [Weave Models](https://docs.wandb.ai/weave/guides/core-types/models) |

## LangGraph Objects

| File | Description | Source |
|------|-------------|--------|
| `langgraph-state.jsonc` | Graph state | [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api#state) |
| `langgraph-checkpoint.jsonc` | StateSnapshot | [Persistence](https://langchain-ai.github.io/langgraph/concepts/persistence/#checkpoints) |
| `langgraph-memory-item.jsonc` | Memory store item | [Memory Store](https://langchain-ai.github.io/langgraph/concepts/persistence/#memory-store) |

## Agent-Loop Objects

| File | Description | Python Module |
|------|-------------|---------------|
| `agentloop-state.jsonc` | AgentState (Pydantic) | `graph/state.py` |
| `agentloop-messages.jsonc` | Message structures (LangChain default) | `langchain_core.messages` |
| `agentloop-memory.jsonc` | Memory structures | `domain/models/memory.py` |

## Usage

These files serve as:

1. **Documentation**: Reference for object structure
2. **Type contracts**: Canonical definitions for consumers
3. **Testing fixtures**: Base data for tests
4. **TypeScript generation**: Input for type generators

## Storage Strategy

Based on the canonical object types:

| What to Store | Where | Object Type |
|---------------|-------|-------------|
| Conversation history | Local JSON/JSONL + LangGraph Checkpointer | `langgraph-checkpoint.jsonc` |
| Learned patterns | Local JSON/JSONL + LangGraph Memory Store | `langgraph-memory-item.jsonc` |
| Observations/traces | Weave | `weave-call.jsonc` |
| Feedback | Local JSON/JSONL + Weave | `agentloop-memory.jsonc` |
| Datasets | Weave | `weave-dataset.jsonc` |

**Key insight**: Local JSON/JSONL is the canonical store; Weave and LangGraph provide observability and thread state.
