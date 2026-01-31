---
title: "Project code requirements contract"
usage: "Use whenever creating/modifying files: where to put code, when to create new types, and how to stay SRP/DDD compliant"
description: "Evergreen contract for change decisions, repository structure/naming, and domain model hierarchy; references rule IDs in `AGENTS.md`"
---

# Project Code Requirements Contract

See `AGENTS.md` ([LC1a-d], [MO1a-f], [AR1a-e], [FS1a-g], [ND1a-c], [CC1a-d], [WV1a-d], [LG1a-d]).

## Non-negotiables (applies to every change)

- **SRP/DDD only**: each new type/function has one reason to change ([MO1d], [CC1a]).
- **New feature → new file**; do not grow monoliths ([MO1a], [MO1b]).
- **No edits to >350 LOC files**; first split/retrofit ([LC1c]).
- **Domain is framework-free**; Weave/LangGraph/FastAPI imports do not belong in `domain/` ([CC1d], [FS1d]).
- **No loose dicts**; use Pydantic models and typed protocols ([FS1b]).
- **Use platform primitives**: Weave ops for observability, LangGraph for orchestration ([ID1c]).

## Repository Structure

```
agent-loop/
├── AGENTS.md                    # Canonical rules (hashed, succinct)
├── docs/
│   ├── project-code-requirements.md  # This file
│   ├── api-contracts/
│   │   └── openapi.md
│   ├── contracts/
│   │   ├── weave-integration.md
│   │   ├── langgraph-state.md
│   │   └── llm-providers.md
│   └── domains/
│       ├── agent-loop.md
│       ├── memory.md
│       └── feedback.md
├── src/
│   └── agent_loop/              # Main package
│       ├── __init__.py
│       ├── domain/              # Framework-free business logic
│       │   ├── models/          # Memory, Evaluation
│       │   └── ports/           # Protocols (MemoryStore)
│       ├── adapters/
│       │   ├── llm/             # Factory for LangChain providers
│       │   └── memory/          # Weave-backed memory
│       ├── application/
│       │   └── usecases/        # RunAgentLoop, RecordFeedback
│       ├── api/                 # FastAPI routes
│       │   └── routes/
│       │       └── v1/
│       ├── graph/               # LangGraph orchestration
│       └── mcp/                 # MCP server for TUI consumption
├── pyproject.toml               # UV-managed dependencies
├── .env.example                 # Environment variable template
└── orval.config.ts              # TypeScript generation config
```

## Layer Responsibility Contract

### Domain Layer (`domain/`)

- **Allowed**: Pure Python, Pydantic models, Protocol definitions, business logic
- **Prohibited**: Any framework imports (Weave, LangGraph, FastAPI, OpenAI SDK)
- **Purpose**: Define WHAT the system does, not HOW

### Adapters Layer (`adapters/`)

- **Allowed**: Implement domain protocols, framework-specific code
- **Prohibited**: Business logic, orchestration
- **Subdirectories**:
  - `llm/`: Factory for LangChain chat models
  - `memory/`: Weave-backed memory implementation

### Application Layer (`application/`)

- **Allowed**: Use cases, orchestration of domain + adapters
- **Prohibited**: HTTP concerns, direct framework coupling
- **Purpose**: Coordinate the execution flow

### API Layer (`api/`)

- **Allowed**: FastAPI routes, request/response handling
- **Prohibited**: Business logic
- **Purpose**: HTTP interface, OpenAPI generation

### Graph Layer (`graph/`)

- **Allowed**: LangGraph StateGraph definitions, node functions
- **Prohibited**: Business logic (delegate to application layer)
- **Purpose**: Orchestration state machine

### MCP Layer (`mcp/`)

- **Allowed**: MCP server, tool definitions
- **Prohibited**: Business logic
- **Purpose**: Tool-call interface for TUI consumers

## Naming Conventions

### Domain Models

| Concept | Pattern | Example |
|---------|---------|---------|
| Agent state | `{Agent}State` | `AgentState` |
| Observations | `{Source}Observation` | `ToolObservation`, `FeedbackObservation` |
| Decisions | `{Type}Decision` | `ToolCallDecision`, `ResponseDecision` |
| Memory entries | `{Type}Memory` | `ConversationMemory`, `PatternMemory` |

### Ports (Protocols)

| Concept | Pattern | Example |
|---------|---------|---------|
| LLM provider | `LLMProvider` | *Removed (use BaseChatModel)* |
| Memory store | `MemoryStore` | Weave-backed implementation |
| Tool registry | `ToolRegistry` | Available tool calls |

### Adapters

| Concept | Pattern | Example |
|---------|---------|---------|
| OpenAI Factory | `create_llm_provider` | Factory function |

### Use Cases

| Concept | Pattern | Example |
|---------|---------|---------|
| Run loop | `RunAgentLoopUseCase` | Main orchestration |
| Evaluate | `EvaluateResponseUseCase` | Quality assessment |
| Record feedback | `RecordFeedbackUseCase` | Store evaluations |

## Decision Matrix: Create New File vs Edit Existing

| Situation | MUST do | MUST NOT do |
|-----------|---------|-------------|
| New agent capability | Add new module ([MO1b]) | Add to existing agent file |
| New tool type | Add to tool registry | Create parallel tool system |
| Bug fix | Edit smallest correct owner ([MO1f]) | Create workaround |
| New LLM provider | Update factory | Create new adapter class |

### When adding a function/method is allowed

All must be true:
- Same responsibility as module's existing purpose ([MO1d])
- No new external dependency ([CC1d])
- File stays under 350 LOC ([LC1a])

If any fails, create a new file.

## Integration References

For framework-specific usage and external API details, see:
- `docs/contracts/weave-integration.md`
- `docs/contracts/langgraph-state.md`

## Verification Checklist

Before any commit:

1. [ ] Type check passes: `uv run ty check`
2. [ ] Lint passes: `uv run ruff check`
3. [ ] Format applied: `uv run ruff format`
4. [ ] Tests pass: `uv run pytest`
5. [ ] No file exceeds 350 LOC
6. [ ] Domain layer has no framework imports
