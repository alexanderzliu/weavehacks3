# agent-loop

Self-improving agentic abstraction with Weave observability and LangGraph orchestration.

## Overview

A clean, minimal abstraction for building self-improving AI agents that:
- **Research**: Execute tasks using flexible tool calls
- **Observe**: Track all actions/results via Weave tracing
- **Evaluate**: Sub-agents assess response quality
- **Learn**: Rank/store feedback for continuous improvement
- **Decide**: Orchestrator determines optimal responses

```
┌─────────────────────────────────────────────────────────────┐
│                     Orchestrator Graph                      │
│  ┌─────────┐    ┌─────────┐    ┌───────────┐                │
│  │  Agent  │───▶│  Tools  │───▶│ Evaluator │                │
│  └─────────┘    └─────────┘    └───────────┘                │
│       │                              │                      │
│       │         ┌─────────┐          │                      │
│       └────────▶│ Ranker  │◀─────────┘                      │
│                 └─────────┘                                 │
│                      │                                      │
│                 ┌─────────┐                                 │
│                 │ Decider │ ──▶ Response / Next Iteration   │
│                 └─────────┘                                 │
└─────────────────────────────────────────────────────────────┘
```

## Domain Architecture

JSON schemas: `docs/api-contracts/json-examples/`

**ID-Based Grouping**: LangGraph and Weave use IDs (not container objects) to group related records:
- `thread_id` groups LangGraph checkpoints
- `trace_id` groups Weave calls

```
┌───────────────────────────────────────────────────────────────────────────┐
│                          AGENT-LOOP DOMAIN MAP                            │
├───────────────────────────────────────────────────────────────────────────┤
│  Grouping: thread_id (LangGraph) | trace_id (Weave)                       │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  AGENT LOOP DOMAIN (docs/domains/agent-loop.md)                     │  │
│  │  State: agentloop-state.jsonc | Messages: agentloop-messages.jsonc  │  │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────────┐  │  │
│  │  │  Agent   │──▶│  Tools   │──▶│Evaluator │──▶│ Ranker ──▶Decider│  │  │
│  │  │[AIMessage]   │[ToolMsg] │   │[Eval]    │   │ [Ranking]        │  │  │
│  │  └──────────┘   └──────────┘   └────┬─────┘   └────────┬─────────┘  │  │
│  │  Traces: weave-call.jsonc | Persist: langgraph-checkpoint.jsonc     │  │
│  └─────────────────────────────────────┼──────────────────┼────────────┘  │
│                                        │                  │               │
│            ┌───────────────────────────┴──────────────────┘               │
│            ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  FEEDBACK DOMAIN (docs/domains/feedback.md)                         │  │
│  │  ┌───────────────────┐   ┌───────────────────┐   ┌───────────────┐  │  │
│  │  │ Evaluation        │──▶│ RankingEntry      │──▶│ Decider Input │  │  │
│  │  │ (agentloop-state  │   │ (agentloop-memory │   │ (next action) │  │  │
│  │  │  .evaluations[])  │   │  .ranking_entry)  │   │               │  │  │
│  │  └────────┬──────────┘   └───────────────────┘   └───────────────┘  │  │
│  │  Persist: weave-evaluation.jsonc                                    │  │
│  └───────────┼─────────────────────────────────────────────────────────┘  │
│              │                                                            │
│              ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  MEMORY DOMAIN (docs/domains/memory.md)                             │  │
│  │  Grouping: thread_id | namespace[] | weave ref                      │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │  │
│  │  │ Conversation    │  │ Pattern         │  │ Ranking+Preference  │  │  │
│  │  │ (langgraph-     │  │ (agentloop-     │  │ (agentloop-memory   │  │  │
│  │  │  checkpoint)    │  │  memory.pattern)│  │  .ranking_entry)    │  │  │
│  │  └───────┬─────────┘  └───────┬─────────┘  └──────────┬──────────┘  │  │
│  │          └────────────────────┼───────────────────────┘             │  │
│  │                               ▼                                     │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────────┐ │  │
│  │  │agentloop-memory │  │ weave-object    │  │langgraph-memory-item │ │  │
│  │  │.jsonc (primary) │  │ .jsonc          │  │.jsonc                │ │  │
│  │  └─────────────────┘  └─────────────────┘  └──────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

## Getting Started

### 1. Clone & Setup
```bash
git clone https://github.com/your-org/agent-loop.git
cd agent-loop
uv sync --dev               # Install dependencies (incl. dev tools)
cp .env.example .env        # Add your API keys (OPENAI_API_KEY, WANDB_API_KEY)
```

### 2. Validation & Hooks
We use `prek` for pre-push hooks that run our full validation gate (`make validate`).
Hooks are configured in `.config/pre-commit-config.yaml` and run automatically on push.

```bash
# Verify everything manually
make validate

# Auto-fix formatting/linting
make fix
```

## Running the Application

### Python Library
```python
import asyncio

from agent_loop import AgentLoop

async def main() -> None:
    agent = AgentLoop()
    result = await agent.arun("Analyze AI trends")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

### REST API
```bash
# Start server
uv run agent-loop

# Usage
curl -X POST http://localhost:8000/v1/loop/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Hello"}' | jq -r '"Response: \(.response)\n\nEvaluation:\n\(.evaluations[0].evaluation)"'
```

### OpenAPI
Docs are served at `http://localhost:8000/v1/docs` and the spec at
`http://localhost:8000/v1/openapi.json`.

### MCP Server (Claude Code)
```bash
# Start MCP server
uv run agent-loop-mcp --stdio
```

## Development Workflow

- **Package Manager**: `uv` (no pip/poetry needed)
- **Commands**:
  - `make validate`: Run all checks (Format, Lint, Typecheck, Test)
  - `make fix`: Auto-format and fix lint errors
  - `make test`: Run unit tests
- **Architecture**: See `AGENTS.md` and `docs/` for strict coding rules.

## Tech Stack
- **LangGraph**: Orchestration & State
- **Weave**: Observability & Memory
- **FastAPI**: REST Interface
- **Pydantic**: Data Validation
- **Ruff/Ty**: Linting & Type Checking
