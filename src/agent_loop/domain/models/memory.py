"""Memory models for persistence and learning.

Defines structures for conversation history, patterns, and feedback.
These are persisted via Weave objects. See [WV1b].

JSON Schema: docs/api-contracts/json-examples/agentloop-memory.jsonc

Sources:
    - Weave Objects: https://docs.wandb.ai/weave/guides/tracking/objects
    - LangGraph Memory Store: https://langchain-ai.github.io/langgraph/concepts/persistence/#memory-store
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(UTC)


class PatternEntry(BaseModel):
    """A learned pattern from past interactions.

    Patterns capture what works well and what doesn't.
    """

    pattern_id: str = Field(description="Unique pattern identifier")
    pattern_type: str = Field(description="Type: prompt, tool_usage, response_style")
    description: str = Field(description="Human-readable pattern description")
    effectiveness_score: float = Field(ge=0.0, le=1.0, description="How well this works")
    usage_count: int = Field(default=0, description="How often this pattern was used")
    last_used: datetime = Field(default_factory=_utc_now)
    examples: list[str] = Field(default_factory=list, description="Example usages")


class FeedbackEntry(BaseModel):
    """Feedback on a specific response or action."""

    feedback_id: str = Field(description="Unique feedback identifier")
    thread_id: str = Field(description="Thread this feedback relates to")
    target_type: str = Field(description="What was evaluated: response, tool_call, decision")
    target_content: str = Field(description="The content that was evaluated")
    quality_score: float = Field(ge=0.0, le=1.0, description="Overall quality score")
    reasoning: str = Field(description="Why this score was given")
    improvements: list[str] = Field(default_factory=list, description="Suggested improvements")
    evaluator: str = Field(description="Which agent/system provided this feedback")
    timestamp: datetime = Field(default_factory=_utc_now)


class RankingEntry(BaseModel):
    """Ranking of responses for comparative learning."""

    ranking_id: str = Field(description="Unique ranking identifier")
    task_summary: str = Field(description="Summary of the task being ranked")
    responses: list[str] = Field(description="The responses being ranked, best first")
    scores: list[float] = Field(description="Scores for each response")
    criteria_used: list[str] = Field(description="Criteria used for ranking")
    ranker_notes: str = Field(description="Notes from the ranking agent")
    timestamp: datetime = Field(default_factory=_utc_now)
