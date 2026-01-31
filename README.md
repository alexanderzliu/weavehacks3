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
from agent_loop import AgentLoop
agent = AgentLoop()
result = await agent.arun("Analyze AI trends")
```

### REST API
```bash
# Start server
uv run agent-loop

# Usage
curl -X POST http://localhost:8000/v1/loop/run \
  -H "Content-Type: application/json" \
  -d '{"task": "Hello"}'
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
