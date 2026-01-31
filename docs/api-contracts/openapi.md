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
# api/routes/v1/loop.py
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
    observations: list[ObservationResponse]
    iterations: int
    evaluations: list[EvaluationResponse]
```

### OpenAPI Generation

FastAPI serves OpenAPI at `/v1/openapi.json` and docs at `/v1/docs`.

**Source:** https://fastapi.tiangolo.com/tutorial/metadata/

## Orval TypeScript Generation

### Configuration

```typescript
// orval.config.ts
import { defineConfig } from "orval";

export default defineConfig({
  agentLoop: {
    input: {
      target: "http://localhost:8000/v1/openapi.json",
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
app.mount("/v1/mcp", mcp.streamable_http_app())
```

### Stdio Entrypoint

```python
# mcp/server.py
from mcp.server import Server

async def run_server():
    # ... setup stdio transport
    pass

if __name__ == "__main__":
    asyncio.run(run_server())
```

```bash
# Start stdio server
uv run agent-loop-mcp --stdio
```

## Python Package API

```python
from agent_loop import AgentLoop

agent = AgentLoop()
result = await agent.arun("Research prompt quality")
```

## JSON Example Contracts

Reference JSON examples live in `docs/api-contracts/json-examples/` and define
canonical shapes for Weave, LangGraph, and agent-loop objects.
