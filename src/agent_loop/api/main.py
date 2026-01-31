"""FastAPI application entry point.

Provides REST API for agent-loop. See [AP1a].

Sources:
    - FastAPI: https://fastapi.tiangolo.com/
    - CORS Middleware: https://fastapi.tiangolo.com/tutorial/cors/
    - Uvicorn: https://www.uvicorn.org/
    - python-dotenv: https://saurabh-kumar.com/python-dotenv/
"""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_loop.api.routes import health_router, loop_router

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
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
