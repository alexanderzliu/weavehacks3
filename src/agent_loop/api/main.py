"""FastAPI application entry point.

Provides REST API for agent-loop. See [AP1a].

Sources:
    - FastAPI: https://fastapi.tiangolo.com/
    - CORS Middleware: https://fastapi.tiangolo.com/tutorial/cors/
    - Uvicorn: https://www.uvicorn.org/
    - python-dotenv: https://saurabh-kumar.com/python-dotenv/
"""

# Load environment variables FIRST, before any other imports
# This ensures env vars are available when modules read them at import time
from dotenv import load_dotenv

load_dotenv()

import os  # noqa: E402
from collections.abc import AsyncGenerator  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402

import uvicorn  # noqa: E402
import weave  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from agent_loop.api.exception_handlers import register_exception_handlers  # noqa: E402
from agent_loop.api.routes import health_router, loop_router  # noqa: E402

# Weave project name from env or default
_WEAVE_PROJECT = os.getenv("WEAVE_PROJECT", "agent-loop")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup: Initialize Weave once for the application
    weave.init(_WEAVE_PROJECT)
    yield
    # Shutdown


app = FastAPI(
    title="agent-loop",
    version="0.1.0",
    description="Self-improving agentic abstraction with Weave and LangGraph",
    openapi_url="/v1/openapi.json",
    docs_url="/v1/docs",
    redoc_url="/v1/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers (RFC 9457)
register_exception_handlers(app)

# Include routers
app.include_router(health_router)
app.include_router(loop_router)


def main() -> None:
    """Run the server."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(
        "agent_loop.api.main:app",
        host=host,
        port=port,
        reload=True,
    )


if __name__ == "__main__":
    main()
