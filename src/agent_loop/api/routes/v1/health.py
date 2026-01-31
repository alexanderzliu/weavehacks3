"""Health check routes (v1).

Sources:
    - FastAPI Routing: https://fastapi.tiangolo.com/tutorial/bigger-applications/
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/v1", tags=["health"])


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok", version="0.1.0")


@router.get("/")
async def root() -> dict[str, str]:
    """Root endpoint for v1."""
    return {"message": "agent-loop API", "docs": "/v1/docs"}
