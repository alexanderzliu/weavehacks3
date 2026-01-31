"""Graph state definition for LangGraph.

Defines the Pydantic state used by LangGraph.
See [LG1b] for typed state requirements.

Contract: docs/contracts/langgraph-state.md
"""

from typing import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class Evaluation(BaseModel):
    """Evaluation result from the evaluator agent."""

    iteration: int = Field(description="Loop iteration number")
    evaluation: str = Field(description="Content of the evaluation")


class Ranking(BaseModel):
    """Ranking result from the ranker agent."""

    iteration: int = Field(description="Loop iteration number")
    ranking: str = Field(description="Content of the ranking")


class AgentState(BaseModel):
    """State for the agent loop.

    Uses Pydantic for validation and LangGraph's add_messages reducer.
    """

    # Core conversation history with reducer
    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)

    # Task context
    task: str = Field(description="Original user task")

    # Loop control
    response: str | None = Field(default=None, description="Final response")
    iteration: int = Field(default=0, description="Current loop iteration")
    max_iterations: int = Field(default=5, description="Max iterations allowed")

    # Sub-agent outputs
    evaluations: list[Evaluation] = Field(default_factory=list, description="Evaluator feedback")
    rankings: list[Ranking] = Field(default_factory=list, description="Ranker output")
