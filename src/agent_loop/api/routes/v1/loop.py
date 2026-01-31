"""Loop routes (v1).

REST API for running the agent loop.

Sources:
    - FastAPI Routing: https://fastapi.tiangolo.com/tutorial/bigger-applications/
"""

from fastapi import APIRouter, HTTPException
from langchain_core.messages import ToolMessage
from pydantic import BaseModel, Field

from agent_loop.application.agent import AgentLoop

router = APIRouter(prefix="/v1/loop", tags=["loop"])


class RunLoopRequest(BaseModel):
    """Request to run the agent loop."""

    task: str = Field(description="The task or query for the agent")
    thread_id: str | None = Field(default=None, description="Thread ID for continuity")
    max_iterations: int = Field(default=5, ge=1, le=20, description="Max iterations")
    provider: str = Field(default="openai", description="LLM provider")
    model: str | None = Field(default=None, description="Model name")


class ObservationResponse(BaseModel):
    """Observation from the agent loop."""

    source: str
    content: str
    timestamp: str = Field(default="")


class EvaluationResponse(BaseModel):
    """Evaluation from the agent loop."""

    iteration: int
    evaluation: str


class RunLoopResponse(BaseModel):
    """Response from running the agent loop."""

    thread_id: str
    response: str
    iterations: int
    observations: list[ObservationResponse]
    evaluations: list[EvaluationResponse]


_agents: dict[str, AgentLoop] = {}


def _get_agent(provider: str, model: str | None) -> AgentLoop:
    """Get or create an agent instance."""
    key = f"{provider}:{model or 'default'}"
    if key not in _agents:
        _agents[key] = AgentLoop(provider=provider, model=model)
    return _agents[key]


@router.post("/run", response_model=RunLoopResponse)
async def run_loop(request: RunLoopRequest) -> RunLoopResponse:
    """Execute the agent loop with the provided task."""
    try:
        agent = _get_agent(request.provider, request.model)
        result = await agent.arun(
            task=request.task,
            thread_id=request.thread_id,
            max_iterations=request.max_iterations,
        )

        observations: list[ObservationResponse] = []
        for msg in result.state.messages:
            if isinstance(msg, ToolMessage):
                observations.append(
                    ObservationResponse(
                        source=msg.name or "unknown",
                        content=str(msg.content),
                    )
                )

        evaluations = [
            EvaluationResponse(
                iteration=e.iteration,
                evaluation=e.evaluation,
            )
            for e in result.state.evaluations
        ]

        return RunLoopResponse(
            thread_id=result.thread_id,
            response=result.response,
            iterations=result.iterations,
            observations=observations,
            evaluations=evaluations,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
