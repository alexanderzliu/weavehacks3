"""Loop routes (v1).

REST API for running the agent loop.

Sources:
    - FastAPI Routing: https://fastapi.tiangolo.com/tutorial/bigger-applications/
    - FastAPI Dependency Injection: https://fastapi.tiangolo.com/tutorial/dependencies/
"""

import openai
import weave
from fastapi import APIRouter, Depends, Request
from langchain_core.messages import ToolMessage
from pydantic import BaseModel, Field

from agent_loop.application.agent import AgentLoop
from agent_loop.domain.exceptions import AuthenticationError, InvalidInputError
from agent_loop.graph.state import DEFAULT_MAX_ITERATIONS

router = APIRouter(prefix="/v1/loop", tags=["loop"])

# Weave trace display name [WV1a]
TRACE_NAME_RUN_LOOP = "POST /v1/loop/run"


def get_agent(request: Request) -> AgentLoop:
    """Dependency to get the shared agent from app.state.

    The agent is created once in lifespan and reused for all requests.
    LangGraph's compiled graph is thread-safe for concurrent invocations.
    """
    return request.app.state.agent


class RunLoopRequest(BaseModel):
    """Request to run the agent loop.

    Provider and model are configured at application startup via environment
    variables (AGENT_PROVIDER, AGENT_MODEL). This ensures a single compiled
    graph is reused for all requests.
    """

    task: str = Field(description="The task or query for the agent")
    thread_id: str | None = Field(default=None, description="Thread ID for continuity")
    max_iterations: int = Field(
        default=DEFAULT_MAX_ITERATIONS, ge=1, le=20, description="Max iterations"
    )


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
    response: str | None = Field(description="Agent response, None if no response generated")
    iterations: int
    observations: list[ObservationResponse]
    evaluations: list[EvaluationResponse]


@router.post("/run", response_model=RunLoopResponse)
@weave.op(call_display_name=TRACE_NAME_RUN_LOOP)
async def run_loop(
    request: RunLoopRequest,
    agent: AgentLoop = Depends(get_agent),
) -> RunLoopResponse:
    """Execute the agent loop with the provided task.

    The agent is injected via FastAPI dependency injection from app.state.
    Domain exceptions bubble up to registered exception handlers.
    """
    try:
        result = await agent.arun(
            task=request.task,
            thread_id=request.thread_id,
            max_iterations=request.max_iterations,
        )
    except openai.AuthenticationError as exc:
        raise AuthenticationError(
            "API key missing or invalid. Check your provider configuration.",
            cause=exc,
        ) from exc
    except ValueError as exc:
        raise InvalidInputError(str(exc), cause=exc) from exc

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
