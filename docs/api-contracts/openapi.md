---
title: "OpenAPI and consumer contract"
usage: "How to expose the API for various consumers"
sources:
  - https://fastapi.tiangolo.com/tutorial/metadata/
  - https://orval.dev/reference/configuration/output
  - https://modelcontextprotocol.github.io/python-sdk/
  - https://github.com/modelcontextprotocol/python-sdk/blob/main/README.md
---

# OpenAPI and Consumer Contract

See `AGENTS.md` ([AP1a-d]).

## Consumer Patterns

agent-loop supports three consumption patterns:

1. **REST API** (FastAPI): For web frontends and Python backends
2. **MCP Server**: For TUI tools like Claude Code
3. **Python Package**: For direct library import

## FastAPI REST API

### Endpoint Design

```python
# api/routes/v1/loop.py
from fastapi import APIRouter

router = APIRouter(prefix="/v1/loop", tags=["loop"])

@router.post("/run")
async def run_loop(request: RunLoopRequest) -> RunLoopResponse:
    """Execute agent loop with provided task."""
    ...
```

### Request/Response Models

```python
# api/models.py
from pydantic import BaseModel

class RunLoopRequest(BaseModel):
    """Request to run the agent loop."""
    task: str
    thread_id: str | None = None
    max_iterations: int = 5
    provider: str = "openai"
    model: str | None = None

class RunLoopResponse(BaseModel):
    """Response from agent loop."""
    thread_id: str
    response: str
    observations: list[Observation]
    iterations: int
    evaluations: list[EvaluationSummary]
```

### OpenAPI Generation

FastAPI serves OpenAPI by default at `/openapi.json` and docs at `/docs` and `/redoc`.
If you override `openapi_url`, keep Orval in sync with the new URL.

**Source:** https://fastapi.tiangolo.com/tutorial/metadata/

```python
# api/main.py
from fastapi import FastAPI

app = FastAPI(
    title="agent-loop",
    version="0.1.0",
    description="Self-improving agentic abstraction",
)
```

## Orval TypeScript Generation

### Configuration

```typescript
// orval.config.ts
import { defineConfig } from "orval";

export default defineConfig({
  agentLoop: {
    input: {
      target: "http://localhost:8000/openapi.json",
    },
    output: {
      mode: "tags-split",
      target: "./generated/api",
      schemas: "./generated/models",
      client: "fetch",
    },
  },
});
```

**Source:** https://orval.dev/reference/configuration/output

## MCP Server

Define the MCP server once, then expose it via:
- **Streamable HTTP** mounted inside FastAPI, and
- **Stdio** for CLI/TUI tools

**Sources:**
- https://modelcontextprotocol.github.io/python-sdk/
- https://github.com/modelcontextprotocol/python-sdk/blob/main/README.md

### Embedded in FastAPI (Streamable HTTP)

```python
# mcp/http.py
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("agent-loop")

app = FastAPI()
app.mount("/mcp", mcp.streamable_http_app())
```

If mounting into an existing ASGI app, run the MCP session manager in the app lifespan.

**Source:** https://github.com/modelcontextprotocol/python-sdk/blob/main/README.md

### Stdio Entrypoint

```python
# mcp/cli.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("agent-loop")

if __name__ == "__main__":
    mcp.run()  # Use standard MCP transports like stdio
```

```bash
# Start stdio server
uv run mcp run mcp/cli.py
```

## Python Package API

```python
from agent_loop import AgentLoopClient

client = AgentLoopClient()
result = client.run(task="Research prompt quality")
```

## JSON Example Contracts

Reference JSON examples live in `docs/api-contracts/json-examples/` and define
canonical shapes for Weave, LangGraph, and agent-loop objects.
